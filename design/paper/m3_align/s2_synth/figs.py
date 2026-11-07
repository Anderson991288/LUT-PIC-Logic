r"""論文 M3 s2：圖——9 個函數的 margin（無損、0.9 dB／MZI）與草稿表 I、偵測器端 −7 dBm 的護欄、16 個起點的收斂。

用途：數字讀 out/synth.json。
輸入：out/synth.json。
輸出：figures/paper/m3/s2_synth.png（圖 M3-2）。
執行：.\lab design\paper\m3_align\s2_synth\figs.py
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
from common.draw import BLUE, GREY, ORANGE, RED                      # noqa: E402

STEP = "paper/m3_align/s2_synth"
G = json.loads(paths.OUT(STEP, "synth.json").read_text(encoding="utf-8"))


def main():
    F = G["functions"]
    names = list(F)
    x = np.arange(len(names))
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw=dict(width_ratios=[1.5, 1]))
    ax = axs[0]
    ax.bar(x - 0.2, [F[k]["lossless"]["best"] for k in names], 0.38, color="#c9d9ee", label="本步：無損")
    ax.bar(x + 0.2, [F[k]["lossy"]["best"] for k in names], 0.38, color=BLUE, label=f"本步：{G['mzi_loss_db']} dB／MZI")
    ax.plot(x - 0.2, [F[k]["draft"]["lossless"] for k in names], "_", color=RED, ms=18, mew=2.5, label="草稿表 I")
    ax.plot(x + 0.2, [F[k]["draft"]["lossy"] for k in names], "_", color=RED, ms=18, mew=2.5)
    ax.plot(x + 0.2, [F[k]["lossy"]["guard"] for k in names], "v", color=ORANGE, ms=7, label="護欄（偵測器端 −7 dBm）")
    ax.set_xticks(x, names)
    ax.set_ylabel("最差 margin（P_u）")
    ax.set_title(f"(a) 9 個函數的 margin：本步與草稿表 I（最大差 {max(abs(F[k][c]['diff_draft']) for k in names for c in ('lossless', 'lossy')):.3f} P_u）",
                 fontsize=10.5)
    ax.legend(fontsize=8.5, loc="upper right")
    ax = axs[1]
    for j, k in enumerate(names):
        for c, dx, col in (("lossless", -0.15, GREY), ("lossy", 0.15, BLUE)):
            lo, med, hi = F[k][c]["soft_spread"]
            ax.plot([j + dx, j + dx], [lo / F[k][c]["best"], hi / F[k][c]["best"]], color=col, lw=2)
            ax.plot([j + dx], [med / F[k][c]["best"]], "o", color=col, ms=5)
            ax.text(j + dx, 1.04, f"{F[k][c]['soft_hits']}", ha="center", fontsize=7.5, color=col)
    ax.plot([], [], color=GREY, lw=2, label="無損")
    ax.plot([], [], color=BLUE, lw=2, label=f"{G['mzi_loss_db']} dB／MZI")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
    ax.set_ylim(-0.08, 1.12)
    ax.set_ylabel("各起點的結果 ／ 最佳已知")
    ax.set_title(f"(b) soft-min {G['starts']} 個起點：範圍與中位數（數字：達到最佳的起點數）", fontsize=10.5)
    ax.legend(fontsize=8.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m3", "s2_synth.png"), dpi=160)
    print("寫出 figures/paper/m3/s2_synth.png")


if __name__ == "__main__":
    main()
