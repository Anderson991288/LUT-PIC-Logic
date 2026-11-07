r"""LUT4v2：逐張驗證中最差的真值表（0x96e9）不設停止門檻，以 400 個起點（16 個 worker 各 25 個）求較完整的裕量。
執行：.\lab design\lut4\v2_epm\worst_eval.py → 印出結果"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from epm_eval import arch  # noqa: E402
import synth4 as S  # noqa: E402

F = 0x96E9


def job(k):
    m, _ = S.synth(F, arch("epm", 3.0), nst=25, seed=500000 + k)
    return round(float(m), 4)


if __name__ == "__main__":
    with ProcessPoolExecutor(16) as ex:
        ms = list(ex.map(job, range(16)))
    print("各組最佳", sorted(ms), " 最佳", max(ms))
