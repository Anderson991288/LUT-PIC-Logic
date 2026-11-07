r"""論文 M1 s5：圖——10 Gb/s 總功率預算（每項代價發生在訊號鏈的哪裡、加起來要多少光）。

用途：上半部畫訊號鏈（發射端 → 光纖 → 輸入 EC → B7 → 輸出 EC → 接收端），把每一項代價標在它發生的位置；
      下半部把靜態需求與各項代價依序疊成一條橫條，最後加上輸入 EC 得到每根光纖要給的功率。數字讀 out/assess.json。
輸入：out/assess.json。
輸出：figures/paper/m1/s5_budget.png（圖 M1-9）。
執行：.\lab design\paper\m1_timing\s5_assess\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.patches import FancyBboxPatch                        # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "paper/m1_timing/s5_assess"
A = json.loads(paths.OUT(STEP, "assess.json").read_text(encoding="utf-8"))["budget"]
DB = {i["item"]: i["db"] for i in A["items"]}

# 每項代價：顯示名稱、白話、發生位置（訊號鏈方塊索引）、顏色
ITEMS = [
    ("轉態與接收端頻寬", "轉態＋頻寬", "邊緣與接收端頻寬讓\n可取樣的時間變短", 5, RED),
    ("skew ≤ 15 ps", "skew", "5 路到達時間\n差 ≤ 15 ps", 1, ORANGE),
    ("消光比（靜態）", "消光比", "「0」的殘留光\n（重新求相位後）", 0, PURPLE),
    ("heater 擺動", "擺動", "7 個 heater\n同時擺動", 3, GREEN),
    ("相位誤差（≤ δ_det）", "相位誤差", "漂移、追蹤落後、\n估計誤差合計", 1, "#8c564b"),
]
BLOCKS = ["發射端\n（4 路調變＋R）", "光纖\n（5 根）", "輸入 EC", "B7\n（heater MZI）", "輸出 EC", "接收端\n（偵測器、取樣）"]


def box(ax, x, y, w, h, t, ec, fc="white", fs=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", ec=ec, fc=fc, lw=1.4))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs)


def fig_budget():
    fig = plt.figure(figsize=(12, 6.6))
    ax = fig.add_axes([0.02, 0.45, 0.96, 0.5])
    ax.set_xlim(0, 12)
    ax.set_ylim(0.95, 4.75)
    ax.axis("off")
    xs = [0.2 + 2.0 * k for k in range(6)]
    for k, (x, t) in enumerate(zip(xs, BLOCKS)):
        box(ax, x, 3.6, 1.6, 1.0, t, GREY, "#f4f6fa")
        if k < 5:
            ax.annotate("", xy=(x + 2.0, 4.1), xytext=(x + 1.6, 4.1), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.3))
    # 光的方向與兩個 EC 的損耗（不是動態代價，另外標）
    ax.text(xs[2] + 0.8, 3.35, f"損耗 {A['fiber_data_dbm'] - A['pu_total_dbm']:.0f} dB（最後再加）", ha="center", fontsize=9, color=GREY)
    ax.text(xs[4] + 0.8, 3.35, "損耗已算在靜態需求", ha="center", fontsize=9, color=GREY)
    box(ax, xs[5] - 0.05, 1.1, 1.7, 0.95, "", GREY, "#eef0f3")
    ax.text(xs[5] + 0.8, 1.78, f"靜態需求 {A['pu_static_dbm']:+.2f} dBm", ha="center", fontsize=9.5, fontweight="bold")
    ax.text(xs[5] + 0.8, 1.4, "訊號要大於雜訊的 7 倍\n（換算到 B7 輸入端）", ha="center", va="center", fontsize=8.3)
    # 每一項代價掛在它發生的方塊下面
    count = {}
    for key, short, plain, k, c in ITEMS:
        n = count.get(k, 0)
        count[k] = n + 1
        y = 2.25 - 1.15 * n
        box(ax, xs[k] - 0.05, y, 1.7, 0.95, "", c, "white")
        ax.text(xs[k] + 0.8, y + 0.68, f"{short}　+{DB[key]:.2f} dB", ha="center", fontsize=9.5, color=c, fontweight="bold")
        ax.text(xs[k] + 0.8, y + 0.3, plain, ha="center", va="center", fontsize=8.3)
        ax.plot([xs[k] + 0.8, xs[k] + 0.8], [y + 0.95, 3.6 if n == 0 else y + 1.15], color=c, lw=1, ls=":")
    ax.set_title("每一項代價發生在訊號鏈的哪裡（代價＝為了維持判讀餘裕要多給的光功率）", fontsize=11, loc="left")

    # 下半部：依序疊起來
    bx = fig.add_axes([0.06, 0.08, 0.9, 0.27])
    left = A["pu_static_dbm"]
    bx.barh(0, left - (-9), left=-9, color="#d0d4da", height=0.5)
    bx.text((left - 9) / 2, 0, f"靜態需求 {left:+.2f} dBm", ha="center", va="center", fontsize=9.5)
    for key, short, plain, k, c in sorted(ITEMS, key=lambda t: -DB[t[0]]):
        w = DB[key]
        bx.barh(0, w, left=left, color=c, height=0.5)
        if w > 0.3:
            bx.text(left + w / 2, 0, f"{short}\n+{w:.2f}", ha="center", va="center", fontsize=9, color="white", fontweight="bold")
        left += w
    small = sum(DB[k] for k in DB if DB[k] <= 0.3)
    n_small = sum(1 for k in DB if DB[k] <= 0.3)
    bx.annotate(f"其餘 {n_small} 項合計 +{small:.2f} dB", xy=(left - small / 2, 0.25), xytext=(left - 0.2, 0.75), fontsize=9,
                ha="right", arrowprops=dict(arrowstyle="->", lw=0.8))
    bx.axvline(A["pu_total_dbm"], color=BLUE, lw=1.6)
    bx.text(A["pu_total_dbm"] + 0.05, -0.55, f"B7 輸入端要 {A['pu_total_dbm']:+.2f} dBm", color=BLUE, fontsize=9.5)
    bx.barh(0, A["fiber_data_dbm"] - A["pu_total_dbm"], left=A["pu_total_dbm"], color="none", ec=GREY, hatch="//", height=0.5)
    bx.text((A["pu_total_dbm"] + A["fiber_data_dbm"]) / 2, 0, "＋輸入 EC", ha="center", va="center", fontsize=9)
    bx.axvline(A["fiber_data_dbm"], color=GREEN, lw=1.6)
    bx.text(A["fiber_data_dbm"] + 0.05, 0.55, f"每根資料光纖 {A['fiber_data_dbm']:+.2f} dBm\n（參考光纖 {A['fiber_ref_dbm']:+.1f}、5 根合計 {A['total_dbm']:+.1f} dBm）",
            color=GREEN, fontsize=9.5, va="center")
    bx.set_xlim(-9, 0.5)
    bx.set_ylim(-0.9, 1.1)
    bx.set_yticks([])
    bx.set_xlabel("功率（dBm）")
    bx.set_title(f"依序疊起來（決定需求的函數 {A['limiting_function']}）：靜態需求＋各項代價 {A['dynamic_db']:.2f} dB", fontsize=11, loc="left")
    bx.grid(axis="x", alpha=0.25)
    fig.savefig(paths.FIG("paper/m1", "s5_budget.png"), dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_budget()
    print("寫出 figures/paper/m1/s5_budget.png")
