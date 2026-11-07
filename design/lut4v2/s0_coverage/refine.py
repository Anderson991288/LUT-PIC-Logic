r"""LUT4 s0：對第一輪（cover4.py，24 個起點）裕量最差的真值表增加起點數重新合成相位，保存相位，看裕量能提高多少。

對象：第一輪結果最差的 N 張（完整模式預設 40、樣本模式預設 5；第一輪未找到解的排最前），加上 XOR4（0x6996）。
做法：同 cover4（synth4.synth_nb、E± 輸入、0.9 dB／MZI、R＝+3、雙差值＋AND），起點數 100 與 400（種子 1000＋f），
      取三者（24、100、400）的最大值；每一組的 14 個相位都保存，可重播。
輸入：out/coverage_phases.npz（完整；沒有時退回 out/coverage_margins.npy，此時第一輪沒有相位）或 out/sample_phases.npz（樣本）。
輸出：out/refine_phases.npz（f、starts、margin、phases、best_starts）、out/refine.json。
      樣本模式加 --reference-json reference/refine.json 時：refine.json 的頂層鍵（build_study 需要的 n、worst10、xor4、new_min、
      new_argmin、rescued、realizable_after、ge_0p1_after、rows…）由既有的全表證據填入並標 source＝reference evidence，
      本輪樣本的結果放在 sample 子鍵，既有證據放在 reference 子鍵。
執行：.\lab design\lut4v2\s0_coverage\refine.py --source sample --n 5 --workers 4 --reference-json design\lut4v2\s0_coverage\reference\refine.json
      .\lab design\lut4v2\s0_coverage\refine.py --source full --n 40 --workers 16
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
CODE, LOSS = "3142132", 0.9
REAL = 1e-3
NPH = 14


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
    t0 = time.perf_counter()
    m, p = S.synth_nb(f, arch, ns, 1000 + f)
    p = np.zeros(NPH) if p is None else np.asarray(p, float) % (2 * np.pi)
    return f, ns, float(m), p, time.perf_counter() - t0


def load_round1(out, source):
    """回傳 (masks, margins, phases 或 None)。"""
    if source == "sample":
        z = np.load(out / "sample_phases.npz")
        return z["masks"].astype(int), z["margins"].astype(float), z["phases"].astype(float)
    npz = out / "coverage_phases.npz"
    if npz.exists():
        z = np.load(npz)
        return z["masks"].astype(int), z["margins"].astype(float), z["phases"].astype(float)
    m = np.load(out / "coverage_margins.npy")
    return np.arange(65536), m.astype(float), None


def stats_after(masks, m2, rows, N):
    worst = rows[:N]
    return dict(new_min=round(float(m2.min()), 4), new_argmin=f"0x{int(masks[int(np.argmin(m2))]):04X}",
                min_best_of_refined=round(min(r["best"] for r in worst), 4),
                mean_gain_pct=round(float(np.mean([r["gain_pct"] for r in worst if r["gain_pct"] is not None])), 1)
                if any(r["gain_pct"] is not None for r in worst) else None,
                rescued=[r["f"] for r in rows if r["m24"] <= REAL < r["best"]],
                realizable_after=int((m2 > REAL).sum()), ge_0p1_after=int((m2 >= 0.1).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["full", "sample"], default="full")
    ap.add_argument("--n", type=int, default=None, help="重求的張數（完整預設 40、樣本預設 5）")
    ap.add_argument("--starts", type=int, nargs="+", default=[100, 400])
    ap.add_argument("--workers", type=int, default=min(int(os.environ.get("LAB_WORKERS", 4)), 24))
    ap.add_argument("--reference-json", help="既有全表的 refine.json（樣本模式時填頂層鍵、放 reference 子鍵）")
    a = ap.parse_args()
    N = a.n if a.n is not None else (40 if a.source == "full" else 5)
    out = paths.OUT(STEP)
    t_all = time.perf_counter()
    masks, m, ph1 = load_round1(out, a.source)
    order = np.argsort(m)                                             # 未找到解（≈0 或負）排最前
    fs = [int(masks[i]) for i in order[:N]]
    if 0x6996 in masks and 0x6996 not in fs:
        fs.append(0x6996)
    pos = {int(f): i for i, f in enumerate(masks)}
    res = {f: {"24": float(m[pos[f]])} for f in fs}
    phases = {f: {"24": (ph1[pos[f]] if ph1 is not None else np.full(NPH, np.nan))} for f in fs}
    secs = {}
    import synth4 as S
    S.synth_nb(0x6996, S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2)), 1, 0)       # 先編譯（numba cache）
    t0 = time.perf_counter()
    jobs = [(f, ns) for ns in a.starts for f in fs]
    with Pool(min(a.workers, len(jobs)), initializer=init) as P:
        for f, ns, v, p, sec in P.imap_unordered(job, jobs):
            res[f][str(ns)] = v; phases[f][str(ns)] = p; secs[(f, ns)] = sec
            print(f"0x{f:04X} {ns} 起點 → {v:.4f}（{sec:.1f} s）", flush=True)
    calc_s = time.perf_counter() - t0
    rows = []
    for f in fs:
        r = res[f]
        best_key = max(r, key=lambda k: r[k])
        rows.append(dict(f=f"0x{f:04X}", m24=round(r["24"], 4), **{f"m{ns}": round(r[str(ns)], 4) for ns in a.starts},
                         best=round(r[best_key], 4), best_starts=int(best_key),
                         gain_pct=round((r[best_key] / r["24"] - 1) * 100, 1) if r["24"] > REAL else None))   # 24 個起點未實現者不算百分比
    rows.sort(key=lambda x: x["m24"])
    m2 = m.copy()
    for r in rows:
        m2[pos[int(r["f"], 16)]] = r["best"]
    this = dict(n=N, starts=list(a.starts), worst10=rows[:10], xor4=next((r for r in rows if r["f"] == "0x6996"), None),
                **stats_after(masks, m2, rows, N), rows=rows,
                n_round1=int(masks.size), seconds_per_job={f"0x{f:04X}_{ns}": round(s, 2) for (f, ns), s in secs.items()},
                calc_s=round(calc_s, 1), workers=a.workers, phases_file="refine_phases.npz")
    # 保存相位
    F, NSs, MG, PH, BEST = [], [], [], [], []
    for f in fs:
        bk = max(res[f], key=lambda k: res[f][k])
        for k, v in res[f].items():
            F.append(f); NSs.append(int(k)); MG.append(v); PH.append(phases[f][k]); BEST.append(int(bk))
    np.savez(out / "refine_phases.npz", masks=np.array(F, np.int32), starts=np.array(NSs, np.int32), margins=np.array(MG, float),
             phases=np.array(PH, float), best_starts=np.array(BEST, np.int32), code=CODE, loss_db=LOSS, seed_rule="1000+f")
    # 核對：保存的相位重算裕量
    arch = S.Arch.from_code(CODE, loss_db=LOSS, order=(1, 3, 2))
    dmax = 0.0
    for f, ns, mg, p in zip(F, NSs, MG, PH):
        if np.isnan(p).any():
            continue
        ins = np.array([f >> x & 1 for x in range(16)], bool)
        dmax = max(dmax, abs(float(arch.margins(p[None], ins).min()) - mg))
    this["phase_margin_recheck_max_diff"] = dmax
    this["wall_s"] = round(time.perf_counter() - t_all, 1)

    if a.source == "sample":
        if a.reference_json:
            ref = json.loads(Path(a.reference_json).read_text(encoding="utf-8"))
            summ = dict(ref)
            summ["source"] = "reference evidence (not rerun this round)"
            summ["note"] = ("頂層鍵（n、worst10、xor4、new_min、new_argmin、rescued、realizable_after、ge_0p1_after、rows…）來自既有的全表補強證據"
                            "（reference 子鍵）；本輪只對樣本第一輪最差的幾張重求，結果在 sample 子鍵。")
            summ["reference"] = ref
            summ["sample"] = this
        else:
            summ = dict(this, source="this round (sample only; no full-table evidence attached)")
    else:
        summ = dict(this, source="this round (full table)")
    (out / "refine.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows[:12]:
        print(r)
    print("XOR4", this["xor4"], "新最差（本次範圍）", this["new_min"], this["new_argmin"], "平均提高 %", this["mean_gain_pct"],
          "救回", this["rescued"], "可實現", this["realizable_after"], "/", this["n_round1"], "≥0.1", this["ge_0p1_after"],
          "相位核對最大差", dmax, "計算", this["calc_s"], "s")


if __name__ == "__main__":
    main()
