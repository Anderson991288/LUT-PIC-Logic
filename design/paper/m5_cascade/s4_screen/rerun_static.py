r"""論文 M5 s4 的靜態合成全量重跑：不動 screen.py 使用的 static.jsonl（參考快取），另寫 static_rerun.jsonl，逐筆比對兩者。

用途：平行上限放寬後補跑全量，把靜態層由「沿用參考快取＋抽查」升級為本次重算。目標、成員抽樣、起點與暖啟動都由 screen.py 的同一段邏輯產生。
輸入：design/paper/m5_cascade/s4_screen/out/static.jsonl。
輸出：design/paper/m5_cascade/s4_screen/out/static_rerun.jsonl（可續跑）、static_rerun_check.json。
執行：.\lab design\paper\m5_cascade\s4_screen\rerun_static.py（6 個 worker 約 45 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import time                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import screen as S                                                   # noqa: E402


def rows(path):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        tt, loss, k, m, z = json.loads(line)
        out[(tt, loss, k)] = (m, z)
    return out


def main():
    t0 = time.time()
    out_dir = paths.OUT(S.STEP, "x").parent
    reps, canon, size = S.classes()
    rng = np.random.default_rng(S.MEMBER_SEED)                       # 與 screen.main() 相同的成員抽樣
    members = {}
    for r in reps:
        pool = np.flatnonzero(canon == r)
        pool = pool[pool != r]
        members[r] = sorted(int(x) for x in rng.choice(pool, min(S.MEMBERS, len(pool)), replace=False)) if len(pool) else []
    targets = [(r, loss) for r in reps for loss in S.LOSSES] + [(m, S.LOSSES[1]) for r in reps for m in members[r]]
    S.synthesize(targets, out_dir / "static_rerun.jsonl", warm=[(r, S.LOSSES[0], S.LOSSES[1]) for r in reps])
    a, b = rows(out_dir / "static_rerun.jsonl"), rows(out_dir / "static.jsonl")
    common = set(a) & set(b)
    exact = sum(a[k] == b[k] for k in common)
    dm = max((abs(a[k][0] - b[k][0]) for k in common), default=None)
    dz = max((max(abs(x - y) for x, y in zip(a[k][1], b[k][1])) for k in common), default=None)
    res = dict(n_rerun=len(a), n_cache=len(b), n_common=len(common), n_only_rerun=len(set(a) - set(b)), n_only_cache=len(set(b) - set(a)),
               n_exact=exact, max_abs_margin_diff=dm, max_abs_phase_diff=dz, workers=S.WORKERS, time_s=round(time.time() - t0, 1))
    (out_dir / "static_rerun_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(res)


if __name__ == "__main__":
    main()
