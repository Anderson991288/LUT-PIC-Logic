r"""論文 M5 s3：串接的盒證明——兩級串接的 x1x8 在 13.2 ps 盒（8 路各 ±6.6 ps）下，共同取樣窗至少多寬（草稿表 III x1x8 列）？

用途：
  1. 為什麼 M4 的證明可以直接搬過來：鏈相位 0、輸入延遲模型（每顆 macro 是固定延遲）下，後級讀取埠的光場是 8 路包絡的線性組合
     y＝M x＋c（M：2×8，c：前級與後級參考光的常數項；M5 s2 的 design() 已算好），所以判讀量
       D(x)＝|M_0 x＋c_0|² − |M_1 x＋c_1|²＝d0 ＋ lᵀx ＋ xᵀQx
     仍是精確的二次式，只是維度從 4 變 8；P_sum＝|M_0 x＋c_0|²＋|M_1 x＋c_1|² 同理。M4 s2 的葉盒下界、時變護欄上界、
     E_in／E_btw 都只用到 (d0, l, Q) 與包絡的斜率、曲率上界，所以把 4 換成 n 即可。本檔把 M4 s2 的 bound()、guard_box()、errors()、
     actual() 改寫成「輸入二次式係數與位元矩陣」的版本，其餘（接收端運算、K_m、區間法、‖h‖₁）直接沿用 M4 s2。
  2. 回歸檢查：同一份程式用在 AND4（係數由 B7 的 U 算出），要與 M4 s3 情境序列單葉的認證窗、M4 s2 的下界 margin 一致。
  3. 串接的對象：x1x8（草稿表 III）；另加 AND8、MAJ8、同步字（草稿只做 x1x8，本計畫新增）。相位用 M5 s1 的 0.9 dB 單判讀解。
     接收端與 M3 s3、M4 相同（類比二階 Butterworth 的一階保持離散，0.5 ps 格點）；序列用 M5 s2 的 8 輸入組成
     （256 個狀態的隨機排列＋768 個隨機符號）。這是「宣告的抽樣歷史」，不是全部歷史（8 輸入的全部歷史 de Bruijn 序列太長，與草稿相同）。
  4. 認證窗：m̲(t)＝min_ℓ min_s [V̲_s(t) − Γ̄_s(t)] − E_in − E_btw ≥ 0 的最長區間（與 M4 s3 同一算法）；每路切 1 份與 2 份（8 路時 256 個葉盒）。
  5. 驗證（與 M4 s2、s3 相同的三項）：盒內抽樣點（角落 2⁸＝256、中心 1、均勻隨機 16、軸上端點 16，共 289 點）
     (a) 每個符號、每個取樣相位 b_s v ≥ 下界；(b) 護欄上界 ≥ 該點的護欄；(c) 認證窗 ≤ 抽樣點的共同窗（所有點在同一取樣相位都安全，與 M3 s3 同一算法）。
  6. 差異診斷（一次只改一項，只算對齊、抽樣共同、單葉認證）：x1x8 改用參考實作的 8 輸入序列組成；以及 M5 s1 中 margin 與最佳解差 ≤ 0.5% 的其他相位解（最多 4 個）。
  驗收：x1x8 與草稿表 III 的認證窗 44.5 ps、每側餘裕 10.75 ps、對齊 63 ps、盒內抽樣最小 50 ps 比較。
輸入：design/paper/m4_cert/s2_leaf/leaf.py（接收端、K_m、區間法）、design/paper/m4_cert/s3_cert/cert.py（認證窗）、
      design/paper/m5_cascade/s2_meander/meander.py（串接的線性映射與 8 輸入序列）、design/paper/m5_cascade/s1_cascade/out/cascade.json、
      design/paper/m4_cert/s3_cert/out/cert.json、design/paper/m4_cert/s2_leaf/out/leaf.json（回歸檢查）。
輸出：design/paper/m5_cascade/s3_cert/out/cert_cascade.json、curves.npz（圖用）。
執行：.\lab design\paper\m5_cascade\s3_cert\cert_cascade.py（5 個 worker 約 10 分鐘；8 輸入 256 葉每個函數約 6 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m4_cert" / "s2_leaf"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m4_cert" / "s3_cert"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s2_meander"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.ndimage import maximum_filter1d, minimum_filter1d         # noqa: E402

import cert as CT                                                    # noqa: E402
import leaf as LF                                                    # noqa: E402
import meander as MD                                                 # noqa: E402
import paths                                                         # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

DT, QD = LF.DT, LF.QD
STEP = "paper/m5_cascade/s3_cert"
R_BOX = LF.R_BOX                                                     # 6.6 ps
T_REQ = CT.T_REQ
FUNCS = ("x1x8", "AND8", "MAJ8", "SYNC")
BINS = (1, 2)
N_RAND = 16
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
NEAR_MAX = 4                                                         # 診斷：margin 相近的其他相位解最多取幾個
DRAFT = {"x1x8": dict(window=44.5, slack_side=10.75, aligned=63.0, box_min=50.0, time_s=532)}


def make_sim(n, seq_kind="ours"):
    """類比接收端（與 M3 s3、M4 相同）；n＝4 用 Euler 情境序列，n＝8 用 M5 s2 的 8 輸入序列（seq_kind＝"ref"：參考實作的序列組成，診斷用）。"""
    S = DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    pu_w = 10 ** (S["pu_dbm"] / 10) * 1e-3
    if n == 4:
        return DT.Sim(DT.sequence("euler"), S["edge_full_ps"], 0.5, A, pu_w, False), DT.BITS
    if seq_kind == "ref":
        seq = MD.ref_seq8()
    else:
        rng = np.random.default_rng(MD.SEED8)
        seq = np.concatenate([rng.permutation(256), rng.integers(0, 256, 768)])
    return MD.Sim8(seq, S["edge_full_ps"], 0.5, A, pu_w, False), MD.B8


def linear_map(fn, z=None):
    """讀取埠的線性映射 (M, c) 與判讀方向；AND4 用 M4 的 U（回歸檢查），8 輸入用 M5 s2 的串接映射（無蛇形）。"""
    if fn == "AND4":
        U = QD.unitary(fn)
        b_sym = np.array([1.0 if DT.TGT[fn](b) else -1.0 for b in DT.BITS])
        return U[list(READ), :4], U[list(READ), 4] * R_AMP, b_sym
    _, _, lin, b_sym = MD.design(fn, z)
    M, c = lin([1.0, 1.0])
    return M, c, b_sym


def coeffs(M, c):
    """D 與 P_sum 的二次式係數 (d0, l, Q)（x 為實數）。"""
    out = []
    for sgn in (-1, 1):
        d0 = float(abs(c[0]) ** 2 + sgn * abs(c[1]) ** 2)
        l = 2 * np.real(np.conj(c[0]) * M[0] + sgn * np.conj(c[1]) * M[1])
        Q = np.real(np.outer(M[0].conj(), M[0]) + sgn * np.outer(M[1].conj(), M[1]))
        out.append((d0, l, Q))
    return out


def derivs(sim, col, tau, rho):
    """M4 s2 的 derivs()，位元改由參數傳入（col：該路逐符號的 0/1）。"""
    bits = col.astype(float)
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


def leaves(weak, bins):
    n = len(weak)
    act = np.flatnonzero(~weak)
    for cell in itertools.product(range(bins), repeat=len(act)):
        c, r = np.zeros(n), np.zeros(n)
        c[act] = -R_BOX + (np.array(cell) + 0.5) * 2 * R_BOX / bins
        r[act] = R_BOX / bins
        yield cell, c, r


def bound(sim, rx, coef, bits, b_sym, c, rho, weak):
    """M4 s2 的 bound()，改為 n 路、輸入二次式係數。"""
    d0, l, Q = coef[0]
    n = len(l)
    G, _ = LF.weak_inputs(l, Q)
    X = np.stack([sim.envelope(j, c[j]) for j in range(n)], axis=1)
    base = rx.filt(QD.quad(d0, l, Q, X))
    g = l[None, :] + 2 * X @ Q
    lin = np.zeros(sim.N)
    eps = np.zeros((sim.N, n))
    rem = np.zeros(sim.N)
    for i in range(n):
        if rho[i] == 0:
            continue
        xd, sl, cv = derivs(sim, bits[sim.seq][:, i], c[i], rho[i])
        lin += rho[i] * np.abs(rx.filt(g[:, i] * xd))
        eps[:, i] = np.minimum(1.0, sl * rho[i])
        rem += np.abs(g[:, i]) * rho[i] ** 2 * cv / 2
    rem += np.einsum("ti,ij,tj->t", eps, np.abs(Q), eps)
    rem = rx.abs_conv(maximum_filter1d(rem, 3, mode="wrap"))
    Lx = math.pi / (2 * sim.edge)
    e_w = LF.HN * float(G[weak].sum()) * min(1.0, Lx * R_BOX)
    L = b_sym[sim.seq][:, None] * base[rx.idx] - lin[rx.idx] - rem[rx.idx] - e_w - LF.RESERVE
    return dict(lin=lin, rem=rem, e_w=e_w, L=L)


def guard_box(sim, coef):
    """M4 s2 的 guard_box()，改為 n 路。"""
    (d0, l, Q), (s0, ls, Qs) = coef
    n = len(l)
    X = np.stack([sim.envelope(j, 0.0) for j in range(n)], axis=1)
    cw = int(math.ceil(R_BOX / sim.dt - 1e-9))
    pad = math.pi ** 2 / (2 * sim.edge ** 2) * sim.dt ** 2 / 8
    lo = np.clip(minimum_filter1d(X, 2 * cw + 1, axis=0, mode="wrap") - pad, 0, 1)
    hi = np.clip(maximum_filter1d(X, 2 * cw + 1, axis=0, mode="wrap") + pad, 0, 1)
    loc, hic = np.minimum(lo, np.roll(lo, -1, 0)), np.maximum(hi, np.roll(hi, -1, 0))
    Sbar = (LF.interval_abs(loc, hic, d0, l, Q) + sim.eps * LF.interval_abs(loc, hic, s0, ls, Qs)) ** 2
    K = LF.ct_kernel(2 * math.pi * DT.D.SETTINGS["rx_bw_ghz"] * 1e-3, sim.dt)
    Kp = np.zeros(sim.N)
    Kp[:len(K)] = K
    s2 = np.fft.irfft(np.fft.rfft(Sbar) * np.fft.rfft(Kp), sim.N)
    G = sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * np.maximum(s2, 0))
    return np.maximum(G, np.roll(G, 1))


def errors(sim, coef):
    d0, l, Q = coef[0]
    G, _ = LF.weak_inputs(l, Q)
    Lx, C = math.pi / (2 * sim.edge), math.pi ** 2 / (2 * sim.edge ** 2)
    M2 = float(G.sum() * C + 2 * Lx ** 2 * np.abs(Q).sum())
    return LF.HN * M2 * sim.dt ** 2 / 8


def actual(sim, rx, M, c, taus):
    """固定延遲的 v 與護欄 Γ_δ（與 M4 s2 的 actual() 同一算法，輸入是線性映射）。"""
    sim.cache.clear()
    X = np.stack([sim.envelope(j, taus[j]) for j in range(M.shape[1])], axis=1)
    y = X @ M.T + c[None, :]
    p2, p4 = np.abs(y[:, 0]) ** 2, np.abs(y[:, 1]) ** 2
    d, s = p2 - p4, p2 + p4
    v = rx.filt(d)
    rin = np.fft.irfft(np.fft.rfft((np.abs(d) + sim.eps * s) ** 2) * sim.H2, sim.N)
    return v, sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * np.maximum(rin, 0))


def box_points(n):
    """角落 2ⁿ、中心、均勻隨機 16、軸上端點 2n（n＝4 時與 M3 s3 的 41 點相同）。"""
    if n == 4:
        return DT.box_points()
    rng = np.random.default_rng(DT.BOX_SEED)
    pts = [np.array(v) * R_BOX for v in itertools.product((-1, 1), repeat=n)] + [np.zeros(n)]
    pts += list(rng.uniform(-R_BOX, R_BOX, (N_RAND, n)))
    for i in range(n):
        z = np.zeros(n)
        z[i] = R_BOX
        pts += [z, -z]
    return pts


def job(arg):
    """arg：函數名，或 (函數名, 序列組成, 相位 z, 切份)（診斷用）。"""
    fn, seq_kind, z, bins_list = (arg, "ours", None, BINS) if isinstance(arg, str) else arg
    t0 = time.time()
    M, c, b_sym = linear_map(fn, None if z is None else np.array(z))
    n = M.shape[1]
    sim, bits = make_sim(n, seq_kind)
    rx = LF.Rx(sim)
    coef = coeffs(M, c)
    d0, l, Q = coef[0]
    G, weak = LF.weak_inputs(l, Q)
    gbar = guard_box(sim, coef)
    gsym = gbar[rx.idx]
    e = errors(sim, coef)
    bs = b_sym[sim.seq][:, None]
    pts = box_points(n)
    wins, gviol, mins = [], -np.inf, np.full(2 * sim.n_ui, np.inf)
    for k, p in enumerate(pts):                                      # 抽樣點：逐點的窗寬與護欄（逐符號的 b_s v 太大，不保留，驗證時重算）
        v, g = actual(sim, rx, M, c, p)
        m = np.min(bs * v[rx.idx] - g[rx.idx], 0)
        wins.append(CT.window(m, sim.dt)[0])
        gviol = max(gviol, float(np.max(g - gbar)))
        mins = np.minimum(mins, m)
        if k == 2 ** n:
            m_aligned = m
    t_s = round(time.time() - t0, 1)
    out = dict(n_inputs=n, n_symbols=len(sim.seq), weak_inputs=[int(i) + 1 for i in np.flatnonzero(weak)],
               G=np.round(G, 5).tolist(), d0=d0, e_in=e, e_btw=e, n_points=len(pts),
               aligned=wins[2 ** n], box_min=CT.window(mins, sim.dt)[0],                  # 共同窗：所有抽樣點在同一取樣相位都安全（與 M3 s3 相同）
               point_min=min(wins), point_min_index=int(np.argmin(wins)),             # 逐點各自的窗寬（不含共同平移）的最小值
               guard_violation=gviol, sampled_time_s=t_s, configs={})
    curves = dict(phase=np.arange(2 * sim.n_ui) * sim.dt, aligned=m_aligned, box_min=mins)
    for bins in bins_list:
        t1 = time.time()
        lv = list(leaves(weak, bins))
        node = np.full(2 * sim.n_ui, np.inf)
        viol, lin_max, rem_max = -np.inf, 0.0, 0.0
        act_idx = np.flatnonzero(~weak)
        owner = [tuple(np.clip(np.floor((p[act_idx] + R_BOX) / (2 * R_BOX) * bins).astype(int), 0, bins - 1)) for p in pts]
        for cell, cc, rr in lv:
            b = bound(sim, rx, coef, bits, b_sym, cc, rr, weak)
            node = np.minimum(node, (b["L"] - gsym).min(0))
            lin_max, rem_max = max(lin_max, float(b["lin"].max())), max(rem_max, float(b["rem"].max()))
            for p, ow in zip(pts, owner):                            # (a) 落在這個葉盒的抽樣點：b_s v ≥ 下界
                if ow == cell:
                    v, _ = actual(sim, rx, M, c, p)
                    viol = max(viol, float(np.max(b["L"] - bs * v[rx.idx])))
            del b
        m = node - 2 * e
        W, a, z = CT.window(m, sim.dt)
        out["configs"][str(len(lv))] = dict(bins=bins, n_leaves=len(lv), window=W, start=a, end=z, slack_side=(W - T_REQ) / 2,
                                            margin_max=float(m.max()), lin_max=lin_max, rem_max=rem_max, max_violation=viol,
                                            time_s=round(time.time() - t1, 1))
        curves[f"cert_{len(lv)}"] = m
    out["time_s"] = round(time.time() - t0, 1)
    return fn, out, curves


def near_solutions(fn, limit=NEAR_MAX):
    """M5 s1 中 margin 與最佳解差 ≤ 0.5% 的其他相位解（去重、依 margin 排序，最多 limit 個，不含最佳解本身）。"""
    runs = [json.loads(s) for s in paths.OUT("paper/m5_cascade/s1_cascade", "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    rs = sorted((r for r in runs if r[0] == [fn] and r[2] > 0), key=lambda r: -r[4])
    best = rs[0][4]
    out, seen = [], {round(best, 6)}
    for r in rs[1:]:
        if r[4] < best * (1 - MD.NEAR):
            break
        if round(r[4], 6) not in seen:
            seen.add(round(r[4], 6))
            out.append((r[4], r[5]))
    return best, out[:limit]


def main():
    t0 = time.time()
    best, near = near_solutions("x1x8")
    diag_jobs = [("x1x8", "ref", None, (1,))] + [("x1x8", "ours", z, (1,)) for _, z in near]
    with ProcessPoolExecutor(WORKERS) as ex:
        R = list(ex.map(job, ("AND4",) + FUNCS))
        DG = list(ex.map(job, diag_jobs))
    F = {fn: out for fn, out, _ in R}
    pick = lambda o: dict(aligned=o["aligned"], box_min=o["box_min"], window_1=o["configs"]["1"]["window"])  # noqa: E731
    diag = dict(ref_sequence=pick(DG[0][1]), best_margin=best,
                near_solutions=[dict(margin=m, **pick(o)) for (m, _), (_, o, _) in zip(near, DG[1:])])
    np.savez(paths.OUT(STEP, "curves.npz"), **{f"{fn}_{k}": v for fn, _, cv in R for k, v in cv.items()})
    m4c = json.loads(paths.OUT("paper/m4_cert/s3_cert", "cert.json").read_text(encoding="utf-8"))["functions"]["AND4"]
    m4l = json.loads(paths.OUT("paper/m4_cert/s2_leaf", "leaf.json").read_text(encoding="utf-8"))["functions"]["AND4"]
    reg = dict(window_1=F["AND4"]["configs"]["1"]["window"], m4_window_1=m4c["scenario"]["configs"]["1"]["window"],
               window_16=F["AND4"]["configs"]["16"]["window"], m4_window_16=m4c["scenario"]["configs"]["16"]["window"],
               box_min=F["AND4"]["box_min"], m4_box_min=m4c["box_min"], e_in=F["AND4"]["e_in"], m4_e_in=m4l["e_in"])
    for fn in FUNCS:
        if fn in DRAFT:
            c1 = F[fn]["configs"]["1"]
            F[fn]["draft"] = DRAFT[fn]
            F[fn]["diff"] = dict(window=c1["window"] - DRAFT[fn]["window"], aligned=F[fn]["aligned"] - DRAFT[fn]["aligned"],
                                 box_min=F[fn]["box_min"] - DRAFT[fn]["box_min"])
    checks = dict(
        regression_and4=abs(reg["window_1"] - reg["m4_window_1"]) < 1e-9 and abs(reg["window_16"] - reg["m4_window_16"]) < 1e-9
        and abs(reg["e_in"] - reg["m4_e_in"]) < 1e-12,
        no_violation=all(c["max_violation"] <= 0 for f in F.values() for c in f["configs"].values()),
        guard_valid=all(f["guard_violation"] <= 0 for f in F.values()),
        below_sampled=all(c["window"] <= f["box_min"] for f in F.values() for c in f["configs"].values()),
        x1x8_above_treq=F["x1x8"]["configs"]["1"]["window"] >= T_REQ,
        more_leaves_wider=all(f["configs"][str(max(int(k) for k in f["configs"]))]["window"] >= f["configs"]["1"]["window"] for f in F.values()))
    res = dict(half_box_ps=R_BOX, span_ps=2 * R_BOX, t_req_ps=T_REQ, dt_ps=0.5, bins=BINS, receiver="類比二階 Butterworth 7 GHz（一階保持離散）",
               seed8=MD.SEED8, regression=reg, functions=F, diagnosis=diag, checks=checks, time_s=round(time.time() - t0, 1), workers=WORKERS)
    path = paths.OUT(STEP, "cert_cascade.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("回歸（AND4）：", reg)
    for fn, f in F.items():
        d = f.get("draft")
        print(f"{fn}：弱輸入 {f['weak_inputs']}｜對齊 {f['aligned']}、{f['n_points']} 點最小 {f['box_min']} ps"
              + (f"（草稿 {d['aligned']}、{d['box_min']}）" if d else "") + f"｜E_in {f['e_in']:.4f}｜護欄違反 {f['guard_violation']:+.1e}｜抽樣 {f['sampled_time_s']} s")
        for k, c in f["configs"].items():
            print(f"   {k:>3} 葉：W＝{c['window']:.1f} ps（{c['start']}–{c['end']}），每側 {c['slack_side']:.2f}，一階 ≤ {c['lin_max']:.3f}、餘項 ≤ {c['rem_max']:.3f}，"
                  f"違反 {c['max_violation']:+.1e}，{c['time_s']} s" + (f"（草稿 {d['window']}、每側 {d['slack_side']}）" if d and k == "1" else ""))
    print("診斷 x1x8（與草稿差異）：", json.dumps(diag, ensure_ascii=False))
    print("檢查：", checks, f"｜{res['time_s']} s")
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
