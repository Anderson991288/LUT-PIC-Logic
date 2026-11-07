r"""論文 M4 s3：圖——(a) AND4 情境序列的認證 margin（1、16、256 個葉盒）與 41 點模擬 margin，標出認證窗；
(b) 三個函數的窗寬：對齊、盒內 41 點最小、認證窗（各種葉盒數與資料歷史）；(c) AND4 全部資料歷史時較舊符號的兩項（3 階、4 階）。

用途：讀 cert.json、curves_<函數>.npz 與 M4 s2 的 curves_AND4.npz 出圖。
輸入：design/paper/m4_cert/s3_cert/out/cert.json、curves_AND4.npz；design/paper/m4_cert/s2_leaf/out/curves_AND4.npz。
輸出：figures/paper/m4/s3_cert.png（圖 M4-3）。
執行：.\lab design\paper\m4_cert\s3_cert\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()
import matplotlib as mpl                                              # noqa: E402
mpl.rcParams["axes.unicode_minus"] = False

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, RED               # noqa: E402

STEP = "paper/m4_cert/s3_cert"
G = json.loads(paths.OUT(STEP, "cert.json").read_text(encoding="utf-8"))


def main():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.4), gridspec_kw=dict(width_ratios=[1.3, 1.25, 1.0], wspace=0.28))
    F = G["functions"]
    c = np.load(paths.OUT(STEP, "curves_AND4.npz"))
    s2 = np.load(paths.OUT("paper/m4_cert/s2_leaf", "curves_AND4.npz"))
    ph = c["phase"]
    ax = axs[0]
    ax.plot(ph, s2["actual_1"], color=GREY, lw=3, alpha=0.6, label="模擬：41 個抽樣點的最小值")
    cfg = F["AND4"]["scenario"]["configs"]
    for (n, col), y in zip([("256", GREEN), ("16", BLUE), ("1", RED)], (-0.06, -0.12, -0.18)):
        k = cfg[n]
        ax.plot(ph, c[f"scenario_cert_{n}"], color=col, lw=1.2, label=f"認證 margin：{n} 個葉盒（W＝{k['window']:g} ps）")
        ax.plot([k["start"], k["end"]], [y, y], color=col, lw=4, solid_capstyle="butt")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_ylim(-0.6, 0.7)
    ax.set_xlim(55, 145)
    ax.set_xlabel("取樣相位（ps，自符號起點）")
    ax.set_ylabel("margin（P_u）")
    ax.set_title("(a) AND4 情境序列：認證 margin 與認證窗（橫條）", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower center")
    ax = axs[1]
    names = list(F)
    x = np.arange(len(names))
    mx = {fn: max(F[fn]["scenario"]["configs"], key=int) for fn in names}
    bars = [("對齊（模擬）", [F[f]["aligned"] for f in names], GREY),
            ("盒內 41 點最小（模擬）", [F[f]["box_min"] for f in names], BLUE),
            ("認證：多葉", [F[f]["scenario"]["configs"][mx[f]]["window"] for f in names], GREEN),
            ("認證：1 葉", [F[f]["scenario"]["configs"]["1"]["window"] for f in names], RED),
            ("認證：全部歷史 B(16,4)、1 葉", [F[f]["order4"]["configs"]["1"]["window"] for f in names], ORANGE)]
    for k, (lab, v, col) in enumerate(bars):
        ax.bar(x + (k - 2) * 0.16, v, 0.15, color=col, label=lab)
    ax.axhline(G["t_req_ps"], color="k", ls="--", lw=0.9, label="T_req＝23 ps")
    ax.set_xticks(x, [f"{f}\n（多葉＝{mx[f]}）" for f in names], fontsize=9)
    ax.set_ylabel("共同取樣窗（ps）")
    ax.set_ylim(0, 92)
    ax.set_xlim(-0.55, len(names) - 0.45)
    ax.set_title("(b) 窗寬：模擬與認證", fontsize=10)
    ax.legend(fontsize=7.5, ncol=2, loc="upper center")
    ax = axs[2]
    for o, ls in ((3, "--"), (4, "-")):
        ax.semilogy(ph, np.maximum(c[f"order{o}_hist_v"], 1e-7), color=ORANGE, ls=ls, lw=1.2, label=f"判讀量項：{o} 階")
        ax.semilogy(ph, np.maximum(c[f"order{o}_hist_g"], 1e-7), color=BLUE, ls=ls, lw=1.2, label=f"護欄增加：{o} 階")
    ax.set_xlim(0, 200 - G["half_box_ps"])
    ax.set_ylim(1e-6, 3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"1e{int(round(np.log10(v)))}"))
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlabel("取樣相位（ps）")
    ax.set_ylabel("較舊符號的影響上界（P_u）")
    ax.set_title("(c) AND4 全部歷史：較舊符號的影響上界", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper right")
    fig.savefig(paths.FIG("paper/m4", "s3_cert.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m4/s3_cert.png")


if __name__ == "__main__":
    main()
