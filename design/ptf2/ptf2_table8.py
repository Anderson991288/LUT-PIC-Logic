r"""PTF2 補充：report/PTF2.html 表 8「上限（Receiver 任意加權）」欄的獨立重算——兩個四階輸入＋R 的一次判讀涵蓋（NPN 類）。

做法（同頁面第 10 節的描述）：v＝(t(x₁,x₂), t(x₃,x₄), R)，R＝1；對 65,536 張真值表逐一以 LP 檢查是否存在 3×3 Hermitian 矩陣 M
      使 s(x)·v†Mv ≥ 1（9 個實數變數：3 個對角、3 組非對角的實部與虛部）。一個 NPN 類只要有任一成員可行即計入。
      六種四階編碼：振幅等間距 a/3；PAM4 √(a/3)（二進位、Gray 映射）；MZM sin(πa/6)；四階相位 e^{iπa/2}（二進位、Gray 映射）。
      二進位映射 a＝b₁＋2b₂；Gray 映射 00→0、10→1、11→2、01→3。
      頁面「固定 o2−o4」欄（非凸最佳化、25 個起點）本檔不重算，標為只核對既有證據。
輸入：無。輸出：out/ptf2_table8.json。
執行：.\lab design\ptf2\ptf2_table8.py　（約 10 分鐘）
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

OUT = Path(__file__).resolve().parent / "out"
XS = np.arange(16)
BITS = ((XS[:, None] >> np.arange(4)) & 1)
REF = {"amplitude a/3": 161, "PAM4 binary": 174, "PAM4 Gray": 116, "MZM sin(pi a/6)": 173, "phase binary": 195, "phase Gray": 89}
GRAY = {(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}


def level(b1, b2, gray):
    return GRAY[(b1, b2)] if gray else b1 + 2 * b2


ENC = {
    "amplitude a/3": (lambda a: a / 3, False),
    "PAM4 binary": (lambda a: np.sqrt(a / 3), False),
    "PAM4 Gray": (lambda a: np.sqrt(a / 3), True),
    "MZM sin(pi a/6)": (lambda a: np.sin(np.pi * a / 6), False),
    "phase binary": (lambda a: np.exp(1j * np.pi * a / 2), False),
    "phase Gray": (lambda a: np.exp(1j * np.pi * a / 2), True),
}


def features(enc):
    t, gray = ENC[enc]
    v = np.array([[t(level(int(b[0]), int(b[1]), gray)), t(level(int(b[2]), int(b[3]), gray)), 1.0] for b in BITS], complex)   # (16, 3)
    cols = [np.abs(v[:, i]) ** 2 for i in range(3)]
    for i, j in itertools.combinations(range(3), 2):
        w = np.conj(v[:, i]) * v[:, j]
        cols += [2 * w.real, -2 * w.imag]                              # v†Mv＝Σ M_ii|v_i|²＋Σ_{i<j} 2Re(M_ij v_i* v_j)
    return np.column_stack(cols)


def npn_rep():
    tts = np.arange(65536, dtype=np.int64); b = (tts[:, None] >> XS) & 1; best = tts.copy()
    for perm in itertools.permutations(range(4)):
        for neg in range(16):
            bb = BITS[:, list(perm)] ^ ((neg >> np.arange(4)) & 1)
            src = (bb << np.arange(4)).sum(1)
            v = (b[:, src] << XS).sum(1); best = np.minimum(best, np.minimum(v, 65535 ^ v))
    return best


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    rep = npn_rep(); reps = np.unique(rep)
    res = dict(method="LP upper bound: exists Hermitian 3x3 M with s(x)·v†Mv ≥ 1; class counted if any member feasible", R=1.0, rows={})
    for enc in ENC:
        t0 = time.perf_counter(); F = features(enc)
        ok = np.zeros(65536, bool)
        for tt in range(65536):
            s = np.where((tt >> XS) & 1, 1.0, -1.0)
            r = linprog(np.zeros(9), A_ub=-(s[:, None] * F), b_ub=-np.ones(16), bounds=[(None, None)] * 9, method="highs")
            ok[tt] = r.status == 0
        cls = int(len(np.unique(rep[ok])))
        res["rows"][enc] = dict(classes_upper_bound=cls, tables_feasible=int(ok.sum()), reference_upper_bound=REF[enc], match=cls == REF[enc],
                                elapsed_s=round(time.perf_counter() - t0, 1))
        print(enc, res["rows"][enc], flush=True)
    res["n_classes_total"] = int(len(reps))
    res["all_match"] = all(r["match"] for r in res["rows"].values())
    (OUT / "ptf2_table8.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("all_match", res["all_match"])
    sys.exit(0 if res["all_match"] else 1)


if __name__ == "__main__":
    main()
