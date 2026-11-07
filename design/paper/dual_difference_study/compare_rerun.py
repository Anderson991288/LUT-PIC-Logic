r"""比較雙差分研究的重跑結果與原有輸出，寫出 rerun_20261107/compare.json。

輸入：本資料夾的原有輸出、rerun_20261107/ 的重跑輸出。
輸出：rerun_20261107/compare.json。
執行：.\lab design\paper\dual_difference_study\compare_rerun.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NEW = HERE / "rerun_20261107"
SKIP = ("seconds", "elapsed", "time", "wall")


def flat(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{pre}/{k}")
    elif isinstance(o, list):
        yield f"{pre}#len", len(o)
        for i, v in enumerate(o):
            yield from flat(v, f"{pre}/{i}")
    else:
        yield pre, o


def json_cmp(name):
    a = dict(flat(json.loads((HERE / name).read_text(encoding="utf-8"))))
    b = dict(flat(json.loads((NEW / name).read_text(encoding="utf-8"))))
    num = worst = other = 0
    for k in a.keys() & b.keys():
        if any(s in k for s in SKIP):
            continue
        x, y = a[k], b[k]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            num += 1
            worst = max(worst, abs(x - y))
        elif x != y:
            other += 1
    return dict(numbers=num, max_abs_diff=worst, other_diff=other, keys_only_old=len(a.keys() - b.keys()), keys_only_new=len(b.keys() - a.keys()))


def npz_cmp(name):
    a, b = np.load(HERE / name), np.load(NEW / name)
    m0, m1 = a["margins"], b["margins"]
    return dict(tables=int(len(m1)), min_old=float(m0.min()), min_new=float(m1.min()), argmin_old=f"0x{int(m0.argmin()):04X}", argmin_new=f"0x{int(m1.argmin()):04X}",
                positive_new=int((m1 > 1e-8).sum()), max_abs_margin_diff=float(np.abs(m0 - m1).max()), n_diff_gt_1e6=int((np.abs(m0 - m1) > 1e-6).sum()),
                median_old=float(np.median(m0)), median_new=float(np.median(m1)))


res = {n: npz_cmp(n) for n in ("scan.npz", "verified_scan.npz")}
for n in ("pilot.json", "summary.json", "window_low_class.json", "port_screen.json", "port_screen_refined.json", "topology_screen.json", "topology_parity.json", "topology_refined.json"):
    res[n] = json_cmp(n) if (NEW / n).exists() else "沒有產生"
(NEW / "compare.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in res.items():
    print(k, v)
