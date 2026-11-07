r"""論文 M4 s2：葉盒下界與時變雜訊界——給一個延遲盒，判讀量的保守下界（草稿式 7–8、III-E；補充資料 S1 步驟 1–6）。

用途：
  1. 葉盒下界（式 7）：延遲盒 𝒟＝∏[−r, r]（r＝6.6 ps）切成葉盒 ℓ（中心 c_ℓ、半寬 ρ_ℓ）；以葉中心的包絡 x̂_ℓ 為基準，
     D(x̂＋e)＝D(x̂)＋gᵀe＋eᵀQe（M4 s1 的二次式，g＝l＋2Qx̂），e_i＝−Δδ_i ẋ_i＋η_i，|η_i| ≤ ρ_i²·sup|ẍ_i|／2、|e_i| ≤ ε_i＝min(1, ρ_i·sup|ẋ_i|)：
       下界 L_s(t)＝b_s(h∗D(x̂))(t) − Σ_i ρ_i |h∗(g_i ẋ_i)|(t) − (|h|∗R_ℓ)(t) − E_w，
       R_ℓ＝Σ_i |g_i| ρ_i² sup|ẍ_i|／2 ＋ εᵀ|Q|ε（式 8 左式）。一階項先經接收端濾波再取絕對值，保留濾波器內的抵消。
     sup|ẋ|、sup|ẍ| 以升餘弦邊緣的解析式在 [t−c−ρ, t−c+ρ] 上求（不靠取樣）。
     弱耦合輸入（G_i＝|l_i|＋2Σ_j|Q_ij| < 10⁻³·max G）不切，整盒的影響以 E_w＝‖h‖₁ Σ_weak G_i min(1, L_x r) 扣除。
  2. 時變雜訊界（式 8 右式）：盒內任意延遲、格內任意時刻，x_i 落在 ±⌈r/Δ⌉ 格的最小／最大值之間（再加內插誤差 |ẍ|Δ²/8），
     以區間法求 |D| 與 P_sum 的上界 → S̄_j＝(|D|＋εP_sum)² 的格上界；σ̄²(t)＝σ_c²＋c² Σ_m K_m S̄_{k−m}，
     K_m＝max_u ∫ w（w＝h²/∫h²，類比二階 Butterworth 的解析響應，細格 Δ/64，含梯形與 u 取樣誤差）；Γ̄＝|V_off|＋q σ̄。
  3. 連續時間（補充資料步驟 6）：M2＝Σ G_i C＋2L_x²Σ|Q|（|d²D/dt²| 的上界），E_in＝E_btw＝‖h‖₁ M2 Δ²/8，‖h‖₁＝(1＋e^−π)/(1−e^−π)。
  4. 驗證（本步驗收）：M3 s3 的 41 個盒內抽樣點（同一模擬器、同一序列），1 個葉盒與每路切 2 份（16 個葉盒；XOR2 只切強耦合的 2 路）：
     (a) 每個符號、每個取樣相位 b_s v_s,δ(t) ≥ L_s(t)；(b) Γ̄(t) ≥ Γ_δ(t)；(c) 細格（Δ/4）的連續時間檢查：
     5 個點的 min_s b_s v(t) ＋ 細格自身誤差 ≥ 相鄰兩節點 min_s L_s 的較小者 − E_in − E_btw。
     (a)(b) 的模擬器與下界用同一個一階保持離散，所以 (a)(b) 不含 E_in、E_btw；(c) 才檢查它們。
     輸入都不轉態的位置下界等於模擬值，所以下界固定再扣 RESERVE＝10⁻⁸ P_u 吸收浮點誤差。
輸入：design/paper/m3_align/s2_synth/out/synth.json、design/paper/m3_align/s3_detail/detail.py（模擬器與 41 個抽樣點）、
      design/paper/m4_cert/s1_quad/quad.py（二次式係數）、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：design/paper/m4_cert/s2_leaf/out/leaf.json、curves_AND4.npz、curves_MAJ4.npz、curves_XOR2.npz（圖用）；M4 s3 import 本檔的 bound()、guard_box()、errors()。
執行：.\lab design\paper\m4_cert\s2_leaf\leaf.py（3 個 worker 約 20 秒）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s1_quad"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s3_detail"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s2_synth"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy import signal                                             # noqa: E402
from scipy.ndimage import maximum_filter1d, minimum_filter1d         # noqa: E402

import paths                                                         # noqa: E402
import quad as QD                                                    # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

DT = QD.DT                                                           # M3 s3 的模擬器
STEP = "paper/m4_cert/s2_leaf"
FUNCS = DT.FUNCS                                                     # AND4、MAJ4、XOR2
R_BOX = DT.HALF_BOX                                                  # 6.6 ps
WEAK = 1e-3
RESERVE = 1e-8                                                       # P_u：浮點的固定扣除（與草稿相同）
BINS = (1, 2)
N_FINE = 5                                                           # 細格檢查的點數（中心＋4 個角落）
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
HN = (1 + math.exp(-math.pi)) / (1 - math.exp(-math.pi))            # 類比二階 Butterworth 的 ‖h‖₁（直流增益 1）


def make_sim(dt=0.5):
    S = DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    return DT.Sim(DT.sequence("euler"), S["edge_full_ps"], dt, A, 10 ** (S["pu_dbm"] / 10) * 1e-3, False)


def pair(U):
    """D 與 P_sum 的二次式係數 (d0, l, Q)。"""
    u2, u4 = U[READ[0]], U[READ[1]]
    out = []
    for sgn in (-1, 1):
        M = np.real(np.outer(u2.conj(), u2) + sgn * np.outer(u4.conj(), u4))
        out.append((R_AMP ** 2 * M[4, 4], 2 * R_AMP * M[:4, 4], M[:4, :4]))
    return out


class Rx:
    """週期穩態的接收端運算（與 M3 s3 的模擬器同一個一階保持離散）。"""

    def __init__(self, sim):
        self.sim = sim
        imp = np.zeros(sim.N)
        imp[0] = 1.0
        self.habs = np.fft.rfft(np.abs(signal.lfilter(sim.num, sim.den, imp)))
        self.idx = (np.arange(len(sim.seq))[:, None] * sim.n_ui + np.arange(2 * sim.n_ui)[None, :]) % sim.N

    def filt(self, u):
        return signal.lfilter(self.sim.num, self.sim.den, np.concatenate([u, u]))[self.sim.N:]

    def abs_conv(self, u):
        return np.fft.irfft(np.fft.rfft(u) * self.habs, self.sim.N)


def derivs(sim, j, tau, rho):
    """x_j(t−τ) 的 ẋ（在 τ），以及 [t−τ−ρ, t−τ+ρ] 上 |ẋ|、|ẍ| 的解析上界。"""
    bits = DT.BITS[sim.seq][:, j].astype(float)
    n = len(bits)
    prev = np.roll(bits, 1)
    Lx, C = math.pi / (2 * sim.edge), math.pi ** 2 / (2 * sim.edge ** 2)
    tt = (sim.t - tau) % (n * sim.ui)
    k = np.floor(tt / sim.ui).astype(int)
    w = (tt - k * sim.ui) / sim.edge
    xd = (bits[k % n] - prev[k % n]) * Lx * np.sin(np.pi * np.clip(w, 0, 1)) * (w <= 1)
    sl, cv = np.zeros(sim.N), np.zeros(sim.N)
    for sh in (-1, 0, 1):
        kk = k + sh
        ch = np.abs(bits[kk % n] - prev[kk % n])
        lo = (tt - rho - kk * sim.ui) / sim.edge
        hi = (tt + rho - kk * sim.ui) / sim.edge
        act = (hi >= 0) & (lo <= 1)
        a, b = np.clip(lo, 0, 1), np.clip(hi, 0, 1)
        smax = np.where((a <= 0.5) & (b >= 0.5), 1.0, np.maximum(np.sin(np.pi * a), np.sin(np.pi * b)))
        cmax = np.maximum(np.abs(np.cos(np.pi * a)), np.abs(np.cos(np.pi * b)))
        sl = np.maximum(sl, act * ch * Lx * smax)
        cv = np.maximum(cv, act * ch * C * cmax)
    return xd, sl, cv


def weak_inputs(l, Q):
    G = np.abs(l) + 2 * np.abs(Q).sum(1)
    return G, G < WEAK * G.max()


def leaves(weak, bins):
    act = np.flatnonzero(~weak)
    for cell in itertools.product(range(bins), repeat=len(act)):
        c, r = np.zeros(4), np.zeros(4)
        c[act] = -R_BOX + (np.array(cell) + 0.5) * 2 * R_BOX / bins
        r[act] = R_BOX / bins
        yield cell, c, r


def bound(sim, rx, U, b_sym, c, rho, weak):
    """一個葉盒的下界各項（逐符號、逐取樣相位）。回傳 dict：base、lin、rem（皆為 N 長）、E_w 與逐符號下界 L。"""
    (d0, l, Q), _ = pair(U)
    G, _ = weak_inputs(l, Q)
    X = np.stack([sim.envelope(j, c[j]) for j in range(4)], axis=1)
    base = rx.filt(QD.quad(d0, l, Q, X))
    g = l[None, :] + 2 * X @ Q
    lin = np.zeros(sim.N)
    eps = np.zeros((sim.N, 4))
    rem = np.zeros(sim.N)
    for i in range(4):
        if rho[i] == 0:
            continue
        xd, sl, cv = derivs(sim, i, c[i], rho[i])
        lin += rho[i] * np.abs(rx.filt(g[:, i] * xd))
        eps[:, i] = np.minimum(1.0, sl * rho[i])
        rem += np.abs(g[:, i]) * rho[i] ** 2 * cv / 2
    rem += np.einsum("ti,ij,tj->t", eps, np.abs(Q), eps)
    rem = rx.abs_conv(maximum_filter1d(rem, 3, mode="wrap"))         # 相鄰節點取大，再與 |h| 摺積
    Lx = math.pi / (2 * sim.edge)
    e_w = HN * float(G[weak].sum()) * min(1.0, Lx * R_BOX)
    L = b_sym[sim.seq][:, None] * base[rx.idx] - lin[rx.idx] - rem[rx.idx] - e_w - RESERVE
    return dict(base=base, lin=lin, rem=rem, e_w=e_w, L=L)


def ct_kernel(omega, dt, span_ps=2000.0, nsub=64):
    """K_m＝max_u ∫_{(m−1)Δ+u}^{mΔ+u} w，w＝h²/∫h²（類比響應），含梯形積分與 u 取樣誤差的上界。"""
    a = omega / math.sqrt(2)
    E = math.sqrt(2) * omega / 4                                     # ∫h²＝ω²/(4a)
    tf = dt / nsub
    t = np.arange(-dt, span_ps + 2 * dt + tf / 2, tf)
    w = np.where(t > 0, math.sqrt(2) * omega * np.exp(-a * t) * np.sin(a * t), 0.0) ** 2 / E
    F = np.concatenate([[0.0], np.cumsum((w[1:] + w[:-1]) / 2 * tf)])
    w1, w2 = 4 * omega ** 3 / E, 8 * omega ** 4 / E                  # |w'|、|w''| 的包絡係數
    M, i0 = int(span_ps / dt), nsub
    K = np.empty(M)
    for m in range(M):
        lo = i0 + (m - 1) * nsub
        A = F[lo + nsub: lo + 2 * nsub + 1] - F[lo: lo + nsub + 1]
        env = math.exp(-2 * a * max(0.0, (m - 1) * dt))
        K[m] = A.max() + (dt * w1 * tf / 2 + 2 * dt * w2 * tf ** 2 / 12) * env
    return K


def interval_abs(lo, hi, d0, l, Q):
    """x ∈ [lo, hi] 時 |d0＋lᵀx＋xᵀQx| 的上界。"""
    xc, r = (lo + hi) / 2, (hi - lo) / 2
    g = l[None, :] + 2 * xc @ Q
    return np.abs(QD.quad(d0, l, Q, xc)) + (np.abs(g) * r).sum(1) + np.einsum("ti,ij,tj->t", r, np.abs(Q), r)


def guard_box(sim, U):
    """整盒、格內任意時刻都成立的時變護欄 Γ̄（節點值取相鄰兩格的較大者），以及 σ̄ 的 S̄。"""
    (d0, l, Q), (s0, ls, Qs) = pair(U)
    X = np.stack([sim.envelope(j, 0.0) for j in range(4)], axis=1)
    cw = int(math.ceil(R_BOX / sim.dt - 1e-9))
    pad = math.pi ** 2 / (2 * sim.edge ** 2) * sim.dt ** 2 / 8
    lo = np.clip(minimum_filter1d(X, 2 * cw + 1, axis=0, mode="wrap") - pad, 0, 1)
    hi = np.clip(maximum_filter1d(X, 2 * cw + 1, axis=0, mode="wrap") + pad, 0, 1)
    loc, hic = np.minimum(lo, np.roll(lo, -1, 0)), np.maximum(hi, np.roll(hi, -1, 0))   # 第 k 格 [kΔ,(k+1)Δ]
    Sbar = (interval_abs(loc, hic, d0, l, Q) + sim.eps * interval_abs(loc, hic, s0, ls, Qs)) ** 2
    K = ct_kernel(2 * math.pi * DT.D.SETTINGS["rx_bw_ghz"] * 1e-3, sim.dt)
    Kp = np.zeros(sim.N)
    Kp[:len(K)] = K
    s2 = np.fft.irfft(np.fft.rfft(Sbar) * np.fft.rfft(Kp), sim.N)
    G = sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * np.maximum(s2, 0))
    return np.maximum(G, np.roll(G, 1)), float(K.sum())


def errors(sim, U):
    """連續時間的兩項：E_in（一階保持重建）與 E_btw（節點之間），P_u。"""
    (d0, l, Q), _ = pair(U)
    G, _ = weak_inputs(l, Q)
    Lx, C = math.pi / (2 * sim.edge), math.pi ** 2 / (2 * sim.edge ** 2)
    M2 = float(G.sum() * C + 2 * Lx ** 2 * np.abs(Q).sum())
    e = HN * M2 * sim.dt ** 2 / 8
    return e, e, M2


def actual(sim, rx, U, taus):
    """固定延遲的逐符號 b_s v_s（未乘 b_s 前的 v）與護欄 Γ_δ（與 M3 s3 的 Sim.window 同一算法）。"""
    X = np.stack([sim.envelope(j, taus[j]) for j in range(4)], axis=1)
    xc = np.hstack([X.astype(complex), np.full((sim.N, 1), R_AMP)]) @ U.T
    p2, p4 = np.abs(xc[:, READ[0]]) ** 2, np.abs(xc[:, READ[1]]) ** 2
    d, s = p2 - p4, p2 + p4
    v = rx.filt(d)
    rin = np.fft.irfft(np.fft.rfft((np.abs(d) + sim.eps * s) ** 2) * sim.H2, sim.N)
    return v, sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * np.maximum(rin, 0))


def job(fn):
    t0 = time.time()
    sim = make_sim()
    rx = Rx(sim)
    U = QD.unitary(fn)
    b_sym = np.array([1.0 if DT.TGT[fn](b) else -1.0 for b in DT.BITS])
    bs = b_sym[sim.seq][:, None]
    (d0, l, Q), _ = pair(U)
    G, weak = weak_inputs(l, Q)
    gbar, ksum = guard_box(sim, U)
    e_in, e_btw, M2 = errors(sim, U)
    pts = DT.box_points()
    acts = []
    for p in pts:
        v, g = actual(sim, rx, U, p)
        acts.append((bs * v[rx.idx], g))
    g0 = actual(sim, rx, U, np.zeros(4))[1]
    out = dict(weak_inputs=[int(i) + 1 for i in np.flatnonzero(weak)], G=np.round(G, 5).tolist(), e_in=e_in, e_btw=e_btw, M2=M2,
               guard_center_max=float(g0.max()), guard_box_max=float(gbar.max()), guard_increase_max=float((gbar - g0).max()),
               k_sum=ksum, guard_violation=float(max(np.max(g - gbar) for _, g in acts)), configs={})
    curves = {}
    for bins in BINS:
        lv = list(leaves(weak, bins))
        res = [bound(sim, rx, U, b_sym, c, r, weak) for _, c, r in lv]
        node = np.min([r["L"].min(0) for r in res], axis=0)          # 全部葉盒、全部符號的下界（未扣護欄）
        gsym = gbar[rx.idx]
        low_margin = np.min([(r["L"] - gsym).min(0) for r in res], axis=0)   # 護欄在每個符號自己的時刻扣
        viol, slack, n_chk = -np.inf, np.inf, 0
        for p, (bv, _) in zip(pts, acts):
            act = np.flatnonzero(~weak)
            cell = tuple(np.clip(np.floor((p[act] + R_BOX) / (2 * R_BOX) * bins).astype(int), 0, bins - 1))
            L = res[[k for k, (cc, _, _) in enumerate(lv) if cc == cell][0]]["L"]
            viol = max(viol, float(np.max(L - bv)))
            slack = min(slack, float(np.min(bv - L)))
            n_chk += L.size
        # 細格的連續時間檢查：Δ/4 的模擬器（同一序列），比較 min_s b_s v 與相鄰節點下界的較小者
        fine = make_sim(sim.dt / 4)
        frx = Rx(fine)
        e_fine = errors(fine, U)[0]
        ph = np.arange(2 * sim.n_ui) * sim.dt
        nodeL = np.minimum(node, np.roll(node, -1))                  # 第 k 格兩端的較小者
        ct_viol = -np.inf
        for p in pts[:N_FINE]:
            v, _ = actual(fine, frx, U, p)
            m = np.min(b_sym[fine.seq][:, None] * v[frx.idx], axis=0)[:4 * (len(node) - 1) + 1]
            k = np.minimum(np.arange(len(m)) // 4, len(node) - 2)
            ct_viol = max(ct_viol, float(np.max(nodeL[k] - e_in - e_btw - (m + e_fine))))
        lin_max = max(float(r["lin"].max()) for r in res)
        rem_max = max(float(r["rem"].max()) for r in res)
        act_margin = np.min([np.min(bv - g[rx.idx], 0) for bv, g in acts], axis=0)
        out["configs"][str(len(lv))] = dict(bins=bins, n_leaves=len(lv), lin_max=lin_max, rem_max=rem_max, e_w=res[0]["e_w"],
                                            n_checks=n_chk, max_violation=viol, min_slack=slack, ct_violation=ct_viol,
                                            fine_err=e_fine, margin_violation=float(np.max(low_margin - act_margin)),
                                            low_margin_max=float(low_margin.max()),
                                            act_margin_max=float(act_margin.max()), gap_at_best=float(act_margin[np.argmax(low_margin)] - low_margin.max()))
        curves[str(len(lv))] = dict(lower=low_margin, actual=act_margin, lin=np.max([r["lin"][rx.idx].max(0) for r in res], 0),
                                    rem=np.max([r["rem"][rx.idx].max(0) for r in res], 0))
    out["center_margin_max"] = float(np.min(bs * actual(sim, rx, U, np.zeros(4))[0][rx.idx] - g0[rx.idx], 0).max())
    out["time_s"] = round(time.time() - t0, 1)
    np.savez(paths.OUT(STEP, f"curves_{fn}.npz"), phase=ph, gbar=gbar[rx.idx].max(0), g0=g0[rx.idx].max(0),
             **{f"{k}_{n}": v for n, c in curves.items() for k, v in c.items()})
    return fn, out


def main():
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        F = dict(ex.map(job, FUNCS))
    checks = dict(no_violation=all(c["max_violation"] <= 0 for f in F.values() for c in f["configs"].values()),
                  guard_valid=all(f["guard_violation"] <= 0 for f in F.values()),
                  margin_below_sim=all(c["margin_violation"] <= 0 for f in F.values() for c in f["configs"].values()),
                  continuous_valid=all(c["ct_violation"] <= 0 for f in F.values() for c in f["configs"].values()),
                  more_leaves_tighter=all(f["configs"][max(f["configs"], key=int)]["low_margin_max"]
                                          >= f["configs"]["1"]["low_margin_max"] for f in F.values()))
    res = dict(half_box_ps=R_BOX, dt_ps=0.5, weak_ratio=WEAK, h_l1=HN, n_points=len(DT.box_points()), n_fine=N_FINE,
               functions=F, checks=checks, time_s=round(time.time() - t0, 1))
    path = paths.OUT(STEP, "leaf.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, f in F.items():
        print(f"{fn}：弱輸入 {f['weak_inputs']}｜E_in＝E_btw＝{f['e_in']:.4f}｜護欄 中心最大 {f['guard_center_max']:.4f}、盒 {f['guard_box_max']:.4f}"
              f"（增加 ≤ {f['guard_increase_max']:.4f}，違反 {f['guard_violation']:+.1e}）")
        for n, c in f["configs"].items():
            print(f"   {n:>2} 葉：一階 ≤ {c['lin_max']:.3f}、餘項 ≤ {c['rem_max']:.3f}、E_w {c['e_w']:.5f}｜檢查 {c['n_checks']} 筆，"
                  f"最大違反 {c['max_violation']:+.2e}、最小餘裕 {c['min_slack']:.4f}｜連續時間 {c['ct_violation']:+.2e}｜"
                  f"最佳下界 margin {c['low_margin_max']:.3f}（模擬 {c['act_margin_max']:.3f}）")
    print("檢查：", checks, f"｜{res['time_s']} s")
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
