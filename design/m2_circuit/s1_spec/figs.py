r"""M2 s1：圖——晶片與外部設備的邊界、14 個相位控制通道的對應、介面容許範圍。

用途：所有標籤（埠名、通道、PAD 編號、R 範圍、功率）都從 spec.json、tolerance.json 讀出；B7 接線用 common/draw.py。
輸入：out/spec.json、out/tolerance.json。
輸出：figures/m2/s1_boundary.png（圖 M2-1）、figures/m2/s1_channels.png（圖 M2-2）、figures/m2/s1_tolerance.png（圖 M2-3）。
執行：.\lab design\m2_circuit\s1_spec\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch                        # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, ORANGE, GREY, PURPLE, RED, draw_b7   # noqa: E402

STEP = "m2_circuit/s1_spec"
SPEC = json.loads(paths.OUT(STEP, "spec.json").read_text(encoding="utf-8"))
TOL = json.loads(paths.OUT(STEP, "tolerance.json").read_text(encoding="utf-8"))


def box(ax, x, y, w, h, text, ec=GREY, fc="white", fs=9.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else None)


def arrow(ax, a, b, color=GREY, lw=1.5):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def fig_boundary(path):
    fig, ax = plt.subplots(figsize=(13, 6.2))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    # 晶片
    ax.add_patch(FancyBboxPatch((4.3, 1.4), 4.4, 4.8, boxstyle="round,pad=0.05", fc="#f3eefa", ec=PURPLE, lw=2))
    ax.text(6.5, 5.85, "PIC（本課程設計）", ha="center", fontsize=11.5, fontweight="bold", color=PURPLE)
    box(ax, 5.3, 2.4, 2.4, 1.8, "B7\n7 顆 MZI\n14 個 heater", ec=PURPLE, fc="white", fs=10)
    ins = [p for p in SPEC["optical_ports"] if p["direction"] == "輸入"]
    outs = [p for p in SPEC["optical_ports"] if p["direction"] == "輸出"]
    for k, p in enumerate(ins):
        y = 4.3 - 0.45 * k
        ax.add_patch(FancyBboxPatch((4.35, y - 0.12), 0.45, 0.24, boxstyle="round,pad=0.01", fc=BLUE, ec=BLUE))
        ax.text(4.95, y, p["port"], fontsize=8, va="center")
        arrow(ax, (5.3, y), (5.3 + 0.01, y))
    for k, p in enumerate(outs):
        y = 4.3 - 0.45 * k
        ax.add_patch(FancyBboxPatch((8.2, y - 0.12), 0.45, 0.24, boxstyle="round,pad=0.01",
                                    fc=RED if p["note"] == "判讀" else GREY, ec="none"))
        ax.text(7.75, y, p["port"], fontsize=8, va="center")
    ax.text(4.55, 1.75, "EC×5\n西緣", ha="center", fontsize=8.5, color=BLUE)
    ax.text(8.45, 1.75, "EC×5\n東緣", ha="center", fontsize=8.5, color=GREY)
    # PAD：都在晶片上（紫框內）；14 個訊號 PAD 與共用 GND PAD 分開畫。GND PAD 的實際數量到 M3 s3 才決定（至少 1 個），這裡畫一塊代表
    for k in range(14):
        ax.add_patch(FancyBboxPatch((5.45 + 0.19 * k, 5.15), 0.14, 0.22, boxstyle="square,pad=0", fc=ORANGE, ec="none"))
    ax.text(6.7, 5.46, "14 個訊號 PAD", ha="center", fontsize=9, color=ORANGE)
    ax.add_patch(FancyBboxPatch((4.6, 5.15), 0.56, 0.22, boxstyle="square,pad=0", fc=GREY, ec="none"))
    ax.text(4.88, 5.26, "GND", ha="center", va="center", fontsize=7.5, color="white", fontweight="bold")
    ax.text(4.88, 5.46, "共用 GND PAD", ha="center", fontsize=9, color=GREY)
    # 外部：光源端
    box(ax, 0.2, 3.4, 1.6, 0.9, "雷射\n1550 nm", ec=GREEN)
    box(ax, 2.1, 3.4, 1.7, 0.9, "分光＋調變\nx1–x4（0／1）", ec=GREEN)
    box(ax, 2.1, 2.1, 1.7, 0.9, "參考光 R\n振幅固定", ec=GREEN)
    arrow(ax, (1.8, 3.85), (2.1, 3.85), GREEN)
    arrow(ax, (1.0, 3.4), (2.1, 2.55), GREEN)
    arrow(ax, (3.8, 3.85), (4.35, 3.85), GREEN, 2)
    arrow(ax, (3.8, 2.55), (4.35, 2.55), GREEN, 2)
    ax.text(2.95, 1.9, f"同一顆雷射（相干）\nR＝{TOL['R_range_all'][0]:g}–{TOL['R_range_all'][1]:g}\n輸入相位誤差 ≤ {TOL['input_phase_sigma_ok']:g} rad",
            ha="center", va="top", fontsize=8.8, color=GREEN)
    # 外部：接收端
    box(ax, 9.3, 3.55, 1.5, 0.75, "PD o2、PD o4", ec=RED)
    box(ax, 11.1, 3.55, 1.7, 0.75, "相減→TIA→比較器\nΔP＞0 判 1", ec=RED)
    box(ax, 9.3, 2.3, 1.5, 0.75, "監看 PD\no1、o3、o5", ec=GREY)
    arrow(ax, (8.7, 3.95), (9.3, 3.95), RED, 2)
    arrow(ax, (10.8, 3.95), (11.1, 3.95), RED)
    arrow(ax, (8.7, 2.7), (9.3, 2.7), GREY, 2)
    # 外部：電氣
    box(ax, 9.3, 4.89, 3.5, 0.75, f"heater 驅動 14 通道\n0–2π，誤差 ≤ 0.05 rad；P_π≈{TOL['P_pi_mW']:g} mW", ec=ORANGE)
    arrow(ax, (9.3, 5.26), (8.1, 5.26), ORANGE)
    ax.text(6.5, 0.6, "紫框內是晶片；框外是外部設備（光源、調變、驅動、接收判讀），本課程只規定它們和晶片之間的介面。",
            ha="center", fontsize=9.5, color=GREY)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_channels(path):
    ch = {(c["mzi"], c["kind"]): c for c in SPEC["phase_channels"]}

    def lab(k):
        t, p = ch[(f"MZI-{k}", "theta")], ch[(f"MZI-{k}", "phi")]
        return f"MZI-{k}\n{t['heater']} θ{k}→{t['pad']}\n{p['heater']} φ{k}→{p['pad']}"

    ins = [f"{p['signal']}  {p['port']}（EC）" for p in SPEC["optical_ports"] if p["direction"] == "輸入"]
    outs = [f"{p['port']}（EC）  {p['signal']} {p['note'][:2]}" for p in SPEC["optical_ports"] if p["direction"] == "輸出"]
    fig, ax = plt.subplots(figsize=(12.5, 5.0))
    draw_b7(ax, box_label=lab, in_labels=ins, out_labels=outs, fs=9.5)
    ax.set_xlim(-2.6, 12.2)
    ax.set_title("14 個相位控制通道：每個相位一個 heater（H01–H14）、一個訊號 PAD（P01–P14），回流共用 GND", fontsize=11)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_tol(path):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 3.8), gridspec_kw=dict(width_ratios=[1.2, 1]))
    names = list(TOL["R_range_per_function"])
    for k, n in enumerate(names):
        lo, hi = TOL["R_range_per_function"][n]
        a1.barh(k, hi - lo, left=lo, color=GREEN if n != "AND4" else ORANGE, height=0.55)
        at_lo, at_hi = lo <= TOL["R_scan"][0] + 1e-9, hi >= TOL["R_scan"][1] - 1e-9
        note = {(True, True): "（兩端都到掃描邊界）", (True, False): "（下限到掃描邊界）",
                (False, True): "（上限到掃描邊界）", (False, False): ""}[(at_lo, at_hi)]
        a1.text(hi + 0.03, k, f"{lo:g}–{hi:g}{note}", va="center", fontsize=8.5)
    lo, hi = TOL["R_range_all"]
    a1.axvspan(lo, hi, color=BLUE, alpha=0.12)
    a1.axvline(TOL["R_nominal"], color=RED, ls="--", lw=1.2)
    a1.text(TOL["R_nominal"], -0.62, f" 設計值 R＝{TOL['R_nominal']:g}", color=RED, fontsize=9, va="center")
    a1.set_ylim(-0.85, len(names) - 0.4)
    a1.set_yticks(range(len(names)), names)
    a1.set_xlim(TOL["R_scan"][0], TOL["R_scan"][1] + 1.6)
    a1.set_xlabel("參考光振幅 R（√P$_u$）；相位固定")
    a1.set_title(f"80 組都判對的 R 範圍：{lo:g}–{hi:g}（藍底）", fontsize=10.5)
    a1.grid(axis="x", alpha=0.3)
    P = TOL["heater_power"]
    a2.bar(range(len(P)), [v["total_mW"] for v in P.values()], color=ORANGE)
    for k, v in enumerate(P.values()):
        a2.text(k, v["total_mW"] + 5, f"{v['total_mW']:.0f}", ha="center", fontsize=9)
    a2.axhline(TOL["worst_case_total_mW"], color=RED, ls="--", lw=1.2)
    a2.text(len(P) - 0.5, TOL["worst_case_total_mW"] + 6, f"最壞情況 {TOL['worst_case_total_mW']:g} mW", ha="right", color=RED, fontsize=9)
    a2.set_xticks(range(len(P)), list(P))
    a2.set_ylim(0, TOL["worst_case_total_mW"] * 1.15)
    a2.set_ylabel("14 個 heater 總功率（mW）")
    a2.set_title(f"heater 功率（P_π＝{TOL['P_pi_mW']:g} mW；未含製程相位偏移與 MMI 損耗）", fontsize=10.5)
    a2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_boundary(paths.FIG("m2", "s1_boundary.png"))
    fig_channels(paths.FIG("m2", "s1_channels.png"))
    fig_tol(paths.FIG("m2", "s1_tolerance.png"))
    print("寫出 figures/m2/s1_boundary.png、s1_channels.png、s1_tolerance.png")


if __name__ == "__main__":
    main()
