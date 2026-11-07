r"""M1 s4：圖——同一串輸入、五組相位得到五種輸出（可程式化）、五個函數的 ΔP 真值表、14 個相位設定、相位誤差的影響。

用途：把 gates.json 畫成圖；波形圖的 ΔP 直接用各函數的相位重新計算。
輸入：out/gates.json、common/mzi.py。
輸出：figures/m1/s4_program.png（圖 M1-13）、figures/m1/s4_truth.png（圖 M1-14）、
      figures/m1/s4_phases.png（圖 M1-15）、figures/m1/s4_robust.png（圖 M1-16）。
執行：.\lab design\m1_logic\s4_gates\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, RED, GREY, ORANGE, PURPLE        # noqa: E402
from common.mzi import R_AMP, READ, b7_matrix                         # noqa: E402

G = json.loads(paths.OUT("m1_logic/s4_gates", "gates.json").read_text(encoding="utf-8"))
F = G["funcs"]
NAMES = list(F)
SEQ = ["0000", "1000", "0100", "1100", "1011", "0111", "1111", "0010", "1101", "0001"]   # 示範輸入串（含 x3、x4 有光的字）


def dP_of(name, word):
    U = b7_matrix(F[name]["theta"], F[name]["phi"])
    P = np.abs(U @ np.array([int(c) for c in word] + [R_AMP], dtype=complex)) ** 2
    return float(P[READ[0]] - P[READ[1]])


def target(name, word):
    return next(r["target"] for r in F[name]["rows"] if r["bits"] == word)


def fig_program(path):
    n = len(SEQ)
    fig, axs = plt.subplots(4 + len(NAMES), 1, figsize=(11, 9.6), sharex=True,
                            gridspec_kw=dict(height_ratios=[0.5] * 4 + [1.0] * len(NAMES)))
    t = np.arange(n + 1)
    for j in range(4):
        v = [int(w[j]) for w in SEQ]
        axs[j].step(t, v + [v[-1]], where="post", color=BLUE if j < 2 else GREY, lw=2)
        axs[j].set_ylim(-0.3, 1.3)
        axs[j].set_yticks([])
        axs[j].set_ylabel(f"x{j + 1}", rotation=0, ha="right", va="center")
    for ax, name in zip(axs[4:], NAMES):
        d = [dP_of(name, w) for w in SEQ]
        ax.step(t, d + [d[-1]], where="post", color=PURPLE, lw=1.8)
        ax.axhline(0, color="black", lw=0.8)
        lim = max(abs(x) for x in d) * 1.35
        ax.set_ylim(-lim, lim)
        ax.set_yticks([])
        ax.set_ylabel(f"{name}\n相位組", rotation=0, ha="right", va="center", fontsize=10)
        for i, (w, x) in enumerate(zip(SEQ, d)):
            ok = int(x > 0) == target(name, w)
            ax.text(i + 0.5, lim * 0.62 if x < 0 else -lim * 0.62, str(int(x > 0)), ha="center", va="center",
                    fontsize=12, fontweight="bold", color=GREEN if ok else RED)
        ax.grid(axis="x", alpha=0.3)
    axs[-1].set_xticks(np.arange(n) + 0.5, SEQ)
    axs[-1].set_xlabel("同一串輸入字 x1x2x3x4（每格一個位元時間）；紫線＝ΔP，數字＝判讀，綠色＝與目標函數相同")
    fig.suptitle("同一顆 B7、同一串輸入，只換 14 個相位：輸出變成五種不同的邏輯函數", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_truth(path):
    fig, axs = plt.subplots(len(NAMES), 1, figsize=(11, 10), sharex=True)
    words = [r["bits"] for r in F[NAMES[0]]["rows"]]
    for ax, name in zip(axs, NAMES):
        rows = F[name]["rows"]
        d = [r["dP"] for r in rows]
        cols = [GREEN if r["target"] else BLUE for r in rows]
        ax.bar(range(16), d, color=cols)
        m = F[name]["margin"]
        ax.axhline(m, color=ORANGE, ls="--", lw=1)
        ax.axhline(-m, color=ORANGE, ls="--", lw=1)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_ylabel(f"{name}\nΔP（P$_u$）", fontsize=10)
        ax.text(15.6, m, f" ±margin {m:.2f}", va="bottom", fontsize=9, color=ORANGE)
        ax.grid(axis="y", alpha=0.3)
    axs[-1].set_xticks(range(16), words, rotation=45)
    axs[-1].set_xlabel("輸入 x1x2x3x4（二輸入函數只看 x1x2，x3、x4 任意）；綠＝目標 1，藍＝目標 0")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_phases(path):
    labels = [f"θ{k}" for k in range(1, 8)] + [f"φ{k}" for k in range(1, 8)]
    M = np.array([F[n]["theta"] + F[n]["phi"] for n in NAMES]) / np.pi
    fig, ax = plt.subplots(figsize=(11.5, 3.4))
    im = ax.imshow(M, cmap="twilight", vmin=0, vmax=2, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8.5,
                    color="white" if 0.4 < M[i, j] < 1.6 else "black")
    ax.set_xticks(range(14), labels)
    ax.set_yticks(range(len(NAMES)), NAMES)
    ax.axvline(6.5, color="white", lw=2)
    ax.set_title("五個函數的 14 個相位（單位 π，0～2）：接線不變，只有這張表不同", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.02, label="相位（π）")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_robust(path):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    sig = G["sigmas"]
    for name, c in zip(NAMES, (BLUE, GREEN, RED, ORANGE, PURPLE)):
        ax.plot(sig, [100 * F[name]["phase_error_pass"][str(s)] for s in sig], "o-", color=c, label=name)
    ax.set_xscale("log")
    ax.set_xticks(sig, [f"{s:g}" for s in sig])
    ax.set_xlabel("每個相位的誤差標準差 σ（rad）")
    ax.set_ylabel("真值表全對的比例（%）")
    ax.set_title(f"14 個相位同時有誤差時（各 {G['trials']} 次）", fontsize=11)
    ax.set_ylim(80, 101)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_program(paths.FIG("m1", "s4_program.png"))
    fig_truth(paths.FIG("m1", "s4_truth.png"))
    fig_phases(paths.FIG("m1", "s4_phases.png"))
    fig_robust(paths.FIG("m1", "s4_robust.png"))
    print("寫出 figures/m1/s4_program.png、s4_truth.png、s4_phases.png、s4_robust.png")


if __name__ == "__main__":
    main()
