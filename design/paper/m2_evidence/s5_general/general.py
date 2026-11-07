r"""論文 M2 s5：通用性與執行時間——同一套流程能不能用在 B7 能做的所有函數？每一步要算多久？

用途：M1 只在課程的 5 個函數上做過。本步把整套流程依序跑在：
  - 所有非常數的二輸入函數（x1、x2 的 14 個函數，含 NAND、NOR、XNOR、單一變數、蘊含），每個都用 M1 的模型重新合成相位；
  - 四輸入的 AND4、OR4（沿用 M1 的相位）。
每個函數依序做六步，並記錄每步的執行時間：
  1. 合成：含 MMI 損耗的 B7，SLSQP 24 個起點（與 M1 的模型相同；XOR、XNOR 用 96 個起點確認是否為全域解，審查 R2），
     得到 14 個相位與靜態 margin m0；
  2. 功率：M1 s1 的雜訊模型反推靜態需求 P_u；
  3. 時序：M1 s4 的時域模型，skew 0、15、20 ps 最差延遲角落的功率代價；
  4. 靜態校正：消光比規格下依殘留重新求相位，margin 保留比例（ψ 取 4 個方向中最差）；
  5. 動態校正的可觀測性：擺動量測對輸入相位的 Jacobian 秩（M1 s3）；
  6. 聯合驗收：消光比規格＋skew 20 ps＋每路相位殘差 ≤ δ_det＋7 個 heater 同時擺動（M1 s5），窗存在所需的 P_u，與系統預算比較。
另跑一個「XNOR（比較器對調）」：用 XOR 的真值表合成相位，比較器兩輸入對調（判讀符號取負），即 XNOR，流程相同（審查 R2）。
XOR 的聯合驗收「通過」是自洽檢查：系統預算本來就由同一模型的 XOR2 訂出，不是獨立驗證。
以 6 個 worker 平行（每個函數一個工作，BLAS 單執行緒）；time_s 是各 worker 內每步的牆上時間，stage_time_total_s 為所有函數的加總。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、s1_budget/out/budget.json、s2_interface/out/interface_v2.json、
      s3_tracking/out/tracking.json、s5_assess/out/assess.json；時域模型、雜訊模型、擺動量測沿用 M1 s4、s1、s3 的程式。
輸出：design/paper/m2_evidence/s5_general/out/general.json。
執行：.\lab design\paper\m2_evidence\s5_general\general.py（6 個 worker 約 2–3 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
M1 = Path(__file__).resolve().parents[2] / "m1_timing"
for sub in ("", "s4_window", "s1_budget", "s3_tracking"):
    sys.path.insert(0, str(M1 / sub))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "paper/m2_evidence/s5_general"
BASE = "paper/m1_timing"
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
SKEWS = (0, 15, 20)
N_SCREEN = 2
# 二輸入函數：真值表 f(x1, x2) 依 (00, 01, 10, 11)
TWO = {"AND": (0, 0, 0, 1), "NAND": (1, 1, 1, 0), "OR": (0, 1, 1, 1), "NOR": (1, 0, 0, 0), "XOR": (0, 1, 1, 0), "XNOR": (1, 0, 0, 1),
       "x1": (0, 0, 1, 1), "¬x1": (1, 1, 0, 0), "x2": (0, 1, 0, 1), "¬x2": (1, 0, 1, 0),
       "x1·¬x2": (0, 0, 1, 0), "¬x1·x2": (0, 1, 0, 0), "x1+¬x2": (1, 0, 1, 1), "¬x1+x2": (1, 1, 0, 1)}
COURSE = {"AND": "AND2", "OR": "OR2", "XOR": "XOR2"}                 # 與 M1 相位核對
MORE_STARTS = {"XOR": 96, "XNOR": 96}                               # 審查 R2：取反等價的兩個函數加大起點數
SWAP = "XNOR（比較器對調）"


def cpu_name():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except OSError:
        import platform
        return platform.processor()


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def run_one(job):
    """一個函數的完整流程；回傳結果與每步時間（s）。在子行程中執行。"""
    rt.setup(plot=False)
    import budget as B1
    import track as T3
    import window as W
    from common.mzi import READ, R_AMP
    from common.synth import best_margin, deltas
    from model import MAXITER, STARTS, b7
    name, kind, data = job
    s1, s2, s3, s5 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json"), \
        load("s5_assess", "assess.json")
    t = s1["timing"]
    A = B1.ASSUME
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    eta = 10 ** (-(s1["power"]["prop_db"] + s1["power"]["ec_loss_db"]) / 10)
    budget = s5["budget"]["pu_total_dbm"]
    bits = np.array(list(itertools.product([0, 1], repeat=4)))
    V0 = W.vecs(0.0, 0.0)
    tm = {}
    # 1. 合成
    t0 = time.perf_counter()
    if kind in ("two", "swap"):
        s = np.array([1 if data[2 * b[0] + b[1]] else -1 for b in bits])
        if kind == "swap":                                           # 比較器對調：判讀符號取負（XNOR 的真值表 → 合成 XOR）
            s = -s
        m0, z = best_margin(lambda z: b7(z[:7], z[7:]), 14, V0, READ, s, MORE_STARTS.get(name, STARTS if kind == "two" else MORE_STARTS["XOR"]),
                            maxiter=MAXITER)
        th0, ph0 = z[:7], z[7:]
        cols = [i for i, dep in enumerate((any(data[b] != data[2 + b] for b in (0, 1)), any(data[2 * a] != data[2 * a + 1] for a in (0, 1)))) if dep]
    else:
        th0, ph0 = np.array(data["theta"]), np.array(data["phi"])
        s = W.signs(name, data)
        m0 = float(np.min(s * deltas(b7(th0, ph0), V0, READ)))
        cols = [0, 1, 2, 3]
    tm["synth"] = time.perf_counter() - t0

    def pu_min(m, S):
        if m <= 0:
            return None

        def ok(p):
            n = B1.noise_terms(p, m, S, A, enbw)
            return n["sig"] - n["off"] - A["q"] * math.sqrt(n["th"] ** 2 + n["comp"] ** 2 + n["shot"] ** 2 + n["rin_diff"] ** 2 + n["rin_cm"] ** 2)
        lo, hi = 1e-8, 1.0
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            lo, hi = (lo, mid) if ok(mid) > 0 else (mid, hi)
        return 10 * math.log10(hi / eta * 1e3)
    # 2. 功率
    t0 = time.perf_counter()
    P = np.abs(np.hstack([bits.astype(complex), np.full((16, 1), R_AMP + 0j)]) @ b7(th0, ph0).T) ** 2
    mm = s * (P[:, READ[0]] - P[:, READ[1]])
    S = float(P[int(np.argmin(mm)), READ[0]] + P[int(np.argmin(mm)), READ[1]])
    pu_static = pu_min(m0, S)
    tm["power"] = time.perf_counter() - t0
    # 3. 時序（理想消光比）
    t0 = time.perf_counter()
    geo = W.geometry(t["ps_per_um"])
    sim = W.Sim(t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], W.debruijn(16, 3))

    def corners(S_):
        out = []
        for c in itertools.product([0, 1], repeat=len(cols)):
            z = np.zeros(4)
            z[cols] = c
            out.append(z * S_)
        return out
    pen = {}
    for S_ in SKEWS:
        mw = min(sim.best_window(sim.run(th0, ph0, geo, s, taus), t["t_req_ps"])[0] for taus in (corners(S_) if S_ else [np.zeros(4)]))
        pen[str(S_)] = None if mw <= 0 else round(10 * math.log10(m0 / mw), 3)
    tm["timing"] = time.perf_counter() - t0
    # 4. 靜態校正（消光比）
    t0 = time.perf_counter()
    a0 = 10 ** (-s2["er_required_db"] / 20)
    best = None
    for psi in W.PSIS:
        xr, mr = W.resolve(np.concatenate([th0, ph0]), W.vecs(a0, psi), s)
        if best is None or mr < best[1]:
            best = (xr, mr, psi)
    th, pp, psi = best[0][:7], best[0][7:], best[2]
    er_keep = best[1] / m0
    tm["static_cal"] = time.perf_counter() - t0
    # 5. 可觀測性
    t0 = time.perf_counter()
    Jd = T3.jac(lambda D: T3.dither(th, pp, D), cols)
    rank, sv = T3.rank_of(Jd)
    tm["observe"] = time.perf_counter() - t0
    # 6. 聯合驗收
    t0 = time.perf_counter()
    v = W.vecs(a0, psi)
    det, eps = s3["det_rad"], s3["dither_rad"]
    cand = []
    for c in itertools.product([-1, 0, 1], repeat=len(cols)):
        dp = np.zeros(4)
        dp[cols] = det * np.array(c)
        D = np.diag(np.exp(1j * np.append(dp, 0.0)))
        for d in itertools.product([-1, 1], repeat=7):
            d = np.array(d)
            cand.append((float(np.min(s * deltas(b7(th, pp + eps * d) @ D, v, READ))), dp, d))
    cand.sort(key=lambda r: r[0])
    mw = min(sim.best_window(sim.run(th, pp + eps * d, geo, s, taus, a0, psi, dphi=dp), t["t_req_ps"])[0]
             for _, dp, d in cand[:N_SCREEN] for taus in corners(20))
    p_joint = pu_min(mw, S)
    tm["joint"] = time.perf_counter() - t0
    return dict(name=name, kind=kind, n_inputs=len(cols), starts=MORE_STARTS.get(name, STARTS) if kind != "swap" else MORE_STARTS["XOR"],
                m0=round(m0, 4), pu_static_dbm=round(pu_static, 2), skew_penalty_db=pen, er_keep=round(er_keep, 3),
                rank=rank, n_phase=len(cols), joint_m_win=round(mw, 4), joint_pu_dbm=None if p_joint is None else round(p_joint, 2),
                joint_pass=bool(p_joint is not None and p_joint <= budget + 1e-9), budget_pu_dbm=budget,
                theta=np.round(th0, 5).tolist(), phi=np.round(ph0, 5).tolist(), time_s={k: round(v, 2) for k, v in tm.items()})


def main():
    from model import load_phases
    ph = load_phases()
    jobs = [(k, "two", v) for k, v in TWO.items()] + [(k, "four", ph["functions"][k]) for k in ("AND4", "OR4")] + [(SWAP, "swap", TWO["XNOR"])]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(run_one, jobs))
    wall = time.perf_counter() - t0
    swap = [r for r in res if r["kind"] == "swap"][0]
    res = [r for r in res if r["kind"] != "swap"]
    out = {r["name"]: r for r in res}
    for r in res:
        print(f"{r['name']}：m0 {r['m0']}、P_u {r['pu_static_dbm']} dBm、skew 代價 {r['skew_penalty_db']}、消光比保留 {r['er_keep']}、"
              f"秩 {r['rank']}／{r['n_phase']}、聯合驗收窗 {r['joint_m_win']}、所需 {r['joint_pu_dbm']} dBm（{'通過' if r['joint_pass'] else '不通過'}）；時間 {r['time_s']}", flush=True)
    course = {k: round(ph["functions"][v]["margin"], 4) for k, v in COURSE.items()}
    synth_match = {k: abs(out[k]["m0"] - course[k]) < 2e-3 for k in COURSE}
    hardest = max(out, key=lambda k: out[k]["joint_pu_dbm"] if out[k]["joint_pu_dbm"] is not None else 99)
    stages = ["synth", "power", "timing", "static_cal", "observe", "joint"]
    tsum = {st: round(sum(r["time_s"][st] for r in res), 1) for st in stages}
    xnor_ok = out["XNOR"]["joint_pass"] or swap["joint_pass"]
    resj = dict(functions=out, n_functions=len(out), wall_s=round(wall, 1), workers=WORKERS, cpu=cpu_name(), stage_time_total_s=tsum,
                xnor_swap=swap, xnor_vs_xor_m0_diff=round(out["XOR"]["m0"] - out["XNOR"]["m0"], 4),
                n_pass_with_swap=sum(r["joint_pass"] for r in res if r["name"] != "XNOR") + int(xnor_ok),
                xor_pass_is_self_consistent=True,
                course_margin=course, synth_matches_course=synth_match, hardest=hardest,
                n_joint_pass=sum(r["joint_pass"] for r in res), budget_pu_dbm=res[0]["budget_pu_dbm"],
                checks=dict(all_observable=all(r["rank"] == r["n_phase"] for r in res),
                            all_er_keep=all(r["er_keep"] >= 0.9 - 1e-3 for r in res),
                            synth_matches_course=all(synth_match.values()),
                            swap_equals_xor=abs(swap["m0"] - out["XOR"]["m0"]) < 2e-3))
    paths.OUT(STEP, "general.json").write_text(json.dumps(resj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"共 {len(out)} 個函數，{WORKERS} 個 worker 約 {wall:.0f} s；各步合計 {tsum}；最需要光的是 {hardest}；聯合驗收通過 {resj['n_joint_pass']}／{len(out)}")
    print("合成與 M1 一致：", synth_match)
    print(f"XNOR 直接合成 m0 {out['XNOR']['m0']}（XOR {out['XOR']['m0']}）；比較器對調 m0 {swap['m0']}、所需 {swap['joint_pu_dbm']} dBm；含對調通過 {resj['n_pass_with_swap']}／{len(out)}")
    print("檢查：", resj["checks"])


if __name__ == "__main__":
    main()
