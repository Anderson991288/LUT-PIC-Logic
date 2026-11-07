r"""M3 s6：圖——KLayout 平台 deck 與 Calibre 草案在四份 GDS 上的結果、maxVertices＝200 匯出後的接縫放大。

用途：數字讀 commercial.json；接縫圖讀 strmout_200.gds 與原 chip.gds 的 GDS 3 多邊形，標出 KLayout 的違規位置（讀 lyrdb）。
輸入：out/commercial.json、out/strmout_200.gds、out/strmout_200_drc.lyrdb；delivery/layout/chip.gds。
輸出：figures/m3/s6_compare.png（圖 M3-16）、figures/m3/s6_seam.png（圖 M3-17）。
執行：.\lab design\m3_layout\s6_commercial\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402
import re                                                            # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.collections import PolyCollection                    # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, RED               # noqa: E402

STEP = "lut4/s8_commercial"
RES = json.loads(paths.OUT(STEP, "commercial.json").read_text(encoding="utf-8"))
NAMES = {"chip": "交付的 LUT4_chip.gds", "fault": "故意加兩種違規", "strmout_200": "Virtuoso 匯出\nmaxVertices 200", "strmout_8191": "Virtuoso 匯出\nmaxVertices 8191"}


def kl_total(t):
    if t == "chip":
        return json.loads(paths.OUT("lut4/s6_verify", "drc_result.json").read_text(encoding="utf-8"))["total"]   # 2026-11-07：改讀 LUT4 s6，原本寫死 0
    if t == "fault":
        return sum(json.loads(paths.OUT("lut4/s6_verify", "drc_result.json").read_text(encoding="utf-8"))["fault_injection"]["counts"].values())   # 2026-11-07：原本誤讀 M3 s4
    return RES["klayout"][t]["total"]


def fig_compare(path):
    tags = list(NAMES)
    kl = [kl_total(t) for t in tags]
    ca = [RES["calibre"][t]["total"] for t in tags]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    x = np.arange(len(tags))
    w = 0.36
    ax.bar(x - w / 2, kl, w, color=BLUE, label=f"KLayout 平台 deck（{RES['deck_categories']} 個檢查類別）")
    ax.bar(x + w / 2, ca, w, color=ORANGE, label=f"Calibre 草案（移植 {RES['coverage']} 個 output 敘述：各層線寬、間距）")
    for k in range(len(tags)):
        ax.text(x[k] - w / 2, kl[k] + 0.5, str(kl[k]), ha="center", fontsize=9.5, color=BLUE)
        ax.text(x[k] + w / 2, ca[k] + 0.5, str(ca[k]), ha="center", fontsize=9.5, color=ORANGE)
    ax.set_xticks(x, [NAMES[t] for t in tags])
    ax.set_ylabel("違規（結果）數")
    ax.set_ylim(0, max(kl + ca) * 1.25 + 2)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title(f"maxVertices＝200 的匯出檔：平台 deck 報 {RES['klayout']['strmout_200']['total']} 處（GDS 3 被 .raw 改成逐塊檢查），Calibre 草案合併後檢查 {RES['calibre']['strmout_200']['total']} 處", fontsize=10.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def polys3(gds):
    structs, dbu = G.parse(str(gds))
    referenced = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in referenced][0]
    out = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), out)
    return [xy * dbu / 1e-6 for l, xy in out if l == 3]


def markers(lyrdb):
    text = Path(lyrdb).read_text(errors="replace")
    pts = []
    for m in re.finditer(r"<value>edge-pair: \(([-\d.]+),([-\d.]+);([-\d.]+),([-\d.]+)\)", text):
        a, b, c, d = map(float, m.groups())
        pts.append(((a + c) / 2, (b + d) / 2))
    return pts


def fig_seam(path):
    mk = markers(paths.OUT(STEP, "strmout_200_drc.lyrdb"))
    cx, cy = mk[0] if mk else (-300.0, 304.0)
    p200 = polys3(paths.OUT(STEP, "strmout_200.gds"))
    p0 = polys3(paths.ROOT / "delivery_lut4" / "layout" / "LUT4_chip.gds")
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, ps, title in ((a, p0, "原 LUT4_chip.gds：曲線是一整塊"), (b, p200, "maxVertices 200 匯出：曲線被切成多塊")):
        near = [p for p in ps if np.min(np.hypot(p[:, 0] - cx, p[:, 1] - cy)) < 40]
        cols = [plt.get_cmap("tab10")(k % 10) for k in range(len(near))]
        ax.add_collection(PolyCollection(near, facecolors=cols if ax is b else [BLUE] * len(near), edgecolors="black", linewidths=0.6, alpha=0.75))
        ax.set_xlim(cx - 2.5, cx + 2.5)
        ax.set_ylim(cy - 2.5, cy + 2.5)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=10.5)
        ax.set_xlabel("x（µm）")
    b.plot([p[0] for p in mk], [p[1] for p in mk], "x", color=RED, ms=10, mew=2, label="KLayout 平台 deck 的標記")
    b.legend(fontsize=9, loc="upper right")
    a.set_ylabel("y（µm）")
    fig.suptitle(f"接縫放大（x≈{cx:.0f} µm，x1 扇入 S 彎）：未合併的分塊在切口形成銳角，逐塊檢查時判為 GDS 3 線寬違規；合併後沒有違規", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_compare(paths.FIG("lut4", "s8_compare.png"))
    fig_seam(paths.FIG("lut4", "s8_seam.png"))
    print("寫出 figures/lut4/s8_compare.png、s8_seam.png")


if __name__ == "__main__":
    main()
