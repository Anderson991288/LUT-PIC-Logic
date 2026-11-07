r"""LUT4 s0：把逐張合成的 65,536 個裕量（cover4.py）依 PTF2／非 PTF2 分組，並依裕量分段計數。

PTF2：可寫成 sign(二次多項式) 的真值表（單一門檻能做到的那一類）。以 LP 判斷：
  特徵 1、xi、xixj（共 11 個），是否存在權重 w 使 y＝1 的輸入 w·f ≥ 1、y＝0 的輸入 w·f ≤ −1。
輸入：out/coverage_margins.npy。
輸出：out/coverage_split.json。
執行：.\lab design\lut4v2\s0_coverage\cover4_split.py
"""
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

OUT = Path(__file__).resolve().parent / "out"
X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)
F = np.column_stack([np.ones(16), X] + [X[:, i] * X[:, j] for i, j in itertools.combinations(range(4), 2)])


def is_ptf2(t):
    s = np.where([(t >> x) & 1 for x in range(16)], 1.0, -1.0)
    A = -(s[:, None] * F)
    r = linprog(np.zeros(F.shape[1]), A_ub=A, b_ub=-np.ones(16), bounds=[(None, None)] * F.shape[1], method="highs")
    return r.status == 0


def stats(m):
    return dict(n=int(m.size), realizable=int((m > 1e-3).sum()), ge_0p05=int((m >= 0.05).sum()), ge_0p1=int((m >= 0.1).sum()),
                ge_0p15=int((m >= 0.15).sum()), median=round(float(np.median(m)), 4), min=round(float(m.min()), 4))


def main():
    m = np.load(OUT / "coverage_margins.npy")
    ptf = np.array([is_ptf2(t) for t in range(65536)])
    bins = [0.0, 0.05, 0.1, 0.15]
    hist = {"不可實現": int((m <= 1e-3).sum()),
            "0～0.05": int(((m > 1e-3) & (m < 0.05)).sum()),
            "0.05～0.1": int(((m >= 0.05) & (m < 0.1)).sum()),
            "0.1～0.15": int(((m >= 0.1) & (m < 0.15)).sum()),
            "≥ 0.15": int((m >= 0.15).sum())}
    res = dict(all=stats(m), ptf2=stats(m[ptf]), non_ptf2=stats(m[~ptf]), hist=hist, bins=bins)
    (OUT / "coverage_split.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
