r"""LUT4 s0（M1 s1 ②）：圖——同一組位元以強度編碼（OOK）與 E+／E− 二相位編碼送出時的光波、功率與判讀。

用途：光訊號是約 193 THz（1550 nm）的載波；「光場 0／1、+1／−1」指的是載波的複數振幅（包絡）：
  OOK：位元 1 → 載波 E·cos(ωt)，位元 0 → 沒有光。
  E±：位元 0 → E·cos(ωt)，位元 1 → E·cos(ωt＋π)＝−E·cos(ωt)，振幅不變、只翻轉相位。
  PD 只反應對許多光週期平均後的功率（包絡的平方）。圖中每個位元只畫 5 個載波週期以便觀察（實際 1 GHz 位元約有 19 萬個週期）。
  判讀用 M1 s1 ② 的 AND2 光路（上臂相位 φ＝π/2、一顆理想 50:50 MMI）：ΔP＝2·E1·E2·sinφ（E1、E2 為兩路包絡）。
  OOK：ΔP＝2·x1·x2，ΔP＞1 判 1 → AND。E±：ΔP＝2·s1·s2＝±2，ΔP＞0 判 1 → XNOR（兩路相同判 1）。
  8 個位元依序為 00、01、10、11、00、01、10、11（x1x2）。
輸入：無（解析式）。
輸出：figures/lut4v2/s1_encoding.png。
執行：.\lab design\lut4v2\s0_basics\encoding.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, RED               # noqa: E402

BITS = [(0, 0), (0, 1), (1, 0), (1, 1)] * 2
X1 = np.array([b[0] for b in BITS], float)
X2 = np.array([b[1] for b in BITS], float)
CYC = 5                                                              # 每個位元畫的載波週期數（示意）
T = np.linspace(0, len(BITS), len(BITS) * 400, endpoint=False)


def stairs(ax, v, **kw):
    t = np.arange(len(v) + 1)
    ax.step(t, np.r_[v, v[-1]], where="post", **kw)


def wave(ax, env, color, lab, phase=False):
    """載波 env(t)·cos(ωt)（實線）與包絡（虛線）；phase＝True 時在每個位元上方標出相位 0／π。"""
    e = env[np.floor(T).astype(int)]
    ax.plot(T, e * np.cos(2 * np.pi * CYC * T), color=color, lw=0.9)
    stairs(ax, env, color=color, lw=1.6, ls="--")
    ax.set_ylim(-1.6, 1.9)
    for k, v in enumerate(env):
        if phase:
            ax.text(k + 0.5, 1.45, "相位 0" if v > 0 else "相位 π", ha="center", fontsize=8, color=color if v > 0 else RED)
        elif v > 0:
            ax.text(k + 0.5, 1.45, "有光", ha="center", fontsize=8, color=color)
    ax.set_ylabel(lab, fontsize=9.5)


def column(axs, E1, E2, thr, title, logic, note1, phase):
    wave(axs[0], E1, BLUE, "x1 的光波", phase)
    wave(axs[1], E2, ORANGE, "x2 的光波", phase)
    axs[0].set_title(title + "\n" + note1, fontsize=10.5)
    stairs(axs[2], np.abs(E1) ** 2 + 0.03, color=BLUE, lw=2.0, label="x1")
    stairs(axs[2], np.abs(E2) ** 2 - 0.03, color=ORANGE, lw=2.0, ls="--", label="x2")
    axs[2].set_ylim(-0.3, 1.5); axs[2].set_ylabel("PD 讀到的功率（Pᵤ）", fontsize=9.5)
    axs[2].legend(fontsize=8, loc="lower right", ncol=2)
    dP = 2 * E1 * E2                                                  # φ＝π/2：sinφ＝1
    y = (dP > thr).astype(int)
    stairs(axs[3], dP, color=GREEN, lw=2.2, label="ΔP＝P上−P下")
    axs[3].axhline(thr, color=RED, lw=1.2, ls=":", label=f"門檻 {thr:g}")
    axs[3].set_ylim(-3.7, 2.9); axs[3].set_ylabel("ΔP（Pᵤ）", fontsize=9.5)
    axs[3].legend(fontsize=8, loc="lower right", ncol=2)
    for k, v in enumerate(y):
        axs[3].text(k + 0.5, 2.3, f"y＝{v}", ha="center", fontsize=8.5, color=RED if v else GREY, fontweight="bold" if v else None)
    axs[3].set_xlabel(f"輸入 x1x2（每格一個位元）；判讀結果為 {logic}")
    for a in axs:
        a.set_xlim(0, len(BITS))
        a.set_xticks(np.arange(len(BITS)) + 0.5)
        a.set_xticklabels([f"{p}{q}" for p, q in BITS], fontsize=9)
        for k in range(1, len(BITS)):
            a.axvline(k, color="#d1d5db", lw=0.6)
        a.axhline(0, color="k", lw=0.5)


def main():
    fig, ax = plt.subplots(4, 2, figsize=(12.5, 8.6), sharex=True)
    column(ax[:, 0], X1, X2, 1.0, "強度編碼（OOK）：位元 1 有光、位元 0 沒有光", "AND", "實線＝光波（載波，示意）；虛線＝包絡：0 或 1", False)
    column(ax[:, 1], 1 - 2 * X1, 1 - 2 * X2, 0.0, "E+／E− 二相位：一直有光，位元 1 時相位翻轉 π", "XNOR", "實線＝光波（載波，示意）；虛線＝包絡：+1 或 −1", True)
    fig.tight_layout()
    out = paths.FIG("lut4v2", "s1_encoding.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("寫出 figures/lut4v2/s1_encoding.png")


if __name__ == "__main__":
    main()
