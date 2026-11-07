"""共用的概念圖版型（每步開頭的「本步概念」圖）。

版型固定：上方一行「本步要回答」；左欄「輸入」（上一步的輸出），中間「本步做什麼」（直觀示意），
右欄「輸出」；下方一句重點。各里程碑的 concept.py 只負責畫中間的示意。
座標：寬 14、高 6.4；中間示意區為 x 3.3–10.7、y 0.9–5.2。
輸出：無（被其他程式 import）。
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED  # noqa: F401  （給各 concept.py 一起 import）

BEIGE = "#fbf3df"
MID = (3.3, 10.7)


def box(ax, x, y, w, h, text, ec=GREY, fc="white", fs=10, bold=False, color="black", lw=1.4, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=lw, ls=ls))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=color,
                fontweight="bold" if bold else None)


def arrow(ax, a, b, color=GREY, lw=1.6, text=None, fs=9, rad=0.0, dy=0.15):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                                    connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, text, ha="center", va="bottom", fontsize=fs, color=color)


def frame(question, inputs, outputs, key, figsize=(13.5, 6.2)):
    """畫固定框架，回傳 (fig, ax)；inputs／outputs 是字串清單（每項一個小框）。"""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    box(ax, 0.1, 5.55, 13.8, 0.7, "本步要回答：" + question, ec=PURPLE, fc="#f3eefa", fs=11.5, bold=True)
    ax.text(1.55, 5.15, "輸入", ha="center", fontsize=10, color=BLUE, fontweight="bold")
    ax.text(12.45, 5.15, "輸出", ha="center", fontsize=10, color=ORANGE, fontweight="bold")
    for col, items, ec, fc in ((0.1, inputs, BLUE, "#eaf1fa"), (11.0, outputs, ORANGE, BEIGE)):
        n = len(items)
        h = min(1.0, (3.9 - 0.15 * (n - 1)) / n)
        top = 4.95
        for k, t in enumerate(items):
            box(ax, col, top - (k + 1) * h - k * 0.15, 2.9, h, t, ec=ec, fc=fc, fs=9)
    arrow(ax, (3.05, 3.0), (3.35, 3.0), BLUE, 2.2)
    arrow(ax, (10.65, 3.0), (10.95, 3.0), ORANGE, 2.2)
    ax.text(7.0, 0.35, key, ha="center", va="center", fontsize=10.5, color="black",
            bbox=dict(boxstyle="round,pad=0.35", fc="#fffbe6", ec=ORANGE, lw=1))
    return fig, ax


def save(fig, path):
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
