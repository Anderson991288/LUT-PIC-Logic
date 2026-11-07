"""親手驗證：用矩陣重新計算全部 65,536 張真值表，確認每一列都判讀正確。

需要的軟體：Python 3 與 numpy。
執行方式：python verify_phase_bank.py

這支程式獨立運作，只讀 design/lut4*/s0_coverage/out/merged_phases.npz 這兩份相位資料，
再用光路的數學模型算出每組輸入的光功率，比較結果與目標真值表。
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RAILS = [2, 0, 3, 1, 0, 2, 1]               # 7 顆 MZI 依序接在哪兩條光路（上方光路的編號，由 0 起算）
LOSS = 10 ** (-0.9 / 20)                    # 每顆 MZI 損耗 0.9 dB，換算成光場的比例
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)   # 50:50 分光器
ROWS = np.arange(16)                        # 四個輸入的 16 種組合
BITS = np.stack([(ROWS >> j) & 1 for j in range(4)]).astype(float)
TOLERANCE = 1e-8


def input_fields(encoding):
    """五條光路的輸入：x1～x4 與參考光 R＝3。"""
    data = BITS if encoding == "OOK" else 1 - 2 * BITS      # OOK：0／1。E±：+1／−1
    return np.vstack([data, np.full(16, 3.0)]).astype(complex)


def output_power(phases, encoding):
    """phases 的欄序是 θ1、φ1、…、θ7、φ7。回傳五個輸出的光功率。"""
    n = len(phases)
    field = np.broadcast_to(input_fields(encoding), (n, 5, 16)).copy()
    for k, rail in enumerate(RAILS):
        theta = np.zeros((n, 2, 2), complex)
        theta[:, 0, 0] = np.exp(1j * phases[:, 2 * k])
        theta[:, 1, 1] = 1
        phi = np.zeros((n, 2, 2), complex)
        phi[:, 0, 0] = np.exp(1j * phases[:, 2 * k + 1])
        phi[:, 1, 1] = 1
        mzi = LOSS * (H @ theta @ H @ phi)
        field[:, rail:rail + 2] = np.einsum("bij,bjq->biq", mzi, field[:, rail:rail + 2])
    return np.abs(field) ** 2


def check(name, path, encoding):
    bank = np.load(ROOT / path)
    masks, phases = bank["masks"], bank["phases"]
    worst, wrong = np.inf, 0
    margins = np.empty(len(masks))
    for start in range(0, len(masks), 2048):
        part = slice(start, start + 2048)
        power = output_power(phases[part], encoding)
        d_a = power[:, 1] - power[:, 3]                     # 第一個比較器：o2 比 o4 亮為正
        d_b = power[:, 3] - power[:, 2]                     # 第二個比較器：o4 比 o3 亮為正
        target = ((masks[part, None] >> ROWS) & 1).astype(bool)
        answer = (d_a > 0) & (d_b > 0)                      # 兩個比較器接 AND
        wrong += int((answer != target).sum())
        margin = np.where(target, np.minimum(d_a, d_b), -np.minimum(d_a, d_b))
        margins[part] = margin.min(axis=1)
    worst = margins.min()
    passed = int(((margins > TOLERANCE)).sum())
    print(f"{name}：檢查 {len(masks):,} 張真值表、{16 * len(masks):,} 列")
    print(f"  判讀正確的真值表：{passed:,} 張")
    print(f"  判讀錯誤的列數：{wrong:,}")
    print(f"  最小 margin：{worst:.4f}（真值表 0x{int(masks[int(margins.argmin())]):04X}）")
    print(f"  margin 中位數：{float(np.median(margins)):.4f}")
    return wrong == 0 and passed == len(masks)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ok = check("LUT4 OOK", "design/lut4/s0_coverage/out/merged_phases.npz", "OOK")
    ok = check("LUT4 E±", "design/lut4v2/s0_coverage/out/merged_phases.npz", "EPM") and ok
    print("結果：全部通過" if ok else "結果：有項目需要檢查")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
