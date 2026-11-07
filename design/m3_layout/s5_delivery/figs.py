r"""M3 s5：圖——交付包的檔案結構與交付檢查結果；交付的整顆晶片（標出每個 PAD 的功能與每個 EC 的訊號）；最終晶片的 B7 核心放大（標出 MZI、φ／θ 與對應 PAD、光學埠）。

用途：檔案清單讀 delivery/MANIFEST.json；檢查結果讀 out/delivery_check.json；核心放大直接讀交付的 delivery/layout/chip.gds，
      標註取自交付包的 chip_info.json（PAD 與 heater 對應）與 M3 s1 的 layout_info.json（MZI 位置、heater、埠）。
輸入：delivery/MANIFEST.json、delivery/layout/chip.gds、delivery/interfaces/chip_info.json；out/delivery_check.json；M3 s1 的 out/layout_info.json。
輸出：figures/m3/s5_delivery.png（圖 M3-12）、figures/m3/s5_chip.png（圖 M3-13，交付的整顆晶片）、figures/m3/s5_core.png（圖 M3-14，最終核心放大）。
執行：.\lab design\m3_layout\s5_delivery\figs.py
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
from matplotlib.patches import Patch, Rectangle                      # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402
from common import gds2png as G                                      # noqa: E402

MAN = json.loads((paths.ROOT / "delivery" / "MANIFEST.json").read_text(encoding="utf-8"))
CHK = json.loads(paths.OUT("m3_layout/s5_delivery", "delivery_check.json").read_text(encoding="utf-8"))
DESC = {"layout": ("佈局", BLUE), "interfaces": ("介面（給使用者接線、接光、設定相位）", ORANGE),
        "verification": ("驗證結果", GREEN), "figures": ("圖", PURPLE), "": ("說明、檢查程式、雜湊清單", GREY)}


WHITE = dict(fc="white", ec="none", pad=1.0)                         # 標籤白底：走線從標籤後方經過時字仍清楚


def load_chip():
    DL = paths.ROOT / "delivery"
    chip = json.loads((DL / "interfaces" / "chip_info.json").read_text(encoding="utf-8"))
    info = json.loads(paths.OUT("m3_layout/s1_core", "layout_info.json").read_text(encoding="utf-8"))
    structs, dbu = G.parse(str(DL / "layout" / "chip.gds"))
    flat = []
    G.flatten(structs, "B7_CHIP", np.eye(2), np.zeros(2), flat)
    by = {}
    for l, xy in flat:
        by.setdefault(l, []).append(xy * dbu / 1e-6)
    return chip, info, by


def callout(ax, text, xy_text, xy_arrow):
    ax.annotate(text, xy=xy_arrow, xytext=xy_text, ha="center", va="center", fontsize=9, zorder=8, annotation_clip=False,
                bbox=dict(boxstyle="round,pad=0.35", fc="#fff8ec", ec="#c9a46a", lw=0.8),
                arrowprops=dict(arrowstyle="->", color="#333333", lw=0.9, shrinkA=2, shrinkB=2))


def fig_chip():
    """交付的整顆晶片：從 chip.gds 讀幾何；每個 PAD 標名稱與功能（MZI 的 φ／θ 或 GND），每個 EC 標訊號；編號說明框放在空白處。"""
    chip, info, by = load_chip()
    (XW, XE), (YB, YT) = chip["die_x_um"], chip["die_y_um"]
    fig, ax = plt.subplots(figsize=(16, 7.4))
    sty = [(4, "#fde68a", "none", 2), (5, "#e377c2", "none", 2), (41, "#2ca02c", "#2ca02c", 3), (3, BLUE, BLUE, 4), (39, ORANGE, ORANGE, 5)]
    for l, fc, ec, z in sty:
        ax.add_collection(PolyCollection(by.get(l, []), facecolors=fc, edgecolors=ec, linewidths=0.6, alpha=0.75 if l == 41 else 1.0,
                                         zorder=z))
    ax.add_patch(Rectangle((XW, YB), XE - XW, YT - YB, fill=False, ec="#8c564b", lw=1.3, zorder=1))
    ax.set_xlim(XW - 260, XE + 300)
    ax.set_ylim(YB - 230, YT + 250)
    ax.set_aspect("equal")
    kind = {h["heater"]: (h["mzi"], h["kind"], h["phase"]) for h in info["heaters"]}
    for pd in chip["pads"]:
        x, y = pd["xy_um"]
        north = pd["side"] == "N"
        if pd["heater"]:
            mzi, k, ph = kind[pd["heater"]]
            sub, col = ph, BLUE if k == "phi" else "#b35900"                 # φk／θk 就是 MZI-k 的兩個相位
        else:
            sub, col = "GND", RED
        yt = YT + 12 if north else YB - 12                                 # 名稱標在晶片外緣外側，不疊在 PAD 或走線上
        ax.text(x, yt, f"{pd['name']}\n{sub}", ha="center", va="bottom" if north else "top", fontsize=7.6, color=col,
                linespacing=1.15, zorder=7)
    read = {"o2", "o4"}
    for e in chip["ec"]:
        x, y = e["facet_um"]
        w = e["side"] == "W"
        sig = e["signal"]
        ax.text(x - 12 if w else x + 12, y, sig + ("（判讀）" if sig in read else ""), ha="right" if w else "left", va="center",
                fontsize=9, color=RED if sig in read else "black", zorder=7)
    nN = chip["n_pads_side"]["N"]
    nS = chip["n_pads_side"]["S"]
    gN = sum(1 for p in chip["pads"] if p["side"] == "N" and p["heater"] is None)
    gS = sum(1 for p in chip["pads"] if p["side"] == "S" and p["heater"] is None)
    ecW = [e for e in chip["ec"] if e["side"] == "W"]
    ecE = [e for e in chip["ec"] if e["side"] == "E"]
    callout(ax, f"① 西緣 5 個輸入 EC\n間距 {chip['ec_pitch_um']:g} µm（x1–x4、R）", (XW + 330, YB - 150), tuple(ecW[3]["facet_um"]))
    callout(ax, "② 東緣 5 個輸出 EC\no2、o4 判讀，其餘終端（監看）", (XE - 330, YB - 150), tuple(ecE[3]["facet_um"]))
    pn = sorted([p for p in chip["pads"] if p["side"] == "N"], key=lambda p: p["xy_um"][0])
    callout(ax, f"③ 北緣 {nN} 個 PAD：{nN - gN} 訊號＋{gN} GND", (XW + 700, YT + 175), (pn[0]["xy_um"][0] - 45, pn[0]["xy_um"][1] + 40))
    ps = sorted([p for p in chip["pads"] if p["side"] == "S"], key=lambda p: p["xy_um"][0])
    callout(ax, f"④ 南緣 {nS} 個 PAD：{nS - gS} 訊號＋{gS} GND", (1050, YB - 150), (ps[3]["xy_um"][0] - 45, ps[3]["xy_um"][1]))
    callout(ax, "⑤ 中央 B7 核心", (1150, -330), (1150, -110))
    ax.set_xlabel("x（µm；交付 GDS 的座標）")
    ax.set_ylabel("y（µm）")
    ax.set_title(f"交付的整顆晶片（讀自 chip.gds，等比例）：{chip['die_um'][0]:g}×{chip['die_um'][1]:g} µm；B7 核心＋10 個 EC＋"
                 f"{len(chip['pads']) - chip['n_gnd_pads']} 個訊號 PAD＋{chip['n_gnd_pads']} 個 GND PAD\n"
                 "PAD 名稱下方是功能：φk、θk 是 MZI-k 的兩個相位（藍 φ、橘 θ），GND 是接地", fontsize=11)
    ax.legend([Patch(fc=BLUE), Patch(fc=ORANGE), Patch(fc="#2ca02c", alpha=0.75), Patch(fc="#fde68a"), Patch(fill=False, ec="#8c564b")],
              ["GDS 3 矽波導", "GDS 39 TiN heater", "GDS 41 Ti/AL（PAD 與走線）", "GDS 4 EC 開窗", "GDS 99 晶片外框"],
              fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=5)
    fig.savefig(paths.FIG("m3", "s5_chip.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_core():
    """最終晶片的 B7 核心放大：從交付的 chip.gds 讀幾何，標出每顆 MZI、φ／θ 接到哪個 PAD、輸入輸出埠（判讀埠標紅）。"""
    DL = paths.ROOT / "delivery"
    chip = json.loads((DL / "interfaces" / "chip_info.json").read_text(encoding="utf-8"))
    info = json.loads(paths.OUT("m3_layout/s1_core", "layout_info.json").read_text(encoding="utf-8"))
    geo = info["geometry"]
    L, P = geo["mzi_length_um"], geo["pitch_um"]
    structs, dbu = G.parse(str(DL / "layout" / "chip.gds"))
    flat = []
    G.flatten(structs, "B7_CHIP", np.eye(2), np.zeros(2), flat)
    by = {}
    for l, xy in flat:
        by.setdefault(l, []).append(xy * dbu / 1e-6)
    x0, x1, y0, y1 = -50.0, geo["columns"] * L + 50.0, -(4 * P) - 40.0, geo["landing_offset_um"] + 34.0
    fig, ax = plt.subplots(figsize=(16, 5.6))
    sty = {41: dict(fc="#2ca02c", ec="none", alpha=0.22, z=1), 39: dict(fc=ORANGE, ec=ORANGE, alpha=1.0, z=4),
           3: dict(fc=BLUE, ec=BLUE, alpha=1.0, z=3)}
    for l, st in sty.items():
        ax.add_collection(PolyCollection(by.get(l, []), facecolors=st["fc"], edgecolors=st["ec"], linewidths=0.5,
                                         alpha=st["alpha"], zorder=st["z"]))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    # 每顆 MZI：虛線框只框住兩條軌之間的光路；名稱放在下臂下方、第一顆 MMI 正下方（不疊在光路上）
    hb = {(h["mzi"], h["kind"]): h for h in info["heaters"]}
    pad_of = {p["heater"]: p["name"] for p in chip["pads"] if p["heater"]}
    gnd_of = {h: p["name"] for p in chip["pads"] if p["heater"] is None for h in p["heaters"]}
    for m in info["placement"]:
        xo, yo = m["origin_um"]
        yb = yo - P
        ax.add_patch(Rectangle((xo + 2, yb - 6), L - 4, P + 12, fill=False, ls="--", lw=0.9, ec=GREY, zorder=5))
        phi, th = hb[(m["mzi"], "phi")], hb[(m["mzi"], "theta")]
        xm = (phi["body_um"][1] + th["body_um"][0]) / 2
        w = m["waveguides"]
        ax.text(xm, yb - 14, f"{m['mzi']} ({w[0]},{w[1]})", ha="center", va="center", fontsize=8.6, color=PURPLE,
                fontweight="bold", zorder=6, bbox=WHITE)
        for h in (phi, th):
            xc = sum(h["body_um"]) / 2
            # 標在 heater 正下方、上下兩臂之間（相位區兩臂平行，中間沒有光路與金屬）；分兩行，寬度不超過 heater，不碰虛線框
            ax.text(xc, h["y_um"] - 4, f"{h['phase']}\n{pad_of[h['heater']]}／{gnd_of[h['heater']]}",
                    ha="center", va="top", fontsize=7.4, color="#b35900", linespacing=1.05, zorder=6, bbox=WHITE)
    for c in range(geo["columns"]):
        ax.text(c * L + L / 2, y1 - 4, f"第 {c + 1} 層", ha="center", va="top", fontsize=9, color=GREY, zorder=6, bbox=WHITE)
    # 光學埠：標在圖框外，不疊在扇出的光路上；判讀埠 o2、o4 標紅
    read = {o["port"] for o in chip["ec"] if o["signal"] in ("o2", "o4")}
    for pt in info["ports"]:
        left = pt["angle"] == 180.0
        ec = next(e for e in chip["ec"] if e["port"] == pt["port"])
        col = RED if pt["port"] in read else "black"
        txt = f"{ec['signal']} → {pt['port']}" if left else f"{pt['port']} → {ec['signal']}" + ("（判讀）" if pt["port"] in read else "")
        ax.text(x0 - 8 if left else x1 + 8, pt["xy_um"][1], txt, ha="right" if left else "left", va="center", fontsize=9,
                color=col, clip_on=False)
    ax.set_xlabel("x（µm；交付 GDS 的座標，原點在核心輸入引線末端）")
    ax.set_yticks([])                                                  # 縱向放大，刻度沒有意義；埠標籤放在兩側
    ax.set_title("最終晶片的 B7 核心放大（讀自交付的 chip.gds；縱向放大）\n"
                 "heater 下方標出相位與「訊號 PAD／GND PAD」；MZI-k (a,b) 的 a、b 是它所在的兩條軌；淡綠是往上下 PAD 的 Ti/AL 走線", fontsize=10.5)
    ax.legend([Patch(fc=BLUE), Patch(fc=ORANGE), Patch(fc="#2ca02c", alpha=0.3), Patch(fill=False, ls="--", ec=GREY)],
              ["GDS 3 矽波導", "GDS 39 TiN heater", "GDS 41 Ti/AL", "一顆 MZI"], fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.16), ncol=4)
    fig.savefig(paths.FIG("m3", "s5_core.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_chip()
    fig_core()
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw=dict(width_ratios=[1.05, 1]))
    a.axis("off")
    groups = {}
    for f in MAN["files"]:
        d = f["path"].split("/")[0] if "/" in f["path"] else ""
        groups.setdefault(d, []).append(f)
    groups.setdefault("", []).append(dict(path="MANIFEST.json", bytes=0))
    y = 1.0
    a.text(0.0, y, "delivery/", fontsize=11, fontweight="bold", va="top")
    y -= 0.05
    for d in ("layout", "interfaces", "verification", "figures", ""):
        name, col = DESC[d]
        if d:
            a.text(0.03, y, f"{d}/", fontsize=10, fontweight="bold", color=col, va="top")
            a.text(0.3, y, name, fontsize=8.8, color=col, va="top")
            y -= 0.045
        for f in groups[d]:
            fn = f["path"].split("/")[-1]
            a.text(0.08 if d else 0.03, y, fn, fontsize=9, va="top", color="black" if d else col)
            kb = f["bytes"] / 1024
            a.text(0.62, y, f"{kb:.0f} KB" if kb >= 1 else ("—" if fn == "MANIFEST.json" else f"{f['bytes']} B"), fontsize=8.5,
                   color=GREY, va="top")
            y -= 0.038
        y -= 0.012
    a.set_title(f"交付包：{len(MAN['files']) + 1} 個檔案（MANIFEST.json 記錄其他 {len(MAN['files'])} 個的 SHA-256）", fontsize=11)
    b.axis("off")
    y = 1.0
    b.text(0.0, y, "交付檢查（只讀交付包本身）", fontsize=10.5, fontweight="bold", va="top")
    y -= 0.06
    for k, v in CHK["checks"].items():
        b.text(0.0, y, "通過" if v["ok"] else "未通過", fontsize=9.5, color=GREEN if v["ok"] else RED, fontweight="bold", va="top")
        b.text(0.12, y, k, fontsize=9.5, va="top")
        y -= 0.048
    y -= 0.03
    b.text(0.0, y, "自我測試：注入錯誤，對應檢查必須失敗", fontsize=10.5, fontweight="bold", va="top")
    y -= 0.06
    tests = CHK["self_test"] or {}
    for k, v in tests.items():
        if v.get("group") == "反向":                                  # 反向測試種類多，下面只畫一行總數
            continue
        b.text(0.0, y, "抓到" if v["caught"] else "漏掉", fontsize=9.5, color=GREEN if v["caught"] else RED, fontweight="bold", va="top")
        b.text(0.12, y, f"{k} → {v['check']}", fontsize=9.5, va="top")
        y -= 0.048
    rev = [v for v in tests.values() if v.get("group") == "反向"]
    if rev:
        allok = all(v["caught"] for v in rev)
        b.text(0.0, y, "抓到" if allok else "漏掉", fontsize=9.5, color=GREEN if allok else RED, fontweight="bold", va="top")
        b.text(0.12, y, f"反向測試（更新 MANIFEST 後仍被語意檢查攔下）{sum(v['caught'] for v in rev)}/{len(rev)}", fontsize=9.5, va="top")
        y -= 0.048
    b.set_title("交付檢查全部通過" if CHK["all_ok"] else "交付檢查有未通過項目", fontsize=11, color=GREEN if CHK["all_ok"] else RED)
    fig.tight_layout()
    fig.savefig(paths.FIG("m3", "s5_delivery.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("寫出 figures/m3/s5_chip.png、s5_core.png、s5_delivery.png")


if __name__ == "__main__":
    main()
