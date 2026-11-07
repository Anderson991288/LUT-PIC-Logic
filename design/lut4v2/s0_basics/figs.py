r"""LUT4 s0（M1 s2 ①②）：圖——E± 輸入時單顆 MZI、二顆 MZI＋R 的接法與判讀結果。

用途：
  圖 a（s2_single_epm.png）：左為單顆 MZI 的接法（s1、s2 進、兩個輸出各接 PD、相減成 D、比較器門檻 0）；
        右為 φ＝0 時 4 個輸入的 D 隨 θ 變化：00 與 11、01 與 10 兩兩重疊，所以只能分出「相同／不同」（XNOR／XOR）。
  圖 b（s2_two_epm.png）：左為二顆 MZI＋R 的接法；右為 R＝1 時幾個代表函數在 4 個輸入的 D（各取裕量最大的相位）。
輸入：out/basics.json。
輸出：figures/lut4v2/s2_single_epm.png、figures/lut4v2/s2_two_epm.png。
執行：.\lab design\lut4v2\s0_basics\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon                # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "lut4v2/s0_basics"
B = json.loads(paths.OUT(STEP, "basics.json").read_text(encoding="utf-8"))


def box(ax, x, y, w, h, text, fc="#f3eefa", ec=PURPLE, fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def readout(ax, x, y_up, y_dn):
    """接收端：兩個輸出各接 PD（光功率 → 光電流）與 TIA（電流 → 電壓），再進比較器（V上＞V下 → y＝1）。x 為 PD 的位置。"""
    ym = (y_up + y_dn) / 2
    for y, lab in ((y_up, "上"), (y_dn, "下")):
        ax.add_patch(Circle((x, y), 0.2, fc="#fff3e0", ec=ORANGE, lw=1.4))
        ax.text(x, y + 0.32, f"PD {lab}", ha="center", fontsize=8.5, color=GREY)
        ax.plot([x + 0.2, x + 0.45], [y, y], color=GREY, lw=1.1)
        ax.add_patch(Polygon([(x + 0.45, y - 0.24), (x + 0.45, y + 0.24), (x + 0.95, y)], closed=True, fc="#eaf2fb", ec=BLUE, lw=1.3))
        ax.text(x + 0.62, y - 0.42, "TIA", ha="center", fontsize=8.5, color=BLUE)
        yi = ym + (0.22 if y == y_up else -0.22)
        ax.plot([x + 0.95, x + 1.25, x + 1.25, x + 1.5], [y, y, yi, yi], color=GREY, lw=1.1)
        ax.text(x + 1.56, yi, "+" if y == y_up else "−", ha="left", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(Polygon([(x + 1.5, ym - 0.5), (x + 1.5, ym + 0.5), (x + 2.3, ym)], closed=True, fc="#eef6ee", ec=GREEN, lw=1.4))
    ax.text(x + 1.9, ym - 0.72, "比較器", ha="center", fontsize=8.5, color=GREEN)
    ax.plot([x + 2.3, x + 2.6], [ym, ym], color=GREY, lw=1.1)
    ax.text(x + 2.65, ym, "y", ha="left", va="center", fontsize=10.5, fontweight="bold")
    ax.text(x + 1.3, y_dn - 0.75, "V上＞V下（即 D＝P上−P下＞0）→ y＝1", ha="center", fontsize=8.8, color=GREY)


def fig_single(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.0), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a.set_xlim(-0.2, 7.9); a.set_ylim(-0.6, 3.2); a.axis("off")
    for y, lab in ((2.3, "x1：s1＝+1／−1"), (0.5, "x2：s2＝+1／−1")):
        a.plot([1.5, 2.6], [y, y], color=BLUE, lw=2.4)
        a.text(1.45, y, lab, ha="right", va="center", fontsize=10)
        a.plot([3.9, 4.6], [y, y], color=BLUE, lw=2.4)
    box(a, 2.6, 0.2, 1.3, 2.4, "MZI\nθ、φ", fs=11)
    readout(a, 4.8, 2.3, 0.5)
    a.text(3.25, 2.95, "兩路資料光直接干涉，沒有參考光", ha="center", fontsize=9.5, color=GREY)
    th = np.array(B["single"]["sweep_theta"])
    sty = {"00": (BLUE, "-", 3.2), "11": (ORANGE, "--", 1.8), "01": (RED, "-", 3.2), "10": (GREEN, "--", 1.8)}
    for k, (c, ls, lw) in sty.items():
        b.plot(th / np.pi, B["single"]["sweep_D"][k], color=c, ls=ls, lw=lw, label=f"輸入 {k}")
    b.axhline(0, color="k", lw=0.8)
    b.fill_between(th / np.pi, -2.3, 2.9, where=np.array(B["single"]["sweep_D"]["00"]) > 0, color="#e8f1fb", zorder=0)
    b.text(0.5, 2.45, "00、11 判 1 → XNOR", ha="center", fontsize=9.5, color=BLUE)
    b.text(1.5, 2.45, "01、10 判 1 → XOR", ha="center", fontsize=9.5, color=RED)
    b.set_xlim(0, 2); b.set_ylim(-2.3, 2.9)
    b.set_xlabel("θ（π）　φ＝0"); b.set_ylabel("D＝P上−P下（Pᵤ）")
    b.legend(fontsize=8.5, ncol=2, loc="lower center")
    b.set_title("00 與 11、01 與 10 的 D 完全重疊", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_two(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.2), gridspec_kw=dict(width_ratios=[1.25, 1]))
    a.set_xlim(-0.2, 9.4); a.set_ylim(-0.9, 3.6); a.axis("off")
    for y, lab in ((2.8, "x1：s1"), (1.6, "x2：s2")):
        a.plot([1.1, 1.9], [y, y], color=BLUE, lw=2.4)
        a.text(1.05, y, lab, ha="right", va="center", fontsize=10)
    box(a, 1.9, 1.35, 1.1, 1.7, "MZI-1\nθ1、φ1", fs=10)
    a.plot([3.0, 3.6, 4.2], [2.8, 2.8, 2.2], color=BLUE, lw=2.4)
    a.text(3.6, 3.0, "u", ha="center", fontsize=10, color=BLUE)
    a.plot([3.0, 3.6], [1.6, 1.6], color=GREY, lw=1.4, ls=":")
    a.text(3.65, 1.45, "不讀", fontsize=8.5, color=GREY)
    a.plot([1.1, 4.2], [0.4, 0.4], color=ORANGE, lw=2.4)
    a.text(1.05, 0.4, "R（不調變）", ha="right", va="center", fontsize=10)
    a.plot([4.2, 4.2], [0.4, 0.4])
    box(a, 4.2, 0.15, 1.1, 2.3, "MZI-2\nθ2、φ2", fs=10)
    for y in (2.2, 0.4):
        a.plot([5.3, 5.9], [y, y], color=BLUE, lw=2.4)
    readout(a, 6.1, 2.2, 0.4)
    a.text(4.75, 3.35, "R 讓資料光可以和「絕對的 +E」比較", ha="center", fontsize=9.5, color=GREY)
    t = B["two_mzi_R"]["1"]["tables"]
    pick = [("0001", "AND"), ("0111", "OR"), ("1110", "NAND"), ("0011", "x1"), ("0110", "XOR")]
    w = 0.18
    for i, k in enumerate(B["bits"]):
        vals = [t[c]["D"][i] for c, _ in pick]
        b.bar(np.arange(len(pick)) + (i - 1.5) * w, vals, w, color=[BLUE if v > 0 else "#c9d6e6" for v in vals],
              edgecolor=GREY, lw=0.6)
    b.axhline(0, color="k", lw=0.8)
    b.set_xticks(range(len(pick))); b.set_xticklabels([f"{n}\n{c}" for c, n in pick], fontsize=9.5)
    lim = 1.12 * max(abs(t[c]["D"][i]) for c, _ in pick for i in range(4))
    b.set_ylabel("D（Pᵤ）"); b.set_ylim(-lim, lim)
    b.set_title("R＝1：每組四根依序為輸入 00、01、10、11\n深色 D＞0（判 1）、淺色 D＜0（判 0）", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    fig_single(paths.FIG("lut4v2", "s2_single_epm.png"))
    fig_two(paths.FIG("lut4v2", "s2_two_epm.png"))
    print("寫出 figures/lut4v2/s2_single_epm.png、s2_two_epm.png")


if __name__ == "__main__":
    main()
