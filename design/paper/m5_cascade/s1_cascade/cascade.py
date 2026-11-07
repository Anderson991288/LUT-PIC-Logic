r"""論文 M5 s1：兩級串接與 8 輸入合成——4 顆 B7 不在中間判讀，能做 x1x8、AND8、MAJ8、同步字等 8 輸入函數嗎（草稿 II-C、圖 3）？

用途：
  1. 網路（草稿 II-C）：前級 Macro 1 收 x1–x4、Macro 2 收 x5–x8（各自在波導 5 加參考光 R＝3）；前級的 o5 接終端，
     其餘四路光場直接送到後級，不經光偵測、不判讀。後級 Macro 4 收兩顆前級的讀取埠（波導 2、4），
     Macro 3 收另外兩路（波導 1、3）；兩顆後級也各自有 R＝3，判讀仍是 P_o2 − P_o4、共用零門檻。
     單判讀只用 Macro 1、2、4（21 顆 MZI、42 個相位）；雙判讀四顆一起（28 顆 MZI、56 個相位），兩個函數放在哪顆後級兩種都算、取較好者。
     標稱模型：級間傳輸的鏈相位已吸收（設為 0）、直線段損耗不計，與草稿 II-A 的模型一致。
  2. 目標（參考實作的具名清單）：14 個 8 輸入單判讀函數與 8 組雙判讀聯合指派；判讀方向 s_f(x)，x 是 256 組 8 位元字。
  3. 合成：同 M3 s2（草稿式 2）——退火的 log-sum-exp soft-min（β 逐段加大）＋ L-BFGS-B，STARTS 個隨機起點，
     最後以實際相位重算最差 margin；兩種損耗：無損與每顆 MZI 0.9 dB。
     42–56 個相位的地形有許多局部最佳解，第二輪只依本身的結果補算（不看參考值）：
     (a) 隨機起點彼此不一致（與最佳值差 ≤ 0.005 P_u 的起點少於 2 個）時，再加 EXTRA 個隨機起點；
     (b) 每一項都從另一種損耗下的最佳相位出發再跑一次（暖啟動）。
  4. 可實現的判斷：margin ＞ 0（共用零門檻下判讀方向全對）、≥ 0.1 P_u（結構性 margin，草稿覆蓋率的門檻）、
     ≥ 0.20 P_u（最大輸出功率時的保守護欄，草稿 II-B）。
  驗收：14 個單判讀與 8 組雙判讀在無損時全部可實現（margin ＞ 0），或列出不能實現者；與參考實作的 margin 比較。
輸入：design/paper/m3_align/s2_synth/synth.py（B7 模型與 soft-min 設定）、design/paper/m3_align/draft.py。
輸出：design/paper/m5_cascade/s1_cascade/out/cascade.json、runs.jsonl（每個起點一筆的快取，中斷後可續跑）。
執行：.\lab design\paper\m5_cascade\s1_cascade\cascade.py（6 個 worker 約 70 分鐘；每個起點 40–60 s）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_timing" / "s1_budget"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s2_synth"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import draft as D                                                    # noqa: E402
import paths                                                         # noqa: E402
import synth as SY                                                   # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

STEP = "paper/m5_cascade/s1_cascade"
SINGLE_ONLY = "--single-only" in sys.argv                            # 重現範圍：只跑 14 個單判讀；8 組雙判讀（平行度 2 約 2.4 h）沿用參考證據並標示
STARTS, SEED0 = 4, 5000                                            # 第一輪與參考實作相同
EXTRA = 8                                                            # 第二輪 (a) 加的隨機起點
BETAS = SY.BETAS
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
LOSSES = (0.0, D.SETTINGS["mzi_loss_db"])
B4 = np.array(list(itertools.product([0, 1], repeat=4)))
B8 = np.array(list(itertools.product([0, 1], repeat=8)))           # 第 w 列＝(x1…x8)；w＝16·a＋b，a、b 是前後半的 4 位元字
WIRE = {"M4": (1, 3), "M3": (0, 2)}                                  # 後級收前級的哪兩個波導（索引 0–4；1、3＝讀取埠 o2、o4）
TARGETS = {
    "AND8": lambda b: b.all(),
    "OR8": lambda b: b.any(),
    "MAJ8": lambda b: b.sum() >= 5,
    "TH7of8": lambda b: b.sum() >= 7,
    "SYNC": lambda b: tuple(b) == (1, 0, 1, 1, 0, 0, 1, 0),
    "XOR2(x1,x2)": lambda b: b[0] != b[1],
    "XOR2(x1,x8)": lambda b: b[0] != b[7],
    "x1": lambda b: bool(b[0]),
    "AND2(x1,x2)": lambda b: b[0] and b[1],
    "x1x8": lambda b: b[0] and b[7],
    "AND4(x1..4)": lambda b: b[:4].all(),
    "AND4(x5..8)": lambda b: b[4:].all(),
    "x1x2+x7x8": lambda b: (b[0] and b[1]) or (b[6] and b[7]),
    "MUX": lambda b: b[0] if b[7] else b[4],
}
DEFN = {"AND8": "x1…x8 全為 1", "OR8": "至少一個為 1", "MAJ8": "至少 5 個為 1", "TH7of8": "至少 7 個為 1", "SYNC": "同步字 10110010",
        "XOR2(x1,x2)": "x1 ⊕ x2", "XOR2(x1,x8)": "x1 ⊕ x8（跨兩顆前級）", "x1": "x1", "AND2(x1,x2)": "x1 x2", "x1x8": "x1 x8（跨兩顆前級）",
        "AND4(x1..4)": "x1 x2 x3 x4", "AND4(x5..8)": "x5 x6 x7 x8", "x1x2+x7x8": "x1 x2 ＋ x7 x8", "MUX": "x8 ? x1 : x5"}
PAIRS = [("AND8", "OR8"), ("MAJ8", "SYNC"), ("AND4(x1..4)", "AND4(x5..8)"), ("x1x8", "MUX"), ("XOR2(x1,x8)", "AND8"),
         ("x1x2+x7x8", "TH7of8"), ("AND2(x1,x2)", "XOR2(x1,x2)"), ("MAJ8", "MAJ8")]
# 參考實作（同一接線、4 個起點）的 margin（P_u），只用來比較：{函數或配對: (無損, 0.9 dB)}；配對取兩種指派較好者
REF = {"AND8": (1.8364, 0.6362), "OR8": (1.8371, 0.6211), "MAJ8": (1.8368, 0.6262), "TH7of8": (1.8365, 0.6317), "SYNC": (1.8989, 0.6506),
       "XOR2(x1,x2)": (0.4954, 0.1193), "XOR2(x1,x8)": (0.4954, 0.1433), "x1": (5.1953, 1.6603), "AND2(x1,x2)": (3.6729, 1.1811),
       "x1x8": (3.6729, 1.3162), "AND4(x1..4)": (2.597, 0.8424), "AND4(x5..8)": (2.597, 0.8982), "x1x2+x7x8": (0.614, 0.1899),
       "MUX": (0.6424, 0.1963),
       "AND8｜OR8": (1.0664, 0.3891), "MAJ8｜SYNC": (1.2473, 0.4475), "AND4(x1..4)｜AND4(x5..8)": (2.1195, 0.7681),
       "x1x8｜MUX": (0.6257, 0.1955), "XOR2(x1,x8)｜AND8": (0.484, 0.1416), "x1x2+x7x8｜TH7of8": (0.5741, 0.1786),
       "AND2(x1,x2)｜XOR2(x1,x2)": (0.25, 0.1228), "MAJ8｜MAJ8": (0.9608, 0.367)}
V4 = np.hstack([B4.astype(complex), np.full((16, 1), R_AMP + 0j)])


def signs(fn):
    return np.array([1.0 if TARGETS[fn](b) else -1.0 for b in B8])


def back_outputs(z, amp, backs):
    """z：每顆 14 個相位，依 Macro 1、2、後級（backs 的順序）排列。回傳 {後級: (P_o2 − P_o4, P_o2 ＋ P_o4)}，各 256 組字。"""
    oA = V4 @ SY.b7(z[:14], amp).T                                   # 16×5：Macro 1 的輸出場
    oB = V4 @ SY.b7(z[14:28], amp).T                                 # Macro 2
    out = {}
    for k, name in enumerate(backs):
        i, j = WIRE[name]
        v = np.empty((256, 5), complex)
        v[:, 0] = np.repeat(oA[:, i], 16)                             # w＝16·a＋b：前半由 a 決定、後半由 b 決定
        v[:, 1] = np.repeat(oA[:, j], 16)
        v[:, 2] = np.tile(oB[:, i], 16)
        v[:, 3] = np.tile(oB[:, j], 16)
        v[:, 4] = R_AMP
        P = np.abs(v @ SY.b7(z[28 + 14 * k:42 + 14 * k], amp).T) ** 2
        out[name] = (P[:, READ[0]] - P[:, READ[1]], P[:, READ[0]] + P[:, READ[1]])
    return out


def signed(z, amp, fns, backs):
    out = back_outputs(z, amp, backs)
    return np.concatenate([signs(f) * out[b][0] for f, b in zip(fns, backs)])


def run(job):
    """一個起點：fns 依序放到 backs（單判讀 ('M4',)；雙判讀 ('M3','M4')）。k 是整數＝隨機起點；k＝'warm' 時從 z0 出發。"""
    fns, backs, loss_db, k, z0 = job
    amp = 10 ** (-loss_db / 20)
    S = [signs(f) for f in fns]
    z = (np.array(z0) if k == "warm" else
         np.random.default_rng(SEED0 + 97 * k + 7 * len(fns) + int(loss_db > 0)).uniform(0, 2 * np.pi, 28 + 14 * len(backs)))

    def m_of(x):
        out = back_outputs(x, amp, backs)
        return np.concatenate([s * out[b][0] for s, b in zip(S, backs)])

    t0 = time.time()
    for beta in BETAS:
        def f(x):
            m = m_of(x)
            return -(-np.log(np.sum(np.exp(-beta * (m - m.min())))) / beta + m.min())
        z = minimize(f, z, method="L-BFGS-B", options=dict(maxiter=500)).x
    return list(fns), list(backs), loss_db, k, float(m_of(z).min()), (z % (2 * np.pi)).tolist(), round(time.time() - t0, 1)


def groups():
    """每一項（單判讀函數或雙判讀配對）的所有指派順序與對應的後級。"""
    G = {(fn,): [((fn,), ("M4",))] for fn in TARGETS}
    for a, b in ([] if SINGLE_ONLY else PAIRS):
        G[(a, b)] = [((a, b), ("M3", "M4"))] + ([((b, a), ("M3", "M4"))] if a != b else [])
    return G


def execute(J, cache, done):
    """執行還沒算過的工作，逐筆寫進快取（中斷後可續跑）。"""
    todo = [j for j in J if (tuple(j[0]), j[2], j[3]) not in done]
    with ProcessPoolExecutor(WORKERS) as ex, open(cache, "a", encoding="utf-8") as fh:
        for r in ex.map(run, todo, chunksize=1):
            done[(tuple(r[0]), r[2], r[3])] = r
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()


def best_of(done, orders, L):
    """隨機起點（第一輪與加算）中的最佳一筆；不含暖啟動，所以從快取續跑時暖啟動的起點不會變。"""
    rs = [r for (f, l, k), r in done.items() if l == L and f in {o for o, _ in orders} and k != "warm"]
    return max(rs, key=lambda r: r[4])


def summarize(runs, key_fns, loss):
    rs = [r for r in runs if tuple(r[0]) in key_fns and r[2] == loss]
    rnd = [r[4] for r in rs if r[3] != "warm"]
    best = max(rs, key=lambda r: r[4])
    best_rnd = max(rnd)
    return dict(best=round(best[4], 4), assignment=best[0], source="暖啟動" if best[3] == "warm" else "隨機起點",
                best_random=round(best_rnd, 4), n_random=len(rnd),
                spread=[round(min(rnd), 4), round(float(np.median(rnd)), 4), round(best_rnd, 4)],
                hits=int(sum(1 for v in rnd if v >= best_rnd - 0.005)), phases=best[5])


def main():
    t0 = time.time()
    cache = paths.OUT(STEP, "runs.jsonl")
    done = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[(tuple(r[0]), r[2], r[3])] = r
    G = groups()
    # 第一輪：每個指派順序 STARTS 個隨機起點
    execute([(o, b, L, k, None) for orders in G.values() for o, b in orders for L in LOSSES for k in range(STARTS)], cache, done)
    # 第二輪（只看本身的結果，不看參考值）：(a) 第一輪的隨機起點不一致（命中最佳值的起點 < 2）時再加 EXTRA 個；
    # (b) 每一項都從另一種損耗下隨機起點的最佳相位暖啟動一次。兩者都只依第一輪／隨機起點判斷，從快取續跑結果不變
    extra = []
    for key, orders in G.items():
        for L in LOSSES:
            ms = [r[4] for (f, l, k), r in done.items() if l == L and f in {o for o, _ in orders} and k != "warm" and k < STARTS]
            if sum(1 for v in ms if v >= max(ms) - 0.005) < 2:
                extra += [(o, b, L, k, None) for o, b in orders for k in range(STARTS, STARTS + EXTRA)]
    execute(extra, cache, done)
    warm = []
    for key, orders in G.items():
        for L, L2 in ((LOSSES[0], LOSSES[1]), (LOSSES[1], LOSSES[0])):
            src = best_of(done, orders, L2)
            o = tuple(src[0])
            warm.append((o, dict(orders)[o], L, "warm", src[5]))
    execute(warm, cache, done)
    runs = list(done.values())
    guard = D.GUARD_COVERAGE
    single, dual = {}, {}
    for fn in TARGETS:
        r = dict(defn=DEFN[fn], n_mzi=21, phases=42)
        for L, key in zip(LOSSES, ("lossless", "lossy")):
            r[key] = summarize(runs, {(fn,)}, L)
            r[key]["ref"] = REF[fn][int(L > 0)]
        single[fn] = r
    if SINGLE_ONLY:                                                  # 未重跑：只核對既有證據，不與本次 runs.jsonl 混合
        dual = json.loads((Path(__file__).resolve().parent / "ref_evidence" / "cascade_ref.json").read_text(encoding="utf-8"))["dual"]
    for a, b in ([] if SINGLE_ONLY else PAIRS):
        lab = f"{a}｜{b}"
        r = dict(funcs=[a, b], n_mzi=28, phases=56)
        for L, key in zip(LOSSES, ("lossless", "lossy")):
            r[key] = summarize(runs, {(a, b), (b, a)}, L)
            r[key]["by_order"] = {f"{o[0]}→M3": round(max(x[4] for x in runs if tuple(x[0]) == o and x[2] == L), 4)
                                  for o in ({(a, b), (b, a)})}
            r[key]["ref"] = REF[lab][int(L > 0)]
        dual[lab] = r
    allv = list(single.values()) + list(dual.values())

    def count(key, th):
        return sum(1 for v in allv[:len(single)] if v[key]["best"] > th), sum(1 for v in allv[len(single):] if v[key]["best"] > th)

    stats = {key: dict(pos=count(key, 0.0), ge01=count(key, 0.1 - 1e-12), ge_guard=count(key, guard - 1e-12),
                       median_single=round(float(np.median([v[key]["best"] for v in single.values()])), 4),
                       median_dual=round(float(np.median([v[key]["best"] for v in dual.values()])), 4),
                       ratio_ref_min=round(min(v[key]["best"] / v[key]["ref"] for v in allv), 3),
                       ratio_ref_max=round(max(v[key]["best"] / v[key]["ref"] for v in allv), 3))
             for key in ("lossless", "lossy")}
    checks = dict(all_lossless_realizable=stats["lossless"]["pos"] == (len(single), len(dual)),
                  lossless_ge_lossy=all(v["lossless"]["best"] >= v["lossy"]["best"] for v in allv),
                  dual_le_single=all(min(single[f]["lossless"]["best"] for f in set(v["funcs"])) >= v["lossless"]["best"] - 1e-3
                                     for v in dual.values()))
    res = dict(scope="single_only" if SINGLE_ONLY else "full",
               dual_source="只核對既有證據（參考專案 cascade.json，本次未重跑）" if SINGLE_ONLY else "本次重跑",
               starts=STARTS, seed0=SEED0, betas=BETAS, wire=WIRE, r_amp=R_AMP, guard_coverage=guard, losses=LOSSES,
               single=single, dual=dual, stats=stats, checks=checks,
               job_time_s=dict(min=min(r[6] for r in runs), median=float(np.median([r[6] for r in runs])), max=max(r[6] for r in runs)),
               n_runs=dict(first=sum(1 for r in runs if r[3] != "warm" and r[3] < STARTS), extra=len(extra), warm=len(warm)),
               warm_improved=sorted({f"{'｜'.join(v.get('funcs', [k]))} {key}" for grp in (single, dual) for k, v in grp.items()
                                     for key in ("lossless", "lossy") if v[key]["source"] == "暖啟動" and v[key]["best"] > v[key]["best_random"] + 0.005}),
               vs_ref={key: {lab: dict(ours=v[key]["best"], ref=v[key]["ref"], ratio=round(v[key]["best"] / v[key]["ref"], 3))
                             for lab, v in list(single.items()) + list(dual.items()) if abs(v[key]["best"] / v[key]["ref"] - 1) > 0.01}
                       for key in ("lossless", "lossy")},
               below_guard_lossy=[lab for lab, v in list(single.items()) + list(dual.items()) if v["lossy"]["best"] < guard],
               extra_s=EXTRA, time_s=dict(this_run=round(time.time() - t0, 1), compute_sum=round(sum(r[6] for r in runs), 1)), workers=WORKERS)
    path = paths.OUT(STEP, "cascade.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, v in single.items():
        print(f"{fn:13s} 無損 {v['lossless']['best']:.4f}（參考 {v['lossless']['ref']:.4f}）｜0.9 dB {v['lossy']['best']:.4f}"
              f"（參考 {v['lossy']['ref']:.4f}，命中 {v['lossy']['hits']}/{v['lossy']['n_random']}）")
    for lab, v in dual.items():
        print(f"{lab:26s} 無損 {v['lossless']['best']:.4f}（參考 {v['lossless']['ref']:.4f}）｜0.9 dB {v['lossy']['best']:.4f}"
              f"（參考 {v['lossy']['ref']:.4f}）｜{v['lossy']['by_order']}")
    print("統計：", stats)
    print("第二輪：加起點", len(extra), "筆、暖啟動", len(warm), "筆；暖啟動改善：", res["warm_improved"])
    print("檢查：", checks, f"｜{res['time_s']} s")
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
