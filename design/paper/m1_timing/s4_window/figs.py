r"""論文 M1 s4：圖——動態 margin 隨取樣相位的變化（眼圖的最差邊界）、功率代價與 skew。

用途：數字讀 out/window.json。
輸入：out/window.json。
輸出：figures/paper/m1/s4_margin.png（圖 M1-7）、figures/paper/m1/s4_penalty.png（圖 M1-8）。
執行：.\lab design\paper\m1_timing\s4_window\figs.py
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
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "paper/m1_timing/s4_window"
W = json.loads(paths.OUT(STEP, "window.json").read_text(encoding="utf-8"))
COL = {"AND2": BLUE, "OR2": GREEN, "XOR2": RED, "AND4": PURPLE, "OR4": ORANGE}


def fig_margin():
    F = W["functions"]
    fig, ax = plt.subplots(figsize=(10.5, 4.9))
    for fn, c in COL.items():
        r = F[fn]["ideal"]
        t = np.arange(len(r["curve_skew0"])) * W["dt_ps"]
        ax.plot(t, np.array(r["curve_skew0"]) / r["m0"], color=c, lw=2, label=f"{fn}（skew 0）")
        ax.plot(t, np.array(r["curve_skew20"]) / r["m0"], color=c, lw=1.2, ls="--")
    # AND4 在 skew 0 的最佳取樣窗
    r = F["AND4"]["ideal"]["rows"][0]
    t0 = r["window_start_ps"]
    ax.axvspan(t0, t0 + W["t_req_ps"], color="#e8e0f5", zorder=0)
    ax.text(t0 + W["t_req_ps"] / 2, 1.12, f"取樣需要 {W['t_req_ps']:g} ps\n（AND4 的最佳位置）", ha="center", fontsize=9, color=PURPLE)
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(1, color=GREY, ls=":", lw=1)
    ax.axvline(W["ui_ps"], color=GREY, ls=":", lw=1)
    ax.text(W["ui_ps"] - 2, -0.9, "下一個符號開始 →", fontsize=9, color=GREY, ha="right")
    ax.set_xlim(0, 2 * W["ui_ps"])
    ax.set_ylim(-1.0, 1.3)
    ax.set_xlabel("取樣時間（ps，從輸入符號的起點算；含接收端濾波的延遲）")
    ax.set_ylabel("動態 margin ／ 靜態 margin")
    ax.set_title("所有輸入組合中最差的判讀量 s·ΔP（低於 0 就會判錯）。實線：各路同時到達；虛線：skew 20 ps 的最差情況\n"
                 "轉態與接收端頻寬讓可取樣的時間只剩中間一段；四輸入函數的平台最窄", fontsize=10.5)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s4_margin.png"), dpi=160)
    plt.close(fig)


def fig_penalty():
    F = W["functions"]
    fig, ax = plt.subplots(figsize=(9.5, 4.9))
    for fn, c in COL.items():
        for case, ls, mk in (("ideal", "-", "o"), ("er", ":", None)):
            rows = F[fn][case]["rows"]
            x = [r["skew_ps"] for r in rows if r["penalty_db"] is not None]
            y = [r["penalty_db"] for r in rows if r["penalty_db"] is not None]
            ax.plot(x, y, color=c, ls=ls, lw=2 if case == "ideal" else 1.2, marker=mk, ms=4, label=fn if case == "ideal" else None)
    ax.axvline(W["skew_at_1db_ideal"], color=RED, lw=1.3)
    ax.text(W["skew_at_1db_ideal"] - 0.6, 7.6, f"完整模型：skew 額外代價 1 dB\n在 {W['skew_at_1db_ideal']:g} ps（{W['skew_at_1db_fn']}）",
            ha="right", fontsize=9.5, color=RED)
    ax.axvline(W["first_order_allow_ps"], color=GREY, lw=1.2, ls="--")
    ax.text(W["first_order_allow_ps"] + 0.6, 7.6, f"M1 s1 一階估計\n{W['first_order_allow_ps']:.1f} ps", fontsize=9.5, color=GREY)
    ax.text(0.8, 4.0, "晶片內 skew 0.335 ps\n（在最左邊，看不出差別）", fontsize=9, color=GREY)
    ax.set_xlim(0, max(W["skews_ps"]))
    ax.set_ylim(0, 10)
    ax.set_xlabel("輸入之間的 skew 範圍 S（ps；16 個延遲角落中最差的）")
    ax.set_ylabel("功率代價（dB）＝10 log₁₀（靜態 margin ／ 取樣窗內 margin）")
    ax.set_title(f"10 Gb/s 的功率代價：各路同時到達時已有 {W['penalty0_max_ideal']:.1f} dB（轉態與接收端頻寬）；"
                 f"\nskew 再加 1 dB 的點與一階估計同一量級（準則不同）；消光比 {W['er_db']:g} dB（點線）只多 {W['er_extra_db_max']:.2f} dB", fontsize=10.5)
    ax.legend(fontsize=9, loc="upper left", title="實線：理想消光比", title_fontsize=8.5)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s4_penalty.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_margin()
    fig_penalty()
    print("寫出 figures/paper/m1/s4_margin.png、s4_penalty.png")
