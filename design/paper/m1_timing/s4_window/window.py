r"""論文 M1 s4：10 Gb/s 取樣窗——輸入轉態時的干涉、skew、消光比與晶片內路徑差會吃掉多少取樣窗。

用途：用時域模型把 M1 s1 的一階估計換成完整計算（晶片只有 heater MZI，輸入相位假設已由 M1 s3 追蹤）：
  - 輸入：x1–x4 是光場開關，邊緣為升餘弦（10–90% 轉態 t_tx），「0」為殘留 a0·e^{iψ}；R 不調變。
    資料序列：16 種輸入的 de Bruijn 序列 B(16, 3)（4096 個符號，任意連續三個符號的組合都恰好出現一次），循環。
  - 每路輸入有延遲 τ_j ∈ [0, S]（S＝skew 範圍），取角落 {0, S} 中最差的（只對會影響判讀的輸入：二輸入函數 x1、x2，四輸入函數 x1–x4）。
  - 晶片：路徑層級的延遲模型。光場逐欄傳過 B7：同一欄裡，走 MZI 的兩條軌先經 2×2 矩陣 a²T(θ, φ) 混合（兩臂等長），
    再比直通多延遲一段（課程 M3 s1 的每欄長度差）；扇入、扇出依課程 M3 s3 的長度延遲。共同延遲不影響判讀，
    每一處都扣掉最短者，只保留相對延遲。延遲以線性內插實作；靜態時（輸入不變）逐欄傳遞的結果要等於 B7 矩陣 U（自動核對）。
    載波相位不另外加：假設各路相位已由校正（M1 s3）對好，這裡只看包絡延遲。
  - 偵測 ΔP(t)＝|y2|²−|y4|²，經接收端濾波（二階 Butterworth，B_rx）。
  - 動態 margin m(t)：取樣相位 t（從符號起點算 0–2 UI）時，所有符號中最差的 s·ΔP。取樣需要 T_req 的時間，
    有效 margin＝最佳的 T_req 寬窗內 m(t) 的最小值 m_win；功率代價＝10 log10(m0／m_win)（m0 是靜態 margin）。
    這個換算假設雜訊不隨光功率變（M1 s1：熱雜訊加比較器雜訊占總雜訊的 99%，假設成立）；skew 的容許值取「skew 額外造成的代價 ≤ 1 dB」。
  - 兩種情況：理想消光比；消光比用 M1 s2 的規格（依殘留重新求相位，ψ 取靜態最差的方向）。
  - 數值檢查：在代價最大的情況，把時間格點從 0.5 ps 縮為 0.25 ps 重算。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、design/paper/m1_timing/s1_budget/out/budget.json（t_tx、B_rx、T_req、雜訊組成）、
      design/paper/m1_timing/s2_interface/out/interface_v2.json（消光比規格）、
      design/m3_layout/s1_core/out/layout_info.json、delivery/interfaces/chip_info.json（路徑長度）。
輸出：design/paper/m1_timing/s4_window/out/window.json。
執行：.\lab design\paper\m1_timing\s4_window\window.py（約 5 分鐘）
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
from scipy import signal                                             # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import R_AMP, READ, T                                 # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import A2, b7 as b7_matrix, load_phases                   # noqa: E402  含 MMI 損耗的 B7（M1 共用模型）

STEP = "paper/m1_timing/s4_window"
DT = 0.5                                                             # 時間格點（ps）
SKEWS = [0, 5, 10, 15, 20, 25, 30, 35, 40]                           # skew 範圍 S（ps）
PSIS = (0.0, np.pi / 2, np.pi, 3 * np.pi / 2)
TARGET = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
BITS = np.array(list(itertools.product([0, 1], repeat=4)))


def debruijn(k=16, n=3):
    """de Bruijn 序列 B(k, n)：長 kⁿ，任意連續 n 個符號的組合恰好出現一次（循環）。"""
    a = [0] * k * n
    seq = []

    def db(t, p):
        if t > n:
            if n % p == 0:
                seq.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    return seq


def signs(fn, f):
    idx = [int(u[1]) - 1 for u in f["uses"]]
    return np.array([1 if TARGET[fn](b[idx]) else -1 for b in BITS])


def used(f):
    return [int(u[1]) - 1 for u in f["uses"]] if len(f["uses"]) < 4 else [0, 1, 2, 3]


def vecs(a0, psi):
    x = np.where(BITS == 1, 1.0 + 0j, a0 * np.exp(1j * psi))
    return np.hstack([x, np.full((16, 1), R_AMP + 0j)])


def resolve(x0, v, s):
    mk = lambda z: b7_matrix(z[:7], z[7:14])                          # noqa: E731

    def cons(z):
        return s * deltas(mk(z[:-1]), v, READ) - z[-1]
    z0 = np.append(x0, np.min(s * deltas(mk(x0), v, READ)))
    r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)],
                 options=dict(maxiter=400, ftol=1e-10))
    return r.x[:-1], float(np.min(s * deltas(mk(r.x[:-1]), v, READ)))


def geometry(ps_per_um):
    """路徑層級的相對延遲（ps）：每欄 MZI 軌比直通多的延遲、扇入與扇出（各扣掉最短者）。"""
    L = json.loads(paths.OUT("m3_layout/s1_core", "layout_info.json").read_text(encoding="utf-8"))
    C = json.loads((paths.ROOT / "delivery" / "interfaces" / "chip_info.json").read_text(encoding="utf-8"))
    g = L["geometry"]
    cols = []
    for c in range(1, g["columns"] + 1):
        mz = sorted((p for p in L["placement"] if p["layer"] == c), key=lambda p: p["mzi"])
        cols.append([(int(p["mzi"].split("-")[1]) - 1, p["waveguides"][0] - 1) for p in mz])   # (MZI 索引, 上方軌索引)
    fin = np.array([C["fan_in_len_um"][f"in{r}"] for r in range(5)])
    fout = np.array([C["fan_out_len_um"][f"out{r}"] for r in range(5)])
    return dict(cols=cols, extra_ps=g["rail_vs_bypass_extra_um"] * ps_per_um,
                fan_in_ps=(fin - fin.min()) * ps_per_um, fan_out_ps=(fout - min(fout[READ[0]], fout[READ[1]])) * ps_per_um)


def delay(x, tau):
    """週期訊號延遲 tau（ps）：整數格點平移＋線性內插。"""
    if abs(tau) < 1e-12:
        return x
    k = tau / DT
    n = int(np.floor(k))
    fr = k - n
    return (1 - fr) * np.roll(x, n) + fr * np.roll(x, n + 1)


def propagate(x, theta, phi, geo):
    """x：(N, 5) 各軌輸入光場；逐欄傳過 B7，回傳 (N, 5) 輸出光場。"""
    y = [delay(x[:, r], geo["fan_in_ps"][r]) for r in range(5)]
    for col in geo["cols"]:
        busy = set()
        for k, r in col:
            t = A2 * T(theta[k], phi[k])
            a, b = y[r], y[r + 1]
            y[r], y[r + 1] = t[0, 0] * a + t[0, 1] * b, t[1, 0] * a + t[1, 1] * b
            busy |= {r, r + 1}
        for r in busy:                                               # 走 MZI 的軌比直通多一段延遲
            y[r] = delay(y[r], geo["extra_ps"])
    return np.stack([delay(y[r], geo["fan_out_ps"][r]) for r in range(5)], axis=1)


class Sim:
    def __init__(self, ui, t_tx, b_rx, seq, dt=DT):
        global DT
        DT = dt
        self.dt = dt
        self.ui, self.seq = ui, np.array(seq)
        self.n_ui = int(round(ui / dt))
        self.N = len(seq) * self.n_ui
        self.t = np.arange(self.N) * dt
        self.T_rc = t_tx / 0.5903                                    # 升餘弦：10–90% 時間＝0.5903 × 全寬
        b, a = signal.butter(2, 2 * np.pi * b_rx * 1e9, analog=True)
        self.bz, self.az = signal.bilinear(b, a, fs=1 / (dt * 1e-12))
        self.cache = {}

    def envelope(self, j, tau):
        """第 j 路的開關波形（0→1 之間），延遲 tau（ps），循環邊界；結果快取。"""
        key = (j, round(tau, 6))
        if key not in self.cache:
            bits = BITS[self.seq][:, j].astype(float)
            n = len(bits)
            prev = np.roll(bits, 1)
            tt = (self.t - tau) % (n * self.ui)
            k = np.floor(tt / self.ui).astype(int)
            w = np.clip((tt - k * self.ui) / self.T_rc, 0, 1)
            self.cache[key] = prev[k] + (bits[k] - prev[k]) * (1 - np.cos(np.pi * w)) / 2
        return self.cache[key]

    def run(self, theta, phi, geo, s_sym, taus, a0=0.0, psi=0.0, dphi=None):
        """回傳取樣相位 0–2 UI 的動態 margin m(t)。dphi：x1–x4 的輸入相位偏差（rad，M1 s5 聯合驗收用；預設無）。"""
        x = np.zeros((self.N, 5), complex)
        z = a0 * np.exp(1j * psi)
        for j in range(4):
            x[:, j] = z + (1 - z) * self.envelope(j, taus[j])
        x[:, 4] = R_AMP
        if dphi is not None:
            x[:, :4] *= np.exp(1j * np.asarray(dphi))
        y = propagate(x, theta, phi, geo)
        dp = np.abs(y[:, READ[0]]) ** 2 - np.abs(y[:, READ[1]]) ** 2
        f = signal.lfilter(self.bz, self.az, np.concatenate([dp, dp]))[self.N:]   # 先跑一輪去掉暫態
        idx = (np.arange(len(self.seq))[:, None] * self.n_ui + np.arange(2 * self.n_ui)[None, :]) % self.N
        return np.min(s_sym[self.seq][:, None] * f[idx], axis=0)

    def best_window(self, m, t_req):
        """在 0–2 UI 的取樣相位中找寬 t_req 的窗，窗內最小值最大者；回傳 (m_win, 起點 ps)。"""
        n_req = int(np.ceil(t_req / self.dt - 1e-9)) + 1                # 端點都算：跨 t_req 需要 t_req/dt＋1 個格點
        w = np.array([m[i:i + n_req].min() for i in range(len(m) - n_req + 1)])
        i = int(np.argmax(w))
        return float(w[i]), i * self.dt


def main():
    ph = load_phases()                                               # 含 MMI 損耗、重新校正後的相位（model.py）
    s1 = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))
    s2 = json.loads(paths.OUT("paper/m1_timing/s2_interface", "interface_v2.json").read_text(encoding="utf-8"))
    t = s1["timing"]
    ui, t_tx, b_rx, t_req = t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], t["t_req_ps"]
    geo = geometry(t["ps_per_um"])
    er = s2["er_required_db"]
    a0 = 10 ** (-er / 20)
    seq = debruijn(16, 3)
    sim = Sim(ui, t_tx, b_rx, seq)
    # 靜態核對：輸入不變時，逐欄傳遞＝B7 矩陣
    rng = np.random.default_rng(rt.MC_SEED_BASE)
    xc = rng.normal(size=5) + 1j * rng.normal(size=5)
    dc_err = 0.0
    for f in ph["functions"].values():
        th, pp = np.array(f["theta"]), np.array(f["phi"])
        yy = propagate(np.tile(xc, (8, 1)), th, pp, dict(geo, fan_in_ps=np.zeros(5), fan_out_ps=np.zeros(5), extra_ps=0.0))
        dc_err = max(dc_err, float(np.max(np.abs(yy[0] - b7_matrix(th, pp) @ xc))))
    out, worst_case = {}, None
    for fn, f in ph["functions"].items():
        s = signs(fn, f)
        x0 = np.concatenate([f["theta"], f["phi"]])
        cols = used(f)
        corners = []
        for c in itertools.product([0, 1], repeat=len(cols)):
            v = np.zeros(4)
            v[cols] = c
            corners.append(v)
        best = None                                                  # 消光比：ψ 取重新求相位後靜態 margin 最差者
        for psi in PSIS:
            xr, mr = resolve(x0, vecs(a0, psi), s)
            if best is None or mr < best[1]:
                best = (xr, mr, psi)
        cases = {"ideal": (np.array(f["theta"]), np.array(f["phi"]), 0.0, 0.0),
                 "er": (best[0][:7], best[0][7:], a0, best[2])}
        res = {}
        for cname, (th, pp, aa, psi) in cases.items():
            m0 = float(np.min(s * deltas(b7_matrix(th, pp), vecs(aa, psi), READ)))
            rows, curve0, curve20 = [], None, None
            for S in SKEWS:
                worst = None
                for c in (corners if S > 0 else corners[:1]):
                    m = sim.run(th, pp, geo, s, c * S, aa, psi)
                    mw, t0 = sim.best_window(m, t_req)
                    if worst is None or mw < worst[0]:
                        worst = (mw, t0, m, c * S)
                pen = 10 * np.log10(m0 / worst[0]) if worst[0] > 0 else None
                rows.append(dict(skew_ps=S, m_win=round(worst[0], 5), penalty_db=None if pen is None else round(pen, 3),
                                 window_start_ps=worst[1]))
                if S == 0:
                    curve0 = worst[2]
                if S == 20:
                    curve20 = worst[2]
                    if cname == "ideal" and pen is not None and (worst_case is None or pen > worst_case[0]):
                        worst_case = (pen, fn, th, pp, s, worst[3], m0)
            res[cname] = dict(m0=m0, rows=rows, curve_skew0=np.round(curve0, 5).tolist(), curve_skew20=np.round(curve20, 5).tolist())
        out[fn] = res
        r0 = res["ideal"]["rows"]
        print(f"{fn}：靜態 m0 {res['ideal']['m0']:.3f}；功率代價（理想消光比）" +
              "、".join(f"{r['skew_ps']}ps {r['penalty_db'] if r['penalty_db'] is not None else '∞'}" for r in r0) +
              f"；消光比 {er:g} dB 時 skew 0 代價 {res['er']['rows'][0]['penalty_db']}、20 ps {res['er']['rows'][4]['penalty_db']}", flush=True)

    # 晶片內路徑差的影響：同一模型把晶片內延遲設為 0 再算 skew 0，與上面比較
    geo0 = dict(geo, fan_in_ps=np.zeros(5), fan_out_ps=np.zeros(5), extra_ps=0.0)
    chip = {}
    for fn, f in ph["functions"].items():
        th, pp = np.array(f["theta"]), np.array(f["phi"])
        m0 = out[fn]["ideal"]["m0"]
        mw0, _ = sim.best_window(sim.run(th, pp, geo0, signs(fn, f), np.zeros(4)), t_req)
        chip[fn] = round(out[fn]["ideal"]["rows"][0]["penalty_db"] - 10 * np.log10(m0 / mw0), 4)
    # 格點收斂：代價最大的情況（skew 20 ps 的最差角落），0.5 → 0.25 ps
    pen5, wfn, th, pp, s, taus, m0 = worst_case
    fine = Sim(ui, t_tx, b_rx, seq, dt=0.25)
    mwf, _ = fine.best_window(fine.run(th, pp, geo, s, taus), t_req)
    pen25 = 10 * np.log10(m0 / mwf)

    def skew_at(case, db):
        """各函數「skew 額外造成的代價」（相對 skew＝0）達 db 時的 skew（線性內插），取最小與最難的函數。"""
        best = (1e9, None)
        for fn in out:
            rows = out[fn][case]["rows"]
            sk = [r["skew_ps"] for r in rows]
            pe = [(r["penalty_db"] if r["penalty_db"] is not None else 99) - rows[0]["penalty_db"] for r in rows]
            v = sk[-1]
            for k in range(1, len(sk)):
                if pe[k] >= db:
                    v = sk[k - 1] + (db - pe[k - 1]) / (pe[k] - pe[k - 1]) * (sk[k] - sk[k - 1])
                    break
            if v < best[0]:
                best = (v, fn)
        return best
    res = dict(ui_ps=ui, t_tx_ps=t_tx, rx_bw_ghz=b_rx, t_req_ps=t_req, dt_ps=0.5, n_symbols=len(seq), er_db=er,
               skews_ps=SKEWS, functions=out, first_order_allow_ps=t["skew_allow_ps"],
               chip_spread_ps=t["readout"]["spread_ps"], chip_penalty_db=chip, chip_bound_db=round(max(abs(v) for v in chip.values()), 4),
               dc_check_err=dc_err, grid=dict(function=wfn, skew_ps=20, penalty_05=round(pen5, 3), penalty_025=round(pen25, 3),
                                              diff_db=round(pen25 - pen5, 3)),
               thermal_share=s1["power"]["thermal_share"],
               skew_at_1db_ideal=round(skew_at("ideal", 1.0)[0], 1), skew_at_1db_fn=skew_at("ideal", 1.0)[1],
               skew_at_db={str(x): round(skew_at("ideal", x)[0], 1) for x in (0.5, 1.0, 2.0)},
               skew_at_db_fn={str(x): skew_at("ideal", x)[1] for x in (0.5, 1.0, 2.0)},
               skew_at_1db_er=round(skew_at("er", 1.0)[0], 1),
               er_extra_db_max=round(max(abs(out[f]["er"]["rows"][k]["penalty_db"] - out[f]["ideal"]["rows"][k]["penalty_db"])
                                         for f in out for k in range(len(SKEWS))
                                         if out[f]["er"]["rows"][k]["penalty_db"] is not None
                                         and out[f]["ideal"]["rows"][k]["penalty_db"] is not None), 3),
               penalty0_max_ideal=max(out[f]["ideal"]["rows"][0]["penalty_db"] or 99 for f in out),
               penalty0_max_er=max(out[f]["er"]["rows"][0]["penalty_db"] or 99 for f in out))
    res["checks"] = dict(window_exists_at_0=all(out[f]["ideal"]["rows"][0]["m_win"] > 0 for f in out),
                         er_window_exists_at_0=all(out[f]["er"]["rows"][0]["m_win"] > 0 for f in out),
                         dc_matches_U=bool(dc_err < 1e-12), grid_converged=bool(abs(pen25 - pen5) < 0.05),
                         penalty_from_margin_ok=bool(s1["power"]["thermal_share"] > 0.9))
    paths.OUT(STEP, "window.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"skew 0 時最大代價：理想 {res['penalty0_max_ideal']} dB、消光比 {er:g} dB {res['penalty0_max_er']} dB；"
          f"skew 額外代價達 1 dB：理想 {res['skew_at_1db_ideal']} ps（{res['skew_at_1db_fn']}）、消光比 {res['skew_at_1db_er']} ps"
          f"（一階估計 {t['skew_allow_ps']} ps）；消光比造成的差最多 {res['er_extra_db_max']} dB")
    print(f"晶片內路徑差造成的代價 {chip}；靜態核對誤差 {dc_err:.1e}；格點 {wfn} skew 20 ps：0.5 ps {pen5:.3f} dB、0.25 ps {pen25:.3f} dB")
    print("檢查：", res["checks"])


if __name__ == "__main__":
    main()
