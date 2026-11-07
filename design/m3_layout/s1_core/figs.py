r"""M3 s1：圖——B7 核心全圖（標出 MZI、heater 編號、光學埠）、單顆 MZI 尺寸、heater 端點放大。

用途：多邊形一律從 b7_core.gds 讀回（不是畫圖時的變數）；標註文字從 layout_info.json 讀出。配色與 GDS 出圖相同。
輸入：out/b7_core.gds、out/layout_info.json。
輸出：figures/m3/s1_core.png（圖 M3-1）、figures/m3/s1_mzi.png（圖 M3-2）、figures/m3/s1_heater.png（圖 M3-3）。
執行：.\lab design\m3_layout\s1_core\figs.py
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

STEP = "m3_layout/s1_core"
INFO = json.loads(paths.OUT(STEP, "layout_info.json").read_text(encoding="utf-8"))
GEO = INFO["geometry"]
COL = {3: G.LAYER_COLOR[3], 39: G.LAYER_COLOR[39], 41: G.LAYER_COLOR[41]}
NAME = {3: "GDS 3 矽波導", 39: "GDS 39 TiN", 41: "GDS 41 Ti/AL"}


def polygons():
    structs, dbu = G.parse(str(paths.OUT(STEP, "b7_core.gds")))
    out = []
    G.flatten(structs, INFO["cells"]["core"], np.eye(2), np.zeros(2), out)
    sc = dbu / 1e-6
    return [(l, p * sc) for l, p in out if l in COL]


def draw(ax, polys, xlim=None, ylim=None):
    for l in (3, 39, 41):
        ps = [p for ll, p in polys if ll == l]
        ax.add_collection(PolyCollection(ps, facecolors=COL[l], edgecolors="none", alpha=0.85 if l != 41 else 0.6,
                                         zorder={3: 1, 39: 2, 41: 3}[l]))
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")


def legend(ax, loc="upper right", **kw):
    ax.legend([Patch(fc=COL[l], alpha=0.85) for l in (3, 39, 41)], [NAME[l] for l in (3, 39, 41)], fontsize=8.5, loc=loc, **kw)


def fig_core(polys, path):
    L, P = GEO["mzi_length_um"], GEO["pitch_um"]
    fig, ax = plt.subplots(figsize=(14, 4.6))
    draw(ax, polys, (-GEO["lead_um"] - 160, GEO["columns"] * L + GEO["lead_um"] + 160), (-4 * P - 22, GEO["landing_offset_um"] + 26))
    for l in range(GEO["columns"] + 1):
        ax.axvline(l * L, color=GREY, lw=0.6, ls=":")
    for l in range(GEO["columns"]):
        ax.text(l * L + L / 2, GEO["landing_offset_um"] + 15, f"第 {l + 1} 層", ha="center", fontsize=9, color=PURPLE)
    for m in INFO["placement"]:
        x, y = m["origin_um"]
        k = m["mzi"].split("-")[1]                                    # MZI-k 的 φk、θk：標籤放在兩個 heater 之間（第一顆 MMI 下方）
        hb = {h["phase"][0]: h["body_um"] for h in INFO["heaters"] if h["phase"][1:] == k}
        xm = (max(hb["φ"]) + min(hb["θ"])) / 2 if {"φ", "θ"} <= set(hb) else x + L / 2
        ax.text(xm, y - P - 12, m["mzi"], ha="center", va="center", fontsize=9, color=PURPLE, fontweight="bold",   # 放在下臂下方，不疊在光路上
                bbox=dict(fc="white", ec=PURPLE, lw=0.8, boxstyle="round,pad=0.2"))
    for h in INFO["heaters"]:
        ax.text(sum(h["body_um"]) / 2, h["y_um"] + 2.5, f"{h['heater']} {h['phase']}", ha="center", va="bottom", fontsize=7.5, color=RED)
    for p in INFO["ports"]:
        left = p["angle"] == 180.0
        ax.text(p["xy_um"][0] + (-6 if left else 6), p["xy_um"][1], f"{p['signal']} {p['port']}" if left else f"{p['port']} {p['signal']}",
                ha="right" if left else "left", va="center", fontsize=8.5)
    ax.set_title(f"B7 核心：{GEO['core_size_um'][0]:g}×{GEO['core_size_um'][1]:g} µm（縱向放大；7 顆 MZI、14 個 MMI、14 個 heater）", fontsize=11)
    legend(ax, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.33))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_mzi(polys, path):
    m = INFO["placement"][0]
    x0, y0 = m["origin_um"]
    L, P, LPH, SB, MM = GEO["mzi_length_um"], GEO["pitch_um"], GEO["phase_section_um"], GEO["sbend_um"], GEO["mmi_length_um"]
    fig, ax = plt.subplots(figsize=(14, 4.2))
    draw(ax, polys, (x0 - 45, x0 + L + 5), (y0 - P - 22, y0 + GEO["landing_offset_um"] + 16))
    xs = np.cumsum([0, LPH, SB, MM, SB, LPH, SB, MM, SB]) + x0
    names = ["φ 相位區", "S 彎", "MMI 1", "S 彎", "θ 相位區（上臂）", "S 彎", "MMI 2", "S 彎"]
    yb = y0 - P - 12
    for a, b, n in zip(xs[:-1], xs[1:], names):
        ax.annotate("", xy=(b, yb), xytext=(a, yb), arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.9))
        ax.text((a + b) / 2, yb - 2.5, f"{n}\n{b - a:g} µm", ha="center", va="top", fontsize=8.2, color=GREY)
        ax.axvline(a, color=GREY, lw=0.5, ls=":")
    ax.annotate("", xy=(x0 - 8, y0 - P), xytext=(x0 - 8, y0), arrowprops=dict(arrowstyle="<->", color=PURPLE, lw=1))
    ax.text(x0 - 10, y0 - P / 2, f"軌距\n{P:g} µm", fontsize=8.5, color=PURPLE, va="center", ha="right")
    for h in INFO["heaters"]:
        if h["mzi"] == m["mzi"]:
            ax.text(sum(h["body_um"]) / 2, y0 + GEO["landing_offset_um"] + 9, f"{h['heater']}（{h['phase']}）", ha="center", fontsize=9, color=RED)
    ax.set_title(f"單顆 MZI：長 {L:g} µm（縱向放大）；上下兩臂等長 {GEO['arm_len_um'][0]:.2f} µm；"
                 f"S 彎最小曲率半徑 {GEO['sbend_rmin_um']:.1f} µm（≥ 10 µm）", fontsize=10.5)
    ax.set_ylim(yb - 14, y0 + GEO["landing_offset_um"] + 16)
    legend(ax, loc="upper right")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_heater(polys, path):
    h = INFO["heaters"][0]
    xe, ye = h["body_um"][0], h["y_um"]
    off, tin, al, w = GEO["landing_offset_um"], GEO["landing_tin_um"], GEO["landing_al_um"], GEO["heater_width_um"]
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    draw(ax, polys, (xe - 16, xe + 22), (ye - 6, ye + off + 10))
    ax.set_aspect("equal")
    gap = off - tin / 2 - w / 2
    ax.annotate("", xy=(xe + 8, ye + off - tin / 2), xytext=(xe + 8, ye + w / 2), arrowprops=dict(arrowstyle="<->", color=RED, lw=1.2))
    ax.text(xe + 9, ye + (off - tin / 2 + w / 2) / 2, f"{gap:.2f} µm\n（TiN 間距 ≥ 10 µm）", fontsize=9, color=RED, va="center")
    ax.text(xe + 14, ye + 1.5, f"加熱條 寬 {w:g} µm →", fontsize=9, ha="center")
    ax.text(xe - 15, ye + off, f"TiN 落墊 {tin:g}×{tin:g}\nTi/AL {al[0]:g}×{al[1]:g}", fontsize=9, va="center")
    ax.text(xe - 15, ye - 4, "波導（加熱條正下方）", fontsize=8.5, color=G.LAYER_COLOR[3])
    ax.set_title(f"{h['heater']} 左端：TiN 短條把接點引離波導", fontsize=11)
    legend(ax, loc="lower right")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    polys = polygons()
    fig_core(polys, paths.FIG("m3", "s1_core.png"))
    fig_mzi(polys, paths.FIG("m3", "s1_mzi.png"))
    fig_heater(polys, paths.FIG("m3", "s1_heater.png"))
    print("寫出 figures/m3/s1_core.png、s1_mzi.png、s1_heater.png")


if __name__ == "__main__":
    main()
