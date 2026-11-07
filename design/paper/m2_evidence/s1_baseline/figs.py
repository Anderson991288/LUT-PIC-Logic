r"""論文 M2 s1：圖——固定加總模型與時域流程的三項對照（skew 容許、功率需求的排序、相位與殘留光的影響）。

用途：數字讀 out/baseline.json。
輸入：out/baseline.json。
輸出：figures/paper/m2/s1_baseline.png（圖 M2-1）。
執行：.\lab design\paper\m2_evidence\s1_baseline\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREY                                   # noqa: E402

STEP = "paper/m2_evidence/s1_baseline"
B = json.loads(paths.OUT(STEP, "baseline.json").read_text(encoding="utf-8"))
FN = list(B["functions"])
F = B["functions"]


def main():
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.4))
    x = np.arange(len(FN))
    w = 0.38
    # (a) skew 容許
    ax = axs[0]
    fx = [F[f]["fixed"]["skew_allow_ps"] for f in FN]
    fl = [F[f]["flow"]["skew_allow_1db_ps"] for f in FN]
    ax.bar(x - w / 2, fx, w, color=GREY, label="固定加總（UI − 邊緣 − 取樣；本研究補的假設）")
    ax.bar(x + w / 2, fl, w, color=BLUE, label="時域流程（額外代價 1 dB）")
    for i, f in enumerate(FN):
        ax.text(x[i] + w / 2, fl[i] + 0.4, f"{fl[i]:g}", ha="center", fontsize=8.5, color=BLUE)
        ax.text(x[i], -3.8, f"skew 0 已有\n{F[f]['flow']['skew_penalty_db']['0']:.1f} dB", ha="center", fontsize=8, color=BLUE)
    ax.set_xticks(x, FN)
    ax.set_ylim(-5, 40)                                               # 上方留給圖例，不蓋住長條的數字
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("可容許的 skew（ps）")
    ax.set_title("(a) skew 容許：固定模型各函數相同", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right")
    # (b) 功率需求（相對最容易的函數）
    ax = axs[1]
    fx = np.array([F[f]["fixed"]["path_loss_db"] for f in FN])
    fl = np.array([F[f]["flow"]["pu_static_dbm"] for f in FN])
    ax.bar(x - w / 2, fx - fx.min(), w, color=GREY, label="固定加總：路徑衰減")
    ax.bar(x + w / 2, fl - fl.min(), w, color=BLUE, label="時域流程：靜態需求（由 margin 與雜訊）")
    ax.set_xticks(x, FN)
    ax.set_ylabel("要多給的光功率（dB，相對最容易者）")
    ax.set_ylim(0, 8.2)
    ax.set_title("(b) 功率：最難的函數不同", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper left")
    # (c) 相位漂移與殘留光
    ax = axs[2]
    d = [F[f]["flow"]["drift_ratio"] * 100 for f in FN]
    e = [F[f]["flow"]["er20_ratio"] * 100 for f in FN]
    ax.axhline(100, color=GREY, lw=2, label="固定加總：不受影響")
    ax.bar(x - w / 2, d, w, color=BLUE, label=f"未追蹤漂移 {B['drift_rad']:g} rad")
    ax.bar(x + w / 2, e, w, color="#9ecae1", label=f"消光比 {B['er_fixed_db']:g} dB、不重解")
    ax.set_xticks(x, FN)
    ax.set_ylim(0, 140)
    ax.set_ylabel("靜態 margin 剩下（%）")
    ax.set_title("(c) 相位與殘留光：固定模型沒有這兩項", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right", ncol=1)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m2", "s1_baseline.png"), dpi=160)
    print("寫出 figures/paper/m2/s1_baseline.png")


if __name__ == "__main__":
    main()
