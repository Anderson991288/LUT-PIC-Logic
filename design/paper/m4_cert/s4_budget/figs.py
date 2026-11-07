r"""論文 M4 s4：圖——(a) 10 Gb/s 一個 UI 的分配（類比接收端、延伸到盒內最小與認證窗；另附數位接收端與草稿表 VI 的 AND4）；
(b) 接收端頻寬 5–9 GHz 的窗寬；(c) 位元率 10–25 Gb/s 的窗寬（認證窗：單葉與每路切 2 份；沒有窗的點畫 ×）。

用途：讀 budget_ui.json、sens.json 出圖。
輸入：design/paper/m4_cert/s4_budget/out/budget_ui.json、sens.json。
輸出：figures/paper/m4/s4_budget.png（圖 M4-4）。
執行：.\lab design\paper\m4_cert\s4_budget\figs.py
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

STEP = "paper/m4_cert/s4_budget"
B = json.loads(paths.OUT(STEP, "budget_ui.json").read_text(encoding="utf-8"))
S = json.loads(paths.OUT(STEP, "sens.json").read_text(encoding="utf-8"))
COL = {"AND4": BLUE, "MAJ4": GREEN, "XOR2": ORANGE}


def cert_lines(ax, x, rows, col, fn):
    """認證窗：單葉（虛線方點）與每路切 2 份（點線空心）；沒有窗（0 ps）的點不連線，在 0 畫 ×。"""
    for key, sty, lab in (("cert", "s--", "單葉"), ("cert_fine", "D:", "切細")):
        y = np.array([r[key] for r in rows], float)
        ok = y > 0
        ax.plot(np.array(x)[ok], y[ok], sty, color=col, lw=1.1, ms=4, mfc="white" if key == "cert_fine" else col,
                label=f"{fn}：認證窗（{lab}）")
        if (~ok).any():                                                # 空序列加 clip_on=False 會把 tight 邊界撐大
            ax.plot(np.array(x)[~ok], np.zeros((~ok).sum()), "x", color=col, ms=6, mew=1.4, clip_on=False, zorder=5)   # 畫在軸上，不裁切


def main():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw=dict(width_ratios=[1.35, 1.0, 1.0], wspace=0.25))
    ax = axs[0]
    F = B["functions"]
    treq = B["t_req_ps"]
    bars = [(f"{fn}\n類比", F[fn]["analog"]["items"]["edges_isi"], F[fn]["analog"]["items"]["noise"], F[fn]["analog"]["items"]["skew"],
             F[fn]["analog"]["box_skew"], F[fn]["analog"]["box_common"], F[fn]["analog"]["cert_conservative"], F[fn]["analog"]["remaining_cert"])
            for fn in F]
    a4 = F["AND4"]["digital"]
    bars.append(("AND4\n數位", a4["items"]["edges_isi"], a4["items"]["noise"], a4["items"]["skew"], 0, 0, 0, a4["remaining"]))
    d = B["draft"]["budget"]
    bars.append(("AND4\n草稿表 VI", d["edges_isi"], d["noise"], d["skew"], 0, 0, 0, d["remaining"]))
    parts = [("邊緣與 ISI", "#8c8c8c"), ("雜訊護欄", RED), ("skew 13.2 ps（一組）", ORANGE), ("盒內其他 skew", "#c9a227"), ("共同平移", "#8d6e63"),
             ("認證的保守量", "#b39ddb"), ("T_req", "#37474f"), ("剩餘", GREEN)]
    x = np.arange(len(bars))
    V = np.array([[*b[1:7], treq, b[7]] for b in bars])               # 每列：依 parts 的順序由下往上
    bottom = np.zeros(len(bars))
    for k, (lab, col) in enumerate(parts):
        ax.bar(x, V[:, k], 0.62, bottom=bottom, color=col, label=lab, edgecolor="white", lw=0.5)
        bottom += V[:, k]
    for i, b in enumerate(bars):
        ax.text(i, 101, f"剩 {b[7]:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, [b[0] for b in bars], fontsize=8.5)
    ax.set_ylim(0, 108)
    ax.set_ylabel("ps（一個 UI＝100 ps）")
    ax.set_title("(a) 10 Gb/s 一個 UI 的分配（由下往上依序扣除）", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, frameon=False)
    ax = axs[1]
    for fn, f in S["functions"].items():
        bw = [r["bw"] for r in f["bw"]]
        ax.plot(bw, [r["skew"] for r in f["bw"]], "o-", color=COL[fn], lw=1.3, ms=4, label=f"{fn}：一組延遲（數位）")
        cert_lines(ax, bw, f["bw"], COL[fn], fn)
    ax.axhline(treq, color="k", ls=":", lw=1)
    ax.set_xlabel("接收端 f_3dB（GHz），10 Gb/s")
    ax.set_ylabel("共同取樣窗（ps）")
    ax.set_ylim(0, 100)
    ax.set_title("(b) 接收端頻寬（虛點線＝T_req）", fontsize=10)
    ax = axs[2]
    for fn, f in S["functions"].items():
        rr = [r["rate"] for r in f["rate"]]
        ax.plot(rr, [r["skew"] for r in f["rate"]], "o-", color=COL[fn], lw=1.3, ms=4, label=f"{fn}：一組延遲")
        cert_lines(ax, rr, f["rate"], COL[fn], fn)
    ax.axhline(treq, color="k", ls=":", lw=1)
    ax.set_xlabel("位元率（Gb/s），f_3dB＝0.7×位元率")
    ax.set_ylabel("共同取樣窗（ps）")
    ax.set_ylim(0, 100)
    ax.set_title("(c) 位元率（T_req、skew 固定；× ＝無窗）", fontsize=10)
    h, lab = axs[1].get_legend_handles_labels()                       # (b)(c) 共用一個圖例，放在兩圖下方
    lab = [s.replace("（數位）", "") for s in lab]
    axs[1].legend(h, lab, fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(1.1, -0.16), frameon=False)
    fig.savefig(paths.FIG("paper/m4", "s4_budget.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m4/s4_budget.png")


if __name__ == "__main__":
    main()
