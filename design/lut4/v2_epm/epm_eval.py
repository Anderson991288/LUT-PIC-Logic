"""LUT4v2：Model-7a 以 OOK（0/1）與 E+/E-（±1）輸入的小比較。只算 7 個範例函數。
情境：OOK R=3（原版）；E± R=3、1、0。每組 24 個起點合成，再以輸入相對相位誤差 σ＝0.05、0.1 rad 各 400 次檢查真值表全對比例。
執行：.\\lab design\\lut4\\v2_epm\\epm_eval.py（約 70 秒）→ out/epm.json"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4
import numpy as np
import synth4 as S

CODE, ORDER, LOSS = "3142132", (1, 3, 2), 0.9
FUNCS = {"AND2": 0x8888, "OR2": 0xEEEE, "XOR2": 0x6666, "NAND2": 0x7777, "AND4": 0x8000, "XOR4": 0x6996, "MUX": 0xCACA}
NST = 24


def arch(enc, r):
    A = S.Arch.from_code(CODE, r_amp=r, loss_db=LOSS, order=ORDER)
    if enc == "epm":
        A.V[:, :4] = 1 - 2 * S.X4          # 位元 0 → +E、1 → −E（與 ALU 課程相同）
    return A


def comp_sym(f):
    """f(x) == f(~x) 對 16 列都成立？"""
    return all((f >> x & 1) == (f >> (15 - x) & 1) for x in range(16))


def phase_mc(A, f, ph, sig, n=400, seed=1):
    ins = np.array([f >> x & 1 for x in range(16)], bool)
    rng = np.random.default_rng(seed); V0 = A.V.copy(); ok = 0
    for _ in range(n):
        A.V = V0 * np.exp(1j * rng.normal(0, sig, 5))[None, :]
        ok += A.margins(ph[None], ins).min() > 0
    A.V = V0
    return ok / n


def main():
    t0 = time.time()
    res = {}
    cases = [("ook", 3.0), ("epm", 3.0), ("epm", 1.0), ("epm", 0.0)]
    for name, f in FUNCS.items():
        row = {"comp_sym": comp_sym(f)}
        for enc, r in cases:
            A = arch(enc, r)
            m, ph = S.synth(f, A, nst=NST, seed=7)
            d = {"margin": round(m, 3)}
            if m > 0:
                d["phase_mc_0.05"] = phase_mc(A, f, ph, 0.05)
                d["phase_mc_0.1"] = phase_mc(A, f, ph, 0.1)
            row[f"{enc}_R{r:g}"] = d
        res[name] = row
        print(name, row, flush=True)
    res["time_s"] = round(time.time() - t0, 1)
    out = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "out" / "epm.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("time", res["time_s"])



if __name__ == "__main__":
    main()
