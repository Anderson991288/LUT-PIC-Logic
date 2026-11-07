r"""學員練習：選一張真值表，求 14 個相位，逐列驗收，再故意用錯輸入編碼看會發生什麼。

用途（附錄 A「學員最小實作路徑」的第 3、4 步；不需要佈局或 EDA 工具）：
  1. 以 Model-7a（拓樸 3142132、每顆 MZI 0.9 dB、R＝+3、判讀 y＝[P(o2)＞P(o4)] AND [P(o4)＞P(o3)]）
     對指定的真值表求 14 個相位（synth4.synth_nb，多起點）。
  2. 列出 16 列的輸入、目標、P(o2)、P(o4)、P(o3)、Da、Db、y，標出是否正確，並印出最小裕量。
  3. 用同一組相位，但把資料輸入改成強度編碼（位元 0／1 → 光場 0／1），重算一次，看錯幾列：
     相位是對 E± 求的，輸入編碼一錯，整張表就不可靠。
輸入：真值表（十六進位，第 x 位元＝輸入 x＝x1＋2x2＋4x3＋8x4 的輸出），預設 0x8888（AND2）；--starts 起點數（預設 24）。
輸出：只印在畫面上，不寫檔。
執行：.\lab design\lut4v2\s0_student\try_one.py 0x6996 --starts 60
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4v2
import numpy as np                                                   # noqa: E402

import synth4 as S                                                   # noqa: E402

CODE, LOSS, R_AMP = "3142132", 0.9, 3.0


def table(A, ph, f, title):
    W = A.powers(ph[None])[0]                                         # (16, 5)：各輸入列、各輸出埠的功率
    a, b, c = A.order                                                 # o2、o4、o3 的索引
    Da, Db = W[:, a] - W[:, b], W[:, b] - W[:, c]
    y = (Da > 0) & (Db > 0)
    tgt = np.array([f >> x & 1 for x in range(16)], bool)
    print(f"\n{title}")
    print(" x1x2x3x4 目標  P(o2)   P(o4)   P(o3)     Da      Db    y  正確")
    for x in range(16):
        bits = "".join(str(x >> k & 1) for k in range(4))
        print(f"   {bits}     {int(tgt[x])}  {W[x, a]:6.3f}  {W[x, b]:6.3f}  {W[x, c]:6.3f}  {Da[x]:+6.3f}  {Db[x]:+6.3f}  {int(y[x])}   {'✓' if y[x] == tgt[x] else '✗'}")
    ok = int((y == tgt).sum())
    m = np.where(tgt, np.minimum(Da, Db), np.maximum(-Da, -Db)).min()
    print(f"→ {ok}/16 列正確；最小裕量 {m:+.3f} Pᵤ（正值才表示每一列都判對）")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table", nargs="?", default="0x8888")
    ap.add_argument("--starts", type=int, default=24)
    arg = ap.parse_args()
    f = int(arg.table, 16)
    A = S.Arch.from_code(CODE, r_amp=R_AMP, loss_db=LOSS)            # 預設 E± 輸入：位元 0＝+1、1＝−1，R＝+3
    m, ph = S.synth_nb(f, A, arg.starts, 7)
    print(f"真值表 0x{f:04X}：{arg.starts} 個起點，求得最小裕量 {m:.3f} Pᵤ")
    print("14 個相位（rad，依 MZI-1…7 的 θ、φ）：" + "、".join(f"{v % (2 * np.pi):.3f}" for v in ph))
    table(A, ph, f, "① 正確的輸入編碼（E±：位元 0＝+E、1＝−E）")
    A.V[:, :4] = S.X4                                                 # 故意改成強度編碼：位元 0／1 → 光場 0／1
    table(A, ph, f, "② 同一組相位，但輸入誤用強度編碼（0／1）")


if __name__ == "__main__":
    main()
