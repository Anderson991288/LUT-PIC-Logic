r"""M1 s2：圖——單顆 MZI 的構造與分光比、兩顆 MZI＋R 的接法、三種結構的二輸入涵蓋、B7 接線圖。

用途：把 capability.py 的結果畫成圖；B7 接線圖由 common/draw.py 依 common/mzi.py 的 B7_OPS 繪製，與後面的模擬、佈局同一個來源。
輸入：out/capability.json、common/mzi.py。
輸出：figures/m1/s2_mzi.png（圖 M1-6）、figures/m1/s2_two_mzi.png（圖 M1-7）、figures/m1/s2_b7.png（圖 M1-8）、
      figures/m1/s2_coverage.png（圖 M1-9）。
執行：.\lab design\m1_logic\s2_b7\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle             # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import T                                             # noqa: E402
from common.draw import BLUE, ORANGE, GREEN, RED, GREY, PURPLE, mzi_box, draw_b7   # noqa: E402

CAP = json.loads(paths.OUT("m1_logic/s2_b7", "capability.json").read_text(encoding="utf-8"))


def fig_mzi(path):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
    a1.set_xlim(0, 10)
    a1.set_ylim(0, 3.2)
    a1.axis("off")
    yu, yd = 2.3, 0.9
    for y in (yu, yd):
        a1.plot([0.6, 9.4], [y, y], color=BLUE, lw=3)
    a1.text(0.1, yu, "上入", va="center")
    a1.text(0.1, yd, "下入", va="center")
    a1.text(9.5, yu, "上出", va="center")
    a1.text(9.5, yd, "下出", va="center")
    a1.add_patch(Rectangle((1.3, yu - 0.12), 1.0, 0.24, fc=ORANGE))
    a1.text(1.8, yu + 0.3, "外相位 φ", ha="center", fontsize=10)
    for x in (3.0, 7.0):
        a1.add_patch(FancyBboxPatch((x, yd - 0.3), 0.55, yu - yd + 0.6, boxstyle="round,pad=0.02", fc="#dde6ee", ec=GREY))
        a1.text(x + 0.27, (yu + yd) / 2, "MMI", ha="center", va="center", fontsize=9, rotation=90)
    a1.add_patch(Rectangle((4.7, yu - 0.12), 1.0, 0.24, fc=RED))
    a1.text(5.2, yu + 0.3, "內相位 θ", ha="center", fontsize=10)
    a1.add_patch(FancyBboxPatch((1.1, 0.35), 2.7, 2.55, boxstyle="round,pad=0.04", fc="none", ec=GREEN, ls="--"))
    a1.text(2.45, 0.15, "M1 s1 的混合單元", ha="center", fontsize=9, color=GREEN)
    a1.add_patch(FancyBboxPatch((0.95, 0.05), 7.0, 3.0, boxstyle="round,pad=0.04", fc="none", ec=PURPLE, lw=1.2))
    a1.text(7.85, 2.9, "一顆 MZI", ha="right", fontsize=10, color=PURPLE)
    th = np.linspace(0, 2 * np.pi, 361)
    bar = [abs(T(t, 0)[0, 0]) ** 2 for t in th]
    a2.plot(th / np.pi, bar, color=BLUE, lw=2, label="上入 → 上出（直通）")
    a2.plot(th / np.pi, 1 - np.array(bar), color=ORANGE, lw=2, ls="--", label="上入 → 下出（交叉）")
    a2.set_xlabel("內相位 θ（π）")
    a2.set_ylabel("功率比例")
    a2.set_title("θ 決定分光比；φ 不改變分光比")
    a2.legend(fontsize=9)
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_two(path):
    pair = CAP["two_mzi"]["best_pair"]
    a, b = (int(c[1]) - 1 for c in pair.split("-"))
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.6)
    ax.axis("off")
    ys = [3.0, 1.9, 0.8]
    for y, lab in zip(ys, ("x1", "x2", "R＝3")):
        ax.plot([1.0, 7.6], [y, y], color=ORANGE if lab.startswith("R") else BLUE, lw=3)
        ax.text(0.9, y, lab, ha="right", va="center", fontsize=11)
    mzi_box(ax, 2.2, ys[0], ys[1], "MZI-a\nθ、φ")
    mzi_box(ax, 4.6, ys[1], ys[2], "MZI-b\nθ、φ")
    for k, y in enumerate(ys):
        hit = k in (a, b)
        ax.text(7.75, y, f"o{k + 1}", va="center", fontsize=11, color=RED if hit else GREY, fontweight="bold" if hit else None)
    ax.annotate("", xy=(8.6, 1.35), xytext=(8.15, ys[a]), arrowprops=dict(arrowstyle="-", color=RED))
    ax.annotate("", xy=(8.6, 1.35), xytext=(8.15, ys[b]), arrowprops=dict(arrowstyle="-", color=RED))
    ax.text(8.7, 1.35, f"比大小\no{a + 1} − o{b + 1}", va="center", fontsize=10, color=RED)
    ax.text(5.0, 0.15, "x1、x2 先在 MZI-a 混成一道光，再和 R 在 MZI-b 混合；讀取 MZI-b 的兩個輸出。", ha="center",
            fontsize=9.5, color=GREY)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_coverage(path):
    rows = [("單顆 MZI\n（無 R）", CAP["single"]["funcs"]),
            (f"兩顆 MZI＋R\n（讀 {CAP['two_mzi']['best_pair']}）", CAP["two_mzi"]["pairs"][CAP["two_mzi"]["best_pair"]]["funcs"]),
            ("B7\n（x3＝x4＝0）", CAP["b7_2in"]["funcs"])]
    keys = list(CAP["single"]["funcs"])
    fig, ax = plt.subplots(figsize=(13, 3.4))
    for r, (lab, f) in enumerate(rows):
        for c, k in enumerate(keys):
            m = f[k]["margin"]
            ok = f[k]["ok"]
            ax.add_patch(Rectangle((c, -r), 0.94, 0.9, fc="#d6eedd" if ok else "#f6d5d1", ec="white"))
            ax.text(c + 0.47, -r + 0.6, "✓" if ok else "✗", ha="center", va="center", fontsize=12,
                    color=GREEN if ok else RED)
            ax.text(c + 0.47, -r + 0.25, f"{m if m > 1e-9 else 0.0:.2f}", ha="center", va="center", fontsize=8.5)
        n = sum(v["ok"] for v in f.values())
        ax.text(-0.15, -r + 0.45, f"{lab}\n{n}/16", ha="right", va="center", fontsize=10)
    for c, k in enumerate(keys):
        ax.text(c + 0.47, 1.25, f"{CAP['single']['funcs'][k]['name']}\n{k}", ha="center", va="center", fontsize=8.5)
    ax.set_xlim(-2.4, 16)
    ax.set_ylim(-2.2, 1.7)
    ax.axis("off")
    ax.set_title("16 種二輸入函數（下排數字＝00、01、10、11 的目標輸出）；格內數字＝最大 margin（P$_u$）", fontsize=11)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_b7(path):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    draw_b7(ax)
    ax.set_title("B7：5 條波導、7 顆 MZI、4 層磚牆排列；14 個相位；o2 與 o4 比大小", fontsize=11.5)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_mzi(paths.FIG("m1", "s2_mzi.png"))
    fig_two(paths.FIG("m1", "s2_two_mzi.png"))
    fig_coverage(paths.FIG("m1", "s2_coverage.png"))
    fig_b7(paths.FIG("m1", "s2_b7.png"))
    print("寫出 figures/m1/s2_mzi.png、s2_two_mzi.png、s2_coverage.png、s2_b7.png")


if __name__ == "__main__":
    main()
