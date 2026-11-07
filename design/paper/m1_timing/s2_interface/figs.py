r"""論文 M1 s2：圖——發射端消光比與 margin（沿用原相位 vs 重新求相位）。

用途：決定輸入介面規格中最關鍵的一項（消光比）；數字讀 out/interface_v2.json。
輸入：out/interface_v2.json。
輸出：figures/paper/m1/s2_er.png（圖 M1-4）。
執行：.\lab design\paper\m1_timing\s2_interface\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "paper/m1_timing/s2_interface"
S = json.loads(paths.OUT(STEP, "interface_v2.json").read_text(encoding="utf-8"))


def fig_er():
    er = np.array(S["er_scan"]["er_db"])
    cols = {"AND2": BLUE, "OR2": GREEN, "XOR2": RED, "AND4": PURPLE, "OR4": ORANGE}
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    for fn, c in cols.items():
        m0 = S["margin_ideal"][fn]
        ax.plot(er, np.array(S["er_scan"]["margin_fixed"][fn]) / m0, color=c, ls="--", lw=1.3)
        ax.plot(er, np.array(S["er_scan"]["margin_resolved"][fn]) / m0, color=c, lw=2.2, marker="o", ms=4, label=fn)
    keep = S["margin_keep"]
    a0 = 10 ** (-er / 20)
    ax.plot(er, 1 - a0, color="black", lw=1, ls=(0, (1, 1)))
    ax.plot(er, (1 - a0) ** 2, color="black", lw=1, ls=(0, (1, 1)))
    lead = dict(arrowstyle="-", color="black", lw=0.7, shrinkA=1, shrinkB=2)
    white = dict(fc="white", ec="none", pad=1.0)
    ax.annotate("近似 (1−a₀)：一次項函數", xy=(12.5, 1 - 10 ** (-12.5 / 20)), xytext=(10.4, 1.01), fontsize=9, va="center",
                arrowprops=lead, bbox=white)
    ax.annotate("近似 (1−a₀)²：XOR2", xy=(17.6, (1 - 10 ** (-17.6 / 20)) ** 2), xytext=(16.7, 0.33), fontsize=9, va="center",
                arrowprops=lead, bbox=white)
    ax.axhline(keep, color=GREY, ls=":", lw=1.3)
    ax.text(19.4, keep + 0.015, f"保留 {keep:.0%} margin", color=GREY, fontsize=9.5, ha="right", va="bottom")
    ax.axvline(S["er_required_db"], color=RED, lw=1.2)
    ax.text(S["er_required_db"] + 0.4, 0.15, f"重新求相位：\n需要 ≥ {S['er_required_db']:g} dB", color=RED, fontsize=9.5)
    ax.axvline(S["er_fixed_db"], color=GREY, lw=1.2, ls="--")
    ax.text(S["er_fixed_db"] - 0.4, 0.15, f"沿用原相位：\n需要 ≥ {S['er_fixed_db']:g} dB", color=GREY, fontsize=9.5, ha="right")
    ax.set_xlim(10, 40)
    ax.set_ylim(-0.6, 1.08)
    ax.set_xlabel("發射端消光比 ER（dB；「0」時殘留光功率＝「1」的 10^(−ER/10)）")
    ax.set_ylabel("margin ／ 理想 margin")
    ax.set_title("消光比需求：「0」不是全暗時，殘留光和參考光干涉；虛線是沿用原相位，實線是依殘留重新求相位\n"
                 "殘留是固定的偏移，只調 heater 重新求相位就能吸收到解析近似（黑點線）", fontsize=11)
    ax.legend(loc="lower right", fontsize=9.5, title="實線＝重新求相位", title_fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s2_er.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_er()
    print("寫出 figures/paper/m1/s2_er.png")
