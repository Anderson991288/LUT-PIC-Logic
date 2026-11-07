r"""M1 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M1 s1–s5 的概念；只是示意，數字以各步結果為準。
      每張圖只用到該步之前已定義的名詞（s1 還沒有 MZI、B7）。
輸入：M1 s5 的 out/phases.json（s3 概念圖以 AND2 的相位畫一個實際的 U）。
輸出：figures/m1/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png、s5_concept.png。
執行：.\lab design\m1_logic\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from matplotlib.patches import Circle, Rectangle                     # noqa: E402

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, PURPLE, RED, arrow, box, frame, save   # noqa: E402
from common.draw import draw_b7, mzi_box                             # noqa: E402
from common.mzi import B7_OPS, chain                                 # noqa: E402


def s1():
    fig, ax = frame("光要怎麼表示 0／1？兩路光混合後，怎麼讀成一個邏輯值？",
                    ["M0 s1：MMI＝理想\n50:50 混合", "兩路資料光 x1、x2\n有光＝1、無光＝0"],
                    ["判讀規則\nΔP＞0 判 1、ΔP＜0 判 0", "發現：只靠資料光不夠\n要加參考光 R"],
                    "偵測器只看得到功率；要做邏輯，得讓兩路光的光場干涉，再比較兩個偵測器的功率。")
    for y, t, c in ((3.9, "x1", BLUE), (2.6, "x2", GREEN)):
        ax.text(3.45, y, t, fontsize=11, va="center", fontweight="bold", color=c)
        ax.plot([3.8, 5.3], [y, y], color=c, lw=3)
    box(ax, 5.3, 2.25, 0.9, 2.0, "MMI\n混合", ec=GREY, fc="#e9eef5", fs=9.5)
    for y, t in ((3.9, "P上"), (2.6, "P下")):
        ax.plot([6.2, 7.3], [y, y], color=PURPLE, lw=3)
        box(ax, 7.3, y - 0.3, 0.9, 0.6, "偵測器\n" + t, ec=RED, fc="#fdecea", fs=8.5)
    box(ax, 8.6, 2.85, 1.0, 0.8, "ΔP＝\nP上 − P下", ec=RED, fc="white", fs=8.8)
    arrow(ax, (8.2, 3.9), (8.6, 3.4), RED, 1.2)
    arrow(ax, (8.2, 2.6), (8.6, 3.1), RED, 1.2)
    box(ax, 9.8, 2.85, 0.8, 0.8, "正→1\n負→0", ec=ORANGE, fc="#fbf3df", fs=8.8)
    arrow(ax, (9.6, 3.25), (9.8, 3.25), ORANGE, 1.2)
    # 相加／抵消
    ax.text(3.5, 1.75, "光場同相：相加（亮）", fontsize=9, color=GREY)
    ax.text(3.5, 1.15, "光場反相：抵消（暗）", fontsize=9, color=GREY)
    kw = dict(arrowstyle="-|>", lw=1.8)
    ax.annotate("", xy=(6.6, 1.85), xytext=(6.0, 1.85), arrowprops=dict(color=BLUE, **kw))     # 同相：頭尾相接
    ax.annotate("", xy=(7.2, 1.85), xytext=(6.6, 1.85), arrowprops=dict(color=GREEN, **kw))
    ax.annotate("", xy=(6.6, 1.33), xytext=(6.0, 1.33), arrowprops=dict(color=BLUE, **kw))     # 反相：方向相反
    ax.annotate("", xy=(6.0, 1.17), xytext=(6.6, 1.17), arrowprops=dict(color=GREEN, **kw))
    ax.text(7.45, 1.85, "→ 2 倍光場、4 倍功率", fontsize=9, va="center", color=GREY)
    ax.text(7.45, 1.25, "→ 0", fontsize=9, va="center", color=GREY)
    ax.plot([3.8, 5.3], [4.6, 4.6], color=ORANGE, lw=2, ls="--")
    ax.text(3.45, 4.6, "R", fontsize=11, va="center", fontweight="bold", color=ORANGE)
    ax.text(4.55, 4.75, "之後加入的參考光", fontsize=8.5, color=ORANGE, ha="center")
    save(fig, paths.FIG("m1", "s1_concept.png"))


def s2():
    fig, ax = frame("一顆、兩顆 MZI 能做幾種邏輯？運算單元為什麼是 7 顆 MZI、4 層？",
                    ["M1 s1：需要參考光 R", "MMI\n（50:50 混合）"],
                    ["B7 的固定接線\n5 條波導、7 顆 MZI", "14 個相位\nθ1–θ7、φ1–φ7", "能做全部 16 種\n二輸入函數"],
                    "像積木：兩顆 MMI 加兩個相位組成可調分光比的 MZI；7 顆 MZI 排成 4 層，就是 B7。")
    # MMI
    box(ax, 3.45, 3.3, 0.7, 1.0, "MMI", ec=GREY, fc="#e9eef5", fs=9)
    ax.text(3.8, 2.95, "固定 50:50", ha="center", fontsize=8.5, color=GREY)
    arrow(ax, (4.25, 3.8), (4.75, 3.8), GREY, 1.5, "＋相位", fs=8.5)
    # MZI
    for y in (4.15, 3.45):
        ax.plot([4.8, 7.0], [y, y], color=BLUE, lw=2)
    box(ax, 5.0, 3.25, 0.4, 1.1, "", ec=GREY, fc="#e9eef5")
    box(ax, 6.35, 3.25, 0.4, 1.1, "", ec=GREY, fc="#e9eef5")
    box(ax, 4.75, 4.05, 0.2, 0.2, "", ec=ORANGE, fc=ORANGE)
    box(ax, 5.65, 4.05, 0.45, 0.2, "", ec=ORANGE, fc=ORANGE)
    ax.text(4.85, 4.45, "φ", ha="center", fontsize=10, color=ORANGE)
    ax.text(5.87, 4.45, "θ", ha="center", fontsize=10, color=ORANGE)
    ax.text(5.9, 2.95, "MZI：θ 調分光比、φ 調相位", ha="center", fontsize=8.5, color=GREY)
    arrow(ax, (7.05, 3.8), (7.45, 3.8), GREY, 1.5, "×7", fs=9)
    # 小 B7
    sub = fig.add_axes([0.52, 0.2, 0.21, 0.46])
    draw_b7(sub, labels=False, fs=7, box_label=lambda k: f"{k}")
    sub.set_title("B7：7 顆 MZI、4 層", fontsize=9, color=PURPLE)
    ax.text(3.5, 1.9, "一顆 MZI：做不出有用的二輸入邏輯", fontsize=9, color=GREY)
    ax.text(3.5, 1.45, "兩顆＋R：大部分可以，但讀取埠要換", fontsize=9, color=GREY)
    ax.text(3.5, 1.0, "B7：固定讀 o2、o4，全部 16 種都做得到", fontsize=9, color=RED)
    save(fig, paths.FIG("m1", "s2_concept.png"))


def s3():
    ph = json.loads(paths.OUT("m1_logic/s5_handoff", "phases.json").read_text(encoding="utf-8"))
    f = ph["functions"]["AND2"]
    U = chain(B7_OPS, f["theta"], f["phi"], 5)
    fig, ax = frame("給定 14 個相位，輸出光場怎麼算？",
                    ["B7 接線", "14 個相位", "輸入光場 v＝\n(x1, x2, x3, x4, R)"],
                    ["計算鏈\nv → y＝U v → ΔP", "ΔP 是輸入的\n二次式"],
                    "光沿每條路徑走：路徑上的係數相乘、所有路徑相加，就是矩陣乘法 y＝U v。")
    x0, y0, c = 4.0, 1.3, 0.58
    A = np.abs(U)
    for i in range(5):
        for j in range(5):
            ax.add_patch(Rectangle((x0 + j * c, y0 + (4 - i) * c), c, c, fc=(0.18, 0.44, 0.71, 0.15 + 0.85 * A[i, j] / A.max()),
                                   ec="white", lw=1))
    ax.text(x0 + 2.5 * c, y0 + 5 * c + 0.2, "U（5×5，顏色＝|u_ij|）", ha="center", fontsize=9.5, color=BLUE)
    ax.text(x0 - 0.25, y0 + 2.5 * c, "U", fontsize=16, ha="right", va="center", color=BLUE, fontweight="bold")
    vx = x0 + 5 * c + 0.35
    for j, t in enumerate(["x1", "x2", "x3", "x4", "R"]):
        box(ax, vx, y0 + (4 - j) * c + 0.05, 0.6, c - 0.1, t, ec=GREEN, fc="#eaf5ee", fs=8.5)
    ax.text(vx + 0.3, y0 + 5 * c + 0.2, "v", ha="center", fontsize=11, color=GREEN, fontweight="bold")
    ax.text(vx + 0.9, y0 + 2.5 * c, "＝", fontsize=16, va="center")
    yx = vx + 1.3
    for i in range(5):
        hit = i in (1, 3)
        box(ax, yx, y0 + (4 - i) * c + 0.05, 0.6, c - 0.1, f"y{i + 1}", ec=RED if hit else GREY,
            fc="#fdecea" if hit else "white", fs=8.5)
    ax.text(yx + 0.3, y0 + 5 * c + 0.2, "y", ha="center", fontsize=11, fontweight="bold")
    ax.text(yx + 0.85, y0 + 2.5 * c + 0.3, "P2＝|y2|²\nP4＝|y4|²\nΔP＝P2 − P4", fontsize=9, va="center", color=RED)
    ax.text(3.45, 4.85, "以 AND2 的相位為例；每個輸出 y_i 都是 5 個輸入的加權和 Σ u_ij v_j", fontsize=9, color=GREY)
    save(fig, paths.FIG("m1", "s3_concept.png"))


def s4():
    fig, ax = frame("同一顆 B7、同一組接線，只換相位就能換函數嗎？",
                    ["計算鏈 v → U v → ΔP", "目標：AND2、OR2、\nXOR2、AND4、OR4"],
                    ["五組 14 個相位", "80 組真值表\n（每個函數 16 組）"],
                    "硬體不變，換一組相位就是換一個函數：這就是「可程式化」。")
    names = ["AND2", "OR2", "XOR2", "AND4", "OR4"]
    cols = [BLUE, GREEN, PURPLE, ORANGE, GREY]
    box(ax, 6.2, 1.4, 1.6, 3.2, "同一顆 B7\n（接線不變）", ec=PURPLE, fc="#f3eefa", fs=10, bold=True)
    for k, (n, c) in enumerate(zip(names, cols)):
        y = 4.3 - 0.72 * k
        box(ax, 3.45, y - 0.25, 2.1, 0.5, f"相位設定：{n}", ec=c, fc="white", fs=8.8)
        ax.add_patch(Circle((5.35, y), 0.13, fc=c, ec="none"))
        arrow(ax, (5.55, y), (6.2, 3.0 + (2 - k) * 0.25), c, 1.1)
        arrow(ax, (7.8, 3.0 + (2 - k) * 0.25), (8.4, y), c, 1.1)
        box(ax, 8.4, y - 0.25, 2.2, 0.5, f"{n} 的真值表 16/16", ec=c, fc="white", fs=8.8)
    ax.text(4.5, 0.95, "每組 14 個相位由最佳化找出（讓 margin 最大）", fontsize=8.8, color=GREY, ha="center")
    ax.text(9.5, 0.95, "相位不準時還對嗎？也一起檢查", fontsize=8.8, color=GREY, ha="center")
    save(fig, paths.FIG("m1", "s4_concept.png"))


def s5():
    fig, ax = frame("怎樣把「固定光路」和「功能設定」分開，讓別人只拿檔案就能重算？",
                    ["B7 接線", "五組相位", "80 組真值表"],
                    ["三個交接檔", "獨立重算 80/80\n竄改會被抓到"],
                    "光路寫一次、功能設定可替換、再附上答案：拿到的人不必讀程式，也能自己驗算。")
    files = [("b7_netlist.json", "固定光路\n（不會變）", BLUE), ("phases.json", "功能設定\n（可替換）", ORANGE),
             ("truth_tables.csv", "驗收答案", GREEN)]
    for k, (fn, t, c) in enumerate(files):
        x = 3.5 + 1.75 * k
        box(ax, x, 2.6, 1.5, 1.9, f"{fn}\n\n{t}", ec=c, fc="white", fs=8.5)
        ax.add_patch(Rectangle((x + 1.15, 4.15), 0.35, 0.35, fc=c, alpha=0.25, ec="none"))
    ax.annotate("", xy=(3.5 + 1.75 + 0.3, 2.6), xytext=(3.5 + 1.2, 2.6),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.4, connectionstyle="arc3,rad=0.5"))
    ax.text(5.0, 1.75, "SHA-256 綁定：相位只對這份接線有效", fontsize=8.8, color=RED, ha="center")
    box(ax, 8.95, 2.6, 1.7, 1.9, "下一步／別人\n\n只用三個檔案\n重算真值表", ec=PURPLE, fc="#f3eefa", fs=8.8)
    arrow(ax, (8.75, 3.55), (8.95, 3.55), PURPLE, 1.6)
    ax.text(9.8, 1.75, "結果與答案比對", fontsize=8.8, color=PURPLE, ha="center")
    save(fig, paths.FIG("m1", "s5_concept.png"))


def main():
    for f in (s1, s2, s3, s4, s5):
        f()
    print("寫出 figures/m1/s1_concept.png … s5_concept.png")


if __name__ == "__main__":
    main()
