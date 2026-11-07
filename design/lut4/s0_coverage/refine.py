r"""LUT4 s0：對涵蓋掃描中裕量最差的函數，增加起點數重新合成相位，看裕量能提高多少；相位一併保存。

原版：對全量掃描（coverage_margins.npy）最差 40 張＋XOR4，以 100、400 個起點重算（種子 1000＋f），取最大值。
本版：預設讀本輪樣本 out/sample_phases.npz，取其中最差 --n 張（預設 5）＋XOR4（0x6996），以 --starts（預設 100）個起點重算，
      種子 1000＋f（與原版一致），保存相位到 out/refine_phases.npz；全量結果存在時（coverage_phases.npz 全部完成）可用
      --full 回到原版的 40 張＋100／400 起點。
輸入：out/sample_phases.npz（或 out/coverage_phases.npz）、reference/refine.json（參考數字，放在 reference 子鍵）。
輸出：out/refine.json、out/refine_phases.npz。
執行：.\lab design\lut4\s0_coverage\refine.py --n 5 --starts 100 --workers 2
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "lut4/s0_coverage"
CODE, LOSS = "3142132", 0.9
HERE = Path(__file__).resolve().parent
XOR4 = 0x6996


def init():
    try:
        import psutil
        psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def job(a):
    f, ns = a
    import synth4 as S
    arch = S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2))
    m, p = S.synth_nb(f, arch, ns, 1000 + f)
    return f, ns, float(m), np.asarray(p, float)


def hx(f):
    return f"0x{int(f):04X}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5); ap.add_argument("--starts", type=int, nargs="+", default=[100])
    ap.add_argument("--workers", type=int, default=2); ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    out = paths.OUT(STEP)
    if a.full:
        z = np.load(out / "coverage_phases.npz"); assert z["done"].all(), "全量尚未算完"
        order = np.argsort(z["masks"]); base_masks, base_m, base_p = z["masks"][order], z["margins"][order], z["phases"][order]
        scope = "full 65,536 (this round)"; a.n = a.n if a.n != 5 else 40; a.starts = a.starts if a.starts != [100] else [100, 400]
    else:
        z = np.load(out / "sample_phases.npz"); assert z["done"].all(), "樣本尚未算完"
        base_masks, base_m, base_p = z["masks"], z["margins"], z["phases"]
        scope = f"sample of {len(base_masks)} masks (this round)"
    pos = {int(f): i for i, f in enumerate(base_masks)}
    fs = [int(base_masks[i]) for i in np.argsort(base_m)[:a.n]]
    if XOR4 in pos and XOR4 not in fs:
        fs.append(XOR4)
    res = {f: {"24": float(base_m[pos[f]])} for f in fs}
    best_p = {f: base_p[pos[f]].copy() for f in fs}
    with Pool(a.workers, initializer=init) as P:
        for f, ns, v, p in P.imap_unordered(job, [(f, ns) for ns in a.starts for f in fs]):
            res[f][str(ns)] = v
            if v > max(res[f][k] for k in res[f] if k != str(ns)):
                best_p[f] = p
    rows = []
    for f in fs:
        r = res[f]; best = max(r.values())
        row = dict(f=hx(f), m24=round(r["24"], 4), **{f"m{ns}": round(r[str(ns)], 4) for ns in a.starts}, best=round(best, 4),
                   gain_pct=round((best / r["24"] - 1) * 100, 1))
        if "m400" not in row: row["m400"] = None                     # build_study 的表格欄位
        rows.append(row)
    rows.sort(key=lambda x: x["m24"])
    worst = [r for r in rows if r["f"] != hx(XOR4)][:a.n]
    m2 = base_m.copy()
    for r in rows:
        m2[pos[int(r["f"], 16)]] = r["best"]
    ref = HERE / "reference" / "refine.json"
    summ = dict(source="this round (sample refine)" if not a.full else "this round (full refine)", scope=scope,
                n=len(worst), starts=a.starts, seed_rule="seed = 1000 + mask", worst10=rows[:10],
                xor4=next((r for r in rows if r["f"] == hx(XOR4)), None),
                new_min=round(float(m2.min()), 4), new_argmin=hx(base_masks[int(np.argmin(m2))]),
                new_min_scope="樣本內最差（非全量）" if not a.full else "全量最差",
                min_best_of_refined=round(min(r["best"] for r in worst), 4),
                mean_gain_pct=round(float(np.mean([r["gain_pct"] for r in worst])), 1), rows=rows,
                phases_file="refine_phases.npz")
    if ref.exists():
        summ["reference"] = dict(file="reference/refine.json", source="reference evidence (not rerun this round)",
                                 **json.loads(ref.read_text(encoding="utf-8")))
        rref = {r["f"]: r for r in summ["reference"]["rows"]}
        summ["compare_reference"] = [dict(f=r["f"], ours_m100=r.get("m100"), ref_m100=rref[r["f"]].get("m100"),
                                          diff=None if r.get("m100") is None or r["f"] not in rref else round(r["m100"] - rref[r["f"]]["m100"], 4))
                                     for r in rows if r["f"] in rref]
    np.savez(out / "refine_phases.npz", masks=np.array(fs, np.int64), phases=np.array([best_p[f] for f in fs]),
             margins=np.array([max(res[f].values()) for f in fs]), phase_order=np.array("theta1,phi1,...,theta7,phi7"))
    (out / "refine.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(r)
    print("XOR4", summ["xor4"], "樣本新最差", summ["new_min"], summ["new_argmin"], "平均提高 %", summ["mean_gain_pct"])
    if "compare_reference" in summ:
        print("與參考 m100 比較", summ["compare_reference"])


if __name__ == "__main__":
    main()
