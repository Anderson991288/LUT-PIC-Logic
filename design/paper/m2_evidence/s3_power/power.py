r"""論文 M2 s3：功率餘裕與相位失敗——相位偏差讓取樣窗消失時，多給光能不能救回來？要多給多少？

用途：判讀量與光功率成正比，雜訊以熱雜訊為主（M1 s1），所以只要取樣窗內的 margin m_win 仍是正的，多給光就能把窗找回來；
m_win ≤ 0 表示窗內某個時刻判讀方向已經錯了，再多光也沒用。本步把「相位造成的失敗」分成這兩類：
  1. P_u,min(δ)：每路輸入相位偏差 |δ_j| ≤ δ（−δ、0、＋δ 的最差組合）時，要讓 23 ps 窗存在所需的最小 P_u（B7 輸入端）。
     條件同總預算：消光比規格（依殘留重新求相位）、skew 20 ps 的最差延遲角落、不追蹤。
     m_win 由 M1 s4 的時域模型算；P_u 由 M1 s1 的雜訊模型反推（熱、比較器、shot、RIN 都隨功率重算，不只用 margin 比值）。
     與總預算的 P_u（已含 δ_det 的相位代價）比較：交點就是「給到預算功率時，可容許的相位偏差」。
  2. W(P_u)：三種情況下取樣窗寬度隨 P_u 的變化（審查 R7：三者條件不同，各自寫明）：
     名義＝M1 的原相位、理想消光比、無 skew、無相位誤差（參考線，不是規格條件）；
     未追蹤漂移＝消光比規格、skew 20 ps、每路 |δ_j| ≤ 0.3 rad；校正後＝消光比規格、skew 20 ps、δ_det、7 個 heater 同時擺動（M1 s5 聯合驗收）。
     給定 P_u 換算成需要的 margin m_req，W＝m(t) ≥ m_req 的最長連續時間（端點都算），各延遲角落取最小。
兩個代表函數：AND4（四輸入）、XOR2（預算最緊）。δ 在 0.3–0.4 rad 之間加密（審查 R8）。
相位與擺動組合以靜態 margin 篩出最差 N_SCREEN 組再跑時域；篩選造成的誤差由 screen_check.py 檢查（審查 R6）。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、s1_budget/out/budget.json、s2_interface/out/interface_v2.json、
      s3_tracking/out/tracking.json、s5_assess/out/assess.json；時域模型沿用 s4_window/window.py，雜訊模型沿用 s1_budget/budget.py。
輸出：design/paper/m2_evidence/s3_power/out/power.json。
執行：.\lab design\paper\m2_evidence\s3_power\power.py（約 15 分鐘，單一行程）
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

import numpy as np                                                   # noqa: E402

import budget as B1                                                  # noqa: E402  s1 的雜訊模型
import paths                                                         # noqa: E402
import window as W                                                   # noqa: E402  s4 的時域模型
from common.mzi import READ                                          # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import b7 as b7_matrix, load_phases                       # noqa: E402

STEP = "paper/m2_evidence/s3_power"
BASE = "paper/m1_timing"
FUNCS = ("AND4", "XOR2")
SKEW = 20
DELTAS = (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.325, 0.35, 0.375, 0.4, 0.5)
N_SCREEN = 2
DRIFT_RAD = 0.3


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def static_m(th, pp, v, s, dphi):
    D = np.diag(np.exp(1j * np.append(dphi, 0.0)))
    return float(np.min(s * deltas(b7_matrix(th, pp) @ D, v, READ)))


def width(m, thr, dt):
    """m(t) ≥ thr 的最長連續時間（ps，端點都算：k 個格點跨 (k−1)·dt）。"""
    best = run = 0
    for ok in (m >= thr):
        run = run + 1 if ok else 0
        best = max(best, run)
    return max(best - 1, 0) * dt


def main():
    ph = load_phases()
    s1, s2, s3, s5 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json"), \
        load("s5_assess", "assess.json")
    t = s1["timing"]
    A = B1.ASSUME
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    eta = 10 ** (-(s1["power"]["prop_db"] + s1["power"]["ec_loss_db"]) / 10)
    wp = B1.worst_patterns()

    def pu_min_dbm(m, S):
        """margin m（P_u 為單位）時，判讀電流 − 偏移 ≥ Q × 總雜訊所需的最小 P_u（B7 輸入端，dBm）；m ≤ 0 回傳 None。"""
        if m <= 0:
            return None

        def ok(pu_pd):
            n = B1.noise_terms(pu_pd, m, S, A, enbw)
            tot = math.sqrt(n["th"] ** 2 + n["comp"] ** 2 + n["shot"] ** 2 + n["rin_diff"] ** 2 + n["rin_cm"] ** 2)
            return n["sig"] - n["off"] - A["q"] * tot
        lo, hi = 1e-8, 1.0
        if ok(hi) <= 0:
            return None
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            lo, hi = (lo, mid) if ok(mid) > 0 else (mid, hi)
        return 10 * math.log10(hi / eta * 1e3)

    def m_req(pu_dbm, S):
        """在 P_u（B7 輸入端，dBm）下剛好通過所需的 margin（二分法）。"""
        lo, hi = 1e-6, 10.0
        for _ in range(80):
            mid = math.sqrt(lo * hi)
            p = pu_min_dbm(mid, S)
            lo, hi = (mid, hi) if (p is None or p > pu_dbm) else (lo, mid)
        return hi
    geo = W.geometry(t["ps_per_um"])
    sim = W.Sim(t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], W.debruijn(16, 3))
    a0 = 10 ** (-s2["er_required_db"] / 20)
    det, eps = s3["det_rad"], s3["dither_rad"]
    out = {}
    for fn in FUNCS:
        f = ph["functions"][fn]
        s = W.signs(fn, f)
        cols = W.used(f)
        S = wp[fn]["S"]
        th0, pp0 = np.array(f["theta"]), np.array(f["phi"])
        x0 = np.concatenate([th0, pp0])
        best = None
        for psi in W.PSIS:
            xr, mr = W.resolve(x0, W.vecs(a0, psi), s)
            if best is None or mr < best[1]:
                best = (xr, mr, psi)
        th, pp, psi = best[0][:7], best[0][7:], best[2]
        v = W.vecs(a0, psi)
        corners = []
        for c in itertools.product([0, 1], repeat=len(cols)):
            z = np.zeros(4)
            z[cols] = c
            corners.append(z * SKEW)

        def screen(amp, with_dither):
            cand = []
            dits = [np.array(d) for d in itertools.product([-1, 1], repeat=7)] if with_dither else [np.zeros(7)]
            for c in itertools.product([-1, 0, 1], repeat=len(cols)):
                dp = np.zeros(4)
                dp[cols] = amp * np.array(c)
                for d in dits:
                    cand.append((static_m(th, pp + eps * d, v, s, dp), dp, d))
            cand.sort(key=lambda r: r[0])
            return cand[:N_SCREEN]

        def worst_case(thx, ppx, aa, combos, keep_curves=False):
            worst, curves = None, []
            for ms, dp, d in combos:
                for taus in corners if aa > 0 else [np.zeros(4)]:
                    m = sim.run(thx, ppx + eps * d, geo, s, taus, aa, psi, dphi=dp)
                    mw, _ = sim.best_window(m, t["t_req_ps"])
                    if keep_curves:
                        curves.append(m)
                    if worst is None or mw < worst[0]:
                        worst = (mw, ms)
            return worst, curves
        # 1. P_u,min(δ)
        rows = []
        for dl in DELTAS:
            combos = screen(dl, False) if dl > 0 else [(static_m(th, pp, v, s, np.zeros(4)), np.zeros(4), np.zeros(7))]
            (mw, ms), _ = worst_case(th, pp, a0, combos)
            p = pu_min_dbm(mw, S)
            rows.append(dict(delta_rad=dl, m_static=round(ms, 5), m_win=round(mw, 5), pu_min_dbm=None if p is None else round(p, 2)))
            print(f"{fn} δ {dl}：靜態 {ms:.4f}、窗 {mw:.4f} → P_u,min {p if p is None else round(p, 2)} dBm", flush=True)
        # 2. W(P_u)：三種情況
        none = [(0.0, np.zeros(4), np.zeros(7))]
        (_, _), c_nom = worst_case(th0, pp0, 0.0, none, keep_curves=True)
        (_, _), c_drift = worst_case(th, pp, a0, screen(DRIFT_RAD, False), keep_curves=True)
        (_, _), c_fin = worst_case(th, pp, a0, screen(det, True), keep_curves=True)
        budget_pu = s5["budget"]["pu_total_dbm"]                     # 系統預算：雷射照最難的函數給光，所有函數都用這個 P_u
        fn_budget_pu = s5["budget"]["per_function"][fn]["total_dbm"]
        static_pu = s1["power"]["pu_core_per_function_dbm"][fn]
        grid = np.arange(math.floor(static_pu) - 1, math.ceil(budget_pu) + 8, 0.5)
        mreq = [m_req(p, S) for p in grid]
        wcurve = {}
        for name, cs in (("nominal", c_nom), ("drift", c_drift), ("final", c_fin)):
            wcurve[name] = [round(min(width(np.asarray(m), mq, sim.dt) for m in cs), 1) for mq in mreq]
        mq_b = m_req(budget_pu, S)
        w_budget = {name: round(min(width(np.asarray(m), mq_b, sim.dt) for m in cs), 1)
                    for name, cs in (("nominal", c_nom), ("drift", c_drift), ("final", c_fin))}
        # 給到預算功率時，可容許的 δ（線性內插）
        tol = None
        for a, b in zip(rows, rows[1:]):
            pa = a["pu_min_dbm"] if a["pu_min_dbm"] is not None else 99
            pb = b["pu_min_dbm"] if b["pu_min_dbm"] is not None else 99
            if pa <= budget_pu < pb:
                tol = round(a["delta_rad"] + (budget_pu - pa) / (pb - pa) * (b["delta_rad"] - a["delta_rad"]), 3)
                break
        out[fn] = dict(rows=rows, budget_pu_dbm=budget_pu, fn_budget_pu_dbm=fn_budget_pu, w_at_budget_ps=w_budget, static_pu_dbm=static_pu, delta_tol_at_budget_rad=tol,
                       pu_grid_dbm=grid.tolist(), w_ps=wcurve,
                       power_fixable=[r["delta_rad"] for r in rows if r["pu_min_dbm"] is not None],
                       not_fixable=[r["delta_rad"] for r in rows if r["pu_min_dbm"] is None])
        print(f"{fn}：系統預算 P_u {budget_pu} dBm 時可容許 δ ≈ {tol} rad（δ_det {det}）；預算處的窗 {w_budget}", flush=True)
    cond = dict(nominal="M1 原相位、理想消光比、無 skew、無相位誤差", drift=f"消光比規格、skew {SKEW} ps、每路 |δ_j| ≤ {DRIFT_RAD} rad",
                final=f"消光比規格、skew {SKEW} ps、每路 |δ_j| ≤ δ_det、7 個 heater 同時擺動")
    res = dict(skew_ps=SKEW, deltas_rad=list(DELTAS), conditions=cond, drift_rad=DRIFT_RAD, det_rad=det, dither_rad=eps, er_db=s2["er_required_db"],
               t_req_ps=t["t_req_ps"], n_screen=N_SCREEN, functions=out,
               checks=dict(tol_above_det=all((r["delta_tol_at_budget_rad"] or 9) >= det for r in out.values()),
                           final_window_at_budget=all(r["w_at_budget_ps"]["final"] >= t["t_req_ps"] - 1e-9 for r in out.values()),
                           final_window_margin_ps={fn: round(r["w_at_budget_ps"]["final"] - t["t_req_ps"], 1) for fn, r in out.items()}))
    paths.OUT(STEP, "power.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("檢查：", res["checks"])


if __name__ == "__main__":
    main()
