r"""論文 M5 s1：圖——(a) 14 個 8 輸入單判讀函數、(b) 8 組雙判讀聯合指派的 margin（無損、0.9 dB／MZI），
並標出草稿的計算程式的值、0.1 P_u 與 0.20 P_u 兩條門檻。

用途：讀 cascade.json 出圖。
輸入：design/paper/m5_cascade/s1_cascade/out/cascade.json。
輸出：figures/paper/m5/s1_cascade.png（圖 M5-1）。
執行：.\lab design\paper\m5_cascade\s1_cascade\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, ORANGE                                 # noqa: E402

C = json.loads(paths.OUT("paper/m5_cascade/s1_cascade", "cascade.json").read_text(encoding="utf-8"))


def panel(ax, rows, labels, title):
    x = np.arange(len(rows))
    w = 0.38
    for k, (key, col, lab) in enumerate((("lossless", BLUE, "無損"), ("lossy", ORANGE, "0.9 dB／MZI"))):
        ax.bar(x + (k - 0.5) * w, [r[key]["best"] for r in rows], w, color=col, label=lab)
        ax.plot(x + (k - 0.5) * w, [r[key]["ref"] for r in rows], "k_", ms=10, mew=1.6, label="草稿的計算程式" if k == 0 else None)
    ax.axhline(0.1, color="k", ls=":", lw=1, label="0.1 P_u")
    ax.axhline(C["guard_coverage"], color="r", ls="--", lw=1, label="0.20 P_u（保守護欄）")
    ax.set_yscale("log")
    ax.set_ylim(0.05, 8)
    ax.yaxis.set_major_locator(FixedLocator([0.05, 0.1, 0.2, 0.5, 1, 2, 5]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))      # 避免 10 的負次方用到缺字的負號
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(x, labels, rotation=55, ha="right", fontsize=8.5)
    ax.set_ylabel("最差 margin（P_u，對數）")
    ax.set_title(title, fontsize=10)


def main():
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw=dict(width_ratios=[14, 8], wspace=0.15))
    S, Dd = C["single"], C["dual"]
    panel(axs[0], list(S.values()), list(S), "(a) 單判讀：Macro 1、2、4（21 顆 MZI）")
    panel(axs[1], list(Dd.values()), [k.replace("｜", "\n＋") for k in Dd], "(b) 雙判讀：四顆（28 顆 MZI），兩種指派取較好者")
    axs[0].legend(fontsize=8, loc="upper right", ncol=2)
    fig.savefig(paths.FIG("paper/m5", "s1_cascade.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m5/s1_cascade.png")


if __name__ == "__main__":
    main()
