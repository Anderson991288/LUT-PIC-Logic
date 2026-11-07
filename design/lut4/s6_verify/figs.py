r"""連接檢查：圖——從 GDS 抽出的電氣網（每個網一種顏色）、LVS 對照表與故障注入結果。

用途：多邊形從 晶片整合 的 chip.gds 讀回，Ti/AL 在這裡重新聯集上色（與 verify.py 相同的做法）；表格讀 connectivity.json、drc_result.json。
輸入：晶片整合 的 out/chip.gds、out/chip_info.json；out/connectivity.json、out/drc_result.json。
輸出：figures/m3/s4_nets.png（圖 M3-10）、figures/m3/s4_checks.png（圖 M3-11）。
執行：.\lab design\m3_layout\s4_verify\figs.py
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
from shapely.geometry import Point, Polygon                          # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402
from common.draw import GREEN, GREY, RED                             # noqa: E402

STEP = "lut4/s6_verify"
CHIP = "lut4/s5_chip"
INFO = json.loads(paths.OUT(CHIP, "chip_info.json").read_text(encoding="utf-8"))
CONN = json.loads(paths.OUT(STEP, "connectivity.json").read_text(encoding="utf-8"))
DRC = json.loads(paths.OUT(STEP, "drc_result.json").read_text(encoding="utf-8"))


def flat(structs, name, M, T, polys, texts):
    st = structs[name]
    polys += [(l, xy @ M.T + T) for l, xy in st["boundaries"]]
    texts += [(l, M @ xy + T, s) for l, xy, s in st["texts"]]
    for s in st["srefs"]:
        M2, T2 = G.affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        flat(structs, s["sname"], M @ M2, M @ T2 + T, polys, texts)


def fig_nets(path):
    structs, dbu = G.parse(str(paths.OUT(CHIP, "chip.gds")))
    polys, texts = [], []
    flat(structs, "L4_CHIP", np.eye(2), np.zeros(2), polys, texts)
    sc = dbu / 1e-6
    polys = [(l, xy * sc) for l, xy in polys]
    texts = [(xy * sc, s) for l, xy, s in texts if l == 100]
    al = unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 41])
    al = list(al.geoms) if hasattr(al, "geoms") else [al]
    pads = {p["name"] for p in INFO["pads"]}
    fig, ax = plt.subplots(figsize=(14, 5.4))
    ax.add_collection(PolyCollection([xy for l, xy in polys if l == 3], facecolors="#9ec3e6", edgecolors="#9ec3e6", linewidths=0.6, zorder=1))
    ax.add_collection(PolyCollection([xy for l, xy in polys if l == 39], facecolors=G.LAYER_COLOR[39], edgecolors=G.LAYER_COLOR[39],
                                     linewidths=1.2, zorder=3))
    cmap = plt.get_cmap("tab20")
    for i, g in enumerate(sorted(al, key=lambda g: g.bounds[0])):
        name = next((s for xy, s in texts if s in pads and g.contains(Point(xy))), "?")
        col = "#4d4d4d" if name[:2] in ("GN", "GS") else cmap(i % 20)
        ax.add_collection(PolyCollection([np.array(g.exterior.coords)], facecolors=col, edgecolors=col, linewidths=0.8,
                                         alpha=0.85, zorder=2))
    for xy, s in texts:
        if s in pads:
            ax.text(xy[0], xy[1], s, ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=5)
        elif s.startswith("H"):
            ax.text(xy[0], xy[1] - 9, s, ha="center", va="top", fontsize=6.5, color=RED, zorder=5)
    px = [p["xy_um"][0] for p in INFO["pads"]]
    ax.set_xlim(min(px) - 80, max(max(px) + 80, 2400))                 # 21 個 PAD 全部入框
    ax.set_ylim(INFO["die_y_um"][0] - 10, INFO["die_y_um"][1] + 10)
    ax.set_aspect("equal")
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")
    e = CONN["electrical"]
    ax.set_title(f"只從 GDS 抽出的電氣網：Ti/AL {e['al_nets']} 個網（訊號網各一色、地網深灰）、TiN {e['tin_regions']} 塊（橘）；"
                 "每塊 TiN 恰好接兩個網：自己的訊號 PAD 與地", fontsize=10)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_checks(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(13.5, 5.0), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a.axis("off")
    ch = sorted(CONN["electrical"]["channels"], key=lambda r: r["heater"])
    a.text(0.0, 1.0, "heater", fontweight="bold", fontsize=9.5, va="top")
    a.text(0.18, 1.0, "接點", fontweight="bold", fontsize=9.5, va="top")
    a.text(0.32, 1.0, "抽出的網", fontweight="bold", fontsize=9.5, va="top")
    a.text(0.66, 1.0, "原理圖", fontweight="bold", fontsize=9.5, va="top")
    a.text(0.88, 1.0, "結果", fontweight="bold", fontsize=9.5, va="top")
    for k, r in enumerate(ch):
        y = 0.93 - 0.062 * k
        a.text(0.0, y, r["heater"], fontsize=9, va="top")
        a.text(0.18, y, str(r["contacts"]), fontsize=9, va="top")
        a.text(0.32, y, "＋".join(sorted(r["nets"])), fontsize=9, va="top")
        a.text(0.66, y, f"{r['expect'][0]}＋GND", fontsize=9, va="top")
        a.text(0.88, y, "一致" if r["ok"] else "不符", fontsize=9, va="top", color=GREEN if r["ok"] else RED, fontweight="bold")
    a.set_title("LVS：14 個 heater 的接點與網", fontsize=10.5)
    f = CONN["faults"]
    names = list(f)
    b.barh(range(len(names)), [1] * len(names), color=[GREEN if v else RED for v in f.values()])
    for k, (n, v) in enumerate(f.items()):
        b.text(0.03, k, f"{n}：{'抓到' if v else '漏掉'}", va="center", fontsize=9.5, color="white", fontweight="bold")
    b.set_yticks([])
    b.set_xticks([])
    b.invert_yaxis()
    b.set_xlim(0, 1)
    b.set_title(f"故障注入：{sum(f.values())}/{len(f)} 抓到（正常晶片：DRC {DRC['total']}、LVS 錯誤 {len(CONN['electrical']['errors'])}、"
                f"光學 {sum(r['ok'] for r in CONN['optical']['ec'])}/10）", fontsize=10)
    for s in b.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_nets(paths.FIG("lut4", "s4_nets.png"))
    fig_checks(paths.FIG("lut4", "s4_checks.png"))
    print("寫出 figures/m3/s4_nets.png、s4_checks.png")


if __name__ == "__main__":
    main()
