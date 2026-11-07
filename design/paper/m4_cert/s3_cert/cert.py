r"""論文 M4 s3：13.2 ps 盒的認證窗——整個延遲盒（每路 ±6.6 ps）、宣告的情境序列與全部資料歷史下，共同取樣窗至少多寬（草稿式 9、命題 1、表 III 認證欄）。

用途：
  1. 認證條件（式 9）：M4 s2 的葉盒下界 V̲_s(t) 減去盒內護欄上界 Γ̄(t)，再扣連續時間的 E_in＋E_btw；
       m̲(t)＝min_ℓ min_s [V̲_s(t) − Γ̄_s(t)] − E_in − E_btw ≥ 0（護欄在每個符號自己的時刻扣，與 M3 s3 的模擬同一算法）
     在相鄰兩個節點都成立時，兩節點之間的整格都安全（Γ̄ 的節點值已取相鄰兩格的較大者，E_btw 涵蓋節點之間）。
     所以認證窗 W＝最長連續安全節點的終點減起點，是連續時間的寬度，不是格點估計。
     每側餘裕＝(W − T_req)/2：取樣時刻放在窗的中點，左右各留多少。
  2. 宣告的情境序列（M3 s3 的 Euler＋768 個隨機符號）：每路切 1、2、4 份（AND4、MAJ4 為 1、16、256 個葉盒；XOR2 只切強耦合的 2 路，為 1、4、16 個）。
  3. 全部資料歷史：改用 n 階 de Bruijn 序列 B(16, n)（n＝3、4；含全部 16ⁿ 種 n 個符號的組合，循環）。
     取樣相位 φ（自符號 s 起點，0 ≤ φ < 2 UI − r）只受符號 s−(n−2)…s＋1 的完整影響；更早的符號只經接收端尾端進來：
     它們改變的輸入都在時刻 −(n−2)·UI＋t_edge＋r 之前，對判讀量的影響 ≤ (D_max − D_min)·Σ_{k ≥ ⌊T/Δ⌋}|h_k|，T＝φ＋(n−2)·UI − t_edge − r（t_edge＝升餘弦全寬，報告記為 t_rc）；
     雜訊項把較舊各格的 S̄ 換成整個 [0,1]⁴ 的最大值 S̄_max，σ̄² 加上 c²·S̄_max·Σ_{m ≥ m_T} K_m（m_T 再退 2 格，涵蓋包絡範圍與節點取大）。
     D_max − D_min 用區間法在 [0,1]⁴ 上求（中心 0.5、半寬 0.5）。
  4. 驗收：
     (a) 與草稿表 III 認證欄 31.5／32.5／37.5 ps 比較；
     (b) 認證窗 ≤ 同一序列、同一延遲盒的詳細模擬最小值（情境序列：M3 s3 的 41 點共同窗；de Bruijn 序列：本步以同一 41 點重算）；
     (c) de Bruijn 序列上，未加歷史項的下界 margin 在每個取樣相位都 ≤ 41 點模擬的 margin（M4 s2 的檢查換一個序列再做一次）。
輸入：design/paper/m4_cert/s2_leaf/leaf.py（bound、guard_box、errors 與 M3 s3 的模擬器）、design/paper/m3_align/s3_detail/out/detail.json。
輸出：design/paper/m4_cert/s3_cert/out/cert.json、curves_AND4.npz、curves_MAJ4.npz、curves_XOR2.npz。
結束碼：0 全部必要檢查通過；1 有必要檢查未通過（JSON 仍會寫出，供檢視）。必要檢查清單見 cert_checks.py。
執行：.\lab design\paper\m4_cert\s3_cert\cert.py（6 個 worker 約 14 分鐘；B(16,4) 16 葉每個工作約 8 分鐘、12 GB）
唯讀驗證：.\lab design\paper\m4_cert\s3_cert\cert.py --verify（不重算、不寫檔，從現有 cert.json 判定）
"""
import sys
from pathlib import Path

if __name__ == "__main__" and "--verify" in sys.argv[1:]:             # 唯讀入口：不載入計算模組
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cert_checks
    sys.exit(cert_checks.main(sys.argv[1:]))

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s2_leaf"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy import signal                                             # noqa: E402

import cert_checks as CK                                             # noqa: E402
import leaf as LF                                                    # noqa: E402
import paths                                                         # noqa: E402

DT = LF.DT
QD = LF.QD
STEP = "paper/m4_cert/s3_cert"
FUNCS = LF.FUNCS
T_REQ = DT.D.SETTINGS["t_req_ps"]                                    # 23 ps
LEAF_BINS = (1, 2, 4)
ORDERS = (3, 4)
HIST_BINS = (1, 2)
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
DRAFT = dict(cert={"AND4": 31.5, "MAJ4": 32.5, "XOR2": 37.5}, and4_leaves={"16": 36.0, "256": 37.0},
             order4={"AND4": 29.5, "MAJ4": 30.5, "XOR2": 37.0}, order3={"AND4": 28.5, "MAJ4": 28.5, "XOR2": 28.5})


def make_sim(seq, dt=0.5):
    S = DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    return DT.Sim(seq, S["edge_full_ps"], dt, A, 10 ** (S["pu_dbm"] / 10) * 1e-3, False)


def window(margin, dt):
    """最長連續安全節點：(寬度, 起點, 終點)，ps（自符號起點）。"""
    best, run, end = 0, 0, -1
    for k, ok in enumerate(margin >= 0):
        run = run + 1 if ok else 0
        if run > best:
            best, end = run, k
    if best < 2:
        return 0.0, None, None
    return (best - 1) * dt, (end - best + 1) * dt, end * dt


def lower(sim, rx, U, b_sym, weak, bins, *gsyms):
    """全部葉盒、全部符號的 min_s (V̲_s − Γ̄_s)（逐取樣相位；護欄在每個符號自己的時刻扣；每個護欄各一條），以及一階項、餘項的最大值。"""
    nodes = [np.full(2 * sim.n_ui, np.inf) for _ in gsyms]
    lin = rem = 0.0
    for _, c, r in LF.leaves(weak, bins):
        b = LF.bound(sim, rx, U, b_sym, c, r, weak)
        nodes = [np.minimum(nd, (b["L"] - g).min(0)) for nd, g in zip(nodes, gsyms)]
        lin, rem = max(lin, float(b["lin"].max())), max(rem, float(b["rem"].max()))
        del b
    return (*nodes, lin, rem)


def sampled(sim, rx, U, b_sym):
    """41 個盒內抽樣點的共同 margin（逐相位取最小，與 M3 s3 的共同窗同一算法）。"""
    bs = b_sym[sim.seq][:, None]
    m = np.full(2 * sim.n_ui, np.inf)
    for p in DT.box_points():
        v, g = LF.actual(sim, rx, U, p)
        m = np.minimum(m, np.min(bs * v[rx.idx] - g[rx.idx], 0))
    return m


def history_terms(sim, U, order):
    """較舊符號的兩項（逐取樣相位）：判讀量 (D_max−D_min)·尾端 |h| 與雜訊 c²·S̄_max·尾端 K；以及 D 的範圍、有效相位上限。"""
    (d0, l, Q), (s0, ls, Qs) = LF.pair(U)
    xc, r = np.full((1, 4), 0.5), np.full((1, 4), 0.5)
    g = l + 2 * xc[0] @ Q
    d_range = 2 * float(np.abs(g).sum() * 0.5 + 0.25 * np.abs(Q).sum())
    lo, hi = np.zeros((1, 4)), np.ones((1, 4))
    s_max = float((LF.interval_abs(lo, hi, d0, l, Q) + sim.eps * LF.interval_abs(lo, hi, s0, ls, Qs))[0] ** 2)
    imp = np.zeros(int(round(3000 / sim.dt)))
    imp[0] = 1.0
    habs = np.abs(signal.lfilter(sim.num, sim.den, imp))
    htail = np.concatenate([np.cumsum(habs[::-1])[::-1], [0.0]])     # htail[k]＝Σ_{j≥k}|h_j|
    K = LF.ct_kernel(2 * math.pi * DT.D.SETTINGS["rx_bw_ghz"] * 1e-3, sim.dt)
    ktail = np.concatenate([np.cumsum(K[::-1])[::-1], [0.0]])
    ph = np.arange(2 * sim.n_ui) * sim.dt
    T = ph + (order - 2) * sim.ui - sim.edge - LF.R_BOX
    k = np.clip(np.floor(T / sim.dt).astype(int), 0, len(htail) - 1)
    m = np.clip(k - 2, 0, len(ktail) - 1)
    valid = ph < 2 * sim.ui - LF.R_BOX
    return d_range * htail[k], sim.c2 * s_max * ktail[m], d_range, s_max, valid


def job(arg):
    fn, seq_kind = arg
    t0 = time.time()
    seq = DT.sequence("euler") if seq_kind == "scenario" else np.array(DT.debruijn(16, seq_kind))
    sim = make_sim(seq)
    rx = LF.Rx(sim)
    U = QD.unitary(fn)
    b_sym = np.array([1.0 if DT.TGT[fn](b) else -1.0 for b in DT.BITS])
    (_, l, Q), _ = LF.pair(U)
    _, weak = LF.weak_inputs(l, Q)
    gbar, _ = LF.guard_box(sim, U)
    gsym = gbar[rx.idx]                                              # 每個符號、每個取樣相位的護欄上界
    e_in, e_btw, _ = LF.errors(sim, U)
    ph = np.arange(2 * sim.n_ui) * sim.dt
    out = dict(n_symbols=len(seq), e_in=e_in, e_btw=e_btw, configs={})
    curves = dict(phase=ph)
    if seq_kind == "scenario":
        for bins in LEAF_BINS:
            t1 = time.time()
            node, lin, rem = lower(sim, rx, U, b_sym, weak, bins, gsym)
            m = node - e_in - e_btw
            W, a, b = window(m, sim.dt)
            n = bins ** int((~weak).sum())
            out["configs"][str(n)] = dict(bins=bins, n_leaves=n, window=W, start=a, end=b, slack_side=(W - T_REQ) / 2,
                                          margin_max=float(m.max()), lin_max=lin, rem_max=rem, time_s=round(time.time() - t1, 1))
            curves[f"cert_{n}"] = m
        out["time_s"] = round(time.time() - t0, 1)
        return fn, seq_kind, out, curves
    dv, dn, d_range, s_max, valid = history_terms(sim, U, seq_kind)
    ghist = sim.off + sim.q * np.sqrt(((gsym - sim.off) / sim.q) ** 2 + dn[None, :])
    t1 = time.time()
    act = sampled(sim, rx, U, b_sym)
    out.update(d_range=d_range, s_max=s_max, sampled_window=window(np.where(valid, act, -1.0), sim.dt)[0],
               sampled_time_s=round(time.time() - t1, 1))
    for bins in HIST_BINS:
        t1 = time.time()
        node_seq, node, lin, rem = lower(sim, rx, U, b_sym, weak, bins, gsym, ghist)   # node_seq：未加歷史項、未扣 E，與模擬比較用
        n = bins ** int((~weak).sum())
        m = np.where(valid, node - dv - e_in - e_btw, -1.0)
        W, a, b = window(m, sim.dt)
        sel = (ph >= (a if a is not None else 0)) & (ph <= (b if b is not None else -1))
        out["configs"][str(n)] = dict(bins=bins, n_leaves=n, window=W, start=a, end=b, slack_side=(W - T_REQ) / 2,
                                      margin_max=float(m.max()), lin_max=lin, rem_max=rem,
                                      margin_violation=float(np.max(node_seq - act)),
                                      hist_v_max=float(dv[sel].max()) if sel.any() else None,
                                      hist_guard_max=float((ghist - gsym)[:, sel].max()) if sel.any() else None,
                                      time_s=round(time.time() - t1, 1))
        curves[f"cert_{n}"] = m
    curves.update(sampled=act, hist_v=dv, hist_g=(ghist - gsym).max(0))
    out["time_s"] = round(time.time() - t0, 1)
    return fn, seq_kind, out, curves


def main():
    t0 = time.time()
    det = json.loads(paths.OUT("paper/m3_align/s3_detail", "detail.json").read_text(encoding="utf-8"))["results"]["D0"]
    jobs = [(fn, o) for o in (4, 3) for fn in FUNCS] + [(fn, "scenario") for fn in FUNCS]
    with ProcessPoolExecutor(WORKERS) as ex:
        R = list(ex.map(job, jobs))
    F = {fn: dict(aligned=det[fn]["aligned"], box_min=det[fn]["box_min"], draft_cert=DRAFT["cert"][fn]) for fn in FUNCS}
    allc = {fn: {} for fn in FUNCS}
    for fn, kind, out, curves in R:
        key = "scenario" if kind == "scenario" else f"order{kind}"
        F[fn][key] = out
        allc[fn].update({f"{key}_{k}" if k != "phase" else k: v for k, v in curves.items()})
    for fn in FUNCS:
        np.savez(paths.OUT(STEP, f"curves_{fn}.npz"), **allc[fn])
    checks = CK.compute_checks(F, FUNCS, ORDERS, T_REQ)
    res = dict(half_box_ps=LF.R_BOX, span_ps=2 * LF.R_BOX, t_req_ps=T_REQ, dt_ps=0.5, leaf_bins=LEAF_BINS, orders=ORDERS,
               draft=DRAFT, functions=F, checks=checks, time_s=round(time.time() - t0, 1))
    path = paths.OUT(STEP, "cert.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, f in F.items():
        print(f"{fn}：對齊 {f['aligned']}、盒內 41 點最小 {f['box_min']} ps（草稿認證 {f['draft_cert']}）")
        for n, c in f["scenario"]["configs"].items():
            print(f"   情境序列 {n:>3} 葉：W＝{c['window']:.1f} ps（{c['start']}–{c['end']}），每側餘裕 {c['slack_side']:.2f}，{c['time_s']} s")
        for o in ORDERS:
            h = f[f"order{o}"]
            for n, c in h["configs"].items():
                print(f"   B(16,{o}) {n:>3} 葉：W＝{c['window']:.1f} ps（41 點 {h['sampled_window']:.1f}），歷史項 ≤ {c['hist_v_max']}，"
                      f"護欄 ≤ {c['hist_guard_max']}，違反 {c['margin_violation']:+.1e}，{c['time_s']} s")
    print("檢查：", checks, f"｜{res['time_s']} s")
    print(f"寫出 {rt.rel(path)}")
    failed = CK.required_failures(checks)
    if failed:
        print("必要檢查未通過：", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
