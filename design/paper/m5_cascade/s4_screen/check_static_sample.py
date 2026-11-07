r"""論文 M5 s4 的重現抽查：靜態合成全量（平行度 2 約 135 分鐘）本次未重跑，screen.py 沿用參考快取 static.jsonl；
這裡以固定規則重算一部分，檢查快取能否由本工作區的程式重新產生。

抽樣規則（事先固定，不看結果）：classes() 的代表依遞增排序後取 reps[::STRIDE]，無損與 0.9 dB 兩種損耗，第一輪 STARTS 個隨機起點。
輸入：design/paper/m5_cascade/s4_screen/out/static.jsonl（參考快取）。
輸出：design/paper/m5_cascade/s4_screen/out/static_sample_check.json。
執行：.\lab design\paper\m5_cascade\s4_screen\check_static_sample.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import paths                                                         # noqa: E402
import screen as S                                                   # noqa: E402

STRIDE = 10


def main():
    t0 = time.time()
    out_dir = paths.OUT(S.STEP, "x").parent
    cache = {}
    for line in (out_dir / "static.jsonl").read_text(encoding="utf-8").splitlines():
        tt, loss, k, m, z = json.loads(line)
        cache[(tt, loss, k)] = (m, z)
    reps = S.classes()[0][::STRIDE]
    tasks = [(r, loss, list(range(S.STARTS))) for r in reps for loss in S.LOSSES]
    rows, worst_m, worst_z, exact = [], 0.0, 0.0, 0
    with ProcessPoolExecutor(S.WORKERS) as ex:
        for res in ex.map(S.soft_task, tasks, chunksize=1):
            for tt, loss, k, m, z in res:
                cm, cz = cache[(tt, loss, k)]
                dm = abs(m - cm)
                dz = max(abs(a - b) for a, b in zip(z, cz))
                worst_m, worst_z = max(worst_m, dm), max(worst_z, dz)
                exact += int(m == cm and z == cz)
                rows.append([tt, loss, k, m, cm, dm, dz])
    res = dict(stride=STRIDE, n_classes=len(reps), n_rows=len(rows), n_cache_rows=len(cache), n_exact=exact,
               max_abs_margin_diff=worst_m, max_abs_phase_diff=worst_z, rows=rows, workers=S.WORKERS, time_s=round(time.time() - t0, 1))
    (out_dir / "static_sample_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"抽查 {len(reps)} 類、{len(rows)}／{len(cache)} 筆：完全相同 {exact} 筆；margin 最大差 {worst_m:.3g}、相位最大差 {worst_z:.3g}｜{res['time_s']} s")


if __name__ == "__main__":
    main()
