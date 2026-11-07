r"""LUT4v2：E± 輸入＋R=3、Model-7a 雙差值，抽樣檢查真值表是否都能實現（不跑全部 65536）。
樣本：隨機 2000 張＋OOK 全覆蓋時最差的 0x9667、XOR4 0x6996。stop=0.05 Pu 即停。
執行：.\lab design\lut4\v2_epm\sample_eval.py（6 個 worker）→ out/sample.json"""
import sys, json, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from epm_eval import arch  # noqa: E402
import synth4 as S  # noqa: E402


def job(f):
    m, _ = S.synth(f, arch("epm", 3.0), nst=24, seed=f, stop=0.05)
    return f, round(m, 4)


if __name__ == "__main__":
    t0 = time.time()
    fs = sorted(set(np.random.default_rng(2026).integers(1, 0xFFFF, 2000).tolist()) | {0x9667, 0x6996})
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(job, fs, chunksize=8))
    fail = [hex(f) for f, m in res if m <= 0]
    out = dict(n=len(res), ok=len(res) - len(fail), fail=fail, min_margin=min(m for _, m in res),
               w9667=dict(res)[0x9667], xor4=dict(res)[0x6996], time_s=round(time.time() - t0, 1))
    (Path(__file__).parent / "out" / "sample.json").write_text(json.dumps(dict(summary=out, all=res), indent=0), encoding="utf-8")
    print(out)
