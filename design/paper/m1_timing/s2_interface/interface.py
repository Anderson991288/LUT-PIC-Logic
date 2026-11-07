r"""論文 M1 s2：輸入介面規格——片外發射端要給什麼樣的光，B7 才能在 10 Gb/s 判對（晶片只有 heater MZI）。

用途：資料在片外調變（發射端不是本計畫設計的元件），晶片仍是 課程 M3 交付的 B7。本步把需求整理成發射端的介面規格：
  1. 消光比（本步的新分析，靜態校正）：發射端在「0」時不是全暗，殘留光場 a0·e^{iψ} 會和參考光干涉、吃掉 margin。
     比較兩種情況下 margin 與消光比的關係：沿用 課程 M1 的相位、依殘留重新求相位（只動 heater，晶片完成後本來就要重新校正，即 課程 M2 的需求 K1）。
     殘留相位 ψ 由發射端決定、事先未知，取 4 個方向中最差的。
  2. 相位、功率、時間對齊：沿用 M1 s1 的結果，換成介面規格的寫法。
輸入：design/paper/m1_timing/out/phases_lossy.json（含 MMI 損耗的 B7 與重新校正的相位，model.py）、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：design/paper/m1_timing/s2_interface/out/interface_v2.json。
執行：.\lab design\paper\m1_timing\s2_interface\interface.py（約 1 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/paper/m1_timing（共用模型 model.py）
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import R_AMP, READ                                   # noqa: E402
from model import b7 as b7_matrix, load_phases                       # noqa: E402  含 MMI 損耗的 B7（M1 共用模型）
from common.synth import deltas                                      # noqa: E402

STEP = "paper/m1_timing/s2_interface"
MARGIN_KEEP = 0.9                                                    # 消光比需求：每個函數的 margin 至少保留 90%
ER_DB = np.arange(10, 40.01, 0.5)
PSIS = (0.0, np.pi / 2, np.pi, 3 * np.pi / 2)                        # 殘留光場相對「1」的相位
TARGET = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
BITS = np.array(list(itertools.product([0, 1], repeat=4)))


def vecs(a0, psi):
    """16 組輸入光場：「1」＝1，「0」＝殘留 a0·e^{iψ}；參考光 R＝3。"""
    x = np.where(BITS == 1, 1.0 + 0j, a0 * np.exp(1j * psi))
    return np.hstack([x, np.full((len(BITS), 1), R_AMP + 0j)])


def signs(fn, f):
    idx = [int(u[1]) - 1 for u in f["uses"]]
    return np.array([1 if TARGET[fn](b[idx]) else -1 for b in BITS])


def resolve(x0, v, s):
    """以原相位為起點重新求相位（同 課程 M1 的 max margin，SLSQP）；回傳 margin。"""
    mk = lambda z: b7_matrix(z[:7], z[7:14])                          # noqa: E731

    def cons(z):
        return s * deltas(mk(z[:-1]), v, READ) - z[-1]
    z0 = np.append(x0, np.min(s * deltas(mk(x0), v, READ)))
    r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)],
                 options=dict(maxiter=400, ftol=1e-10))
    return float(np.min(s * deltas(mk(r.x[:-1]), v, READ)))


def margin_vs_leak(phases, a0s, re=False):
    """每個 a0 取 4 個 ψ 中最差的 margin；re＝True 時每個 (a0, ψ) 都重新求相位。"""
    out = {}
    for fn, f in phases["functions"].items():
        x0 = np.concatenate([f["theta"], f["phi"]])
        U = b7_matrix(np.array(f["theta"]), np.array(f["phi"]))
        s = signs(fn, f)
        out[fn] = [min((resolve(x0, vecs(a0, psi), s) if re else float(np.min(s * deltas(U, vecs(a0, psi), READ))))
                       for psi in PSIS) for a0 in a0s]
    return out


def need_of(m, m0):
    out = {}
    for fn, ms in m.items():
        ok = np.array(ms) >= MARGIN_KEEP * m0[fn]
        out[fn] = float(ER_DB[np.argmax(ok)]) if ok.any() else None
    return out


def main():
    ph = load_phases()                                               # 含 MMI 損耗、重新校正後的相位（model.py）
    s1 = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))
    a0 = 10 ** (-ER_DB / 20)                                         # 功率消光比 ER → 殘留場振幅
    m0 = {fn: v[0] for fn, v in margin_vs_leak(ph, [0.0]).items()}
    mf = margin_vs_leak(ph, a0)                                      # 沿用原相位
    mr = margin_vs_leak(ph, a0, re=True)                             # 重新求相位
    nf, nr = need_of(mf, m0), need_of(mr, m0)
    er_fixed = max(nf.values())
    # 解析近似（數值支持的縮放關係，不是嚴格上界）：重新求相位後 margin ≈ (1−a0)^n m0；只靠一次項（R 與資料干涉）的函數 n＝1，靠二次項（資料彼此干涉）的 XOR2 n＝2。
    # 由 20 dB 的重解結果求 n，再求保留 MARGIN_KEEP 所需的消光比：a0＝1−keep^(1/n)、ER＝−20 log10 a0。
    k20 = int(np.argmin(np.abs(ER_DB - 20.0)))
    a20 = a0[k20]
    order = {fn: round(float(np.log(mr[fn][k20] / m0[fn]) / np.log(1 - a20)), 3) for fn in mr}
    fit_err = {fn: float(np.max(np.abs(np.array(mr[fn]) / m0[fn] - (1 - a0) ** round(order[fn])))) for fn in mr}
    er_analytic = {fn: round(float(-20 * np.log10(1 - MARGIN_KEEP ** (1 / round(order[fn])))), 2) for fn in mr}
    er_req = max(er_analytic.values())
    fn_hard = max(er_analytic, key=er_analytic.get)
    # 各路不同的殘留：a0_j ∈ [0.5, 1] × a0、ψ_j 隨機（4 路調變器不必相同），在 er_req 重新求相位，看 margin 是否仍保留 keep
    rng = np.random.default_rng(rt.MC_SEED_BASE)
    a_req = 10 ** (-er_req / 20)
    per_input = {}
    for fn, f in ph["functions"].items():
        x0 = np.concatenate([f["theta"], f["phi"]])
        sgn = signs(fn, f)
        worst = np.inf
        for _ in range(8):
            av = a_req * rng.uniform(0.5, 1.0, 4)
            pv = rng.uniform(0, 2 * np.pi, 4)
            x = np.where(BITS == 1, 1.0 + 0j, av * np.exp(1j * pv))
            v = np.hstack([x, np.full((16, 1), R_AMP + 0j)])
            worst = min(worst, resolve(x0, v, sgn) / m0[fn])
        per_input[fn] = round(worst, 4)
    t, w, p = s1["timing"], s1["power"], s1["phase"]
    spec = [
        dict(item="光源", need="5 路（x1–x4、R）來自同一顆雷射，波長 1550 nm", why="B7 靠干涉判讀，各路要同調"),
        dict(item="資料格式", need="光場開關（OOK）：「1」振幅 1、「0」接近全暗；參考光 R 不調變、振幅 3（功率 9 P_u）", why="課程 M1 的輸入定義"),
        dict(item="消光比", need=f"≥ {er_req:g} dB（晶片完成後依殘留重新求相位）；若沿用原相位需 ≥ {er_fixed:g} dB", why=f"保留 {MARGIN_KEEP:.0%} margin；最難的是 {fn_hard}"),
        dict(item="功率", need=f"每根資料光纖 ≥ {w['pu_fiber_dbm']:.1f} dBm、參考光纖 ≥ {w['r_fiber_dbm']:+.1f} dBm", why="M1 s1：由接收端雜訊與最小 margin 反推"),
        dict(item="相對相位", need=f"5 路之間的固定偏差 ≤ {p['det_rad']:g} rad（margin 保留 90%），隨機誤差 σ ≤ {p['sigma_random_rad']:g} rad；"
             "慢漂移由晶片上的 heater 追蹤（M1 s3）", why="M1 s1 的確定性容許；課程 M2 s1 的隨機容許"),
        dict(item="時間對齊", need=f"5 路到達晶片的時間差 ≤ {t['skew_allow_ps'] - t['worst_skew_ps']:.1f} ps（一階允許 {t['skew_allow_ps']:.3g} ps 扣掉晶片內 {t['worst_skew_ps']:.2g} ps）",
             why="M1 s1；M1 s4 以完整模型確認"),
    ]
    res = dict(margin_keep=MARGIN_KEEP, psi_rad=list(PSIS),
               er_scan=dict(er_db=ER_DB.tolist(), margin_fixed={k: np.round(v, 5).tolist() for k, v in mf.items()},
                            margin_resolved={k: np.round(v, 5).tolist() for k, v in mr.items()}),
               margin_ideal=m0, er_need_fixed_db=nf, er_need_resolved_db=nr,
               er_fixed_db=er_fixed, er_required_db=er_req, er_hardest_function=fn_hard,
               order=order, fit_err=fit_err, er_analytic_db=er_analytic, per_input_ratio=per_input,
               interface_draft=spec,                                   # 草稿；整合後的介面規格在 M1 s5
               checks=dict(resolve_not_worse=all(b >= a - 1e-6 for k in mf for a, b in zip(mf[k], mr[k])),
                           er_found=all(v is not None for v in nr.values()), er_reduced=bool(er_req < er_fixed),
                           bound_fits=bool(max(fit_err.values()) < 0.01),
                           per_input_ok=bool(min(per_input.values()) >= MARGIN_KEEP - 0.01)))
    paths.OUT(STEP, "interface_v2.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"消光比（保留 {MARGIN_KEEP:.0%} margin）：沿用原相位 {nf} → ≥ {er_fixed} dB")
    print(f"                         重新求相位（0.5 dB 格點）{nr}")
    print(f"解析近似 margin≈(1−a0)^n m0：n＝{order}（與格點結果最大差 {max(fit_err.values()):.4f}）→ 需求 {er_analytic} → ≥ {er_req} dB（{fn_hard}）")
    print(f"各路不同殘留（8 組）重解後最差 margin 比例：{per_input}")
    for x in spec:
        print(f"介面：{x['item']}：{x['need']}")
    print("檢查：", res["checks"])


if __name__ == "__main__":
    main()
