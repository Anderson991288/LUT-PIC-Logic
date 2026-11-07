r"""論文 M4 s1：圖——(a) XOR2 的時域 D(t)：逐點模擬與二次式重疊，下方為兩者的差；(b) 9 個函數的 margin，
以及拿掉 Q（只留 d0＋lᵀx）後的 margin；(c) XOR2 的 Q 矩陣。

用途：(a) 用 M3 s3 的包絡重算一段波形（約 2 秒）；(b)(c) 讀 out/quad.json。
輸入：out/quad.json、design/paper/m3_align/s2_synth/out/synth.json、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：figures/paper/m4/s1_quad.png（圖 M4-1）。
執行：.\lab design\paper\m4_cert\s1_quad\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import quad as QD                                                    # noqa: E402
from common.draw import BLUE, GREY, ORANGE, RED                      # noqa: E402

G = json.loads(paths.OUT(QD.STEP, "quad.json").read_text(encoding="utf-8"))


def main():
    fig = plt.figure(figsize=(16, 4.8))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.4, 1.2, 0.8], height_ratios=[3, 1], hspace=0.08, wspace=0.3)
    S = QD.DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    sim = QD.DT.Sim(QD.DT.sequence("euler"), S["edge_full_ps"], 0.5, A, 10 ** (S["pu_dbm"] / 10) * 1e-3, False)
    U = QD.unitary("XOR2")
    d0, l, Q = QD.coeffs(U)
    p = np.array([-1, 1, -1, -1]) * QD.DT.HALF_BOX
    X = np.stack([sim.envelope(j, p[j]) for j in range(4)], axis=1)
    sl = slice(0, int(1600 / sim.dt))
    t = sim.t[sl]
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(t, QD.direct(U, X)[sl], color=GREY, lw=3.5, alpha=0.5, label="逐點：先算場再取平方")
    ax.plot(t, QD.quad(d0, l, Q, X)[sl], color=RED, lw=1.1, label="二次式 d0＋lᵀx＋xᵀQx")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("D（P_u）")
    ax.tick_params(labelbottom=False)
    ax.set_title("(a) XOR2 的判讀量 D(t)（x1 早 6.6 ps、x2 晚 6.6 ps）", fontsize=10)
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0.1, 0.97))     # 第一段與第二段脈衝之間的空白
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax)
    ax2.plot(t, (QD.direct(U, X) - QD.quad(d0, l, Q, X))[sl] * 1e15, color=BLUE, lw=0.8)
    ax2.set_ylabel("差（1e−15）")
    ax2.set_xlabel("時間（ps，前 16 個符號）")
    ax = fig.add_subplot(gs[:, 1])
    F = G["functions"]
    x = np.arange(len(F))
    ax.bar(x - 0.2, [v["margin"] for v in F.values()], 0.38, color=BLUE, label="完整二次式")
    ax.bar(x + 0.2, [v["margin_linear_only"] for v in F.values()], 0.38, color=ORANGE, label="拿掉 Q（只留 d0＋lᵀx）")
    for k, v in enumerate(F.values()):
        if not v["linearly_separable"]:
            ax.text(k, -0.9, "不可分", ha="center", fontsize=8, color=RED)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x, list(F), rotation=35, fontsize=8.5)
    ax.set_ylabel("16 組字中最差的 b·D（P_u）")
    ax.set_ylim(-1.0, 1.8)
    ax.set_title("(b) 同一組相位下，拿掉二次項的影響", fontsize=10)
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    ax = fig.add_subplot(gs[:, 2])
    q = np.array(F["XOR2"]["Q"])
    v = np.abs(q).max()
    ax.imshow(q, cmap="RdBu_r", vmin=-v, vmax=v)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{q[i, j]:+.2f}" if abs(q[i, j]) > 1e-6 else "0", ha="center", va="center", fontsize=9,
                    color="white" if abs(q[i, j]) > 0.6 * v else "black")
    ax.set_xticks(range(4), [f"x{i + 1}" for i in range(4)])
    ax.set_yticks(range(4), [f"x{i + 1}" for i in range(4)])
    ax.set_title("(c) XOR2 的 Q（l＝" + "、".join(f"{a:.2f}" if abs(a) > 1e-6 else "0" for a in F["XOR2"]["l"]) + "）", fontsize=10)
    fig.savefig(paths.FIG("paper/m4", "s1_quad.png"), dpi=160, bbox_inches="tight")
    print("寫出 figures/paper/m4/s1_quad.png")


if __name__ == "__main__":
    main()
