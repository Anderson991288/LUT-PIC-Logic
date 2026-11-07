r"""M1 s5：圖——三個交接檔各裝什麼、交給 M2 的誰；B7 的教學編號與佈局埠名對照。

用途：交接示意圖的檔名、函數數、列數、SHA-256 前 12 碼都從交接檔讀出；埠名對照圖讀 b7_netlist.json。
輸入：out/b7_netlist.json、out/phases.json、out/truth_tables.csv、common/draw.py。
輸出：figures/m1/s5_handoff.png（圖 M1-17）、figures/m1/s5_ports.png（圖 M1-18）。
執行：.\lab design\m1_logic\s5_handoff\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.patches import FancyBboxPatch                        # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, ORANGE, GREY, PURPLE, RED, draw_b7   # noqa: E402

STEP = "m1_logic/s5_handoff"
NET = json.loads(paths.OUT(STEP, "b7_netlist.json").read_text(encoding="utf-8"))
PH = json.loads(paths.OUT(STEP, "phases.json").read_text(encoding="utf-8"))
N_ROWS = sum(1 for _ in open(paths.OUT(STEP, "truth_tables.csv"), encoding="utf-8-sig")) - 1


def box(ax, x, y, w, h, title, body, ec, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=fc, ec=ec, lw=1.6))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=11, fontweight="bold", color=ec)
    ax.text(x + 0.15, y + h - 0.65, body, ha="left", va="top", fontsize=9.3, linespacing=1.5)


def arrow(ax, a, b, color=GREY, text=None, ls="-"):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, ls=ls))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, text, ha="center", fontsize=8.8, color=color)


def fig_handoff(path):
    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 5.8)
    ax.axis("off")
    box(ax, 0.2, 1.6, 2.2, 2.6, "M1 的成果", "B7 接線（M1 s2）\n計算鏈（M1 s3）\n五組相位與\n80 組真值表（M1 s4）", PURPLE, "#f3eefa")
    box(ax, 3.4, 3.7, 3.6, 1.9, "b7_netlist.json　固定光路",
        f"{NET['n_waveguides']} 條波導、{len(NET['mzis'])} 顆 MZI 的位置與層\n輸入／輸出的教學編號與佈局埠名\n"
        f"MZI 矩陣慣例、R＝{PH['R']:g}、讀 o2 − o4\n換函數時完全不變", BLUE, "#eef4fb")
    box(ax, 3.4, 1.55, 3.6, 1.9, "phases.json　相位設定檔",
        f"{len(PH['functions'])} 個函數 × 14 個相位（rad）\n各函數的 margin、驗證條件\n相位容許誤差 σ ≤ 0.05 rad\n"
        f"接線 SHA-256：{PH['netlist_sha256'][:12]}…", ORANGE, "#fdf5e6")
    box(ax, 3.4, 0.05, 3.6, 1.25, "truth_tables.csv　驗收答案",
        f"{N_ROWS} 列：函數、x1–x4、目標、P2、P4、ΔP、判讀", GREEN, "#eaf5ee")
    for y in (4.6, 2.5, 0.7):
        arrow(ax, (2.45, 2.9), (3.35, y))
    arrow(ax, (5.2, 3.45), (5.2, 3.68), ORANGE, None, "--")
    ax.text(5.3, 3.53, "SHA-256 綁定", fontsize=8.5, color=ORANGE)
    box(ax, 8.2, 4.0, 4.1, 1.6, "M2 s1　介面規格", "埠名 → 晶片光學埠\n14 個相位 → 14 個控制通道", PURPLE, "white")
    box(ax, 8.2, 2.0, 4.1, 1.6, "M2 s3　電路模擬", "接線＋相位 → PDK 模型重算\n結果要和真值表一致", PURPLE, "white")
    box(ax, 8.2, 0.05, 4.1, 1.6, "M3　佈局", "只用接線：MZI 的位置與層\n相位在晶片做好之後才設定", PURPLE, "white")
    arrow(ax, (7.05, 4.65), (8.15, 4.8), BLUE)
    arrow(ax, (7.05, 2.5), (8.15, 4.4), ORANGE)
    arrow(ax, (7.05, 4.4), (8.15, 3.0), BLUE)
    arrow(ax, (7.05, 2.3), (8.15, 2.7), ORANGE)
    arrow(ax, (7.05, 0.7), (8.15, 2.3), GREEN)
    arrow(ax, (7.05, 4.2), (8.15, 0.9), BLUE)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_ports(path):
    ins = [f"{i['signal']}（輸入 {i['index']}） {i['layout_port']}" for i in NET["inputs"]]
    outs = [f"{o['layout_port']}  {o['name']} {o['role']}" for o in NET["outputs"]]
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    draw_b7(ax, in_labels=ins, out_labels=outs)
    ax.set_xlim(-2.2, 11.6)
    ax.set_title("教學編號與佈局埠名：x1–x4、R ↔ in0–in4；o1–o5 ↔ out0–out4（判讀 o2＝out1、o4＝out3）", fontsize=11)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_handoff(paths.FIG("m1", "s5_handoff.png"))
    fig_ports(paths.FIG("m1", "s5_ports.png"))
    print("寫出 figures/m1/s5_handoff.png、s5_ports.png")


if __name__ == "__main__":
    main()
