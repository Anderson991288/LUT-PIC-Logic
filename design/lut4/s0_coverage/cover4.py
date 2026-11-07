r"""LUT4 s0：Model-7a 的邏輯涵蓋——4 輸入真值表逐張合成，保存 mask、14 個相位與裕量。

用途：每張真值表 f（第 x 位元＝輸入 x＝x1＋2x2＋4x3＋8x4 的輸出）以 synth4.synth_nb 合成 14 個相位
     （每顆 MZI 0.9 dB、R＝3、雙差值判讀 o2＞o4＞o3、24 個起點、種子＝f），記錄最大裕量與對應的相位。
     不使用等價類代表（Model-7a 對輸入的排列與反相不對稱，同一類的裕量不一定相同）。
     本版與原版的差異：worker 回傳 (mask, 裕量, 14 相位, 秒數)，相位一併存檔；可指定 mask 清單、worker 數、
     分片（--shard k/n）與續跑（已存的 npz 會被讀回，只算還沒算的）。
輸入：synth4.py；--masks 時另讀 mask 清單（JSON：{"masks": [...]}，十六進位字串或整數）。
輸出：
  --masks：out/<tag>_phases.npz（masks、phases、margins、seconds、done）、out/<tag>_coverage.json（統計、與參考裕量逐張比較）
  全量（不給 --masks）：out/coverage_phases.npz 同上，並以 --write-coverage-json 產生 out/coverage.json
  --make-sample：out/sample_masks.json（七個範例＋參考 worst10＋種子 20261107 隨機 200 張）
  --write-coverage-json：out/coverage.json（build_study 讀的檔；本輪樣本統計＋ reference 子鍵的參考全量統計）
執行：.\lab design\lut4\s0_coverage\cover4.py --make-sample
      .\lab design\lut4\s0_coverage\cover4.py --masks design\lut4\s0_coverage\out\sample_masks.json --workers 4 --tag sample
      .\lab design\lut4\s0_coverage\cover4.py --write-coverage-json
      .\lab design\lut4\s0_coverage\cover4.py --workers 6            （全部 65,536 張，約 2 小時；需使用者授權）
      .\lab design\lut4\s0_coverage\cover4.py --workers 4 --shard 0/4 （分片；之後以 --merge 合併）
"""
import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "lut4/s0_coverage"
CODE, LOSS, NST = "3142132", 0.9, 24
REAL = 1e-3                                                          # 裕量大於此值才算可實現
NPH = 14
EXAMPLES = {"AND2": 0x8888, "OR2": 0xEEEE, "XOR2": 0x6666, "NAND2": 0x7777, "AND4": 0x8000, "XOR4": 0x6996, "MUX": 0xCACA}
REF_WORST10 = [0x9667, 0xD669, 0x5669, 0x1669, 0x966E, 0x9679, 0x9629, 0x7996, 0x9665, 0x3D96]   # 參考全量掃描的最差 10 張
SAMPLE_SEED, SAMPLE_N = 20261107, 200
REF_NPY = Path(__file__).resolve().parent / "reference" / "coverage_margins.npy"     # 參考專案的全量裕量（既有證據，非本輪重跑）


def init():
    try:
        import psutil
        psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def job(f):
    import synth4 as S
    arch = S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2))
    t0 = time.perf_counter()
    m, p = S.synth_nb(f, arch, NST, f)
    return f, float(m), np.asarray(p, float), time.perf_counter() - t0


def summary(m):
    ok = m > REAL
    ms = m[ok]
    return dict(n=int(m.size), realizable=int(ok.sum()), ge_0p05=int((m >= 0.05).sum()), ge_0p1=int((m >= 0.1).sum()),
                median=float(np.median(ms)), min=float(ms.min()), argmin=f"0x{int(np.argmin(np.where(ok, m, 9))):04X}",
                xor4=float(m[0x6996]), xnor4=float(m[0x9669]),
                worst10=[[f"0x{int(f):04X}", round(float(m[f]), 4)] for f in np.argsort(np.where(ok, m, 9))[:10]],
                code=CODE, loss_db=LOSS, starts=NST, real_threshold=REAL)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hx(f):
    return f"0x{int(f):04X}"


def parse_mask(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def make_sample(out):
    rng = np.random.default_rng(SAMPLE_SEED)
    rand = [int(v) for v in rng.integers(0, 65536, SAMPLE_N)]
    fixed = list(EXAMPLES.values()) + REF_WORST10
    masks, seen = [], set()
    for f in fixed + rand:
        if f not in seen:
            masks.append(f); seen.add(f)
    doc = dict(description="固定小樣本：七個範例、參考全量掃描的最差 10 張、種子 20261107 以 integers(0, 65536, 200) 抽 200 張（去重）",
               examples={k: hx(v) for k, v in EXAMPLES.items()}, reference_worst10=[hx(v) for v in REF_WORST10],
               random_seed=SAMPLE_SEED, random_n=SAMPLE_N, random_duplicates_removed=len(fixed + rand) - len(masks),
               n=len(masks), masks=[hx(f) for f in masks])
    (out / "sample_masks.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sample_masks.json：{len(masks)} 張")


def load_store(npz, masks):
    """讀回已存的結果（續跑）；回傳 (phases, margins, seconds, done)，順序依 masks。"""
    P = np.full((len(masks), NPH), np.nan); M = np.full(len(masks), np.nan); T = np.full(len(masks), np.nan)
    done = np.zeros(len(masks), bool)
    if npz.exists():
        z = np.load(npz)
        pos = {int(f): i for i, f in enumerate(masks)}
        for f, p, m, t, d in zip(z["masks"], z["phases"], z["margins"], z["seconds"], z["done"]):
            if int(f) in pos and d:
                i = pos[int(f)]; P[i], M[i], T[i], done[i] = p, m, t, True
    return P, M, T, done


def save_store(npz, masks, P, M, T, done):
    np.savez(npz, masks=np.asarray(masks, np.int64), phases=P, margins=M, seconds=T, done=done,
             phase_order=np.array("theta1,phi1,...,theta7,phi7"), code=np.array(CODE), loss_db=LOSS, starts=NST, seed_rule=np.array("seed = mask"))


def compare_reference(masks, M):
    if not REF_NPY.exists():
        return dict(available=False)
    ref = np.load(REF_NPY)
    d = M - ref[masks]
    order = np.argsort(-np.abs(d))
    return dict(available=True, file="reference/coverage_margins.npy", sha256=sha(REF_NPY), n=int(len(masks)),
                max_abs_diff=float(np.max(np.abs(d))), n_diff_gt_1e_6=int((np.abs(d) > 1e-6).sum()), n_diff_gt_1e_3=int((np.abs(d) > 1e-3).sum()),
                n_ours_better=int((d > 1e-6).sum()), n_ref_better=int((d < -1e-6).sum()),
                worst_mismatch=[dict(mask=hx(masks[i]), ours=round(float(M[i]), 6), reference=round(float(ref[masks[i]]), 6), diff=round(float(d[i]), 6))
                                for i in order[:10] if abs(d[i]) > 1e-6])


def run(masks, out, tag, workers, chunk):
    import synth4 as S
    S.synth_nb(0x6996, S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2)), 1, 0)   # 先編譯（numba cache）
    npz = out / f"{tag}_phases.npz"
    P, M, T, done = load_store(npz, masks)
    todo = [int(masks[i]) for i in np.where(~done)[0]]
    pos = {int(f): i for i, f in enumerate(masks)}
    print(f"{tag}：{len(masks)} 張，已有 {int(done.sum())}，待算 {len(todo)}，worker {workers}", flush=True)
    t0 = time.perf_counter()
    if todo:
        with Pool(workers, initializer=init) as pool:
            for k, (f, m, p, sec) in enumerate(pool.imap_unordered(job, todo, chunksize=4), 1):
                i = pos[f]; P[i], M[i], T[i], done[i] = p, m, sec, True
                if k % chunk == 0 or k == len(todo):
                    save_store(npz, masks, P, M, T, done)
                    el = time.perf_counter() - t0
                    print(f"{k}/{len(todo)}　{el / 60:.1f} 分　預估剩 {el / k * (len(todo) - k) / 60:.1f} 分", flush=True)
    wall = time.perf_counter() - t0
    return P, M, T, done, wall, npz


def sample_report(masks, P, M, T, wall, workers, npz, src, out, tag):
    masks = np.asarray(masks)
    order = np.argsort(M)
    sec_mean, sec_med = float(np.nanmean(T)), float(np.nanmedian(T))
    rep = dict(source="this round (sample synthesis)", masks_file=str(src.name), n=int(len(masks)), starts=NST, seed_rule="seed = mask",
               code=CODE, loss_db=LOSS, workers=workers, wall_s=round(wall, 1),
               sec_per_mask=dict(mean=round(sec_mean, 3), median=round(sec_med, 3), max=round(float(np.nanmax(T)), 3)),
               full_run_estimate_h={f"{w} workers": round(sec_mean * 65536 / w / 3600, 2) for w in (4, 6, 8, 12)},
               stats=dict(min=float(M.min()), argmin=hx(masks[order[0]]), median=float(np.median(M)), max=float(M.max()),
                          realizable=int((M > REAL).sum()), ge_0p05=int((M >= 0.05).sum()), ge_0p1=int((M >= 0.1).sum())),
               examples={k: round(float(M[list(masks).index(v)]), 6) for k, v in EXAMPLES.items() if v in masks},
               reference_worst10={hx(v): round(float(M[list(masks).index(v)]), 6) for v in REF_WORST10 if v in masks},
               worst5=[dict(mask=hx(masks[i]), margin=round(float(M[i]), 6)) for i in order[:5]],
               phases_file=npz.name, phases_sha256=sha(npz), reference_compare=compare_reference(masks, M))
    (out / f"{tag}_coverage.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("stats", "examples", "sec_per_mask", "full_run_estimate_h")}, ensure_ascii=False))
    rc = rep["reference_compare"]
    if rc.get("available"):
        print(f"與參考裕量比較：最大差 {rc['max_abs_diff']:.2e}，>1e-6 者 {rc["n_diff_gt_1e_6"]} 張，>1e-3 者 {rc["n_diff_gt_1e_3"]} 張")


def write_coverage_json(out):
    """build_study 讀的 coverage.json：本輪只有樣本，全量統計來自參考既有證據（reference 子鍵）。"""
    samp = json.loads((out / "sample_coverage.json").read_text(encoding="utf-8"))
    full = out / "coverage_phases.npz"
    doc = dict(source="reference evidence (not rerun this round)",
               note="全量 65,536 張逐張合成本輪未重跑（需使用者授權，約 1–2 小時）；本輪只重跑固定小樣本，見 sample 子鍵。"
                    "reference 子鍵由 reference/coverage_margins.npy（參考專案的既有證據）以本檔的 summary() 重算。",
               sample=samp)
    if full.exists():
        z = np.load(full)
        if z["done"].all():
            doc["source"] = "this round (full rerun)"
            doc.update(summary(z["margins"][np.argsort(z["masks"])]))
    if REF_NPY.exists():
        doc["reference"] = dict(file="reference/coverage_margins.npy", sha256=sha(REF_NPY), **summary(np.load(REF_NPY)))
    (out / "coverage.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("coverage.json 寫出；source =", doc["source"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks"); ap.add_argument("--workers", type=int, default=4); ap.add_argument("--tag")
    ap.add_argument("--shard"); ap.add_argument("--merge", action="store_true"); ap.add_argument("--chunk", type=int)
    ap.add_argument("--make-sample", action="store_true"); ap.add_argument("--write-coverage-json", action="store_true")
    a = ap.parse_args()
    out = paths.OUT(STEP)
    if a.make_sample:
        return make_sample(out)
    if a.write_coverage_json:
        return write_coverage_json(out)
    if a.masks:
        src = Path(a.masks)
        masks = [parse_mask(v) for v in json.loads(src.read_text(encoding="utf-8"))["masks"]]
        tag = a.tag or src.stem.replace("_masks", "")
        chunk = a.chunk or 32
    else:
        src = Path("all"); masks = list(range(65536)); tag = a.tag or "coverage"; chunk = a.chunk or 2048
    if a.merge:
        shards = sorted(out.glob(f"{tag}_shard*_phases.npz"))
        P, M, T, done = load_store(out / "__none__.npz", masks)
        pos = {int(f): i for i, f in enumerate(masks)}
        for s in shards:
            z = np.load(s)
            for f, p, m, t, d in zip(z["masks"], z["phases"], z["margins"], z["seconds"], z["done"]):
                if d: i = pos[int(f)]; P[i], M[i], T[i], done[i] = p, m, t, True
        save_store(out / f"{tag}_phases.npz", masks, P, M, T, done)
        print(f"合併 {len(shards)} 個分片 → {tag}_phases.npz，完成 {int(done.sum())}/{len(masks)}")
        return
    if a.shard:
        k, n = map(int, a.shard.split("/"))
        masks = masks[k::n]; tag = f"{tag}_shard{k}of{n}"
    P, M, T, done, wall, npz = run(masks, out, tag, a.workers, chunk)
    if not done.all():
        print("尚未算完"); return
    if a.masks:
        sample_report(masks, P, M, T, wall, a.workers, npz, src, out, tag)
    elif not a.shard:
        np.save(out / "coverage_margins.npy", M)
        write_coverage_json(out)


if __name__ == "__main__":
    main()
