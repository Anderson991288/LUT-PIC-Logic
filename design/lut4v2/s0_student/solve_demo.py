r"""學員示範：相位怎麼求——從一張真值表反推 Model-7a 的 14 個相位（教學版，與 synth4.py 的正式求解同一個模型）。

用途：把求解流程寫成最少的程式，方便對照 M1 s2 ⑤ 的說明：
  1. 目標：16 組輸入應輸出 0 或 1（真值表）。
  2. 未知數：7 顆 MZI 的 θ、φ，共 14 個相位。
  3. 評分：一組相位 → 16 組輸入的 Da、Db → 每列離判讀邊界的距離 → 取最小值＝裕量。
  4. 求解：裕量含 min，梯度法不好走，改用平滑版（soft-min）當目標，以 BFGS 從起點往上爬。
  5. 多起點：從多組隨機相位各爬一次，取真實裕量最大的一組。
光路與功率由 synth4.Arch 計算（拓樸 3142132、每顆 MZI 0.9 dB、R＝+3、E± 輸入）。
輸入：真值表（十六進位，預設 0x8888＝AND2）；--starts 起點數（預設 24）。
輸出：只印在畫面上；加 --record 時改跑 AND2（24 個起點）、XOR4（24、60 個起點）並寫 out/solve_demo.json（供報告引用）。
執行：.\lab design\lut4v2\s0_student\solve_demo.py 0x6996 --starts 24
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4v2
import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import synth4 as S                                                   # noqa: E402

A = S.Arch.from_code("3142132", r_amp=3.0, loss_db=0.9)               # Model-7a：14 個相位 → 16 組輸入的 P(o1)…P(o5)


def row_margins(p, target):
    """一組相位 p（14 個）→ 16 列各自離判讀邊界的距離（正＝判對）。"""
    W = A.powers(p[None])[0]                                          # (16, 5)：各輸入列、各輸出埠的功率
    Da, Db = W[:, 1] - W[:, 3], W[:, 3] - W[:, 2]                      # P(o2)−P(o4)、P(o4)−P(o3)
    return np.where(target, np.minimum(Da, Db), np.maximum(-Da, -Db))  # 應判 1：兩個都要 ＞0；應判 0：其中一個 ＜0 即可


def margin(p, target):
    return row_margins(p, target).min()                               # 裕量＝16 列中最小的距離


def soft_margin(p, target, s=40.0):
    """平滑版裕量：每列的 min／max 與 16 列取最小，都改用 soft-min（log-sum-exp），讓目標對相位可微，梯度法才走得動。"""
    W = A.powers(p[None])[0]
    Da, Db = W[:, 1] - W[:, 3], W[:, 3] - W[:, 2]
    soft = np.logaddexp(-s * Da, -s * Db) / s                         # ≈ −min(Da, Db)
    m = np.where(target, -soft, soft)                                 # 應判 1 ≈ min(Da, Db)；應判 0 ≈ max(−Da, −Db)
    return -np.logaddexp.reduce(-s * m) / s                           # ≈ min（16 列）


def solve(f, starts=24, seed=7):
    target = np.array([f >> x & 1 for x in range(16)], bool)         # 第 x 列：輸入 x＝x1＋2x2＋4x3＋8x4 的目標輸出
    rng = np.random.default_rng(seed)
    best_m, best_p = -np.inf, None
    for _ in range(starts):
        p0 = rng.uniform(0, 2 * np.pi, 14)                            # 起點：一組隨機相位
        r = minimize(lambda p: -soft_margin(p, target), p0, method="BFGS")   # 往裕量變大的方向一步步調整
        m = margin(r.x, target)
        if m > best_m:                                                # 多起點：留下真實裕量最大的一組
            best_m, best_p = m, r.x % (2 * np.pi)
    return best_m, best_p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table", nargs="?", default="0x8888")
    ap.add_argument("--starts", type=int, default=24)
    ap.add_argument("--record", action="store_true")
    arg = ap.parse_args()
    if arg.record:
        import json
        rec = {f"{name}_{n}": round(float(solve(f, n)[0]), 4) for name, f, n in (("AND2", 0x8888, 24), ("XOR4", 0x6996, 24), ("XOR4", 0x6996, 60))}
        out = Path(__file__).resolve().parent / "out"; out.mkdir(exist_ok=True)
        (out / "solve_demo.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(rec)
        return
    f = int(arg.table, 16)
    m, p = solve(f, arg.starts)
    print(f"真值表 0x{f:04X}：{arg.starts} 個起點，最大裕量 {m:.3f} Pᵤ（{'16 列全對' if m > 0 else '找不到全對的相位'}）")
    print("14 個相位（rad，依 MZI-1…7 的 θ、φ）：" + "、".join(f"{v:.3f}" for v in p))


if __name__ == "__main__":
    main()
