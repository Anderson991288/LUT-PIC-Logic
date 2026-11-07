r"""LUT4 s0：Model-7a 的邏輯涵蓋——4 輸入真值表逐張合成（E+／E− 輸入），同時保存 mask、14 個相位與裕量。

用途：每張真值表 f（第 x 位元＝輸入 x＝x1＋2x2＋4x3＋8x4 的輸出）以 synth4.synth_nb 合成 14 個相位
     （每顆 MZI 0.9 dB、R＝+3、雙差值判讀 o2＞o4＞o3、預設 24 個起點，種子＝f），記錄最大裕量與對應的 14 個相位。
     不使用等價類代表（Model-7a 對輸入的排列與反相不對稱，同一類的裕量不一定相同）。
     worker 回傳 (f, 裕量, 14 相位, 秒數)，所以結果可重播；每 CHUNK 張存一次進度，可中斷後以同樣的命令續跑。
模式：
  完整 65,536 張（不帶 --masks）：out/coverage_phases.npz、out/coverage_margins.npy（相容舊格式）、out/coverage.json。
  樣本（--masks 檔案）：out/<prefix>_phases.npz、out/<prefix>_coverage.json（prefix 預設 sample）。
  --compare <npy>：逐張與既有的裕量陣列（例如 reference/coverage_margins.npy）比較，結果寫進 json 的 reference_compare。
  --reference-json <coverage.json>：樣本模式時把既有的全表統計放進 json 的 reference 子鍵，
        並把 build_study 需要的頂層鍵（realizable、ge_0p1、median、xor4…）以該檔填入、標 source＝reference evidence。
  --shard k/n：只算第 k 片（masks[k::n]），寫 out/<prefix>_shard_k_of_n.npz；--merge 把各片合併成正式輸出。
  --summary：不計算，只由既有的 npz 重算統計。
輸入：synth4.py；--masks 的 JSON（整數或 "0x…" 字串的列表，或含 "masks" 鍵的物件）。
輸出：見上。npz 內容：masks(int32)、margins(float64)、phases(float64, M×14)、seconds(float64)、starts、code、loss_db。
執行：.\lab design\lut4v2\s0_coverage\cover4.py --masks design\lut4v2\s0_coverage\sample_masks.json --workers 4 ^
          --compare design\lut4v2\s0_coverage\reference\coverage_margins.npy --reference-json design\lut4v2\s0_coverage\reference\coverage.json
      .\lab design\lut4v2\s0_coverage\cover4.py --workers 16            （完整 65,536 張，16 個 worker 約 75 分鐘）
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4v2
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "lut4v2/s0_coverage"
CODE, LOSS, NST, CHUNK = "3142132", 0.9, 24, 2048
NPH = 14
REAL = 1e-3                                                          # 裕量大於此值才算可實現
_NST = NST                                                           # worker 用的起點數（由 main 設定）


def init(nst):
    global _NST
    _NST = nst
    try:
        import psutil
        psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def job(f):
    import synth4 as S
    arch = S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2))
    t0 = time.perf_counter()
    m, p = S.synth_nb(f, arch, _NST, f)
    p = np.zeros(NPH) if p is None else np.asarray(p, float) % (2 * np.pi)
    return f, float(m), p, time.perf_counter() - t0


def verify(masks, margins, phases):
    """用保存的相位重算裕量（與 synth4 相同模型），確認相位與裕量一致；回傳最大差。"""
    import synth4 as S
    arch = S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2))
    d = 0.0
    for f, m, p in zip(masks, margins, phases):
        if not np.isfinite(m) or m <= -1e9:
            continue
        ins = np.array([int(f) >> x & 1 for x in range(16)], bool)
        d = max(d, abs(float(arch.margins(p[None], ins).min()) - m))
    return d


def load_masks(spec):
    d = json.loads(Path(spec).read_text(encoding="utf-8"))
    if isinstance(d, dict):
        d = d["masks"]
    out = []
    for v in d:
        out.append(int(v, 16) if isinstance(v, str) else int(v))
    assert all(0 <= f < 65536 for f in out)
    return out


def summary(masks, m, starts):
    """統計（與原版 coverage.json 相同鍵）；m 為裕量陣列，NaN 表示未算。"""
    masks = np.asarray(masks); m = np.asarray(m, float)
    ok = m > REAL
    ms = m[ok]
    by = {int(f): float(v) for f, v in zip(masks, m)}
    order = np.argsort(np.where(ok, m, 9))
    out = dict(n=int(m.size), realizable=int(ok.sum()), ge_0p05=int((m >= 0.05).sum()), ge_0p1=int((m >= 0.1).sum()),
               median=float(np.median(ms)) if ms.size else None, min=float(ms.min()) if ms.size else None,
               argmin=f"0x{int(masks[order[0]]):04X}" if ms.size else None,
               xor4=by.get(0x6996), xnor4=by.get(0x9669),
               worst10=[[f"0x{int(masks[i]):04X}", round(float(m[i]), 4)] for i in order[:10]],
               unrealizable=[f"0x{int(f):04X}" for f in masks[~ok]][:50],
               code=CODE, loss_db=LOSS, starts=starts, real_threshold=REAL)
    return out


def save_npz(path, masks, margins, phases, seconds, starts):
    np.savez(path, masks=np.asarray(masks, np.int32), margins=np.asarray(margins, float), phases=np.asarray(phases, float),
             seconds=np.asarray(seconds, float), starts=starts, code=CODE, loss_db=LOSS)


def load_npz(path):
    z = np.load(path)
    return z["masks"].astype(int), z["margins"].astype(float), z["phases"].astype(float), z["seconds"].astype(float)


def run(masks, starts, workers, npz, label):
    """算 masks 中尚未算的（可續跑），結果存 npz；回傳 (margins, phases, seconds)。"""
    M = len(masks)
    margins, phases, seconds = np.full(M, np.nan), np.zeros((M, NPH)), np.full(M, np.nan)
    if npz.exists():
        om, omg, oph, osc = load_npz(npz)
        pos = {int(f): i for i, f in enumerate(om)}
        for i, f in enumerate(masks):
            if f in pos and np.isfinite(omg[pos[f]]):
                margins[i], phases[i], seconds[i] = omg[pos[f]], oph[pos[f]], osc[pos[f]]
    idx = {f: i for i, f in enumerate(masks)}
    todo = [f for i, f in enumerate(masks) if not np.isfinite(margins[i])]
    print(f"[{label}] {M} 張，已有 {M - len(todo)}，待算 {len(todo)}，{workers} 個 worker、{starts} 個起點", flush=True)
    if todo:
        import synth4 as S
        S.synth_nb(0x6996, S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2)), 1, 0)   # 先編譯（numba cache）
        t0 = time.perf_counter()
        with Pool(workers, initializer=init, initargs=(starts,)) as P:
            for k, (f, v, p, sec) in enumerate(P.imap_unordered(job, todo, chunksize=max(1, min(16, len(todo) // (4 * workers) or 1))), 1):
                i = idx[f]
                margins[i], phases[i], seconds[i] = v, p, sec
                if k % CHUNK == 0 or k == len(todo):
                    save_npz(npz, masks, margins, phases, seconds, starts)
                    el = time.perf_counter() - t0
                    print(f"[{label}] {k}/{len(todo)}　{el / 60:.1f} 分　預估剩 {el / k * (len(todo) - k) / 60:.1f} 分", flush=True)
        print(f"[{label}] 計算 {time.perf_counter() - t0:.1f} s；每張平均 {np.nanmean(seconds[[idx[f] for f in todo]]):.3f} s（單一 worker）", flush=True)
    return margins, phases, seconds


def compare(masks, margins, ref_npy):
    ref = np.load(ref_npy)
    rows, mism = [], []
    for f, m in zip(masks, margins):
        r = float(ref[f]); d = abs(m - r)
        rows.append(dict(f=f"0x{int(f):04X}", this=round(float(m), 6), ref=round(r, 6), diff=round(float(d), 6)))
        if d > 1e-3 or ((m > REAL) != (r > REAL)):
            mism.append(rows[-1])
    diffs = np.array([r["diff"] for r in rows])
    return dict(reference_npy=str(Path(ref_npy).name), n=len(rows), max_abs_diff=float(diffs.max()),
                argmax=rows[int(diffs.argmax())]["f"], n_within_1e_3=int((diffs <= 1e-3).sum()),
                n_within_1e_6=int((diffs <= 1e-6).sum()), mismatches=mism, rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks", help="JSON 檔：要合成的真值表列表（不給則為全部 65,536 張）")
    ap.add_argument("--prefix", default=None, help="樣本模式的輸出檔名前綴（預設 sample；完整模式固定 coverage）")
    ap.add_argument("--starts", type=int, default=NST)
    ap.add_argument("--workers", type=int, default=min(int(os.environ.get("LAB_WORKERS", 4)), 24))
    ap.add_argument("--shard", help="k/n：只算第 k 片（0 起算）")
    ap.add_argument("--merge", action="store_true", help="把各片 npz 合併成正式輸出（不計算）")
    ap.add_argument("--summary", action="store_true", help="只由既有 npz 重算統計")
    ap.add_argument("--compare", help="既有裕量 .npy（65,536 個），逐張比較")
    ap.add_argument("--reference-json", help="既有的全表 coverage.json：樣本模式時放進 reference 子鍵並填頂層鍵")
    ap.add_argument("--no-verify", action="store_true", help="略過用保存相位重算裕量的核對")
    a = ap.parse_args()

    out = paths.OUT(STEP)
    full = a.masks is None
    prefix = "coverage" if full else (a.prefix or "sample")
    masks = list(range(65536)) if full else load_masks(a.masks)
    npz = out / f"{prefix}_phases.npz"
    t_all = time.perf_counter()

    if a.shard and not a.merge:
        k, n = map(int, a.shard.split("/"))
        sub = masks[k::n]
        run(sub, a.starts, a.workers, out / f"{prefix}_shard_{k}_of_{n}.npz", f"shard {k}/{n}")
        return
    if a.merge:
        margins, phases, seconds = np.full(len(masks), np.nan), np.zeros((len(masks), NPH)), np.full(len(masks), np.nan)
        idx = {f: i for i, f in enumerate(masks)}
        for p in sorted(out.glob(f"{prefix}_shard_*_of_*.npz")):
            om, omg, oph, osc = load_npz(p)
            for f, v, ph, sc in zip(om, omg, oph, osc):
                if np.isfinite(v):
                    margins[idx[int(f)]], phases[idx[int(f)]], seconds[idx[int(f)]] = v, ph, sc
        save_npz(npz, masks, margins, phases, seconds, a.starts)
        print("合併", len(masks), "張，尚未算", int(np.isnan(margins).sum()))
    elif a.summary:
        om, margins, phases, seconds = load_npz(npz)
        assert list(om) == masks, "npz 的 masks 與指定的不同"
    else:
        margins, phases, seconds = run(masks, a.starts, a.workers, npz, prefix)
    assert not np.isnan(margins).any(), "尚未算完"

    s = summary(masks, margins, a.starts)
    s["seconds_per_mask_mean"] = round(float(np.nanmean(seconds)), 4)
    s["seconds_per_mask_max"] = round(float(np.nanmax(seconds)), 4)
    s["wall_s"] = round(time.perf_counter() - t_all, 1)
    s["workers"] = a.workers
    s["phases_file"] = npz.name
    if not a.no_verify:
        s["phase_margin_recheck_max_diff"] = float(verify(masks, margins, phases))
    if full:
        np.save(out / "coverage_margins.npy", margins)
        s["source"] = "this round (full 65,536 rerun)"
        s["masks_file"] = None
        s["mask_list"] = None
    else:
        s["masks_file"] = Path(a.masks).name
        s["mask_list"] = [f"0x{f:04X}" for f in masks]
        s["margins"] = {f"0x{f:04X}": round(float(m), 6) for f, m in zip(masks, margins)}
    if a.compare:
        s["reference_compare"] = compare(masks, margins, a.compare)
    if full:
        (out / "coverage.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in s.items() if k not in ("worst10",)}, ensure_ascii=False))
        return
    (out / f"{prefix}_coverage.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.reference_json:
        ref = json.loads(Path(a.reference_json).read_text(encoding="utf-8"))
        full_json = dict(ref)                                           # build_study 需要的頂層鍵由既有全表證據填入
        full_json["source"] = "reference evidence (not rerun this round)"
        full_json["note"] = ("頂層 n／realizable／ge_0p05／ge_0p1／median／min／argmin／xor4／xnor4／worst10 來自既有的全表證據"
                             "（reference 子鍵）；本輪只重算 sample 子鍵列出的樣本。")
        full_json["reference"] = ref
        full_json["sample"] = {k: v for k, v in s.items() if k not in ("margins", "mask_list")}
        full_json["sample"]["unrealizable"] = s["unrealizable"]
        (out / "coverage.json").write_text(json.dumps(full_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k not in ("margins", "mask_list", "reference_compare")}, ensure_ascii=False))
    if a.compare:
        c = s["reference_compare"]
        print("與既有裕量比較：最大差", c["max_abs_diff"], "＠", c["argmax"], "；≤1e-3 的張數", c["n_within_1e_3"], "/", c["n"],
              "；不一致", [(r["f"], r["this"], r["ref"]) for r in c["mismatches"]])


if __name__ == "__main__":
    main()
