r"""論文 M1 s1：圖——時序（skew 來源與允許值）、相位（溫度容許與路徑長度）、功率（由接收端反推到光纖）。

用途：三張圖各回答一項預算「需要多少、現在有多少」；數字全部讀 out/budget.json。
輸入：out/budget.json。
輸出：figures/paper/m1/s1_skew.png（圖 M1-1）、figures/paper/m1/s1_phase.png（圖 M1-2）、figures/paper/m1/s1_power.png（圖 M1-3）。
執行：.\lab design\paper\m1_timing\s1_budget\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.ticker import FuncFormatter                          # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREY, ORANGE, RED                      # noqa: E402

STEP = "paper/m1_timing/s1_budget"
B = json.loads(paths.OUT(STEP, "budget.json").read_text(encoding="utf-8"))
PLAIN = FuncFormatter(lambda v, _: f"{v:g}")                         # 對數刻度直接寫數字（避免上標負號缺字）


def fig_skew():
    t = B["timing"]
    rows = [("晶片內：每多經過一顆 MZI", t["column_extra_ps"], BLUE),
            (f"晶片內：最差的 MZI 輸入（{t['worst_mzi']}）", t["worst_skew_ps"], BLUE),
            ("晶片內：5 個輸出之間（只有 o2、o4 判讀）", t["outputs_spread_ps"], "#8fb3d9")]
    rows += [("片外：" + o["item"], o["skew_ps"], ORANGE) for o in t["offchip"]]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    y = np.arange(len(rows))
    ax.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=0.6)
    for k, r in enumerate(rows):
        ax.text(r[1] * 1.12, k, f"{r[1]:.3g} ps", va="center", fontsize=9.5)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=10)
    ax.set_xscale("log")
    ax.set_xlim(0.05, 400)
    ax.xaxis.set_major_formatter(PLAIN)
    a, ui = t["skew_allow_ps"], t["ui_ps"]
    ax.axvline(a, color=RED, ls="--", lw=1.6)
    ax.text(a * 1.06, len(rows) - 1.5, f"允許的 skew\n（一階估計）\n{a:.3g} ps", color=RED, fontsize=9.5, va="center")
    ax.axvline(ui, color=GREY, ls=":", lw=1.4)
    ax.text(ui * 1.06, -0.45, f"1 UI＝{ui:g} ps", color=GREY, fontsize=9.5, va="bottom")
    ax.set_xlabel("到達時間差（ps，對數刻度）")
    ax.set_title(f"10 Gb/s 的時序預算：晶片內最差 {t['worst_skew_ps']:.3g} ps，只占允許值的 {t['worst_fraction_of_allow']:.1%}；"
                 f"判讀用的 o2、o4 所有路徑相差 ≤ {t['readout']['spread_ps']:.3g} ps\n片外光纖或 RF 線差 1 cm 就超過允許值", fontsize=11)
    ax.grid(axis="x", which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s1_skew.png"), dpi=160)
    plt.close(fig)


def fig_phase():
    p = B["phase"]
    sig = p["det_rad"]                                               # 確定性偏差的預算（margin 保留 90%）
    L = np.logspace(-6, 1, 200)
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.loglog(L, sig / (p["k_si_rad_mK"] * L), color=BLUE, lw=2, label=f"矽波導（{p['k_si_rad_mK']:g} rad/(m·K)）")
    ax.loglog(L, sig / (p["k_fiber_rad_mK"] * L), color=ORANGE, lw=2, label=f"光纖（{p['k_fiber_rad_mK']:g} rad/(m·K)）")
    for c, dx in zip(p["cases"], (1.6, 1.6, 0.06)):
        col = BLUE if c["medium"] == "矽波導" else ORANGE
        ax.plot(c["L_m"], c["dT_allow_K"], "o", ms=9, color=col, mec="black")
        ax.annotate(f"{c['case']}\n溫度要穩在 {c['dT_allow_K']:.2g} K 以內", (c["L_m"], c["dT_allow_K"]),
                    xytext=(c["L_m"] * dx, c["dT_allow_K"] * (6 if dx > 1 else 0.12)), fontsize=9.5,
                    ha="left" if dx > 1 else "right", arrowprops=dict(arrowstyle="->", color="black", lw=0.8))
    ax.axhspan(0.1, 1, color="#eeeeee", zorder=0)
    ax.text(2e-6, 0.3, "一般實驗室的溫度變化（約 0.1–1 K）", fontsize=9.5, color="#555555", va="center")
    ax.set_xlim(1e-6, 10)
    ax.set_ylim(1e-4, 1e4)
    ax.xaxis.set_major_formatter(PLAIN)
    ax.yaxis.set_major_formatter(PLAIN)
    ax.set_xlabel("造成相位差的路徑長度 L（m）：長度差（同溫），或整段溫度不同的長度")
    ax.set_ylabel(f"相對相位偏差 ≤ {sig:g} rad\n（margin 保留 90%）的容許溫度變化（K）")
    ax.set_title("相位預算：晶片內的路徑差幾乎不受溫度影響；5 根光纖各自送光時，\n要把光纖溫差控制在 mK 等級，實際做不到 → 需要相位追蹤", fontsize=11)
    ax.legend(loc="upper right", fontsize=9.5)
    ax.grid(which="major", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s1_phase.png"), dpi=160)
    plt.close(fig)


def fig_power():
    w = B["power"]
    st = w["steps"]
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    base = -20
    cols = [GREY, GREY, GREY, BLUE, ORANGE, ORANGE, RED]
    for k, (name, v) in enumerate(st):
        ax.bar(k, v - base, bottom=base, color=cols[k], width=0.62)
        ax.text(k, v + 0.4, f"{v:+.1f} dBm", ha="center", fontsize=9.5)
        if 0 < k < 5:
            d = v - st[k - 1][1]
            ax.annotate("", xy=(k - 0.33, v), xytext=(k - 0.67, st[k - 1][1]), arrowprops=dict(arrowstyle="->", color="black", lw=0.8))
            ax.text(k - 0.62, (v + st[k - 1][1]) / 2 + 0.9, f"{d:+.1f} dB", ha="right", fontsize=8.5)
    ax.set_xticks(range(len(st)), [s[0].replace("P_u", "$P_u$").replace("→", "\n→").replace("（", "\n（") for s in st], fontsize=9)
    ax.set_ylim(base, 12)
    ax.set_ylabel("功率（dBm）")
    ax.set_title(f"功率預算：最難的函數（{w['margin_function']}，margin {w['margin_min']:g}）每根資料光纖要 {w['pu_fiber_dbm']:+.1f} dBm，"
                 f"\n5 根合計 {w['total_dbm']:+.1f} dBm → 在假設的接收端下功率可滿足", fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s1_power.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_skew()
    fig_phase()
    fig_power()
    print("寫出 figures/paper/m1/s1_skew.png、s1_phase.png、s1_power.png")
