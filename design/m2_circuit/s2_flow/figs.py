r"""M2 s2：圖——從規格到交付的流程、PDK cell 的實際外形、元件在晶片上的位置與來源。

用途：流程與元件都從 flow.json、components.json 讀出；cell 外形畫 PDK 的實際多邊形（pdk_cells_geom.json），配色與 GDS 出圖相同。
輸入：out/flow.json、out/components.json、out/pdk_cells_geom.json。
輸出：figures/m2/s2_flow.png（圖 M2-4）、figures/m2/s2_cells.png（圖 M2-5）、figures/m2/s2_components.png（圖 M2-6）。
執行：.\lab design\m2_circuit\s2_flow\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle    # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, ORANGE, GREY, PURPLE, RED       # noqa: E402
from common.gds2png import LAYER_COLOR                               # noqa: E402

STEP = "m2_circuit/s2_flow"
FLOW = json.loads(paths.OUT(STEP, "flow.json").read_text(encoding="utf-8"))["flow"]
COMP = json.loads(paths.OUT(STEP, "components.json").read_text(encoding="utf-8"))
GEOM = json.loads(paths.OUT(STEP, "pdk_cells_geom.json").read_text(encoding="utf-8"))
BEIGE = "#fbf3df"
LAYER_NAME = {3: "GDS 3 矽波導", 39: "GDS 39 TiN 加熱條", 41: "GDS 41 Ti/AL 接點與 PAD"}


def box(ax, x, y, w, h, text, ec=GREY, fc="white", fs=9, bold=False, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=1.4, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else None)


def arrow(ax, a, b, color=GREY, lw=1.4, rad=0.0):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, connectionstyle=f"arc3,rad={rad}"))


def fig_flow(path):
    """兩列各四步：上列 M2（規格、元件、模擬），下列 M3（佈局到交付）；每步下方是它的輸出檔。"""
    fig, ax = plt.subplots(figsize=(13.5, 6.6))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 6.8)
    ax.axis("off")
    W, H, DX = 2.75, 1.15, 3.3
    xs = [0.35 + DX * k for k in range(4)]
    rows = [(5.2, FLOW[:4]), (1.9, FLOW[4:])]
    for (y, steps), lab, lx in zip(rows, ("M2 電路：規格、元件、模擬", "M3 佈局：核心、晶片、檢查、交付"), (0.05, xs[1])):
        ax.text(lx, y + H + 0.3, lab, fontsize=10.5, fontweight="bold", color=PURPLE)
        for k, s in enumerate(steps):
            cur = s["step"] == "M2 s2"
            box(ax, xs[k], y, W, H, f"{s['step']}　{s['name']}\n{s['tool']}", ec=RED if cur else BLUE,
                fc="#fdecea" if cur else "#eaf1fa", fs=9.2, bold=cur)
            box(ax, xs[k] + 0.1, y - 0.95, W - 0.2, 0.7, "\n".join(s["output"]) if len(s["output"]) < 3 else "、".join(s["output"]),
                ec=ORANGE, fc=BEIGE, fs=8.4)
            arrow(ax, (xs[k] + W / 2, y), (xs[k] + W / 2, y - 0.25), ORANGE, 1.1)
            ax.text(xs[k] + W / 2, y - 1.12, "驗收：" + s["check"], ha="center", va="top", fontsize=7.6, color=GREY, wrap=True)
            if k < 3:
                arrow(ax, (xs[k] + W, y + H / 2), (xs[k + 1], y + H / 2), BLUE, 1.8)
    yl = 3.75                                                        # 換列：M3 s1 往下、往左、再往下接 M3 s2
    ax.plot([xs[3] + W / 2, xs[3] + W / 2, xs[0] + W / 2], [5.2 - 1.45, yl, yl], color=BLUE, lw=1.8)
    arrow(ax, (xs[0] + W / 2, yl), (xs[0] + W / 2, 1.9 + H + 0.05), BLUE, 1.8)
    ax.text(6.7, 0.12, "藍框：設計步驟與使用的工具；米色框：該步產生、交給下一步的檔案；紅框：本步。",
            ha="center", fontsize=9, color=GREY)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def draw_cell(ax, name, title, zoom=None):
    g = GEOM[name]
    seen = set()
    for q in g["polygons"]:
        layer = q["gds"][0]
        col = LAYER_COLOR.get(layer, "#999999") if layer != 6 else "#264d73"
        if q.get("path_width"):
            xs, ys = zip(*q["xy"])
            ax.plot(xs, ys, color=col, lw=0, solid_capstyle="butt")
            # Path 的線寬以資料座標畫成矩形（加熱條是直線）
            ax.add_patch(Rectangle((min(xs), min(ys) - q["path_width"] / 2), max(xs) - min(xs), q["path_width"],
                                   fc=col, ec="none", alpha=0.85, zorder=3))
        else:
            ax.add_patch(Polygon(q["xy"], closed=True, fc=col, ec="none", alpha=0.85 if layer != 41 else 0.55,
                                 zorder={41: 4, 6: 3}.get(layer, 2)))
        seen.add(layer)
    for p in g["ports"]:
        ax.plot(*p["xy"], "o", ms=4, color=RED, zorder=6)
        ax.annotate(p["name"], p["xy"], textcoords="offset points", xytext=(4, 5), fontsize=8, color=RED, zorder=6)
    ax.set_aspect("equal")
    ax.autoscale_view()
    if zoom:
        ax.set_xlim(*zoom[0])
        ax.set_ylim(*zoom[1])
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("x（µm）")
    ax.grid(alpha=0.25)
    return seen


def fig_cells(path):
    S = COMP["summary"]
    fig = plt.figure(figsize=(13.5, 7.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.15], width_ratios=[1.5, 1.2, 0.9])
    a = fig.add_subplot(gs[0, :2])
    b = fig.add_subplot(gs[0, 2])
    c = fig.add_subplot(gs[1, 0])
    d = fig.add_subplot(gs[1, 1:])
    layers = set()
    layers |= draw_cell(a, "SOI220nm_1550nm_TE_STRIP_2x2_MMI", f"C1　2×2 MMI（{S['mmi_size_um'][0]:g}×{S['mmi_size_um'][1]:g} µm；DRC 0）")
    a.set_ylim(-6, 6)
    layers |= draw_cell(b, "HeaterPad", f"C4／C5　PAD（{S['pad_size_um'][0]:g}×{S['pad_size_um'][1]:g} µm）")
    layers |= draw_cell(c, "StraightHeaterFilament", f"C3　PDK 加熱條全長（{S['heater_length_um']:g} µm；DRC 違規 {COMP['components'][2]['pdk']['drc_total']}，改自建）")
    c.set_ylim(-8, 8)
    draw_cell(d, "StraightHeaterFilament", f"C3　端點放大（線寬 {S['heater_width_um']:g} µm）", zoom=((-3, 6), (-3, 3)))
    handles = [Rectangle((0, 0), 1, 1, fc=LAYER_COLOR.get(l, "#264d73"), alpha=0.85) for l in sorted(layers)]
    fig.legend(handles, [LAYER_NAME.get(l, f"GDS {l}") for l in sorted(layers)], loc="lower center", ncol=4, fontsize=9,
               bbox_to_anchor=(0.5, -0.02), frameon=False)
    fig.suptitle("PDK cell 的實際外形（取自 PDK 的多邊形；紅點是埠）", fontsize=11.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_components(path):
    """示意圖（不按比例）：每個元件在晶片上的位置，顏色表示來源。"""
    src = {c["id"]: c["decision"] for c in COMP["components"]}
    col = lambda i: BLUE if src[i].startswith("PDK") else ORANGE                     # noqa: E731
    fig, ax = plt.subplots(figsize=(13, 6.4))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    ax.add_patch(Rectangle((0.6, 0.6), 11.8, 5.4, fc="#fafafa", ec=GREY, lw=1.6))
    ax.text(6.5, 6.15, "晶片（示意，不按比例）", ha="center", fontsize=10, color=GREY)
    # EC
    for k in range(5):
        y = 2.2 + 0.45 * k
        ax.add_patch(Polygon([(0.6, y - 0.05), (1.4, y - 0.12), (1.4, y + 0.12), (0.6, y + 0.05)], fc=col("C8"), ec="none"))
        ax.add_patch(Polygon([(12.4, y - 0.05), (11.6, y - 0.12), (11.6, y + 0.12), (12.4, y + 0.05)], fc=col("C8"), ec="none"))
    ax.text(1.0, 1.75, "C8 EC×5", ha="center", fontsize=9, color=col("C8"))
    ax.text(12.0, 1.75, "C8 EC×5", ha="center", fontsize=9, color=col("C8"))
    # 波導
    for k in range(5):
        y = 2.2 + 0.45 * k
        ax.plot([1.4, 3.0], [y, y], color=col("C7"), lw=1.2)
        ax.plot([10.0, 11.6], [y, y], color=col("C7"), lw=1.2)
    ax.text(2.2, 4.55, "C7 波導與彎道", ha="center", fontsize=9, color=col("C7"))
    # B7 核心
    ax.add_patch(FancyBboxPatch((3.0, 1.9), 7.0, 2.6, boxstyle="round,pad=0.05", fc="#f3eefa", ec=PURPLE, lw=1.5))
    ax.text(6.5, 4.25, "B7 核心：7 顆 MZI", ha="center", fontsize=9.5, color=PURPLE, fontweight="bold")
    for k, x in enumerate((3.4, 5.3, 7.2)):
        ax.add_patch(Rectangle((x, 2.6), 0.45, 0.9, fc=col("C1"), ec="none"))
        ax.add_patch(Rectangle((x + 1.25, 2.6), 0.45, 0.9, fc=col("C1"), ec="none"))
        ax.add_patch(Rectangle((x + 0.55, 3.25), 0.6, 0.1, fc=LAYER_COLOR[39], ec="none"))
        ax.add_patch(Rectangle((x - 0.35, 2.15), 0.3, 0.08, fc=LAYER_COLOR[39], ec="none"))
    ax.annotate("C1 MMI（每顆 MZI 2 個）", (3.62, 3.5), xytext=(3.2, 3.85), fontsize=9, color=col("C1"),
                arrowprops=dict(arrowstyle="-", color=col("C1")))
    ax.annotate("C3 加熱條＋C2 相位區", (5.85 + 0.3, 3.35), xytext=(6.4, 3.85), fontsize=9, color=col("C3"),
                arrowprops=dict(arrowstyle="-", color=col("C3")))
    # PAD 與繞線
    for k in range(8):
        x = 3.2 + 0.85 * k
        ax.add_patch(Rectangle((x, 5.35), 0.5, 0.5, fc=LAYER_COLOR[41], ec="none", alpha=0.7))
        ax.plot([x + 0.25, x + 0.25], [5.35, 4.55], color=col("C6"), lw=1, ls="--")
    for k in range(7):
        x = 3.6 + 0.85 * k
        ax.add_patch(Rectangle((x, 0.75), 0.5, 0.5, fc=LAYER_COLOR[41], ec="none", alpha=0.7))
        ax.plot([x + 0.25, x + 0.25], [1.25, 1.85], color=col("C6"), lw=1, ls="--")
    ax.text(10.4, 5.55, "C4／C5 PAD（14 訊號＋GND）", fontsize=9, color=col("C4"), va="center")
    ax.text(10.4, 4.9, "C6 繞線（虛線）", fontsize=9, color=col("C6"), va="center")
    handles = [Rectangle((0, 0), 1, 1, fc=BLUE), Rectangle((0, 0), 1, 1, fc=ORANGE),
               Rectangle((0, 0), 1, 1, fc=LAYER_COLOR[39]), Rectangle((0, 0), 1, 1, fc=LAYER_COLOR[41], alpha=0.7)]
    ax.legend(handles, ["PDK 提供（cell 或模板）", "自建（模型或幾何）", "加熱條：自建（GDS 39 配色）",
                        "PAD：PDK cell（GDS 41 配色）"], loc="upper center", ncol=4, fontsize=9, frameon=False,
              bbox_to_anchor=(0.5, 0.08))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_flow(paths.FIG("m2", "s2_flow.png"))
    fig_cells(paths.FIG("m2", "s2_cells.png"))
    fig_components(paths.FIG("m2", "s2_components.png"))
    print("寫出 figures/m2/s2_flow.png、s2_cells.png、s2_components.png")


if __name__ == "__main__":
    main()
