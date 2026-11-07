r"""論文 M4 s2：圖——(a) AND4 的 margin 下界（1 個、16 個葉盒）與 41 個盒內抽樣點的模擬最小值；(b) 下界扣掉的兩項（一階項、餘項）隨取樣相位的變化；
(c) 三個函數的最佳 margin：對齊、盒內模擬最小、下界（多葉、1 葉）。

用途：讀 leaf.json 與 curves_<函數>.npz 出圖。
輸入：design/paper/m4_cert/s2_leaf/out/leaf.json、curves_AND4.npz、curves_MAJ4.npz、curves_XOR2.npz。
輸出：figures/paper/m4/s2_leaf.png（圖 M4-2）。
執行：.\lab design\paper\m4_cert\s2_leaf\figs.py
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

STEP = "paper/m4_cert/s2_leaf"
G = json.loads(paths.OUT(STEP, "leaf.json").read_text(encoding="utf-8"))


def main():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.4), gridspec_kw=dict(width_ratios=[1.3, 1.3, 1.0], wspace=0.28))
    c = np.load(paths.OUT(STEP, "curves_AND4.npz"))
    ph = c["phase"]
    ax = axs[0]
    ax.plot(ph, c["actual_1"], color=GREY, lw=3, alpha=0.6, label="模擬：41 個抽樣點的最小值")
    ax.plot(ph, c["lower_16"], color=BLUE, lw=1.3, label="下界：16 個葉盒")
    ax.plot(ph, c["lower_1"], color=RED, lw=1.3, label="下界：1 個葉盒")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_ylim(-0.6, 0.7)
    ax.set_xlim(55, 145)
    ax.set_xlabel("取樣相位（ps，自符號起點）")
    ax.set_ylabel("margin＝min_s (b_s v_s − Γ_s)（P_u）")
    ax.set_title("(a) AND4：盒內所有延遲的 margin 下界", fontsize=10)
    ax.legend(fontsize=8, loc="lower center")
    ax = axs[1]
    ax.plot(ph, c["lin_1"], color=ORANGE, lw=1.3, label="一階項 Σρ|h∗(g ẋ)|：1 葉")
    ax.plot(ph, c["rem_1"], color=GREEN, lw=1.3, label="餘項 |h|∗Ψ：1 葉")
    ax.plot(ph, c["lin_16"], color=ORANGE, lw=1.1, ls="--", label="一階項：16 葉")
    ax.plot(ph, c["rem_16"], color=GREEN, lw=1.1, ls="--", label="餘項：16 葉")
    ax.plot(ph, c["gbar"] - c["g0"], color=GREY, lw=1.1, label="護欄增加：盒內上界 − 對齊")
    ax.set_xlabel("取樣相位（ps）")
    ax.set_ylabel("各符號中的最大值（P_u）")
    ax.set_title("(b) AND4：下界扣掉的各項", fontsize=10)
    ax.set_ylim(0, 0.98)
    ax.legend(fontsize=8, loc="upper center", ncol=2)
    ax = axs[2]
    F = G["functions"]
    x = np.arange(len(F))
    many = [max(f["configs"], key=int) for f in F.values()]
    bars = [("對齊（模擬）", [f["center_margin_max"] for f in F.values()], GREY),
            ("盒內 41 點最小（模擬）", [f["configs"]["1"]["act_margin_max"] for f in F.values()], BLUE),
            ("下界：多葉", [f["configs"][n]["low_margin_max"] for f, n in zip(F.values(), many)], GREEN),
            ("下界：1 葉", [f["configs"]["1"]["low_margin_max"] for f in F.values()], RED)]
    for k, (lab, v, col) in enumerate(bars):
        ax.bar(x + (k - 1.5) * 0.2, v, 0.19, color=col, label=lab)
    ax.set_xticks(x, [f"{fn}\n（多葉＝{n}）" for fn, n in zip(F, many)], fontsize=9)
    ax.set_ylabel("最佳取樣相位的 margin（P_u）")
    ax.set_title("(c) 最佳 margin：模擬與下界", fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=8, ncol=2, loc="upper center")
    fig.savefig(paths.FIG("paper/m4", "s2_leaf.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m4/s2_leaf.png")


if __name__ == "__main__":
    main()
