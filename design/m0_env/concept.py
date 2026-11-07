r"""M0 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M0 s1、s2 的概念；只是示意，數字以各步結果為準。
      M0 還沒教到光路元件的組合，所以圖中只出現 MMI，不出現後面才定義的名詞。
輸入：無。
輸出：figures/m0/s1_concept.png、figures/m0/s2_concept.png。
執行：.\lab design\m0_env\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

from matplotlib.patches import Rectangle                             # noqa: E402

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, RED, arrow, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("這台電腦能不能跑後面每一步要用的工具？",
                    ["這台電腦", "Python 環境\n（IPKISS）", "CORNERSTONE PDK", "KLayout"],
                    ["env.json\n13 項檢查結果", "mmi_test.gds\n（DRC 跑得完）", "事實：PDK 的 MMI\n＝理想 50:50"],
                    "先用最小的元件把整條流程跑一遍：任何一環不通，就停在這一步，不要等到佈局才發現。")
    ax.text(3.5, 4.75, "① 基本工具能不能動", fontsize=10, color=GREY, fontweight="bold")
    for k, t in enumerate(["Python 與數值套件", "BLAS 只用 1 個執行緒", "中文字型"]):
        box(ax, 3.5 + 2.4 * k, 3.85, 2.2, 0.65, t + "　OK", ec=GREEN, fc="#eaf5ee", fs=9)
    ax.text(3.5, 3.35, "② 用一顆 MMI 把「模型 → 佈局 → GDS → DRC」走一遍", fontsize=10, color=GREY, fontweight="bold")
    steps = ["載入 PDK\n（SOI220）", "MMI\n電路模型 S", "MMI 佈局\n讀埠位", "寫出\nGDS", "KLayout\nDRC"]
    for k, t in enumerate(steps):
        x = 3.4 + 1.5 * k
        box(ax, x, 1.95, 1.3, 1.0, t, ec=BLUE, fc="#eaf1fa", fs=9)
        if k < len(steps) - 1:
            arrow(ax, (x + 1.3, 2.45), (x + 1.5, 2.45), BLUE, 1.4)
    # MMI 小圖
    ax.add_patch(Rectangle((4.85, 1.3), 0.6, 0.3, fc=BLUE, alpha=0.7))
    for y in (1.37, 1.53):
        ax.plot([4.55, 4.85], [y, y], color=BLUE, lw=1.5)
        ax.plot([5.45, 5.75], [y, y], color=BLUE, lw=1.5)
    ax.text(6.0, 1.45, "2 進 2 出的 MMI：把兩路光混合後再分到兩個輸出", fontsize=8.8, va="center", color=GREY)
    ax.text(7.0, 1.0, "任何一項失敗 → 記為「失敗」，結束碼非 0", fontsize=9, color=RED, ha="center")
    save(fig, paths.FIG("m0", "s1_concept.png"))


def s2():
    fig, ax = frame("報告組裝程式的檢查，真的抓得到錯誤嗎？",
                    ["M0 s1 的報告片段", "組裝程式\nbuild_report.py", "env.json"],
                    ["tool_tests.json\n每個案例的結果", "可以信任的\n組裝工具"],
                    "故意放進錯誤，看檢查會不會報錯；不會報錯的檢查，等於沒有檢查。")
    good = "原片段（沒有錯）"
    bad = ["缺少一節、順序顛倒", "數字與 JSON 不符", "禁用字：本機路徑、用詞", "圖檔、連結不存在", "名詞先用後定義"]
    ys = [4.35, 3.6, 2.95, 2.3, 1.65, 1.0]
    box(ax, 3.45, ys[0], 2.6, 0.5, good, ec=GREEN, fc="#eaf5ee", fs=9)
    for y, t in zip(ys[1:], bad):
        box(ax, 3.45, y, 2.6, 0.5, "注入：" + t, ec=RED, fc="#fdecea", fs=8.8)
    box(ax, 6.65, 1.0, 1.5, 3.85, "組裝程式\n的檢查", ec=GREY, fc="#f4f4f4", fs=10, bold=True)
    for y in ys:
        arrow(ax, (6.05, y + 0.25), (6.65, y + 0.25), GREEN if y == ys[0] else RED, 1.2)
    box(ax, 8.75, ys[0], 1.85, 0.5, "通過（不誤報）", ec=GREEN, fc="#eaf5ee", fs=9)
    arrow(ax, (8.15, ys[0] + 0.25), (8.75, ys[0] + 0.25), GREEN, 1.4)
    box(ax, 8.75, 1.0, 1.85, 2.95, "每一種都要\n報錯並停下\n（或自動更正）", ec=RED, fc="#fdecea", fs=9.5)
    for y in ys[1:]:
        arrow(ax, (8.15, y + 0.25), (8.75, min(max(y + 0.25, 1.2), 3.8)), RED, 1.0)
    save(fig, paths.FIG("m0", "s2_concept.png"))


def main():
    s1()
    s2()
    print("寫出 figures/m0/s1_concept.png、s2_concept.png")


if __name__ == "__main__":
    main()
