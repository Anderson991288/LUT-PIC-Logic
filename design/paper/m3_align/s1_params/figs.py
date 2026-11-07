r"""論文 M3 s1：圖——同一參考面的雜訊護欄（我們、草稿式、草稿表 I）與護欄隨偵測器端功率的變化。

用途：數字讀 out/align.json。
輸入：out/align.json。
輸出：figures/paper/m3/s1_align.png（圖 M3-1）。
執行：.\lab design\paper\m3_align\s1_params\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.lines import Line2D                                  # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "paper/m3_align/s1_params"
G = json.loads(paths.OUT(STEP, "align.json").read_text(encoding="utf-8"))
PARTS = (("th", "TIA 熱雜訊", BLUE), ("comp", "比較器雜訊", PURPLE), ("shot", "shot", ORANGE), ("rin_diff", "RIN（差動）", GREEN),
         ("rin_cm", "RIN（PD 失配）", GREY))


def main():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    ax = axs[0]
    fns = list(G["guard_compare"])
    x = np.arange(len(fns))
    for j, fn in enumerate(fns):                                     # 我們的護欄：各項雜訊的 qσ 份量按平方比例分配（只為看組成）
        p = G["guards"][fn]["parts"]
        var = {k: p[k] ** 2 for k, _, _ in PARTS}
        tot = sum(var.values())
        qs = G["guards"][fn]["guard_ours"] - p["off"]
        bottom = p["off"]
        ax.bar(j - 0.2, p["off"], 0.36, color="#d9d9d9", label="比較器偏移" if j == 0 else None)
        for k, lab, c in PARTS:
            h = qs * var[k] / tot
            ax.bar(j - 0.2, h, 0.36, bottom=bottom, color=c, label=lab if j == 0 else None)
            bottom += h
    ax.plot(x + 0.2, [G["guard_compare"][f]["draft_style"] for f in fns], "D", color="k", ms=7, mfc="white", label="草稿式（不含 shot）")
    ax.plot(x + 0.2, [G["guard_compare"][f]["draft"] for f in fns], "_", color=RED, ms=26, mew=3, label="草稿表 I")
    ax.set_xticks(x, fns)
    ax.set_ylabel("雜訊護欄 Γ（P_u）")
    ax.set_ylim(0, 0.22)
    ax.set_title(f"(a) 偵測器端 {G['draft_pu_dbm']:g} dBm 的護欄（margin 最差那組輸入）", fontsize=10.5)
    h, lab = ax.get_legend_handles_labels()                          # 圖上的橫線 ms＝26 比圖例樣本長，圖例改用一般線段
    h[lab.index("草稿表 I")] = Line2D([], [], color=RED, lw=3)
    ax.legend(h, lab, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax = axs[1]
    p = np.array(G["curve_dbm"])
    for fn, c in (("XOR2", RED), ("AND4", BLUE)):
        ax.plot(p, G["curve"][fn], color=c, lw=2, label=f"{fn} 的護欄")
        if G["plane"][fn]["margin"] < 0.6:                           # 只畫在座標範圍內的 margin（AND4 約 0.97，超出）
            ax.axhline(G["plane"][fn]["margin"], color=c, ls=":", lw=1.2)
            ax.text(-2.1, G["plane"][fn]["margin"] + 0.01, f"{fn} margin {G['plane'][fn]['margin']:.3f}", color=c, fontsize=8, va="bottom", ha="right")
    x2 = G["plane"]["XOR2"]
    ax.plot([x2["pd_dbm"]], [x2["guard_at_pd_need"]], "o", color=RED, ms=8)
    ax.annotate(f"我們的需求（偵測器端）{x2['pd_dbm']} dBm\n＝B7 輸入端 {x2['b7_input_dbm']} dBm − 輸出側 {G['loss_out_db']} dB",
                (x2["pd_dbm"], x2["guard_at_pd_need"]), xytext=(-14.0, 0.10), fontsize=8, arrowprops=dict(arrowstyle="->", color=RED))
    ax.axvline(G["draft_pu_dbm"], color="k", ls="--", lw=1)
    ax.annotate(f"草稿 {G['draft_pu_dbm']:g} dBm：XOR2 護欄 {x2['guard_at_m7']:.3f}", (G["draft_pu_dbm"], x2["guard_at_m7"]),
                xytext=(-6.8, 0.40), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.set_xlabel("偵測器端每路 P_u（dBm）")
    ax.set_ylabel("雜訊護欄 Γ（P_u）")
    ax.set_ylim(0, 0.6)
    ax.set_title("(b) 護欄隨功率變化：參考面不同，看起來就差約 2 倍", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m3", "s1_align.png"), dpi=160)
    print("寫出 figures/paper/m3/s1_align.png")


if __name__ == "__main__":
    main()
