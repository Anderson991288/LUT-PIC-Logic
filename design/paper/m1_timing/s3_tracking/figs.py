r"""論文 M1 s3：圖——補償與量測（漂移前後的 margin、兩種量法能分辨幾個相位）、擺動幅度的取捨。

用途：數字讀 out/tracking.json。
輸入：out/tracking.json。
輸出：figures/paper/m1/s3_track.png（圖 M1-5）、figures/paper/m1/s3_dither.png（圖 M1-6）。
執行：.\lab design\paper\m1_timing\s3_tracking\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter           # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, RED               # noqa: E402

STEP = "paper/m1_timing/s3_tracking"
S = json.loads(paths.OUT(STEP, "tracking.json").read_text(encoding="utf-8"))
F = S["functions"]
FN = list(F)
PLAIN = FuncFormatter(lambda v, _: f"{v:g}")


def fig_track():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw=dict(width_ratios=[1.5, 1]))
    rng = np.random.default_rng(1)
    for i, fn in enumerate(FN):
        r = F[fn]
        for vals, dx, c, lab in ((r["comp_before"], -0.25, RED, "漂移後（不補償）"),
                                 (r["comp_after"], 0.0, BLUE, "只調 φ（已知漂移）"),
                                 (None, 0.25, GREEN, "擺動量測＋只調 φ")):
            if vals is None:
                a1.plot(i + dx, r["comp_est_min"], "v", color=c, ms=9, label=lab if i == 0 else None)
                continue
            a1.scatter(i + dx + rng.uniform(-0.06, 0.06, len(vals)), vals, s=14, color=c, alpha=0.8, label=lab if i == 0 else None)
    a1.axhline(0, color="black", lw=0.8)
    a1.axhline(1, color=GREY, ls=":", lw=1)
    a1.set_xticks(range(len(FN)), FN)
    a1.set_ylim(-2.2, 1.25)
    a1.set_ylabel("margin ／ 無漂移時的 margin")
    a1.set_title(f"輸入相位漂移 σ {S['assume']['comp_sigma_rad']:g} rad：不補償時會判錯（低於 0）；\n"
                 "只調 7 個 φ 就能完全補回；用擺動量測估計漂移再補，也回到 99% 以上（▼ 為最差）", fontsize=10.5)
    a1.legend(fontsize=9, loc="lower left")
    a1.grid(axis="y", alpha=0.25)
    w = 0.26
    x = np.arange(len(FN))
    a2.bar(x - w, [F[f]["n_phase"] for f in FN], w, color=GREY, label="要分辨的相位數")
    a2.bar(x, [F[f]["rank_blind"] for f in FN], w, color=ORANGE, label="盲量（平均功率）")
    a2.bar(x + w, [F[f]["rank_dither"] for f in FN], w, color=GREEN, label="擺動（∂P̄／∂φ）")
    a2.set_xticks(x, FN)
    a2.set_yticks(range(5))
    a2.set_ylabel("能分辨的相位數（Jacobian 的秩）")
    a2.set_title("只看平均功率分辨不出來（最佳相位下一階變化是 0）；\n加上 heater 擺動就都分辨得出", fontsize=10.5)
    a2.legend(fontsize=9, loc="upper left")
    a2.set_ylim(0, 5.2)
    a2.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s3_track.png"), dpi=160)
    plt.close(fig)


def fig_dither():
    e = S["eps_scan"]
    eps, bw, mg = np.array(e["eps_rad"]), np.array(e["loop_bw_hz"]), np.array(e["margin_during"])
    fig, ax = plt.subplots(figsize=(9.5, 4.9))
    ax.loglog(eps, bw, color=BLUE, lw=2.2, label="回授頻寬（左軸）")
    ax.set_xlabel("heater 擺動幅度 ε（rad）")
    ax.set_ylabel("回授頻寬 f_L（Hz）", color=BLUE)
    ax.xaxis.set_major_formatter(PLAIN)
    ax.yaxis.set_major_formatter(PLAIN)
    ax2 = ax.twinx()
    ax2.semilogx(eps, (1 - mg) * 100, color=RED, lw=2, ls="--", label="7 個同時擺動時的 margin 損失（右軸）")
    ax2.set_ylabel("擺動時 margin 損失（%）", color=RED)
    ax2.set_ylim(0, 30)
    ax2.axhline(100 * (1 - S['assume']['dither_keep']), color=RED, lw=0.8, ls=':')
    for axis in (ax.xaxis, ax.yaxis, ax2.xaxis):
        axis.set_minor_formatter(NullFormatter())
    ax2.xaxis.set_major_formatter(PLAIN)
    e0 = S["dither_rad"]
    ax.axvline(e0, color=GREY, lw=1)
    ax.plot(e0, S["loop_bw_hz"], "o", color=BLUE, mec="black", ms=9)
    ax.annotate(f"選定 ε＝{e0:.4f} rad（同時擺動損失 ≤ {100 * (1 - S['assume']['dither_keep']):.0f}%）：f_L＝{S['loop_bw_hz']:.2f} Hz\n"
                f"可追漂移 {S['ramp_rate_allow_rad_s']:.2f} rad/s（1 m 光纖熱漂移約 {S['fiber_ramp_rad_s']:g} rad/s）",
                (e0, S["loop_bw_hz"]), xytext=(0.0034, 8), fontsize=9.5, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(0.02, 0.2, f"擺動頻率 {S['dither_hz']:.0f} Hz\n受 heater 熱時間常數限制；\n右上平台＝量測至少 10 個擺動週期", fontsize=9, color=GREY, ha="left")
    ax.set_title("擺動幅度的取捨：幅度越大，量測越快（雜訊主要來自資料本身的功率起伏），但擺動時 margin 掉得越多", fontsize=10.5)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="lower right")
    ax.grid(which="major", alpha=0.25)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m1", "s3_dither.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    fig_track()
    fig_dither()
    print("寫出 figures/paper/m1/s3_track.png、s3_dither.png")
