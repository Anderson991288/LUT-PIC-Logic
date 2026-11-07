r"""論文 M1 s5：校正後的聯合驗收——同時加入所有誤差，在同一個 23 ps 取樣窗內重算 margin。

用途：assess.py 的總預算把各項代價直接相加，是近似。這裡選兩個代表函數（AND4：四輸入、一次項；XOR2：二次項、預算最緊），
用 M1 s4 的時域模型同時加入：
  - 消光比殘留（M1 s2 規格，依殘留重新求相位，ψ 取靜態最差；與 s4 相同）；
  - 輸入 skew 20 ps（s4 的延遲角落中最差者）；
  - 追蹤後的輸入相位殘差：每路 |δ_j| ≤ δ_det（M1 s3 的幅度相加預算用滿；各路 −δ、0、＋δ）；
  - 7 個 φ heater 同時擺動 ±ε（M1 s3 的擺動幅度）。
相位與擺動的組合太多（AND4：3⁴×2⁷），先用靜態 margin 篩選最差的 N_SCREEN 組，再對每組跑所有 skew 角落的時域計算，取最差。
同一表也列「偏差前 → 偏差後（未追蹤）→ 校正後」：名義（理想消光比、無 skew、無相位誤差）、規格條件（消光比＋skew 20 ps）、
未追蹤的漂移（每路 |δ_j| ≤ DRIFT_RAD，其餘同規格條件）、校正後（上述全部）。
代價＝10 log10(m0／m_win)，m0 是名義的靜態 margin（與 assess.py 相同的參考面）。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、s1_budget/out/budget.json、s2_interface/out/interface_v2.json、
      s3_tracking/out/tracking.json；時域模型沿用 s4_window/window.py。
輸出：design/paper/m1_timing/s5_assess/out/joint.json。
執行：.\lab design\paper\m1_timing\s5_assess\joint.py（約 3 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/paper/m1_timing（共用模型 model.py）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s4_window"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import window as W                                                   # noqa: E402  s4 的時域模型
from common.mzi import READ                                          # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import b7 as b7_matrix, load_phases                       # noqa: E402

STEP = "paper/m1_timing/s5_assess"
BASE = "paper/m1_timing"
FUNCS = ("AND4", "XOR2")
SKEW = 20                                                            # ps，與總預算相同（介面規格 15 ps，取 20 ps 偏保守）
DRIFT_RAD = 0.3                                                      # 未追蹤時的漂移（M1 s3 估計測試用的兩次更新間漂移）
N_SCREEN = 3


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def static_m(th, pp, v, s, dphi):
    D = np.diag(np.exp(1j * np.append(dphi, 0.0)))
    return float(np.min(s * deltas(b7_matrix(th, pp) @ D, v, READ)))


def main():
    ph = load_phases()
    s1, s2, s3 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json")
    t = s1["timing"]
    geo = W.geometry(t["ps_per_um"])
    sim = W.Sim(t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], W.debruijn(16, 3))
    a0 = 10 ** (-s2["er_required_db"] / 20)
    det, eps = s3["det_rad"], s3["dither_rad"]
    out = {}
    for fn in FUNCS:
        f = ph["functions"][fn]
        s = W.signs(fn, f)
        cols = W.used(f)
        th0, pp0 = np.array(f["theta"]), np.array(f["phi"])
        m0 = static_m(th0, pp0, W.vecs(0.0, 0.0), s, np.zeros(4))
        x0 = np.concatenate([th0, pp0])
        best = None                                                  # 消光比：與 s4 相同，ψ 取重新求相位後靜態最差者
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

        def dyn(thx, ppx, aa, taus_list, dphi):
            worst = None
            for taus in taus_list:
                mw, t0 = sim.best_window(sim.run(thx, ppx, geo, s, taus, aa, psi, dphi=dphi), t["t_req_ps"])
                if worst is None or mw < worst[0]:
                    worst = (mw, t0)
            return worst

        def screen(amp, with_dither):
            """靜態 margin 最差的 N_SCREEN 組（輸入相位 −amp、0、＋amp；擺動 ±ε 的角落）。"""
            cand = []
            dits = itertools.product([-1, 1], repeat=7) if with_dither else [np.zeros(7)]
            dits = [np.array(d) for d in dits]
            for c in itertools.product([-1, 0, 1], repeat=len(cols)):
                dp = np.zeros(4)
                dp[cols] = amp * np.array(c)
                for d in dits:
                    cand.append((static_m(th, pp + eps * d, v, s, dp), dp, d))
            cand.sort(key=lambda r: r[0])
            return cand[:N_SCREEN]

        def case(name, thx, ppx, aa, taus_list, combos):
            worst = None
            for ms, dp, d in combos:
                mw, t0 = dyn(thx, ppx + eps * d, aa, taus_list, dp)
                if worst is None or mw < worst["m_win"]:
                    worst = dict(m_win=round(mw, 5), window_start_ps=t0, m_static=round(ms, 5),
                                 dphi_rad=np.round(dp, 4).tolist(), dither=d.astype(int).tolist())
            worst["penalty_db"] = round(10 * np.log10(m0 / worst["m_win"]), 3) if worst["m_win"] > 0 else None
            worst["name"] = name
            print(f"{fn} {name}：靜態 {worst['m_static']:.4f}、23 ps 窗 {worst['m_win']:.4f} Pu、代價 {worst['penalty_db']} dB", flush=True)
            return worst
        none = [(static_m(th, pp, v, s, np.zeros(4)), np.zeros(4), np.zeros(7))]
        res = dict(m0=m0, er_psi=psi)
        res["nominal"] = case("名義", th0, pp0, 0.0, [np.zeros(4)], [(m0, np.zeros(4), np.zeros(7))])
        res["spec"] = case("規格條件（消光比＋skew 20 ps）", th, pp, a0, corners, none)
        res["drift"] = case(f"未追蹤漂移 {DRIFT_RAD} rad", th, pp, a0, corners, screen(DRIFT_RAD, False))
        res["final"] = case("校正後（再加相位殘差 δ_det 與同時擺動）", th, pp, a0, corners, screen(det, True))
        out[fn] = res
    J = dict(skew_ps=SKEW, drift_rad=DRIFT_RAD, det_rad=det, dither_rad=eps, er_db=s2["er_required_db"], t_req_ps=t["t_req_ps"],
             n_screen=N_SCREEN, functions=out,
             checks=dict(final_window_exists=all(r["final"]["m_win"] > 0 for r in out.values()),
                         drift_hurts=all(r["drift"]["m_win"] < r["final"]["m_win"] for r in out.values())))
    paths.OUT(STEP, "joint.json").write_text(json.dumps(J, ensure_ascii=False, indent=2), encoding="utf-8")
    print("檢查：", J["checks"])


if __name__ == "__main__":
    main()
