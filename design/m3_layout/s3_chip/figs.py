r"""M3 s3：圖——整顆晶片（EC、扇出、PAD、繞線）、EC 放大、繞線放大（橫移與跨越波導）、電流密度。

用途：多邊形從 chip.gds 讀回；標註從 chip_info.json 讀出。配色與 GDS 出圖相同。
輸入：out/chip.gds、out/chip_info.json。
輸出：figures/m3/s3_chip.png（圖 M3-7）、figures/m3/s3_ec.png（圖 M3-8）、figures/m3/s3_route.png（圖 M3-9）。
執行：.\lab design\m3_layout\s3_chip\figs.py
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
from matplotlib.patches import Patch                                 # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402
from common.draw import GREY, PURPLE, RED                            # noqa: E402

STEP = "m3_layout/s3_chip"
INFO = json.loads(paths.OUT(STEP, "chip_info.json").read_text(encoding="utf-8"))
LAY = {3: "GDS 3 矽波導", 4: "GDS 4 120 nm 蝕刻窗", 5: "GDS 5 薄矽（100 nm）", 39: "GDS 39 TiN", 41: "GDS 41 Ti/AL"}
ZO = {4: 0, 5: 1, 3: 2, 39: 3, 41: 4}


def polygons():
    structs, dbu = G.parse(str(paths.OUT(STEP, "chip.gds")))
    out = []
    G.flatten(structs, "B7_CHIP", np.eye(2), np.zeros(2), out)
    return [(l, p * dbu / 1e-6) for l, p in out]


def draw(ax, polys, xlim, ylim, thick=0.0, layers=(4, 5, 3, 39, 41)):
    for l in layers:
        ps = [p for ll, p in polys if ll == l]
        if not ps:
            continue
        ax.add_collection(PolyCollection(ps, facecolors=G.LAYER_COLOR.get(l, "#999"), edgecolors=G.LAYER_COLOR.get(l, "#999") if thick else "none",
                                         linewidths=thick, alpha=0.6 if l in (41, 4) else 0.9, zorder=ZO[l]))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")


def legend(ax, layers, **kw):
    ax.legend([Patch(fc=G.LAYER_COLOR[l], alpha=0.8) for l in layers], [LAY[l] for l in layers], fontsize=8.5, **kw)


def fig_chip(polys, path):
    x0, x1 = INFO["die_x_um"]
    y0, y1 = INFO["die_y_um"]
    fig, ax = plt.subplots(figsize=(14, 5.6))
    draw(ax, polys, (x0 - 60, x1 + 60), (y0 - 30, y1 + 30), thick=1.2)
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="#8c564b", lw=1.2)
    ax.set_aspect("equal")
    for e in INFO["ec"]:
        x, y = e["facet_um"]
        ax.text(x + (15 if e["side"] == "W" else -15), y + 22, f"{e['signal']}", ha="left" if e["side"] == "W" else "right", fontsize=8)
    for p in INFO["pads"]:
        ax.text(p["xy_um"][0], p["xy_um"][1], p["name"], ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=6)
    ax.set_title(f"整顆晶片 {INFO['die_um'][0]:g}×{INFO['die_um'][1]:g} µm：西緣 5 個輸入 EC、東緣 5 個輸出 EC（間距 {INFO['ec_pitch_um']:g} µm）；"
                 f"PAD 在上下緣最外圍：北側 {sum(p['side'] == 'N' for p in INFO['pads'])} 個、南側 {sum(p['side'] == 'S' for p in INFO['pads'])} 個（含 GND {INFO['n_gnd_pads']} 個）", fontsize=10.5)
    legend(ax, (3, 39, 41), loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.32))
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_ec(polys, path):
    e = next(e for e in INFO["ec"] if e["side"] == "W" and e["port"] == "in2")
    x, y = e["facet_um"]
    p = INFO["ec_params"]
    fig, (a, b) = plt.subplots(2, 1, figsize=(13, 5.6), gridspec_kw=dict(height_ratios=[1.3, 1]))
    L = p["tip_len"] + p["taper_len"] + p["bilevel_len"]
    draw(a, polys, (x - 5, x + L + 15), (y - 14, y + 14))
    xs = np.cumsum([0, p["tip_len"], p["taper_len"], p["bilevel_len"]]) + x
    for s, t, n in zip(xs[:-1], xs[1:], [f"尖端定寬 {p['tip_w']:g} µm\n（研磨窗口）", "100 nm 薄矽 taper", "雙層轉換"]):
        a.annotate("", xy=(t, y - 12), xytext=(s, y - 12), arrowprops=dict(arrowstyle="<->", color=GREY))
        a.text((s + t) / 2, y - 11.3, f"{n}　{t - s:g} µm", ha="center", va="bottom", fontsize=8.5, color=GREY)
    a.text(x + 1, y + 11, "端面（光纖側）", fontsize=8.5, color=RED)
    a.set_title("(a) 西緣 EC（縱向放大）：GDS 4 開窗內只用 GDS 5 保護一條細線，該處剩 100 nm 厚的矽", fontsize=10.5)
    legend(a, (3, 4, 5), loc="upper right")
    draw(b, polys, (x + p["tip_len"] + p["taper_len"] - 5, x + L + 8), (y - 2, y + 2))
    b.set_aspect("equal")
    b.set_title(f"(b) 雙層轉換放大（等比例）：GDS 3 核心從 {p['core_end_w']:g} µm 漸寬到波導寬，下面墊著 GDS 5 薄矽", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_route(polys, path):
    jog = [r for r in INFO["routes"] if r["jog"] and r["side"] == "N"]
    xs = [pt[0] for r in jog for pt in r["pts"]]
    fig, ax = plt.subplots(figsize=(13, 6.4))
    xl = (min(xs) - 60, max(xs) + 60)
    yp = max(p["xy_um"][1] for p in INFO["pads"])                       # 北側 PAD 中心
    draw(ax, polys, xl, (-115, yp + 60), thick=0.6)
    for r in INFO["routes"]:
        if r["side"] == "N" and xl[0] < r["pts"][0][0] < xl[1]:
            x0, y0 = r["pts"][0]
            left = r["end"] == "L"                                     # 左端標在落墊左邊、右端標在右邊，避免蓋住落墊
            ax.text(x0 + (-7 if left else 7), y0 - 9, f"{r['heater']}{'訊' if r['role'] == 'sig' else '地'}",
                    ha="right" if left else "left", va="center", fontsize=7.5, color=RED if r["jog"] else PURPLE, zorder=7,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    for p in INFO["pads"]:
        if p["side"] == "N" and xl[0] < p["xy_um"][0] < xl[1]:
            ax.text(p["xy_um"][0], p["xy_um"][1], p["name"], va="center", ha="center", fontsize=8.5, color="white", fontweight="bold", zorder=7)
    ax.set_title("北側繞線（縱向放大）：紅字的端點先在落墊高度橫移，避開上方 heater 的 TiN，再直走跨過波導；\n"
                 "PAD 一排在晶片最外緣，訊號線各接自己的 PAD，相鄰兩個 heater 的地線接同一個 GND PAD（GN1、GN2…）",
                 fontsize=10)
    legend(ax, (3, 39, 41), loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.1))
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    polys = polygons()
    fig_chip(polys, paths.FIG("m3", "s3_chip.png"))
    fig_ec(polys, paths.FIG("m3", "s3_ec.png"))
    fig_route(polys, paths.FIG("m3", "s3_route.png"))
    print("寫出 figures/m3/s3_chip.png、s3_ec.png、s3_route.png")


if __name__ == "__main__":
    main()
