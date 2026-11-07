r"""論文 M5 s2：依時序限制選蛇形（草稿 III-F 演算法 1、表 IV）——補長度會同時延遲與衰減，最短且通過驗收的候選是哪一個？

用途：
  1. 模型：輸入線分成路徑群 g，群內各路長度相同 L_g（mm），到達時間 δ_g＝n_g·L_g/c（14.24 ps/mm）。
     蛇形加長 ΔL_g 時，該群延遲增加 n_g·ΔL_g/c，光場振幅乘 10^(−α·ΔL_g/20)（α：蛇形損耗 dB/mm），改變干涉權重。
     單顆 macro：每路輸入一群，損耗只乘在資料輸入上；串接：x1–x4、x5–x8 各一群（前級到後級的那段線），損耗乘在該前級
     送出的全部光場上（含前級參考光的貢獻）。蛇形造成的載波相位變化假設由校正吸收（草稿 III-F）。
  2. 候選（草稿 III-F）：依群的影響力（群內各路 c_i＝L_x·(|l_i|＋2Σ_j|Q_ij|) 的和，二次式係數取自未加蛇形的設計）排序，
     只補「影響大且早到」的前 k 群：ΔL_g＝κ(δ_max − δ_g)/(n_g/c)，κ∈{0.5, 0.75, 1}（補償比例；變數名 BETAS 沿用），k＝1…早到群數；加上零長度候選，去重後依總長排序。
  3. 演算法 1：依總長逐一以詳細模擬驗收（名義延遲與全部角落），第一個「最差角落窗 ≥ T_req」的候選即為選擇。
     角落（補充資料 S5）：每群 ±0.05 mm 繞線公差的所有符號組合 × 每路 ±0.9 ps 內部 skew 的兩種交錯奇偶型。
     另以詳細模擬算兩個對照：不補償、完整等長（全部群補齊到最晚者）。
     草稿的轉態時間窗界（screen）只當診斷，本計畫沒有實作，不影響選擇。
  4. 詳細模擬：M3 s3 的模擬器換成數位二階 Butterworth（雙線性，草稿 IV 節與表 IV、VI 用；與 M4 s4 相同），0.5 ps 格點，
     時變護欄；共同窗＝所有符號在同一取樣相位都安全的最長區間。延遲先減去 (max＋min)/2，共同延遲由取樣時刻吸收。
     情境：4 輸入用 M3 s3 的 Euler 序列＋768 個隨機符號；8 輸入用 256 個狀態的隨機排列＋768 個隨機符號（草稿 IV-D 的組成；種子依草稿 20261023＋8）。
  5. 案例（表 IV）：x1x8、AND8、MAJ8、同步字（stress lengths 2.8／3.7 mm，span 12.8 ps）；AND4、MAJ4、XOR2 fan-in A
     （1.20／1.55／1.90／2.20 mm，14.2 ps）；AND4 fan-in B（0.90／1.40／1.80／2.20 mm，18.5 ps），蛇形 0.3 與 1 dB/mm。
     長度來自參考實作；相位：單顆 macro 用 M3 s2 的 0.9 dB／MZI 相位，串接用 M5 s1 的 0.9 dB 單判讀相位（標稱模型、鏈相位 0）。
  6. 壓力案例（本計畫新增，草稿沒有）：表 IV 的案例全部不需要蛇形，只能說明「不需要時演算法不會加」；為了檢驗方法的主張
     （零長度不夠時，選出比完整等長短、而且通過驗收的蛇形），把 fan-in B 的線長差放大：fan-in C＝3 倍（span 55.5 ps）、fan-in D＝5 倍（92.6 ps）。
  7. 差異診斷（一次只改一項）：8 輸入改用參考實作的序列組成（同一種子，先排列 256 個狀態再抽 768×8 個 0/1）；
     以及 M5 s1 中 margin 與最佳解差 ≤ 0.5% 的其他相位解，不補償時的最差角落窗範圍。
  驗收：與草稿表 IV 的選擇、窗寬、完整等長的長度與窗寬比較；重現「完整等長在 1 dB/mm 時窗變小」；壓力案例中選出的蛇形比完整等長短且通過。
輸入：design/paper/m3_align/s3_detail/detail.py（模擬器）、design/paper/m3_align/s2_synth/out/synth.json、
      design/paper/m5_cascade/s1_cascade/out/cascade.json、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：design/paper/m5_cascade/s2_meander/out/meander.json。
執行：.\lab design\paper\m5_cascade\s2_meander\meander.py（6 個 worker 約 3 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s3_detail"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s2_synth"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s1_cascade"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy import signal                                             # noqa: E402

import cascade as CS                                                 # noqa: E402
import detail as DT                                                  # noqa: E402
import draft as D                                                    # noqa: E402
import paths                                                         # noqa: E402
import synth as SY                                                   # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

STEP = "paper/m5_cascade/s2_meander"
PS_PER_MM = D.SETTINGS["ng"] * 1000 / 299.792458                     # 14.24 ps/mm
TOL_MM, INT_SKEW = 0.05, 1.8                                         # 繞線公差；每路內部 skew 預算（±0.9 ps）
T_REQ = D.SETTINGS["t_req_ps"]
BETAS = (0.5, 0.75, 1.0)
DT_PS = 0.5
SEED8 = 20261023 + 8
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
STRESS8 = [2.8, 3.7]
FAN_A = [1.20, 1.55, 1.90, 2.20]
FAN_B = [0.90, 1.40, 1.80, 2.20]
FAN_C = [round(0.9 + 3 * (x - 0.9), 3) for x in FAN_B]              # 壓力案例：最短線不變，其他線長差放大 3 倍
FAN_D = [round(0.9 + 5 * (x - 0.9), 3) for x in FAN_B]              # 放大 5 倍
# 案例：(標籤, 函數, 長度, α dB/mm)
CASES = [("x1x8, stress", "x1x8", STRESS8, 0.3), ("AND4, fan-in A", "AND4", FAN_A, 0.3), ("MAJ4, fan-in A", "MAJ4", FAN_A, 0.3),
         ("XOR2, fan-in A", "XOR2", FAN_A, 0.3), ("AND4, fan-in B", "AND4", FAN_B, 0.3), ("AND4, fan-in B, 1 dB/mm", "AND4", FAN_B, 1.0),
         ("AND8, stress", "AND8", STRESS8, 0.3), ("MAJ8, stress", "MAJ8", STRESS8, 0.3), ("SYNC, stress", "SYNC", STRESS8, 0.3),
         ("AND4, fan-in C", "AND4", FAN_C, 0.3), ("AND4, fan-in C, 1 dB/mm", "AND4", FAN_C, 1.0), ("MAJ4, fan-in C", "MAJ4", FAN_C, 0.3),
         ("MAJ4, fan-in C, 1 dB/mm", "MAJ4", FAN_C, 1.0), ("XOR2, fan-in D", "XOR2", FAN_D, 0.3)]
NEAR = 0.005                                                         # 診斷：與最佳 margin 差 ≤ 0.5% 的相位解
# 草稿表 IV：(原始 span ps, 選擇的蛇形 mm, 窗 ps, 完整等長 mm, 完整等長窗 ps, 不補償窗 ps)
TABLE4 = {"x1x8, stress": (12.8, 0.0, 63, 0.90, 63, 63), "AND4, fan-in A": (14.2, 0.0, 48, 1.95, 47, 48),
          "MAJ4, fan-in A": (14.2, 0.0, 45, 1.95, 47, 45), "XOR2, fan-in A": (14.2, 0.0, 57, 1.95, 58, 57),
          "AND4, fan-in B": (18.5, 0.0, 46, 2.50, 47, 46), "AND4, fan-in B, 1 dB/mm": (18.5, 0.0, 46, 2.50, 33, 46),
          "AND8, stress": (12.8, 0.0, 38, 0.90, 39, 38), "MAJ8, stress": (12.8, 0.0, 30, 0.90, 36, 30),
          "SYNC, stress": (12.8, 0.0, 38, 0.90, 36, 38)}
B8 = CS.B8


class Sim8(DT.Sim):
    """8 輸入版：符號是 0–255，第 j 路取 x_{j+1}（與 M5 s1 的 B8 同一排列）。"""
    def envelope(self, j, tau):
        key = (j, round(tau, 6))
        if key not in self.cache:
            bits = B8[self.seq][:, j].astype(float)
            n = len(bits)
            prev = np.roll(bits, 1)
            tt = (self.t - tau) % (n * self.ui)
            k = np.floor(tt / self.ui).astype(int)
            w = np.clip((tt - k * self.ui) / self.edge, 0, 1)
            self.cache[key] = prev[k] + (bits[k] - prev[k]) * (1 - np.cos(np.pi * w)) / 2
        return self.cache[key]


def make_sim(n):
    """數位二階 Butterworth（雙線性）接收端的模擬器；n＝4 或 8 個輸入。"""
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    pu_w = 10 ** (D.SETTINGS["pu_dbm"] / 10) * 1e-3
    if n == 4:
        sim = DT.Sim(DT.sequence("euler"), D.SETTINGS["edge_full_ps"], DT_PS, A, pu_w, False)
    else:
        rng = np.random.default_rng(SEED8)
        seq = np.concatenate([rng.permutation(256), rng.integers(0, 256, 768)])
        sim = Sim8(seq, D.SETTINGS["edge_full_ps"], DT_PS, A, pu_w, False)
    sim.num, sim.den = signal.butter(2, D.SETTINGS["rx_bw_ghz"] / (500.0 / sim.dt))
    imp = np.zeros(int(round(2000 / sim.dt)))
    imp[0] = 1.0
    h = signal.lfilter(sim.num, sim.den, imp)
    sim.h2 = np.zeros(sim.N)
    sim.h2[:len(h)] = h ** 2 / np.sum(h ** 2)
    sim.H2 = np.fft.rfft(sim.h2)
    return sim


def design(fn, z=None):
    """z：串接的 42 個相位（預設用 M5 s1 的最佳 0.9 dB 解）。回傳 (n, 群編號, lin(a) → (M, c), 判讀方向 b_sym)：M 是 2×n 的讀取埠對各輸入的場係數，c 是常數項（參考光）。"""
    if fn in ("AND4", "MAJ4", "XOR2"):
        r = json.loads(paths.OUT("paper/m3_align/s2_synth", "synth.json").read_text(encoding="utf-8"))["functions"][fn]["lossy"]
        U = SY.b7(np.array(r["theta"] + r["phi"]), 10 ** (-D.SETTINGS["mzi_loss_db"] / 20))

        def lin(a):
            return U[list(READ), :4] * np.asarray(a)[None, :], U[list(READ), 4] * R_AMP
        b_sym = np.array([1.0 if DT.TGT[fn](b) else -1.0 for b in DT.BITS])
        return 4, [0, 1, 2, 3], lin, b_sym
    if z is None:
        z = np.array(json.loads(paths.OUT("paper/m5_cascade/s1_cascade", "cascade.json").read_text(encoding="utf-8"))["single"][fn]["lossy"]["phases"])
    amp = 10 ** (-D.SETTINGS["mzi_loss_db"] / 20)
    UA, UB, U4 = SY.b7(z[:14], amp), SY.b7(z[14:28], amp), SY.b7(z[28:42], amp)
    i, j = CS.WIRE["M4"]

    def lin(a):
        # 前級 A 的波導 i、j 送往後級輸入 0、1，前級 B 送往 2、3；蛇形損耗 a[0]、a[1] 乘在各前級送出的光場上
        F = np.zeros((5, 9), complex)                                # 後級輸入（5 路）對 [x1…x8, 1] 的係數
        for row, src, U, ga in ((0, i, UA, a[0]), (1, j, UA, a[0]), (2, i, UB, a[1]), (3, j, UB, a[1])):
            cols = slice(0, 4) if U is UA else slice(4, 8)
            F[row, cols] = ga * U[src, :4]
            F[row, 8] = ga * U[src, 4] * R_AMP
        F[4, 8] = R_AMP
        Y = U4[list(READ)] @ F
        return Y[:, :8], Y[:, 8]
    b_sym = np.array([1.0 if CS.TARGETS[fn](b) else -1.0 for b in B8])
    return 8, [0] * 4 + [1] * 4, lin, b_sym


def quad_coeffs(M, c):
    """D＝|M_0 x＋c_0|² − |M_1 x＋c_1|² 的一次與二次係數（x 為實數）。"""
    l = 2 * np.real(np.conj(c[0]) * M[0] - np.conj(c[1]) * M[1])
    Q = np.real(np.outer(M[0].conj(), M[0]) - np.outer(M[1].conj(), M[1]))
    return l, Q


def window(sim, M, c, b_sym, taus):
    """共同取樣窗（與 M3 s3 的 Sim.window 同一算法），輸入是任意線性映射 y＝M x＋c 的兩個讀取埠。"""
    n = M.shape[1]
    sim.cache.clear()                                                # 每組延遲都不同，不保留包絡（避免記憶體累積）
    taus = np.round(np.asarray(taus) - (max(taus) + min(taus)) / 2, 9)   # 共同延遲由取樣時刻吸收；四捨五入避免 1e-15 的延遲讓取餘數落在週期邊界
    x = np.stack([sim.envelope(k, taus[k]) for k in range(n)], 1)
    y = x @ M.T + c[None, :]
    p2, p4 = np.abs(y[:, 0]) ** 2, np.abs(y[:, 1]) ** 2
    d, s = p2 - p4, p2 + p4
    v = signal.lfilter(sim.num, sim.den, np.concatenate([d, d]))[sim.N:]
    rin = np.fft.irfft(np.fft.rfft((np.abs(d) + sim.eps * s) ** 2) * sim.H2, sim.N)
    g = sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * np.maximum(rin, 0))
    idx = (np.arange(len(sim.seq))[:, None] * sim.n_ui + np.arange(2 * sim.n_ui)[None, :]) % sim.N
    margin = np.min(b_sym[sim.seq][:, None] * v[idx] - g[idx], axis=0)
    return DT.longest(margin, sim.dt)


def corners(groups, G):
    tol = TOL_MM * PS_PER_MM
    return [np.array([sg[g] * tol + (1 if (k + par) % 2 else -1) * INT_SKEW / 2 for k, g in enumerate(groups)])
            for sg in itertools.product((-1, 1), repeat=G) for par in (0, 1)]


def run_case(case):
    label, fn, L_mm, alpha = case
    t0 = time.time()
    n, groups, lin, b_sym = design(fn)
    sim = make_sim(n)
    G = max(groups) + 1
    t_g = np.array(L_mm) * PS_PER_MM
    late = t_g.max()
    crn = corners(groups, G)
    count = dict(detail=0)

    def evaluate(pad):
        M, c = lin([10 ** (-alpha * p / 20) for p in pad])
        base = np.array([t_g[g] + pad[g] * PS_PER_MM for g in groups])
        ws = []
        for o in crn:
            ws.append(window(sim, M, c, b_sym, base + o))
            count["detail"] += 1
        count["detail"] += 1
        return min(ws), window(sim, M, c, b_sym, base)

    l, Q = quad_coeffs(*lin([1.0] * G))
    Lx = math.pi / (2 * D.SETTINGS["edge_full_ps"])                    # 升餘弦包絡的斜率上界（1/ps）
    ci = Lx * (np.abs(l) + 2 * np.abs(Q).sum(1))
    infl = np.array([ci[[k for k, g in enumerate(groups) if g == gg]].sum() for gg in range(G)])
    early = [g for g in np.argsort(-infl) if late - t_g[g] > 1e-9]
    cands = [np.zeros(G)]
    for k in range(1, len(early) + 1):
        for beta in BETAS:
            pad = np.zeros(G)
            for g in early[:k]:
                pad[g] = beta * (late - t_g[g]) / PS_PER_MM
            cands.append(pad)
    seen, order = set(), []
    for pad in sorted(cands, key=lambda p: p.sum()):
        key = tuple(np.round(pad, 6))
        if key not in seen:
            seen.add(key)
            order.append(pad)
    tried, chosen = [], None
    for pad in order:                                                # 演算法 1：依總長逐一詳細驗收，第一個通過即選
        wmin, wnom = evaluate(pad)
        tried.append(dict(pad_mm=np.round(pad, 4).tolist(), total_mm=round(float(pad.sum()), 4), worst=wmin, nominal=wnom))
        if wmin >= T_REQ:
            chosen = len(tried) - 1
            break
    full = np.array([(late - t_g[g]) / PS_PER_MM for g in range(G)])
    ref = {}
    for lab, pad in (("none", np.zeros(G)), ("full", full)):
        wmin, wnom = evaluate(pad)
        ref[lab] = dict(pad_mm=np.round(pad, 4).tolist(), total_mm=round(float(pad.sum()), 4), worst=wmin, nominal=wnom)
    return dict(label=label, fn=fn, L_mm=L_mm, alpha_db_mm=alpha, raw_span_ps=round(float(late - t_g.min()), 2),
                influence=np.round(infl, 4).tolist(), candidates=[dict(pad_mm=np.round(p, 4).tolist(), total_mm=round(float(p.sum()), 4)) for p in order],
                tried=tried, chosen=chosen, chosen_summary=tried[chosen] if chosen is not None else None, reference=ref,
                corners=len(crn), evaluations=count["detail"], draft=dict(zip(("span", "chosen_mm", "window", "full_mm", "full_window", "none_window"), TABLE4[label])) if label in TABLE4 else None,
                time_s=round(time.time() - t0, 1))


def ref_seq8():
    """參考實作的 8 輸入序列組成（同一種子）：先排列 256 個狀態（狀態 s 的第 i 路＝(s>>i)&1），再抽 768×8 個 0/1；換成 B8 的編號。"""
    rng = np.random.default_rng(SEED8)
    bits = np.array([[(s >> i) & 1 for i in range(8)] for s in rng.permutation(256)])
    bits = np.vstack([bits, rng.integers(0, 2, (768, 8))])
    return bits @ (2 ** np.arange(7, -1, -1))


def none_window(fn, L, sim, z=None):
    n, groups, lin, b_sym = design(fn, z)
    G = max(groups) + 1
    t_g = np.array(L) * PS_PER_MM
    M, c = lin([1.0] * G)
    base = np.array([t_g[g] for g in groups])
    return min(window(sim, M, c, b_sym, base + o) for o in corners(groups, G))


def diagnose(fn):
    """8 輸入的差異診斷：(a) 參考實作的序列組成；(b) margin 相近的其他相位解。"""
    sim = make_sim(8)
    base = none_window(fn, STRESS8, sim)
    alt = make_sim(8)
    alt.seq = ref_seq8()
    ref = none_window(fn, STRESS8, alt)
    runs = [json.loads(s) for s in paths.OUT("paper/m5_cascade/s1_cascade", "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    rs = [r for r in runs if r[0] == [fn] and r[2] > 0]
    best = max(r[4] for r in rs)
    near = [r for r in rs if r[4] >= best * (1 - NEAR)]
    ws = sorted({(round(r[4], 4), none_window(fn, STRESS8, sim, np.array(r[5]))) for r in near})
    return fn, dict(base=base, ref_sequence=ref, near_solutions=[dict(margin=m, window=w) for m, w in ws],
                    near_window_range=[min(w for _, w in ws), max(w for _, w in ws)], n_near=len(ws))


def main():
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(run_case, CASES))
        diag = dict(ex.map(diagnose, ("AND8", "MAJ8", "SYNC")))
    for r in res:
        d, cs, rf = r["draft"], r["chosen_summary"], r["reference"]
        if d:
            r["diff"] = dict(window=None if cs is None else cs["worst"] - d["window"], full_mm=rf["full"]["total_mm"] - d["full_mm"],
                             full_window=rf["full"]["worst"] - d["full_window"], none_window=rf["none"]["worst"] - d["none_window"])
    by = {r["label"]: r for r in res}
    tab = [r for r in res if r["draft"]]
    stress = [r for r in res if not r["draft"]]
    checks = dict(
        same_choice=all(r["chosen_summary"] is not None and abs(r["chosen_summary"]["total_mm"] - r["draft"]["chosen_mm"]) < 0.01 for r in tab),
        full_length_match=all(abs(r["diff"]["full_mm"]) < 0.01 for r in tab),
        full_eq_shrinks_at_1db=by["AND4, fan-in B, 1 dB/mm"]["reference"]["full"]["worst"] < by["AND4, fan-in B"]["reference"]["full"]["worst"] - 5,
        chosen_beats_full_at_1db=by["AND4, fan-in B, 1 dB/mm"]["chosen_summary"]["worst"] > by["AND4, fan-in B, 1 dB/mm"]["reference"]["full"]["worst"],
        stress_needs_meander=all(r["reference"]["none"]["worst"] < T_REQ for r in stress),
        stress_chosen_shorter=all(r["chosen_summary"]["total_mm"] < r["reference"]["full"]["total_mm"] for r in stress if r["chosen_summary"]),
        stress_chosen_passes_full_fails=by["AND4, fan-in C, 1 dB/mm"]["chosen_summary"] is not None
        and by["AND4, fan-in C, 1 dB/mm"]["reference"]["full"]["worst"] < T_REQ,
    )
    within = {r["label"]: abs(r["diff"]["window"]) <= 3 and abs(r["diff"]["full_window"]) <= 3 for r in tab}
    out = dict(ps_per_mm=PS_PER_MM, tol_mm=TOL_MM, internal_skew_ps=INT_SKEW, t_req_ps=T_REQ, dt_ps=DT_PS, betas=BETAS, receiver="數位二階 Butterworth 7 GHz（雙線性）",
               seed8=SEED8, fan_c=FAN_C, fan_d=FAN_D, cases=res, within_3ps=within, diagnosis=diag, checks=checks,
               time_s=round(time.time() - t0, 1), workers=WORKERS)
    path = paths.OUT(STEP, "meander.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res:
        cs, rf, d = r["chosen_summary"], r["reference"], r["draft"]
        ref = f"（草稿 {d['chosen_mm']} mm、{d['window']}）" if d else "（新增）"
        print(f"{r['label']:24s} span {r['raw_span_ps']:5.1f} ps｜選 {cs['pad_mm'] if cs else '—'}（{cs['total_mm'] if cs else '—'} mm）、最差角落窗 {cs['worst'] if cs else '—'}{ref}"
              f"｜完整等長 {rf['full']['total_mm']} mm、{rf['full']['worst']}" + (f"（草稿 {d['full_mm']}、{d['full_window']}）" if d else "")
              + f"｜不補償 {rf['none']['worst']}" + (f"（草稿 {d['none_window']}）" if d else "") + f"｜試 {len(r['tried'])}、評估 {r['evaluations']}、{r['time_s']} s")
    for fn, v in diag.items():
        print(f"診斷 {fn}：本計畫序列 {v['base']}、參考序列組成 {v['ref_sequence']}｜margin 差 ≤ 0.5% 的 {v['n_near']} 個解：窗 {v['near_window_range']}")
    print("與草稿差 ≤ 3 ps：", within)
    print("檢查：", checks, f"｜{out['time_s']} s")
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
