r"""論文 M1 s3：輸入相位追蹤——只用晶片上原有的 heater MZI，能不能追上 5 路輸入光之間的相位漂移。

用途：把「追蹤」拆成三個可以計算的問題（晶片不加任何元件，資料照常傳送）：
  1. 補得回來嗎：輸入相位漂移 δ（以 R 為基準）等於在 U 右邊乘上 diag(e^{iδ})。只調 7 個外相位 φ（θ 不動），
     從原相位出發重新求 margin，看能否回到無漂移時的 margin。
  2. 量得出來嗎：比較兩種量法對 δ 的 Jacobian 秩（等於要分辨的相位數才行）：
     (a) 盲量：只看隨機資料下 5 個輸出的平均功率 P̄；
     (b) 擾動：每個 φ heater 加一個小擺動（各用不同頻率），用同步偵測量出 ∂P̄/∂φ（5×7 個值），連同 P̄ 一起看。
     最佳相位下 P̄ 對 δ 的一階變化多半是 0（干涉項在極值），所以 (a) 不夠；∂P̄/∂φ 對 δ 是一階，(b) 可以。
     再用 Gauss-Newton 由（含雜訊的）量測反求 δ，套用到「只調 φ」的補償，檢查 margin 是否回復。
  3. 追得上嗎：擾動量測的雜訊（資料圖樣造成的功率起伏＋接收端雜訊，沿用課程與 M1 s1）決定要平均多久；
     擾動頻率受 heater 熱時間常數限制。由量測時間得到回授頻寬 f_L，殘餘誤差約 A·f／f_L，求相位偏差不超過 M1 s1 的確定性容許（margin 保留 90%）時容許的擾動。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、design/m2_circuit/s1_spec/out/tolerance.json（σ）、
      design/paper/m1_timing/s1_budget/out/budget.json（接收端雜訊與功率）。
輸出：design/paper/m1_timing/s3_tracking/out/tracking.json。
執行：.\lab design\paper\m1_timing\s3_tracking\track.py（約 2 分鐘）
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

STEP = "paper/m1_timing/s3_tracking"
ASSUME = dict(
    comp_sigma_rad=0.5,       # 補償測試：每路漂移的標準差（遠大於容許的 0.1 rad）
    est_sigma_rad=0.3,        # 估計測試：兩次更新之間的漂移（回授持續運作時遠小於此）
    n_trials=20,              # 每個函數的漂移樣本數
    dither_keep=0.97,         # 擺動幅度的選法：7 個 heater 同時擺動時，各函數 margin 至少保留 97%
    eps_scan=(0.003, 0.1),    # 擺動幅度掃描範圍（rad）
    est_target_rad=0.01,      # 每次估計的相位誤差目標（各方向的標準差；3 倍計入相位預算）
    tau_heater_us=20.0,       # TiN heater 的熱時間常數（SOI 上典型 10–40 µs）
    dither_ratio=4.0,         # 擺動頻率取 heater 頻寬的 1/4
    min_periods=10,           # 同步偵測至少平均 10 個擺動週期
    bit_rate_gbps=10.0,
)
TARGET = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
BITS = np.array(list(itertools.product([0, 1], repeat=4)))
V = np.hstack([BITS.astype(complex), np.full((16, 1), R_AMP + 0j)])   # 16 組輸入光場（隨機資料時等機率）


def signs(fn, f):
    idx = [int(u[1]) - 1 for u in f["uses"]]
    return np.array([1 if TARGET[fn](b[idx]) else -1 for b in BITS])


def used(f):
    """會影響判讀的輸入：二輸入函數只有 x1、x2（x3、x4 的光不進判讀埠，相位不影響結果）。"""
    return [int(u[1]) - 1 for u in f["uses"]] if len(f["uses"]) < 4 else [0, 1, 2, 3]


def drift(d, cols=range(4)):
    v = np.zeros(4)
    v[list(cols)] = d
    return np.diag(np.exp(1j * np.append(v, 0.0)))


def margin(U, s):
    return float(np.min(s * deltas(U, V, READ)))


def resolve_phi(theta, phi0, D, s):
    """只調 7 個外相位 φ（θ 固定），從原相位出發最大化 margin（SLSQP）；回傳 φ。"""
    mk = lambda p: b7_matrix(theta, p) @ D                            # noqa: E731

    def cons(z):
        return s * deltas(mk(z[:-1]), V, READ) - z[-1]
    z0 = np.append(phi0, margin(mk(phi0), s))
    r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)],
                 options=dict(maxiter=400, ftol=1e-12))
    return r.x[:-1]


def pbar(theta, phi, D):
    """隨機資料下 5 個輸出的平均功率。"""
    return np.mean(np.abs(V @ (b7_matrix(theta, phi) @ D).T) ** 2, axis=0)


def dither(theta, phi, D, h=1e-5):
    """同步偵測量到的 ∂P̄/∂φ_k（5×7），攤平；與 P̄ 一起回傳。"""
    g = []
    for k in range(7):
        e = np.zeros(7)
        e[k] = h
        g.append((pbar(theta, phi + e, D) - pbar(theta, phi - e, D)) / (2 * h))
    return np.concatenate([pbar(theta, phi, D), np.array(g).T.ravel()])


def jac(fun, cols, h=1e-4):
    return np.array([(fun(drift([h], [j])) - fun(drift([-h], [j]))) / (2 * h) for j in cols]).T


def rank_of(J):
    sv = np.linalg.svd(J, compute_uv=False)
    return int(np.sum(sv > 1e-6)), sv                                # 絕對門檻：單位 P_u／rad，1e-6 以下視為 0


def estimate(meas, model, cols, iters=12):
    """Gauss-Newton：由量測反求 δ（從 0 出發）。"""
    d = np.zeros(len(cols))
    for _ in range(iters):
        f0 = model(drift(d, cols))
        J = np.array([(model(drift(d + h, cols)) - model(drift(d - h, cols))) / 2e-4
                      for h in np.eye(len(cols)) * 1e-4]).T
        step = np.linalg.lstsq(J, meas - f0, rcond=None)[0]
        d = d + step
        if np.max(np.abs(step)) < 1e-9:
            break
    return d


def sim_ratio(th, p0, s, m0, e):
    """7 個 heater 同時擺動（各用不同頻率，相位組合都會出現）時的最差 margin 比例：取 2⁷ 個 ±ε 角落中最差。"""
    return min(margin(b7_matrix(th, p0 + e * np.array(c)), s) / m0 for c in itertools.product([-1, 1], repeat=7))


def main():
    A = ASSUME
    ph = load_phases()                                               # 含 MMI 損耗、重新校正後的相位（model.py）
    s1 = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))
    sig = float(s1["phase"]["det_rad"])                               # 漂移是固定偏差：用 M1 s1 的確定性容許，不用隨機 σ
    # 相位預算分配：δ_det 是固定偏差的容許量，三項可能同向，所以用幅度相加（不用平方和）：
    # 估計誤差（3 倍標準差，視為上界）＋追蹤落後＋快速擾動 ≤ δ_det；後兩者平分剩下的部分
    est3 = 3 * A["est_target_rad"]
    lag = fast = float((sig - est3) / 2)
    a, pw = s1["assume"], s1["power"]
    eta = 10 ** (-(pw["prop_db"] + pw["ec_loss_db"]) / 10)
    pu_w = 10 ** (pw["pu_core_dbm"] / 10) * 1e-3
    rx_noise = pw["noise_ua"] * 1e-6 / a["resp_a_w"] / (pu_w * eta)   # 每個樣本的接收端雜訊（P_u）
    funcs = {fn: (np.array(f["theta"]), np.array(f["phi"]), signs(fn, f)) for fn, f in ph["functions"].items()}
    m0s = {fn: margin(b7_matrix(th, p0), s) for fn, (th, p0, s) in funcs.items()}
    # 擺動幅度：先掃描「7 個同時擺動」時的 margin 損失，選損失 ≤ dither_keep 的最大 ε
    eps = np.logspace(np.log10(A["eps_scan"][0]), np.log10(A["eps_scan"][1]), 25)
    pen_e = [min(sim_ratio(th, p0, s, m0s[fn], e) for fn, (th, p0, s) in funcs.items()) for e in eps]
    ok = [e for e, r in zip(eps, pen_e) if r >= A["dither_keep"]]
    eps0 = float(max(ok))
    rng = np.random.default_rng(rt.MC_SEED_BASE)
    res_fn = {}
    for fn, f in ph["functions"].items():
        th, p0, s = funcs[fn]
        U = b7_matrix(th, p0)
        m0 = m0s[fn]
        cols = used(f)
        # 1. 補償
        before, after = [], []
        for _ in range(A["n_trials"]):
            D = drift(rng.normal(0, A["comp_sigma_rad"], 4))
            before.append(margin(U @ D, s) / m0)
            after.append(margin(b7_matrix(th, resolve_phi(th, p0, D, s)) @ D, s) / m0)
        # 2. 可觀測性（5 個輸出都有監測偵測器；另算只用判讀埠 o2、o4 的情況）
        rb, _ = rank_of(jac(lambda D: pbar(th, p0, D), cols))
        Jd = jac(lambda D: dither(th, p0, D), cols)
        rd, sv = rank_of(Jd)
        gain = float(np.linalg.norm(np.linalg.pinv(Jd, rcond=1e-6), 2))
        rows_rd = [1, 3] + [5 + 7 * o + k for o in (1, 3) for k in range(7)]      # P̄2、P̄4 與它們對 7 個 φ 的斜率
        Jr = Jd[rows_rd]
        rd_r, _ = rank_of(Jr)
        gain_r = float(np.linalg.norm(np.linalg.pinv(Jr, rcond=1e-6), 2))
        # 3. 雜訊：資料圖樣造成的功率起伏＋接收端雜訊（逐位元獨立，需隨機資料，例如 PRBS 或擾碼）。
        #    平均 N 位元時，P̄ 的雜訊 σ_tot／√N，擺動 ε 的斜率雜訊 √2 σ_tot／(ε √N)；估計誤差（各方向的標準差）≤ est_target
        sig_bit = float(np.max(np.std(np.abs(V @ U.T) ** 2, axis=0)))
        sig_tot = float(np.hypot(sig_bit, rx_noise))
        n_bits = int(np.ceil(2 * (gain * sig_tot / (eps0 * A["est_target_rad"])) ** 2))
        n_bits_r = int(np.ceil(2 * (gain_r * sig_tot / (eps0 * A["est_target_rad"])) ** 2))
        sig_g = np.sqrt(2) * sig_tot / (eps0 * np.sqrt(n_bits))
        sig_p = sig_tot / np.sqrt(n_bits)
        err, comp_est = [], []
        for _ in range(A["n_trials"]):
            dt = rng.normal(0, A["est_sigma_rad"], len(cols))
            meas = dither(th, p0, drift(dt, cols))
            meas = meas + np.concatenate([rng.normal(0, sig_p, 5), rng.normal(0, sig_g, 35)])
            de = estimate(meas, lambda D: dither(th, p0, D), cols)
            err.extend((de - dt).tolist())
            ph_hat = resolve_phi(th, p0, drift(de, cols), s)
            comp_est.append(margin(b7_matrix(th, ph_hat) @ drift(dt, cols), s) / m0)
        res_fn[fn] = dict(m0=m0, n_phase=len(cols), comp_before=np.round(before, 4).tolist(), comp_after=np.round(after, 4).tolist(),
                          comp_before_min=float(min(before)), comp_after_min=float(min(after)),
                          n_wrong_before=int(sum(b <= 0 for b in before)),
                          rank_blind=rb, rank_dither=rd, rank_readout_only=rd_r, dither_sv=[float(f"{x:.4g}") for x in sv],
                          gain=gain, gain_readout_only=gain_r, sig_bit=sig_bit, n_bits=n_bits, n_bits_readout_only=n_bits_r,
                          est_err_max=float(np.max(np.abs(err))), est_err_rms=float(np.sqrt(np.mean(np.square(err)))),
                          comp_est_min=float(min(comp_est)), dither_margin=float(sim_ratio(th, p0, s, m0, eps0)),
                          dither_margin_single=float(min(margin(b7_matrix(th, p0 + sg * eps0 * np.eye(7)[k]), s) / m0
                                                         for k in range(7) for sg in (1, -1))))
    # 追蹤頻寬
    f_h = 1 / (2 * np.pi * A["tau_heater_us"] * 1e-6)
    f_d = f_h / A["dither_ratio"]

    def loop(nb):
        t_noise = nb / (A["bit_rate_gbps"] * 1e9)
        t_meas = max(t_noise, A["min_periods"] / f_d)
        return t_noise, t_meas, 1 / (2 * np.pi * t_meas)
    n_max = max(r["n_bits"] for r in res_fn.values())
    t_noise, t_meas, f_L = loop(n_max)
    f_L_r = loop(max(r["n_bits_readout_only"] for r in res_fn.values()))[2]
    worst_g = max(r["gain"] * np.hypot(r["sig_bit"], rx_noise) for r in res_fn.values())
    t_e = np.maximum(2 * (worst_g / (eps * A["est_target_rad"])) ** 2 / (A["bit_rate_gbps"] * 1e9), A["min_periods"] / f_d)
    res = dict(assume=A, det_rad=sig, rx_noise_pu=float(f"{rx_noise:.4g}"), functions=res_fn, dither_rad=round(eps0, 4),
               phase_alloc=dict(est_3sigma_rad=est3, lag_rad=round(lag, 4), fast_rad=round(fast, 4),
                                sum_rad=round(float(est3 + lag + fast), 4)),
               heater_bw_hz=round(f_h, 1), dither_hz=round(f_d, 1), bits_needed=n_max, t_noise_ms=round(t_noise * 1e3, 4),
               t_meas_ms=round(t_meas * 1e3, 3), loop_bw_hz=round(f_L, 2), loop_bw_readout_only_hz=round(f_L_r, 2),
               ramp_rate_allow_rad_s=round(lag * 2 * np.pi * f_L, 3),
               fiber_ramp_rad_s=round(s1["phase"]["cases"][2]["rad_per_K"] * 0.1 / 60, 4),    # 1 m 光纖、溫差每分鐘 0.1 K
               eps_scan=dict(eps_rad=eps.tolist(), loop_bw_hz=[float(f"{x:.4g}") for x in 1 / (2 * np.pi * t_e)],
                             margin_during=[round(float(x), 5) for x in pen_e]),
               checks=dict(phi_only_restores=all(r["comp_after_min"] > 0.999 for r in res_fn.values()),
                           blind_insufficient=all(r["rank_blind"] < r["n_phase"] for r in res_fn.values()),
                           dither_full_rank=all(r["rank_dither"] == r["n_phase"] for r in res_fn.values()),
                           readout_only_full_rank=all(r["rank_readout_only"] == r["n_phase"] for r in res_fn.values()),
                           estimate_rms_ok=all(r["est_err_rms"] <= 1.5 * A["est_target_rad"] for r in res_fn.values()),
                           tracked_margin_ok=all(r["comp_est_min"] > 0.95 for r in res_fn.values()),
                           alloc_ok=bool(est3 + lag + fast <= sig + 1e-9)))
    paths.OUT(STEP, "tracking.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for fn, r in res_fn.items():
        print(f"{fn}：漂移 σ {A['comp_sigma_rad']} rad 時 margin 最差 {r['comp_before_min']:.2f}（判錯 {r['n_wrong_before']}/{A['n_trials']}）"
              f" → 只調 φ 後 {r['comp_after_min']:.4f}；分辨 {r['n_phase']} 個相位：盲量秩 {r['rank_blind']}、擾動秩 {r['rank_dither']}"
              f"（只用 o2、o4：{r['rank_readout_only']}）；需平均 {r['n_bits']:.3g} 位元；估計誤差 rms {r['est_err_rms']:.4f}、最大 {r['est_err_max']:.4f} rad；"
              f"估計後補償 margin 最差 {r['comp_est_min']:.4f}；7 個同時擺動時 margin {r['dither_margin']:.4f}")
    print(f"擺動幅度 {eps0:.4f} rad（同時擺動損失 ≤ {1 - A['dither_keep']:.0%}）；heater {f_h:.0f} Hz、擺動 {f_d:.0f} Hz；量測 {t_meas * 1e3:.3g} ms → 回授 {f_L:.2f} Hz"
          f"（只用 o2、o4：{f_L_r:.2f} Hz）")
    print(f"相位預算：估計 3σ {est3:.3f}＋追蹤落後 {lag:.3f}＋快速擾動 {fast:.3f}（幅度相加 {res['phase_alloc']['sum_rad']} ≤ {sig}）；"
          f"容許斜率 {res['ramp_rate_allow_rad_s']} rad/s（1 m 光纖每分鐘 0.1 K 約 {res['fiber_ramp_rad_s']} rad/s）")
    print("檢查：", res["checks"])

if __name__ == "__main__":
    main()
