r"""LUT4 s0：產生本輪全覆蓋抽樣的真值表清單 sample_masks.json（給 cover4.py --masks 用）。

內容：七個範例函數、既有全表第一輪裕量最低的 10 張（既有證據的 worst10）與 0x9F69（第一輪未找到解）、
     既有補強後全表最差的 0x967A，再以種子 20261107 由 65,536 張中不放回隨機抽 200 張；去重後依固定清單在前、隨機在後排列。
輸入：無（清單寫在程式裡，來源見 reference/coverage.json、reference/refine.json）。
輸出：sample_masks.json（與本程式同資料夾）。
執行：.\lab design\lut4v2\s0_coverage\sample_masks.py
"""
import json
from pathlib import Path

import numpy as np

SEED, N_RANDOM = 20261107, 200
EXAMPLES = {"AND2": 0x8888, "OR2": 0xEEEE, "XOR2": 0x6666, "NAND2": 0x7777, "AND4": 0x8000, "XOR4": 0x6996, "MUX": 0xCACA}
REF_WORST = [0x9F69, 0x96E9, 0xB46B, 0x7B96, 0x966B, 0x6997, 0x69D6, 0x698F, 0xD67D, 0xD6E1]   # 既有第一輪：未找到解 ＋ worst10（0x6996 已在範例）
REF_AFTER_WORST = [0x967A]                                                                   # 既有補強後全表最差


def main():
    fixed = list(EXAMPLES.values()) + REF_WORST + REF_AFTER_WORST
    rng = np.random.default_rng(SEED)
    rand = [int(v) for v in rng.choice(65536, N_RANDOM, replace=False)]
    seen, masks = set(), []
    for f in fixed + rand:
        if f not in seen:
            seen.add(f); masks.append(f)
    out = dict(seed=SEED, n_random=N_RANDOM, n_fixed=len(fixed), n=len(masks), overlap_random_fixed=len(fixed) + N_RANDOM - len(masks),
               groups=dict(examples={k: f"0x{v:04X}" for k, v in EXAMPLES.items()}, reference_round1_worst=[f"0x{v:04X}" for v in REF_WORST],
                           reference_after_refine_worst=[f"0x{v:04X}" for v in REF_AFTER_WORST], random=[f"0x{v:04X}" for v in rand]),
               masks=[f"0x{v:04X}" for v in masks])
    p = Path(__file__).resolve().parent / "sample_masks.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"寫出 {p.name}：固定 {len(fixed)} ＋ 隨機 {N_RANDOM} → 去重後 {len(masks)} 張（重疊 {out['overlap_random_fixed']}）")


if __name__ == "__main__":
    main()
