r"""LUT4 s0：把 65,536 張真值表依 PTF2／非 PTF2 分組，並對兩組裕量資料分欄統計。

PTF2：可寫成 sign(二次多項式) 的真值表（單一門檻能做到的那一類）。以 LP 判斷：
  特徵 1、xi、xixj（共 11 個），是否存在權重 w 使 y＝1 的輸入 w·f ≥ 1、y＝0 的輸入 w·f ≤ −1。
  本輪對全部 65,536 張重算（參考：57,574 PTF2、7,962 非 PTF2），旗標存 out/ptf2_flags.npy。
裕量欄（兩欄各算一次，分開標示）：
  reference_scan24：reference/coverage_margins.npy——本專案原本 24 起點全量掃描的既有證據（本輪未重跑）。
  codex_bank_replay：out/bank_replay_margins.npy——Codex 相位庫以 replay_bank.py 重播的裕量（本輪重播）。
輸入：reference/coverage_margins.npy、out/bank_replay_margins.npy。
輸出：out/coverage_split.json、out/ptf2_flags.npy。
執行：.\lab design\lut4\s0_coverage\cover4_split.py
"""
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)
F = np.column_stack([np.ones(16), X] + [X[:, i] * X[:, j] for i, j in itertools.combinations(range(4), 2)])
COLUMNS = {
    "reference_scan24": dict(file=HERE / "reference" / "coverage_margins.npy", source="reference evidence (24-start scan, not rerun this round)"),
    "codex_bank_replay": dict(file=OUT / "bank_replay_margins.npy", source="this round: replay of the Codex phase bank (replay_bank.py)"),
    "this_round_scan24": dict(file=OUT / "coverage_margins.npy", source="this round: full 24-start scan (cover4.py, only present after the full rerun)"),
}


def is_ptf2(t):
    s = np.where([(t >> x) & 1 for x in range(16)], 1.0, -1.0)
    A = -(s[:, None] * F)
    r = linprog(np.zeros(F.shape[1]), A_ub=A, b_ub=-np.ones(16), bounds=[(None, None)] * F.shape[1], method="highs")
    return r.status == 0


def stats(m):
    return dict(n=int(m.size), realizable=int((m > 1e-3).sum()), ge_0p05=int((m >= 0.05).sum()), ge_0p1=int((m >= 0.1).sum()),
                ge_0p15=int((m >= 0.15).sum()), median=round(float(np.median(m)), 4), min=round(float(m.min()), 4),
                argmin=f"0x{int(np.argmin(m)):04X}")


def hist(m):
    return {"不可實現": int((m <= 1e-3).sum()), "0～0.05": int(((m > 1e-3) & (m < 0.05)).sum()),
            "0.05～0.1": int(((m >= 0.05) & (m < 0.1)).sum()), "0.1～0.15": int(((m >= 0.1) & (m < 0.15)).sum()),
            "≥ 0.15": int((m >= 0.15).sum())}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    ptf = np.array([is_ptf2(t) for t in range(65536)])
    el = time.perf_counter() - t0
    np.save(OUT / "ptf2_flags.npy", ptf)
    res = dict(ptf2=dict(method="LP（highs）：11 個特徵的二次門檻可分性，65,536 張逐張判定（本輪重算）", elapsed_s=round(el, 1),
                         n_ptf2=int(ptf.sum()), n_non_ptf2=int((~ptf).sum()), reference=dict(n_ptf2=57574, n_non_ptf2=7962),
                         match_reference=bool(ptf.sum() == 57574), flags_file="ptf2_flags.npy",
                         xor4_is_ptf2=bool(ptf[0x6996]), xor3_0x0069_is_ptf2=bool(ptf[0x0069]), mux_0xCACA_is_ptf2=bool(ptf[0xCACA])),
               bins=[0.0, 0.05, 0.1, 0.15], columns={})
    for name, c in COLUMNS.items():
        if not c["file"].exists():
            res["columns"][name] = dict(source=c["source"], available=False); continue
        m = np.load(c["file"])
        res["columns"][name] = dict(source=c["source"], file=c["file"].name, sha256=hashlib.sha256(c["file"].read_bytes()).hexdigest(),
                                    all=stats(m), ptf2=stats(m[ptf]), non_ptf2=stats(m[~ptf]), hist=hist(m))
    (OUT / "coverage_split.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["ptf2"], ensure_ascii=False))
    for name, c in res["columns"].items():
        print(name, json.dumps({k: c.get(k) for k in ("all", "ptf2", "non_ptf2", "hist")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
