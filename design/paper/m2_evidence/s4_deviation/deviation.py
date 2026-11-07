r"""論文 M2 s4：一種模型偏差——用名義模型設計與校正、用有 MMI 分光誤差的「硬體」驗收，結果還一致嗎？

用途：M1 的設計、校正與驗收都用同一個模型（含 MMI 損耗的 B7），驗收通過可能只是「模型和自己一致」。本步只加一種偏差：
  硬體每顆 MMI（14 顆）的分光比有誤差：H(ε)＝[[cos(π/4+ε), i sin(π/4+ε)], [i sin(π/4+ε), cos(π/4+ε)]]，ε ~ N(0, SIGMA_E)
  （SIGMA_E＝0.03 rad 約等於分光比 50% ± 3%；ε 即報告中的 ε_MMI）。設計者不知道 ε，只有名義模型。
  每個硬體實例先抽一組 ε（14 個），AND4 與 XOR2 都在同一組硬體上比較（審查 R1）。比較三種狀態，都在硬體上驗收：
  1. 名義相位：M1 s2 依消光比殘留、以名義模型重新求的 14 個相位，直接用在硬體上。
  2. 名義校正後：M1 s3 的動態校正迴路（擺動量測在硬體上做，估計與補償都用名義模型）跑 LOOPS 次。
     硬體上沒有輸入漂移，迴路看到的「漂移」全是模型偏差造成的；它只能調 7 個 φ。
  3. 已知硬體的參考解（靜態最佳）：已知 ε、在硬體模型上重新求 14 個相位，只最佳化靜態 margin——相當於完美辨識硬體，
     不代表量測型重解的結果，也不保證窗內 margin 最大（審查 R4）。
  每種狀態算：硬體上的靜態 margin、名義模型「以為」的 margin（校正迴路的自我評估）、硬體上 23 ps 窗內的 margin，
  以及窗存在所需的 P_u（M1 s1 的雜訊模型），與系統預算比較。窗內 margin 的條件與 M1 s5 聯合驗收相同（審查 R5）：
  消光比規格、skew 20 ps 最差角落、每路相位殘差 −δ_det／0／＋δ_det、7 個 heater 同時擺動 ±ε_d；
  相位與擺動的組合先以硬體上的靜態 margin 篩出最差 N_SCREEN 組，再跑所有 skew 角落的時域計算。
  兩個代表函數 AND4、XOR2，N_INST 個硬體實例（固定種子），以 6 個 worker 平行（每個實例一個工作，BLAS 單執行緒）。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、s1_budget/out/budget.json、s2_interface/out/interface_v2.json、
      s3_tracking/out/tracking.json、s5_assess/out/assess.json；時域模型沿用 s4_window/window.py，雜訊模型沿用 s1_budget/budget.py。
輸出：design/paper/m2_evidence/s4_deviation/out/deviation.json。
執行：.\lab design\paper\m2_evidence\s4_deviation\deviation.py（6 個 worker 約 25 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
M1 = Path(__file__).resolve().parents[2] / "m1_timing"
sys.path.insert(0, str(M1))
sys.path.insert(0, str(M1 / "s4_window"))
sys.path.insert(0, str(M1 / "s1_budget"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import budget as B1                                                  # noqa: E402  s1 的雜訊模型
import paths                                                         # noqa: E402
import window as W                                                   # noqa: E402  s4 的時域模型
from common.mzi import B7_OPS, READ, embed                           # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import A2, b7 as b7_nom, load_phases                      # noqa: E402

STEP = "paper/m2_evidence/s4_deviation"
BASE = "paper/m1_timing"
FUNCS = ("AND4", "XOR2")
SIGMA_E = 0.03
N_INST = 32
LOOPS = 3
SKEW = 20
SEED = 4400
N_SCREEN = 2
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
EDGE_DB = 0.05                                                       # 所需 P_u 與預算相差在此以內者列為「邊界」
STATES = ("nominal", "loop", "oracle")


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def He(e):
    c, s = math.cos(math.pi / 4 + e), math.sin(math.pi / 4 + e)
    return np.array([[c, 1j * s], [1j * s, c]])


def T_hw(eps2, th, ph):
    """硬體 MZI：第二顆 MMI · diag(e^{iθ},1) · 第一顆 MMI · diag(e^{iφ},1)；eps2＝(ε1, ε2)。"""
    return He(eps2[1]) @ np.diag([np.exp(1j * th), 1.0]) @ He(eps2[0]) @ np.diag([np.exp(1j * ph), 1.0])


def b7_hw(eps):
    def f(theta, phi):
        U = np.eye(5, dtype=complex)
        for k, ((rail, _), th, ph) in enumerate(zip(B7_OPS, theta, phi)):
            U = embed(A2 * T_hw(eps[k], th, ph), rail, 5) @ U
        return U
    return f


def propagate_hw(eps):
    """與 window.propagate 相同的逐欄傳遞，只把每顆 MZI 換成硬體矩陣。"""
    def prop(x, theta, phi, geo):
        y = [W.delay(x[:, r], geo["fan_in_ps"][r]) for r in range(5)]
        for col in geo["cols"]:
            busy = set()
            for k, r in col:
                t = A2 * T_hw(eps[k], theta[k], phi[k])
                a, b = y[r], y[r + 1]
                y[r], y[r + 1] = t[0, 0] * a + t[0, 1] * b, t[1, 0] * a + t[1, 1] * b
                busy |= {r, r + 1}
            for r in busy:
                y[r] = W.delay(y[r], geo["extra_ps"])
        return np.stack([W.delay(y[r], geo["fan_out_ps"][r]) for r in range(5)], axis=1)
    return prop


def drift(d, cols):
    v = np.zeros(4)
    v[list(cols)] = d
    return np.diag(np.exp(1j * np.append(v, 0.0)))


def margin(bf, th, ph, v, s, D=None):
    U = bf(th, ph) if D is None else bf(th, ph) @ D
    return float(np.min(s * deltas(U, v, READ)))


def measure(bf, th, ph, Vd, h=1e-5):
    """隨機資料下 5 個輸出的平均功率，與 7 個 φ 的擺動斜率（同步偵測），攤平。"""
    pb = lambda p: np.mean(np.abs(Vd @ bf(th, p).T) ** 2, axis=0)    # noqa: E731
    g = [(pb(ph + h * e) - pb(ph - h * e)) / (2 * h) for e in np.eye(7)]
    return np.concatenate([pb(ph), np.array(g).T.ravel()])


def estimate(meas, model, cols, iters=15):
    d = np.zeros(len(cols))
    for _ in range(iters):
        f0 = model(d)
        J = np.array([(model(d + e) - model(d - e)) / 2e-4 for e in np.eye(len(cols)) * 1e-4]).T
        step = np.linalg.lstsq(J, meas - f0, rcond=None)[0]
        d = d + step
        if np.max(np.abs(step)) < 1e-9:
            break
    return d


def resolve_phi(bf, th, ph0, D, v, s):
    def cons(z):
        return s * deltas(bf(th, z[:-1]) @ D, v, READ) - z[-1]
    z0 = np.append(ph0, margin(bf, th, ph0, v, s, D))
    r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)], options=dict(maxiter=400, ftol=1e-12))
    return r.x[:-1]


def resolve_all(bf, x0, v, s):
    def cons(z):
        return s * deltas(bf(z[:7], z[7:14]), v, READ) - z[-1]
    z0 = np.append(x0, margin(bf, x0[:7], x0[7:], v, s))
    r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)], options=dict(maxiter=400, ftol=1e-10))
    return r.x[:7], r.x[7:14]


_CTX = None


def context():
    """各行程共用的設定：名義設計（與 M1 s4／s5 相同，ψ 取重新求相位後靜態最差者）、時域模型、雜訊模型、預算。"""
    global _CTX
    if _CTX is not None:
        return _CTX
    ph = load_phases()
    s1, s2, s3, s5 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json"), \
        load("s5_assess", "assess.json")
    t = s1["timing"]
    a0 = 10 ** (-s2["er_required_db"] / 20)
    wp = B1.worst_patterns()
    fns = {}
    for fn in FUNCS:
        f = ph["functions"][fn]
        s = W.signs(fn, f)
        cols = W.used(f)
        x0 = np.concatenate([f["theta"], f["phi"]])
        best = None
        for psi in W.PSIS:
            xr, mr = W.resolve(x0, W.vecs(a0, psi), s)
            if best is None or mr < best[1]:
                best = (xr, mr, psi)
        corners = []
        for c in itertools.product([0, 1], repeat=len(cols)):
            z = np.zeros(4)
            z[cols] = c
            corners.append(z * SKEW)
        fns[fn] = dict(s=s, cols=cols, S=wp[fn]["S"], th=best[0][:7], ph=best[0][7:], psi=best[2], v=W.vecs(a0, best[2]), corners=corners)
    _CTX = dict(t=t, a0=a0, s1=s1, s2=s2, det=s3["det_rad"], eps_d=s3["dither_rad"], budget=s5["budget"]["pu_total_dbm"], fns=fns,
                geo=W.geometry(t["ps_per_um"]), sim=W.Sim(t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], W.debruijn(16, 3)))
    return _CTX


def pu_min(m, S, s1):
    A = B1.ASSUME
    if m <= 0:
        return None
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    eta = 10 ** (-(s1["power"]["prop_db"] + s1["power"]["ec_loss_db"]) / 10)

    def ok(p):
        n = B1.noise_terms(p, m, S, A, enbw)
        return n["sig"] - n["off"] - A["q"] * math.sqrt(n["th"] ** 2 + n["comp"] ** 2 + n["shot"] ** 2 + n["rin_diff"] ** 2 + n["rin_cm"] ** 2)
    lo, hi = 1e-8, 1.0
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        lo, hi = (lo, mid) if ok(mid) > 0 else (mid, hi)
    return round(10 * math.log10(hi / eta * 1e3), 2)


def joint_window(bf, prop, th, pp, F, C):
    """聯合驗收條件下的窗內 margin：相位殘差 × 擺動組合以 bf 的靜態 margin 篩選，最差 N_SCREEN 組跑時域（prop 傳遞）。"""
    cols, s, v, det, e = F["cols"], F["s"], F["v"], C["det"], C["eps_d"]
    dits = [np.array(d) for d in itertools.product([-1, 1], repeat=7)]
    cand = []
    for c in itertools.product([-1, 0, 1], repeat=len(cols)):
        dp = np.zeros(4)
        dp[cols] = det * np.array(c)
        D = np.diag(np.exp(1j * np.append(dp, 0.0)))
        for d in dits:
            cand.append((margin(bf, th, pp + e * d, v, s, D), dp, d))
    cand.sort(key=lambda r: r[0])
    nominal_prop = W.propagate
    W.propagate = prop
    try:
        mw = min(C["sim"].best_window(C["sim"].run(th, pp + e * d, C["geo"], s, taus, C["a0"], F["psi"], dphi=dp), C["t"]["t_req_ps"])[0]
                 for _, dp, d in cand[:N_SCREEN] for taus in F["corners"])
    finally:
        W.propagate = nominal_prop
    return cand[0][0], mw


def run_inst(job):
    """一個硬體實例：同一組 ε 上跑 AND4 與 XOR2 的三種狀態。在子行程中執行。"""
    rt.setup(plot=False)
    i, eps = job
    eps = np.array(eps)
    C = context()
    t0 = time.perf_counter()
    bh, prop = b7_hw(eps), propagate_hw(eps)
    Vd = W.vecs(0.0, 0.0)                                            # 擺動量測用隨機資料（理想消光比近似）
    res = dict(eps_mmi_rad=np.round(eps, 4).tolist())
    for fn, F in C["fns"].items():
        th_n, ph_n, v, s, cols = F["th"], F["ph"], F["v"], F["s"], F["cols"]
        # 2. 名義校正迴路：硬體上量測、名義模型估計與補償（只調 φ）
        phl = ph_n.copy()
        believed = []
        for _ in range(LOOPS):
            meas = measure(bh, th_n, phl, Vd)
            de = estimate(meas, lambda d: measure(lambda a, b: b7_nom(a, b) @ drift(d, cols), th_n, phl, Vd), cols)
            phl = resolve_phi(b7_nom, th_n, phl, drift(de, cols), v, s)
            believed.append(margin(b7_nom, th_n, phl, v, s, drift(de, cols)))
        # 3. 已知硬體的參考解（靜態最佳）
        th_o, ph_o = resolve_all(bh, np.concatenate([th_n, ph_n]), v, s)
        r = dict(loop_believed=round(believed[-1], 4))
        for name, (th, pp) in zip(STATES, ((th_n, ph_n), (th_n, phl), (th_o, ph_o))):
            ms_j, mw = joint_window(bh, prop, th, pp, F, C)
            r[name] = dict(m_static=round(margin(bh, th, pp, v, s), 4), m_static_joint=round(ms_j, 4), m_win=round(mw, 4),
                           pu_min_dbm=pu_min(mw, F["S"], C["s1"]))
        res[fn] = r
    res["time_s"] = round(time.perf_counter() - t0, 1)
    print(f"實例 {i}：" + "｜".join(f"{fn} " + "、".join(f"{k} {res[fn][k]['m_win']}" for k in STATES) for fn in FUNCS)
          + f"（{res['time_s']} s）", flush=True)
    return res


def add_stats(res):
    """由各實例的結果加上摘要：所需 P_u 超出系統預算的 dB、窗內 margin 相對名義模型的比例、窗內判錯的實例數。"""
    b = res["budget_pu_dbm"]
    for v in res["functions"].values():
        ref = v["nominal_model"]["m_win"]
        for k in STATES:
            ex = [r[k]["pu_min_dbm"] - b for r in v["instances"] if r[k]["pu_min_dbm"] is not None]
            rat = [r[k]["m_win"] / ref for r in v["instances"]]
            v["summary"][k].update(extra_db=dict(min=round(min(ex), 2), median=round(float(np.median(ex)), 2), max=round(max(ex), 2)),
                                   ratio=dict(min=round(min(rat), 3), median=round(float(np.median(rat)), 3)),
                                   n_wrong=sum(1 for r in v["instances"] if r[k]["m_win"] <= 0))


def main():
    if "--stats" in sys.argv:                                        # 只重算摘要（不重跑模擬）
        res = json.loads(paths.OUT(STEP, "deviation.json").read_text(encoding="utf-8"))
        add_stats(res)
        paths.OUT(STEP, "deviation.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print({fn: {k: v["summary"][k]["extra_db"] for k in STATES} for fn, v in res["functions"].items()})
        return
    t0 = time.perf_counter()
    C = context()
    eps_all = np.random.default_rng(SEED).normal(0, SIGMA_E, (N_INST, 7, 2))   # 每個實例一組 ε，兩個函數共用
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        insts = list(ex.map(run_inst, [(i, eps_all[i].tolist()) for i in range(N_INST)]))
    budget = C["budget"]
    out = {}
    for fn, F in C["fns"].items():
        ms_j, mw_n = joint_window(b7_nom, W.propagate, F["th"], F["ph"], F, C)   # 名義模型上的參考（無偏差、同聯合驗收條件）
        rows = [dict(eps_mmi_rad=q["eps_mmi_rad"], **q[fn]) for q in insts]

        def summ(key, fld):
            vals = [r[key][fld] for r in rows]
            return dict(min=min(vals), median=float(np.median(vals)), max=max(vals))

        def count(key):
            pu = [r[key]["pu_min_dbm"] for r in rows]
            return dict(n_window_at_budget=sum(1 for p in pu if p is not None and p <= budget),
                        n_edge=sum(1 for p in pu if p is not None and abs(p - budget) <= EDGE_DB))
        out[fn] = dict(nominal_model=dict(m_static=round(margin(b7_nom, F["th"], F["ph"], F["v"], F["s"]), 4), m_static_joint=round(ms_j, 4),
                                          m_win=round(mw_n, 4), pu_min_dbm=pu_min(mw_n, F["S"], C["s1"])),
                       instances=rows,
                       summary={k: dict(m_static=summ(k, "m_static"), m_win=summ(k, "m_win"), **count(k)) for k in STATES},
                       loop_worse_win=sum(1 for r in rows if r["loop"]["m_win"] < r["nominal"]["m_win"]),
                       oracle_below_loop_win=sum(1 for r in rows if r["oracle"]["m_win"] < r["loop"]["m_win"]),
                       loop_believed_vs_actual=[(r["loop_believed"], r["loop"]["m_static"]) for r in rows])
    # 同一實例上兩個函數的比較（審查 R1）：XOR2 的窗內 margin 比例低於 AND4 的實例數
    ratio = {fn: [r["nominal"]["m_win"] / out[fn]["nominal_model"]["m_win"] for r in out[fn]["instances"]] for fn in FUNCS}
    paired = dict(xor2_below_and4=sum(1 for a, b in zip(ratio["AND4"], ratio["XOR2"]) if b < a), n=N_INST)
    res = dict(sigma_eps_rad=SIGMA_E, split_pct=round(100 * math.sin(2 * SIGMA_E) / 2, 2), n_inst=N_INST, loops=LOOPS, skew_ps=SKEW,
               seed=SEED, n_screen=N_SCREEN, det_rad=C["det"], dither_rad=C["eps_d"], er_db=C["s2"]["er_required_db"], budget_pu_dbm=budget,
               edge_db=EDGE_DB, workers=WORKERS, wall_s=round(time.perf_counter() - t0, 1),
               inst_time_total_s=round(sum(q["time_s"] for q in insts), 1), functions=out, paired=paired,
               checks=dict(loop_not_worse=all(np.median([r["loop"]["m_static"] for r in v["instances"]]) >= np.median([r["nominal"]["m_static"] for r in v["instances"]]) - 1e-3
                                              for v in out.values()),
                           oracle_best_static=all(r["oracle"]["m_static"] >= r["loop"]["m_static"] - 1e-3 for v in out.values() for r in v["instances"])))
    add_stats(res)
    paths.OUT(STEP, "deviation.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for fn, v in out.items():
        print(fn, "名義模型：", v["nominal_model"], "迴路窗內變差：", v["loop_worse_win"], "參考解窗內低於迴路：", v["oracle_below_loop_win"])
        for k in STATES:
            print(f"  {k}：{v['summary'][k]}")
    print("同實例比較：", paired, "；檢查：", res["checks"], f"；{res['wall_s']} s")


if __name__ == "__main__":
    main()
