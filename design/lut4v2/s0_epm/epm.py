r"""LUT4 v2 s0：E+／E− 二相位輸入與 OOK 的比較，以及不用參考光時能做的真值表。

用途：
  1. 7 個範例函數在 Model-7a（0.9 dB／MZI、雙差值＋AND）上，比較 OOK＋R＝3 與 E±＋R＝3、1、0 的最小裕量
     （synth4.synth_nb，60 個起點，種子 7）；再以輸入相對相位誤差 σ＝0.05、0.1 rad 各 400 次看 16 組全對的比例。
  2. 不用參考光（R＝0）時，16 列分成 8 組互補對（x 與 15−x），逐一合成「每組兩列輸出相同」的 254 張非常數真值表（24 個起點）。
編碼：OOK 位元 0／1 → 光場 0／1；E± 位元 0／1 → +1／−1；R 不調變，與位元 0 同相（+E）。
輸入：synth4.py。
輸出：out/epm.json。
執行：.\lab design\lut4v2\s0_epm\epm.py（LAB_WORKERS 個 worker，預設 4）
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4v2
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import synth4 as S                                                   # noqa: E402

STEP = "lut4v2/s0_epm"
CODE, ORDER, LOSS = "3142132", (1, 3, 2), 0.9
WORKERS = min(int(os.environ.get("LAB_WORKERS", 4)), 24)
FUNCS = {"AND2": 0x8888, "OR2": 0xEEEE, "XOR2": 0x6666, "NAND2": 0x7777, "AND4": 0x8000, "XOR4": 0x6996, "MUX": 0xCACA}
CASES = [("ook", 3.0), ("epm", 3.0), ("epm", 1.0), ("epm", 0.0)]
PAIRS = [(x, 15 - x) for x in range(8)]


def arch(enc, r):
    A = S.Arch.from_code(CODE, r_amp=r, loss_db=LOSS, order=ORDER)
    A.V[:, :4] = S.X4 if enc == "ook" else S.S4
    return A


def comp_sym(f):
    return all((f >> x & 1) == (f >> (15 - x) & 1) for x in range(16))


def phase_mc(A, f, ph, sig, n=400, seed=1):
    ins = np.array([f >> x & 1 for x in range(16)], bool)
    rng = np.random.default_rng(seed); V0 = A.V.copy(); ok = 0
    for _ in range(n):
        A.V = V0 * np.exp(1j * rng.normal(0, sig, 5))[None, :]
        ok += A.margins(ph[None], ins).min() > 0
    A.V = V0
    return ok / n


def ex_job(a):
    name, enc, r = a
    A = arch(enc, r)
    f = FUNCS[name]
    m, ph = S.synth_nb(f, A, 60, 7)
    d = dict(margin=round(float(m), 4))
    if m > 0:
        d.update(mc005=phase_mc(A, f, ph, 0.05), mc01=phase_mc(A, f, ph, 0.1))
    return name, f"{enc}_R{r:g}", d


def table_of(k):
    f = 0
    for i, (a, b) in enumerate(PAIRS):
        if k >> i & 1:
            f |= (1 << a) | (1 << b)
    return f


def nr_job(k):
    f = table_of(k)
    m, _ = S.synth_nb(f, arch("epm", 0.0), 24, k)
    return f, round(float(m), 4)


def main():
    t0 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        ex_res = list(ex.map(ex_job, [(n, e, r) for n in FUNCS for e, r in CASES]))
        nr = list(ex.map(nr_job, range(1, 255)))
    ex_out = {n: dict(hex=f"0x{f:04X}", comp_sym=comp_sym(f)) for n, f in FUNCS.items()}
    for n, k, d in ex_res:
        ex_out[n][k] = d
    ms = [m for _, m in nr]
    out = dict(encoding=dict(ook="位元 0／1 → 光場 0／1", epm="位元 0／1 → 光場 +1／−1", R="不調變，與位元 0 同相（+E）"),
               examples=ex_out,
               noref=dict(n=len(ms), ok=int(sum(m > 1e-3 for m in ms)), min=min(ms), argmin=f"0x{min(nr, key=lambda t: t[1])[0]:04X}",
                          median=float(np.median(ms)), xor4=dict(nr).get(0x6996)),
               time_s=round(time.time() - t0, 1))
    paths.OUT(STEP, "epm.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, r in ex_out.items():
        print(n, {k: v for k, v in r.items() if k.startswith(("ook", "epm"))})
    print("noref", out["noref"], out["time_s"])


if __name__ == "__main__":
    main()
