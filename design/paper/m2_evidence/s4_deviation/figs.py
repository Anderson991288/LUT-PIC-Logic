r"""論文 M2 s4：圖——MMI 分光誤差下，名義相位、名義校正後、已知硬體的參考解三種狀態的 margin 與所需光功率。

用途：數字讀 out/deviation.json。
輸入：out/deviation.json。
輸出：figures/paper/m2/s4_deviation.png（圖 M2-3）。
執行：.\lab design\paper\m2_evidence\s4_deviation\figs.py
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
from common.draw import BLUE, GREEN, GREY, RED                       # noqa: E402

STEP = "paper/m2_evidence/s4_deviation"
D = json.loads(paths.OUT(STEP, "deviation.json").read_text(encoding="utf-8"))
STATES = (("nominal", "名義相位", RED), ("loop", "名義校正後", BLUE), ("oracle", "已知硬體的參考解", GREEN))


def main():
    F = D["functions"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
    # (a)(b) 每個實例的窗內 margin（相對名義模型）
    for ax, fn in zip(axs[:2], F):
        r = F[fn]
        ref = r["nominal_model"]["m_win"]
        x = np.arange(len(r["instances"]))
        w = 0.27
        for k, (key, lab, c) in enumerate(STATES):
            ax.bar(x + (k - 1) * w, [q[key]["m_win"] / ref for q in r["instances"]], w, color=c, label=lab)
        ax.axhline(1.0, color=GREY, ls="--", lw=1)
        ax.axhline(0.0, color="k", lw=0.6)
        ax.set_xticks(x[::4], [str(i + 1) for i in x[::4]])
        ax.set_xlabel("硬體實例")
        ax.set_ylabel("聯合驗收的 23 ps 窗內 margin（以名義模型為 1）")
        ax.set_title(f"({'a' if fn == 'AND4' else 'b'}) {fn}（同一組 {len(x)} 個硬體實例）", fontsize=10.5)
        ax.set_ylim(-0.3, 1.45)
        ax.legend(fontsize=8, loc="upper center", ncol=3, framealpha=0.95)
    # (c) XOR2：每個實例窗存在所需的 P_u 與系統預算
    ax = axs[2]
    r = F["XOR2"]
    x = np.arange(len(r["instances"]))
    for k, (key, lab, c) in enumerate(STATES):
        y = [q[key]["pu_min_dbm"] for q in r["instances"]]
        ax.plot(x + 1, y, "o-", color=c, label=lab, lw=1.0, ms=4)
    ax.axhline(D["budget_pu_dbm"], color="k", ls="--", lw=1.2)
    ax.text(len(x) * 0.5, D["budget_pu_dbm"] - 0.9, f"系統預算 {D['budget_pu_dbm']:.2f} dBm（線下才有窗）", fontsize=8.5)
    ax.set_ylim(D["budget_pu_dbm"] - 1.4, None)
    ax.set_xticks((x + 1)[::4])
    ax.set_xlabel("硬體實例")
    ax.set_ylabel("23 ps 窗存在所需的 P_u（dBm）")
    ax.set_title("(c) XOR2：所需光功率", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m2", "s4_deviation.png"), dpi=160)
    print("寫出 figures/paper/m2/s4_deviation.png")


if __name__ == "__main__":
    main()
