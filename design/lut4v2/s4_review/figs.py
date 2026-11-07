r"""佈局審查：圖——從 GDS 抽出的光路（每段波導一種顏色）、審查放大圖、由佈局重算 U 的結果。

用途：多邊形從 LUT4 s3 的 l4_core.gds 讀回；連通塊在這裡重新聯集上色（與 review.py 相同的做法）；數字讀 review_checks.json、extracted.json。
輸入：LUT4 s3 的 out/l4_core.gds、out/layout_info.json；out/review_checks.json、out/extracted.json。
輸出：figures/m3/s2_extract.png（圖 M3-4）、figures/m3/s2_zoom.png（圖 M3-5）、figures/m3/s2_checks.png（圖 M3-6）。
執行：.\lab design\m3_layout\s2_review\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.collections import PolyCollection                    # noqa: E402
from matplotlib.ticker import FuncFormatter                          # noqa: E402
from shapely.geometry import Polygon                                 # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "lut4v2/s4_review"
CORE = "lut4v2/s3_core"
INFO = json.loads(paths.OUT(CORE, "layout_info.json").read_text(encoding="utf-8"))
REV = json.loads(paths.OUT(STEP, "review_checks.json").read_text(encoding="utf-8"))
EXT = json.loads(paths.OUT(STEP, "extracted.json").read_text(encoding="utf-8"))
GEO = INFO["geometry"]


def polygons():
    structs, dbu = G.parse(str(paths.OUT(CORE, "l4_core.gds")))
    out = []
    G.flatten(structs, INFO["cells"]["core"], np.eye(2), np.zeros(2), out)
    return [(l, p * dbu / 1e-6) for l, p in out]


def fig_extract(polys, path):
    """MMI 以外的波導聯集後，每個連通塊一種顏色；MMI 用灰色；節點畫點。"""
    fig, ax = plt.subplots(figsize=(14, 4.6))
    wg = [Polygon(xy).buffer(0) for l, xy in polys if l == 3]
    big = [p for p in wg if p.area > 50 and (p.bounds[3] - p.bounds[1]) > 4 and (p.bounds[2] - p.bounds[0]) < 100]  # MMI 本體
    rest = unary_union([p for p in wg if p not in big])
    comps = list(rest.geoms) if hasattr(rest, "geoms") else [rest]
    cmap = plt.get_cmap("tab20")
    for i, c in enumerate(sorted(comps, key=lambda c: (c.bounds[0], -c.bounds[3]))):
        geoms = list(c.geoms) if hasattr(c, "geoms") else [c]
        for g in geoms:
            xy = np.array(g.buffer(0.6).exterior.coords)            # 加粗，縱向放大後才看得見
            ax.add_collection(PolyCollection([xy], facecolors=cmap(i % 20), edgecolors="none"))
    ax.add_collection(PolyCollection([np.array(p.exterior.coords) for p in big], facecolors="#9aa0a6", edgecolors="none"))
    for n, (x, y) in EXT["nodes"].items():
        if not n.startswith("M"):
            ax.text(x + (-6 if n.startswith("in") else 6), y, n, ha="right" if n.startswith("in") else "left", va="center", fontsize=8.5)
    for h in EXT["heaters"]:
        x0, y0, x1, y1 = h["bounds"]
        ax.text((x0 + x1) / 2, y0 - 2, h["label"], ha="center", va="top", fontsize=7.5, color=RED)
    ax.set_xlim(-GEO["lead_um"] - 120, GEO["columns"] * GEO["mzi_length_um"] + GEO["lead_um"] + 120)
    ax.set_ylim(-4 * GEO["pitch_um"] - 15, 30)
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")
    ax.set_title(f"只從 GDS 抽出的光路：{REV['n_components']} 段波導（每段一種顏色）、14 個 MMI（灰），每段恰接兩個節點；紅字是 TiN 旁的 heater 標記（縱向放大）",
                 fontsize=10.5)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def draw(ax, polys, xlim, ylim):
    col = {3: G.LAYER_COLOR[3], 39: G.LAYER_COLOR[39], 41: G.LAYER_COLOR[41]}
    for l in (3, 39, 41):
        ax.add_collection(PolyCollection([p for ll, p in polys if ll == l], facecolors=col[l], edgecolors="none",
                                         alpha=0.85 if l != 41 else 0.6, zorder={3: 1, 39: 2, 41: 3}[l]))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_xlabel("x（µm）")


def fig_zoom(polys, path):
    m = INFO["placement"][0]
    x0, y0 = m["origin_um"]
    L, P, SB = GEO["mzi_length_um"], GEO["pitch_um"], GEO["sbend_um"]
    xa = x0 + GEO["phase_section_um"] + SB                            # MMI1 輸入
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1, 1.1, 1.2]))
    a, b, c = axs
    draw(a, polys, (xa - 6, xa + 4), (y0 - P / 2 - 3.5, y0 - P / 2 + 3.5))
    a.set_title("(a) S 彎接到 MMI 輸入埠", fontsize=10.5)
    a.text(xa - 5.6, y0 - P / 2 + 2.9, f"波導寬 {GEO['waveguide_width_um']:g} µm＝MMI 埠寬\n兩埠中心距 2.03 µm", fontsize=8.5, va="top")
    # (b) heater 落墊與上一軌的距離：找一個上方有波導的 heater（MZI 在第 2 條以下的軌）
    h = next(h for h in INFO["heaters"] if h["y_um"] < 0)
    xe, ye = h["body_um"][1], h["y_um"]
    draw(b, polys, (xe - 16, xe + 16), (ye - 4, ye + P + 4))
    top = ye + GEO["landing_offset_um"] + GEO["landing_tin_um"] / 2
    b.annotate("", xy=(xe + 9, ye + P - GEO["waveguide_width_um"] / 2), xytext=(xe + 9, top), arrowprops=dict(arrowstyle="<->", color=RED))
    b.text(xe + 10, (top + ye + P) / 2, f"TiN 落墊到上一軌\n{REV['min_tin_to_other_wg_um']:.2f} µm", fontsize=8.5, color=RED, va="center")
    b.set_title(f"(b) {h['heater']} 右端：金屬離其他波導最近處", fontsize=10.5)
    # (c) 加熱條本體到下臂
    hb = INFO["heaters"][1]
    xm = sum(hb["body_um"]) / 2
    draw(c, polys, (xm - 25, xm + 25), (hb["y_um"] - P - 4, hb["y_um"] + 6))
    c.annotate("", xy=(xm, hb["y_um"] - P + 0.3), xytext=(xm, hb["y_um"] - 0.5), arrowprops=dict(arrowstyle="<->", color=RED))
    c.text(xm + 1, hb["y_um"] - P / 2, f"加熱條本體到最近的其他波導\n{REV['min_heater_body_to_other_wg_um']:.1f} µm（熱串擾；下臂與上一軌幾乎等距）",
           fontsize=8.5, color=RED, va="center")
    c.set_title(f"(c) {hb['heater']}：本體只蓋上臂", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_checks(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw=dict(width_ratios=[1, 1.4]))
    names = list(REV["per_function"])
    vals = [max(REV["per_function"][n]["U_err"], 1e-17) for n in names]
    a.bar(range(len(vals)), vals, color=GREEN)
    a.set_yscale("log")
    a.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"1e{np.log10(v):.0f}"))
    a.axhline(1e-12, color=GREY, ls="--", lw=1)
    a.text(-0.4, 2.5e-12, "門檻 1e-12", fontsize=8.5, color=GREY)
    for k, n in enumerate(names):
        a.text(k, vals[k] * 3, f"{REV['per_function'][n]['passed']}/16", ha="center", fontsize=8.5)
    a.set_xticks(range(len(vals)), names)
    a.set_ylim(1e-17, 1e-9)
    a.set_title("由佈局重算的 U 與接線表＋相位的 U 之差", fontsize=10.5)
    rows = [c for c in REV["checks"]]
    b.axis("off")
    y = 1.0
    for cc in rows:
        st, col = ("通過", GREEN) if cc["ok"] is True else (("處置", ORANGE) if cc["ok"] is None else ("未通過", RED))
        b.text(0.0, y, cc["id"], fontsize=9, fontweight="bold", va="top")
        b.text(0.07, y, st, fontsize=9, color=col, va="top", fontweight="bold")
        b.text(0.17, y, f"{cc['item']}：{cc['result']}", fontsize=8.6, va="top")
        y -= 0.071
    b.set_title(f"審查表：{REV['n_pass']} 項通過、{REV['n_disposition']} 項有處置", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    polys = polygons()
    fig_extract(polys, paths.FIG("lut4v2", "s2_extract.png"))
    fig_zoom(polys, paths.FIG("lut4v2", "s2_zoom.png"))
    fig_checks(paths.FIG("lut4v2", "s2_checks.png"))
    print("寫出 figures/m3/s2_extract.png、s2_zoom.png、s2_checks.png")


if __name__ == "__main__":
    main()
