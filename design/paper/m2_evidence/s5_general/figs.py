r"""論文 M2 s5：圖——16 個函數的光功率需求（靜態與聯合驗收）與各步執行時間。

用途：數字讀 out/general.json。
輸入：out/general.json。
輸出：figures/paper/m2/s5_general.png（圖 M2-4）。
執行：.\lab design\paper\m2_evidence\s5_general\figs.py
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

STEP = "paper/m2_evidence/s5_general"
G = json.loads(paths.OUT(STEP, "general.json").read_text(encoding="utf-8"))
STAGES = (("synth", "合成", GREY), ("power", "功率", ORANGE), ("timing", "時序", BLUE), ("static_cal", "靜態校正", PURPLE),
          ("observe", "可觀測性", GREEN), ("joint", "聯合驗收", RED))


def main():
    F = G["functions"]
    names = sorted(F, key=lambda k: F[k]["joint_pu_dbm"] if F[k]["joint_pu_dbm"] is not None else 99)
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw=dict(width_ratios=[1.6, 1]))
    ax = axs[0]
    x = np.arange(len(names))
    st = [F[k]["pu_static_dbm"] for k in names]
    jt = [F[k]["joint_pu_dbm"] if F[k]["joint_pu_dbm"] is not None else np.nan for k in names]
    ax.vlines(x, st, jt, color=GREY, lw=1)
    ax.plot(x, st, "o", color=GREY, ms=7, label="靜態需求")
    ax.plot(x, jt, "^", color=BLUE, ms=8, label="聯合驗收（校正後、skew 20 ps、相位殘差、擺動）")
    bad = [i for i, k in enumerate(names) if not F[k]["joint_pass"]]
    ax.plot(x[bad], np.array(jt)[bad], "^", color=RED, ms=9, label="超過系統預算")
    sw = G["xnor_swap"]                                             # XNOR 以 XOR 相位＋比較器對調（審查 R2）
    ax.plot([names.index("XNOR")], [sw["joint_pu_dbm"]], "*", color=GREEN, ms=13, label="XNOR 改用比較器對調")
    ax.axhline(G["budget_pu_dbm"], color="k", ls="--", lw=1.2)
    ax.text(7.5, G["budget_pu_dbm"] + 0.25, f"系統預算 {G['budget_pu_dbm']:.2f} dBm", fontsize=8.5)
    ax.set_xticks(x, names, rotation=45, ha="right")
    ax.set_ylim(min(F[k]["pu_static_dbm"] for k in names) - 1.5, max(G["budget_pu_dbm"], *[F[k]["joint_pu_dbm"] or -99 for k in names]) + 1.5)
    ax.set_ylabel("B7 輸入端 P_u（dBm）")
    ax.set_title(f"(a) {G['n_functions']} 個函數的光功率需求", fontsize=10.5)
    ax.legend(fontsize=8, loc="center left")
    ax = axs[1]
    left = 0.0
    for key, lab, c in STAGES:
        v = G["stage_time_total_s"][key]
        ax.barh([0], [v], left=left, color=c, label=f"{lab} {v:g} s")
        left += v
    ax.set_yticks([])
    ax.set_xlabel(f"{G['n_functions']} 個函數各步時間的加總（s，各 worker 內的牆上時間）")
    ax.set_title(f"(b) 執行時間（{G['workers']} 個 worker 實際 {G['wall_s']:g} s）", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3)
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m2", "s5_general.png"), dpi=160)
    print("寫出 figures/paper/m2/s5_general.png")


if __name__ == "__main__":
    main()
