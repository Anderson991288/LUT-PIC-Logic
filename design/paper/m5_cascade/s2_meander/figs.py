r"""論文 M5 s2：圖——(a) 草稿表 IV 的 9 個案例：選擇的蛇形（全部 0 mm）的最差角落窗與完整等長的窗，對照草稿；
(b) 壓力案例（本研究新增）：演算法 1 依序試過的候選（總長 vs 最差角落窗）、完整等長與 T_req。

用途：讀 meander.json 出圖。
輸入：design/paper/m5_cascade/s2_meander/out/meander.json。
輸出：figures/paper/m5/s2_meander.png（圖 M5-2）。
執行：.\lab design\paper\m5_cascade\s2_meander\figs.py
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
from common.draw import BLUE, GREEN, GREY, ORANGE, RED               # noqa: E402

C = json.loads(paths.OUT("paper/m5_cascade/s2_meander", "meander.json").read_text(encoding="utf-8"))
TREQ = C["t_req_ps"]


def main():
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.2), gridspec_kw=dict(width_ratios=[1.25, 1.0], wspace=0.22))
    ax = axs[0]
    tab = [r for r in C["cases"] if r["draft"]]
    x = np.arange(len(tab))
    w = 0.2
    ax.bar(x - 1.5 * w, [r["chosen_summary"]["worst"] for r in tab], w, color=BLUE, label="選擇（0 mm）：本研究")
    ax.bar(x - 0.5 * w, [r["draft"]["window"] for r in tab], w, color=BLUE, alpha=0.4, label="選擇：草稿表 IV")
    ax.bar(x + 0.5 * w, [r["reference"]["full"]["worst"] for r in tab], w, color=ORANGE, label="完整等長：本研究")
    ax.bar(x + 1.5 * w, [r["draft"]["full_window"] for r in tab], w, color=ORANGE, alpha=0.4, label="完整等長：草稿")
    ax.axhline(TREQ, color="k", ls=":", lw=1, label="T_req")
    ax.set_xticks(x, [r["label"].replace(", ", "\n") for r in tab], fontsize=8)
    ax.set_ylabel("最差角落的共同窗（ps）")
    ax.set_ylim(0, 75)
    ax.set_title("(a) 草稿表 IV 的案例：演算法 1 全部選 0 mm", fontsize=10)
    ax.legend(fontsize=7.5, ncol=3, loc="upper right")
    ax = axs[1]
    col = {"AND4, fan-in C": BLUE, "AND4, fan-in C, 1 dB/mm": RED, "MAJ4, fan-in C": GREEN, "MAJ4, fan-in C, 1 dB/mm": GREY, "XOR2, fan-in D": ORANGE}
    for r in C["cases"]:
        if r["draft"]:
            continue
        c = col[r["label"]]
        tx = [t["total_mm"] for t in r["tried"]]
        ty = [t["worst"] for t in r["tried"]]
        ax.plot(tx, ty, "o-", color=c, ms=4, lw=1.2, label=f"{r['label']}（span {r['raw_span_ps']:.0f} ps）")
        if r["chosen_summary"]:
            ax.plot(r["chosen_summary"]["total_mm"], r["chosen_summary"]["worst"], "*", color=c, ms=14, mec="k", mew=0.6)
        ax.plot(r["reference"]["full"]["total_mm"], r["reference"]["full"]["worst"], "s", color=c, ms=7, mfc="white", mew=1.5)
    ax.axhline(TREQ, color="k", ls=":", lw=1)
    ax.plot([], [], "*", color="k", ms=10, label="選擇（第一個通過者）")
    ax.plot([], [], "s", color="k", mfc="white", label="完整等長")
    ax.set_xlabel("蛇形總長（mm），依演算法 1 的試驗順序")
    ax.set_ylabel("最差角落的共同窗（ps）")
    ax.set_ylim(0, 45)
    ax.set_title("(b) 壓力案例（本研究新增）：零長度不過時的選擇", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    fig.savefig(paths.FIG("paper/m5", "s2_meander.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m5/s2_meander.png")


if __name__ == "__main__":
    main()
