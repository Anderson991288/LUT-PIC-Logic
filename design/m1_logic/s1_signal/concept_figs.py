r"""M1 s1：概念示意圖——光路與讀取鏈、光場箭頭的相加與抵消、參考光 R 的作用。

用途：把 and2_readout.py 的計算畫成直覺的圖；數值全部由同一個模型（common/optics.py 的 H 與相位）算出，不另外假設。
  1. 光路與讀取鏈：x1、x2（OOK）→ 相位 φ → MMI → 兩個 PD → 電流相減 → TIA → 比較器（零點）→ y。
  2. 光場箭頭：φ＝π/2 時，每路輸入對上、下輸出貢獻的光場畫成箭頭，頭尾相接得到合成光場與功率。
  3. 參考光 R 的作用（示意）：只有資料光時 ΔP＝2·x1·x2；若 R 貢獻 −1 P_u 的常數項，四組輸入都離開邊界；
     雷射功率降到 40% 時，兩者都等比例縮小，正負號不變。R 的實際電路在 M1 s2 之後設計，這裡只示意常數項的效果。
輸入：and2_readout.py 的 mix()。
輸出：figures/m1/s1_circuit.png（圖 M1-1）、figures/m1/s1_reference.png（圖 M1-2）、figures/m1/s1_phasor.png（圖 M1-3）。
執行：.\lab design\m1_logic\s1_signal\concept_figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup()

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.patches import FancyBboxPatch, Circle                # noqa: E402

import paths                                                         # noqa: E402
from common.optics import H, phase                                   # noqa: E402
from and2_readout import PHI, INPUTS, mix                            # noqa: E402

BLUE, ORANGE, GREEN, RED, GREY = "#2f6fb5", "#c08a2b", "#2e7d4f", "#c0392b", "#5f6368"


def box(ax, x, y, w, h, text, fc="#eef4fb", ec=BLUE, fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x0, y0, x1, y1, color="black"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=1.6, color=color))


def fig_circuit(path):
    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.8)
    ax.axis("off")
    yu, yd = 2.7, 1.3                                              # 上、下兩條波導
    box(ax, 0.05, yu - 0.32, 1.25, 0.64, "x1（OOK）\n0／1，1 ns", fc="#eef4fb")
    box(ax, 0.05, yd - 0.32, 1.25, 0.64, "x2（OOK）\n0／1，1 ns", fc="#eaf5ee", ec=GREEN)
    ax.plot([1.35, 4.6], [yu, yu], color=BLUE, lw=3)
    ax.plot([1.35, 4.6], [yd, yd], color=BLUE, lw=3)
    ax.add_patch(FancyBboxPatch((2.0, yu - 0.13), 0.75, 0.26, boxstyle="round,pad=0.02", fc=ORANGE, ec=ORANGE))
    ax.text(2.37, yu + 0.33, "相位器 φ", ha="center", fontsize=10)
    ax.add_patch(FancyBboxPatch((3.3, yd - 0.35), 0.55, yu - yd + 0.7, boxstyle="round,pad=0.02", fc="#dde6ee", ec=GREY))
    ax.text(3.57, (yu + yd) / 2, "MMI\n50:50", ha="center", va="center", fontsize=10)
    ax.add_patch(FancyBboxPatch((1.7, 0.55), 2.6, 2.95, boxstyle="round,pad=0.05", fc="none", ec="#8e6fb5", lw=1.4, ls="--"))
    ax.text(3.0, 0.7, "混合：光場相加或抵消", ha="center", fontsize=9.5, color="#8e6fb5")
    ax.text(4.2, yu + 0.15, "y上", fontsize=10)
    ax.text(4.2, yd + 0.15, "y下", fontsize=10)
    box(ax, 4.9, yu - 0.3, 1.0, 0.6, "PD上", fc="#fdecea", ec=RED)
    box(ax, 4.9, yd - 0.3, 1.0, 0.6, "PD下", fc="#eef4fb", ec=BLUE)
    ax.text(5.4, yu - 0.55, "量功率 P上", ha="center", fontsize=9, color=GREY)
    ax.text(5.4, yd - 0.55, "量功率 P下", ha="center", fontsize=9, color=GREY)
    ax.add_patch(Circle((6.7, 2.0), 0.22, fc="white", ec="black", lw=1.4))
    ax.text(6.7, 2.0, "−", ha="center", va="center", fontsize=14)
    ax.plot([5.9, 6.7, 6.7], [yu, yu, 2.22], color="black", lw=1.4)
    ax.plot([5.9, 6.7, 6.7], [yd, yd, 1.78], color="black", lw=1.4)
    ax.text(6.25, yu + 0.12, "電流", fontsize=9, color=GREY)
    arrow(ax, 6.92, 2.0, 7.45, 2.0)
    box(ax, 7.5, 1.6, 1.5, 0.8, "TIA\n電流差 → 電壓", fc="white", ec=GREY)
    arrow(ax, 9.0, 2.0, 9.45, 2.0)
    box(ax, 9.5, 1.55, 1.7, 0.9, "比較器\n電壓＞0 → 1\n電壓＜0 → 0", fc="#fdf5e6", ec=ORANGE)
    arrow(ax, 11.2, 2.0, 11.7, 2.0)
    ax.text(11.8, 2.0, "y", fontsize=13, va="center", fontweight="bold")
    ax.text(8.3, 3.05, "讀取：比大小（ΔP＝P上 − P下 的正負）", ha="center", fontsize=10.5, color=RED)
    ax.text(6, 0.15, "OOK：開關鍵控（亮＝1、暗＝0）；PD：光偵測器；TIA：轉阻放大器。兩個 PD 相減稱為平衡偵測，比較器的零點不隨雷射功率改變。",
            ha="center", fontsize=9, color=GREY)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_phasor(path):
    """φ＝π/2：每路輸入對每個輸出的光場貢獻＝(H·phase)[輸出, 輸入]·x。"""
    M = H @ phase(PHI)
    cases = [(0, 1), (1, 0), (1, 1)]
    fig, axs = plt.subplots(2, 3, figsize=(9.5, 7.4))
    lim = 1.6
    for c, (x1, x2) in enumerate(cases):
        for r, name in enumerate(("上", "下")):
            ax = axs[r, c]
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_aspect("equal")
            ax.axhline(0, color="#ccc", lw=0.8)
            ax.axvline(0, color="#ccc", lw=0.8)
            ax.set_xticks([])
            ax.set_yticks([])
            tip = 0j
            k = 0
            n = None
            for j, (x, col, lab) in enumerate(((x1, BLUE, "x1"), (x2, ORANGE, "x2"))):
                if not x:
                    continue
                v = M[r, j] * x
                if n is None:
                    n = 1j * v / abs(v)                            # 以第一支箭頭的垂直方向為準
                sh = 0.08 * n if k else 0                          # 第二支箭頭略為平移，只為了不和第一支重疊
                a, b = tip + sh, tip + v + sh
                ax.annotate("", xy=(b.real, b.imag), xytext=(a.real, a.imag),
                            arrowprops=dict(arrowstyle="-|>", lw=2.6, color=col, mutation_scale=16))
                m = (a + b) / 2 + (0.3 if k else -0.25) * n       # 兩支的標籤分在箭頭兩側
                ax.text(m.real, m.imag, lab, color=col, fontsize=10.5, ha="center", va="center", fontweight="bold")
                tip += v
                k += 1
            if x1 and x2:
                if abs(tip) > 1e-9:
                    ax.annotate("", xy=(tip.real, tip.imag), xytext=(0, 0),
                                arrowprops=dict(arrowstyle="-|>", lw=2.0, ls="--", color=GREEN, mutation_scale=16))
                else:
                    ax.plot(0, 0, "o", color=GREEN, ms=8)
            p = mix(x1, x2)[2 + r]
            ax.set_title(f"x1x2＝{x1}{x2}，{name}方輸出\n|y{name}|＝{abs(tip):.2f} → P{name}＝{p:.1f}", fontsize=10.5)
    fig.suptitle("φ＝π/2 時每路光對輸出的光場箭頭（頭尾相接相加；綠色＝合成光場）\n"
                 "11：上方兩支箭頭同向 → 相加變亮；下方兩支反向 → 抵消變暗", fontsize=11.5)
    fig.text(0.5, 0.015, "箭頭長度＝光場大小，方向＝相位（向右 0°、向上 90°、向左 180°）。箭頭方向不是光在晶片上的行進方向。",
             ha="center", fontsize=9.5, color=GREY)
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.subplots_adjust(hspace=0.42)                               # 第二排標題不壓到第一排的框
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_reference(path):
    labels = ["00", "01", "10", "11"]
    data_only = np.array([mix(x1, x2)[4] for x1, x2 in INPUTS])
    with_r = data_only - 1.0                                       # 示意：R 貢獻 −1 P_u 的常數項
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for ax, (title, vals) in zip(axs, (("只有資料光：ΔP＝2·x1·x2", data_only),
                                       ("加入參考光 R（示意：常數項 −1）", with_r))):
        x = np.arange(4)
        for s, alpha, lab in ((1.0, 1.0, "雷射功率 100%"), (0.4, 0.45, "雷射功率 40%")):
            v = vals * s
            off = -0.18 if s == 1.0 else 0.18
            cols = [GREY if abs(t) < 1e-9 else (GREEN if t > 0 else BLUE) for t in v]
            ax.bar(x + off, v, width=0.34, color=cols, alpha=alpha, label=lab)
            for xi, t in zip(x + off, v):
                if abs(t) < 1e-9:
                    ax.text(xi, 0.08, "邊界", ha="center", fontsize=8.5, color=RED)
        ax.axhline(0, color="black", lw=1)
        ax.set_xticks(x, labels)
        ax.set_xlabel("x1x2")
        ax.set_title(title, fontsize=11)
        ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel("ΔP（P$_u$）")
    axs[0].legend(fontsize=8.5, loc="upper left")
    fig.text(0.5, -0.04, "綠＝正（判 1）、藍＝負（判 0）、紅字「邊界」＝ΔP 等於 0。深色＝功率 100%、淺色＝40%：整體縮小但正負號不變。"
             "R 的實際電路在後面的步驟設計，這裡只示意常數項的效果。", ha="center", fontsize=9.5, color=GREY)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_circuit(paths.FIG("m1", "s1_circuit.png"))
    fig_phasor(paths.FIG("m1", "s1_phasor.png"))
    fig_reference(paths.FIG("m1", "s1_reference.png"))
    print("寫出 figures/m1/s1_circuit.png、s1_phasor.png、s1_reference.png")


if __name__ == "__main__":
    main()
