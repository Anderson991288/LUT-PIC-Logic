"""共用的示意圖元件（M1 s2 起）：MZI 方塊與 B7 接線圖，所有步驟畫 B7 都用這裡，確保接線與 common/mzi.py 一致。

輸出：無（被其他程式 import）。
"""
from matplotlib.patches import FancyBboxPatch

from common.mzi import B7_OPS, READ

BLUE, ORANGE, GREEN, RED, GREY, PURPLE = "#2f6fb5", "#c08a2b", "#2e7d4f", "#c0392b", "#5f6368", "#8e6fb5"
B7_YS = [4.0, 3.0, 2.0, 1.0, 0.0]             # 波導 1–5 的 y
B7_XL = [1.2, 3.2, 5.2, 7.2]                  # 四層 MZI 方塊的左緣
B7_W = 1.2
B7_INS = ["x1", "x2", "x3", "x4", "R"]


def mzi_box(ax, x, y0, y1, label, w=1.0, fc="#f3eefa", ec=PURPLE, lw=1.4, fs=9.5):
    """在 x 處畫一顆 MZI 方塊，跨越波導 y0（上）到 y1（下）。"""
    ax.add_patch(FancyBboxPatch((x, y1 - 0.25), w, y0 - y1 + 0.5, boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, (y0 + y1) / 2, label, ha="center", va="center", fontsize=fs)


def draw_b7(ax, labels=True, path=None, path_color=RED, box_label=None, fs=10, in_labels=None, out_labels=None):
    """畫 B7 接線。path：[(MZI 編號, 輸出 local, 輸入 local), …]（local 1＝上、2＝下），由起點輸入沿線畫紅色路徑。
    in_labels／out_labels：自訂左右兩側的文字（預設為「x1（輸入 1）」與「o1  終端」）。"""
    ys, xl, w = B7_YS, B7_XL, B7_W
    for j, y in enumerate(ys):
        ax.plot([0.6, 9.2], [y, y], color=ORANGE if j == 4 else BLUE, lw=2.4, zorder=0, alpha=0.35 if path else 1)
        if labels:
            ax.text(0.5, y, in_labels[j] if in_labels else f"{B7_INS[j]}（輸入 {j + 1}）", ha="right", va="center",
                    fontsize=fs)
            hit = j in READ
            ax.text(9.3, y, out_labels[j] if out_labels else f"o{j + 1}" + ("  判讀" if hit else "  終端"),
                    va="center", fontsize=fs, color=RED if hit else GREY, fontweight="bold" if hit else None)
    for k, (rail, lay) in enumerate(B7_OPS, 1):
        lab = box_label(k) if box_label else f"MZI-{k}\nθ{k}、φ{k}"
        mzi_box(ax, xl[lay], ys[rail], ys[rail + 1], lab, w=w, fs=fs - 1)
    if path:
        # 起點：路徑第一步所在 MZI 的輸入波導
        k0, _, b0 = path[0]
        rail = B7_OPS[k0 - 1][0] + b0 - 1
        x = 0.6
        for k, a, b in path:
            r0, lay = B7_OPS[k - 1]
            xin, xout = xl[lay], xl[lay] + w
            ax.plot([x, xin], [ys[rail], ys[rail]], color=path_color, lw=3.2, zorder=3)
            new = r0 + a - 1
            ax.plot([xin, xout], [ys[rail], ys[new]], color=path_color, lw=3.2, zorder=3)
            rail, x = new, xout
        ax.plot([x, 9.2], [ys[rail], ys[rail]], color=path_color, lw=3.2, zorder=3)
    for lay, x in enumerate(xl):
        ax.text(x + w / 2, 4.75, f"第 {lay + 1} 層", ha="center", fontsize=fs - 0.5, color=PURPLE)
    ax.set_xlim(-1.2, 10.8)
    ax.set_ylim(-0.7, 5.1)
    ax.axis("off")
