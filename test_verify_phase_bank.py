"""反向測試：故意放入有問題的相位資料，確認 verify_phase_bank.py 都能抓到。

需要的軟體：Python 3 與 numpy。
執行方式：python test_verify_phase_bank.py

程式會用真實的 E± 相位資料做出幾份壞資料，存在暫存資料夾，再交給驗證程式檢查。
真實資料應該通過，每一份壞資料都應該被抓到。
"""
import contextlib
import io
import sys
import tempfile
from pathlib import Path

import numpy as np

import verify_phase_bank as V

REAL = "design/lut4v2/s0_coverage/out/merged_phases.npz"


def bad_banks(masks, phases):
    one = int(np.where(masks == 0x6996)[0][0])
    swapped = phases.copy()
    swapped[[0, one]] = swapped[[one, 0]]
    repeated = masks.copy()
    repeated[1] = repeated[0]
    outside = masks.copy()
    outside[0] = V.N_TABLES
    with_nan = phases.copy()
    with_nan[0, 0] = np.nan
    return {
        "同一張真值表重複 65,536 次": (np.full(V.N_TABLES, masks[one]), np.tile(phases[one], (V.N_TABLES, 1))),
        "只有一張真值表": (masks[one:one + 1], phases[one:one + 1]),
        "只有前 1,000 張": (masks[:1000], phases[:1000]),
        "少一張真值表": (masks[:-1], phases[:-1]),
        "有一個編號重複": (repeated, phases),
        "有一個編號超出範圍": (outside, phases),
        "每張多兩個相位": (masks, np.hstack([phases, np.zeros((V.N_TABLES, 2))])),
        "每張少一個相位": (masks, phases[:, :-1]),
        "含有 NaN": (masks, with_nan),
        "編號是小數": (masks.astype(float), phases),
        "兩張表的相位互換": (masks, swapped),
    }


def verdict(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return V.check("測試", path, "EPM")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    bank = np.load(V.ROOT / REAL)
    masks, phases = bank["masks"], bank["phases"]
    ok = verdict(REAL)
    print(f"{'通過' if ok else '需要檢查'}　真實資料")
    caught = 0
    cases = bad_banks(masks, phases)
    with tempfile.TemporaryDirectory() as folder:
        for k, (name, (m, p)) in enumerate(cases.items()):
            path = Path(folder) / f"case{k}.npz"
            np.savez(path, masks=m, phases=p)
            hit = not verdict(path)
            caught += hit
            print(f"{'抓到' if hit else '需要檢查'}　{name}")
    print(f"結果：壞資料抓到 {caught}／{len(cases)}，真實資料{'通過' if ok else '需要檢查'}")
    sys.exit(0 if ok and caught == len(cases) else 1)


if __name__ == "__main__":
    main()
