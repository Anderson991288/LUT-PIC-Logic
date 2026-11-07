r"""論文 M1 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M1 各步的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/paper/m1/s1_concept.png、figures/paper/m1/s2_concept.png、figures/paper/m1/s3_concept.png、figures/paper/m1/s4_concept.png、figures/paper/m1/s5_concept.png、figures/paper/m1/flow.png（論文延伸的流程）。
執行：.\lab design\paper\m1_timing\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, PURPLE, RED, arrow, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("現有晶片要以 10 Gb/s（每 100 ps 一個位元）運作，時序、功率、相位各差多少？",
                    ["交付的佈局幾何\n每段波導多長", "校正後的 margin\n（最難的函數）", "課程 M1 的相位\n（含損耗重新校正）"],
                    ["budget.json\n三項預算", "要改的地方：\n交給 M1 s2"],
                    "三項都用「需要多少、現在有多少」比較；在宣告的模型下，晶片內 skew 很小，要求最嚴的是 5 根光纖之間的相位。")
    # 中間：片外 5 根光纖 → 晶片 → 2 個偵測器
    for k in range(5):
        y = 4.55 - 0.32 * k
        ax.plot([3.55, 5.0], [y, y], color=ORANGE, lw=1.6)
        ax.text(3.5, y, ["x1", "x2", "x3", "x4", "R"][k], ha="right", va="center", fontsize=8.5)
    ax.text(4.95, 4.9, "片外：5 根光纖各自送光", ha="right", fontsize=8.8, color=ORANGE)
    box(ax, 5.0, 3.05, 1.9, 1.75, "晶片\nB7 核心", ec=BLUE, fc="#eaf1fa", fs=9.5)
    for y in (4.1, 3.6):
        ax.plot([6.9, 7.6], [y, y], color=BLUE, lw=1.6)
    box(ax, 7.6, 3.35, 1.1, 1.0, "偵測器\n比大小", ec=GREY, fs=8.5)
    ax.text(7.25, 4.25, "o2、o4", ha="center", fontsize=8.5)
    rows = [("時序", "到達時間差是否小於取樣窗允許的值", "晶片內 < 1 ps：夠", GREEN),
            ("功率", "偵測器要多少 → 反推每根光纖", "幾 dBm：夠", GREEN),
            ("相位", "5 根光纖的相對相位能否穩住", "要 mK 級溫控：不夠", RED)]
    for k, (t, q, a, c) in enumerate(rows):
        y = 2.45 - 0.58 * k
        box(ax, 3.5, y - 0.22, 0.9, 0.44, t, ec=c, fc="white", fs=10, bold=True, color=c)
        ax.text(4.55, y, q, va="center", fontsize=9)
        ax.text(10.55, y, a, va="center", ha="right", fontsize=9.5, color=c, fontweight="bold")
    arrow(ax, (8.7, 3.85), (9.9, 3.85), GREY, 1.4, "判讀", fs=8.5)
    ax.text(10.1, 3.85, "0／1", va="center", fontsize=9.5, color=PURPLE)
    save(fig, paths.FIG("paper/m1", "s1_concept.png"))


def s2():
    fig, ax = frame("發射端「0」不全暗的殘留光會占去 margin；能不能只靠重新求 heater 相位吸收（靜態校正）？",
                    ["M1 s1：三項預算\n（相位要求最嚴）", "課程 M1 的 5 組相位", "課程 M2 s1 的輸入相位容許"],
                    ["interface_v2.json\n消光比需求", "介面規格草稿\n（M1 s5 整合）"],
                    "殘留是固定的誤差：量到之後重新求 heater 相位就能吸收大部分（靜態校正），晶片不加元件。")
    box(ax, 3.45, 3.6, 1.6, 1.2, "片外發射端\n（同一顆雷射\n＋4 路調變）", ORANGE, "#fbf3df", fs=8.5)
    for k, y in enumerate((4.6, 4.35, 4.1, 3.85, 3.6)):
        ax.plot([5.05, 6.6], [y, y], color=ORANGE, lw=1.2)
    ax.text(5.8, 4.75, "x1–x4、R", ha="center", fontsize=8.5)
    box(ax, 6.6, 3.45, 1.6, 1.3, "晶片：B7\n（只有 heater MZI，\n不變）", BLUE, "#eaf1fa", fs=8.5)
    # 「0」不是全暗：示意兩個位準
    ax.plot([8.6, 8.9, 8.9, 9.5, 9.5, 9.8], [3.75, 3.75, 4.55, 4.55, 3.75, 3.75], color=GREEN, lw=1.6)
    ax.plot([8.6, 9.8], [3.62, 3.62], color=GREY, lw=0.8, ls=":")
    ax.text(9.2, 4.65, "「1」", ha="center", fontsize=8.5)
    ax.text(9.95, 3.68, "「0」的殘留", fontsize=8.5, color=RED, va="center")
    rows = [("殘留光", "「0」的殘留和參考光干涉：沿用原相位時占去多少 margin？", RED),
            ("重新求相位", "殘留是固定偏移：只調 heater 重新求 14 個相位，能補回多少？", BLUE),
            ("消光比需求", "保留 90% margin 要多少 dB → M1 s4 驗收、M1 s5 整合成規格", GREEN)]
    for k, (t, q, c) in enumerate(rows):
        y = 2.5 - 0.55 * k
        box(ax, 3.5, y - 0.21, 1.25, 0.42, t, ec=c, fc="white", fs=9.5, bold=True, color=c)
        ax.text(4.9, y, q, va="center", fontsize=9)
    save(fig, paths.FIG("paper/m1", "s2_concept.png"))

def s3():
    fig, ax = frame("只用晶片上原有的 heater MZI，能不能一邊傳資料、一邊追上輸入光的相位漂移？",
                    ["M1 s1：相位要求最嚴\n（光纖會慢慢漂）", "課程 M1 的 5 組相位", "M1 s1 的接收端雜訊"],
                    ["tracking.json\n追蹤方法與頻寬", "對發射端的要求：\n快的相位擾動要小"],
                    "只調 7 個 φ 就補得回來；平均功率量不出漂移，給 heater 一個小擺動再同步偵測就量得出。")
    box(ax, 3.45, 3.7, 1.2, 1.0, "片外 5 路光\n（相位慢漂）", ORANGE, "#fbf3df", fs=8.5)
    arrow(ax, (4.65, 4.2), (5.2, 4.2), ORANGE, 1.4)
    box(ax, 5.2, 3.55, 1.7, 1.3, "B7\n7 個 φ heater\n（加小擺動）", BLUE, "#eaf1fa", fs=8.5)
    arrow(ax, (6.9, 4.2), (7.45, 4.2), BLUE, 1.4)
    box(ax, 7.45, 3.7, 1.35, 1.0, "5 個輸出的\n平均功率與\n擺動響應", GREEN, "#eaf6ea", fs=8.5)
    ax.annotate("", xy=(6.05, 3.5), xytext=(8.1, 3.65), arrowprops=dict(arrowstyle="-|>", color=PURPLE, lw=1.4,
                                                                       connectionstyle="arc3,rad=-0.4"))
    ax.text(7.1, 2.85, "估計漂移 → 只調 φ 補回", ha="center", fontsize=8.8, color=PURPLE)
    rows = [("補得回來嗎", "只調 7 個外相位 φ，margin 能否回到無漂移時", BLUE),
            ("量得出來嗎", "平均功率 vs 加上 heater 擺動：能分辨幾個相位", GREEN),
            ("追得上嗎", "量測要平均多久 → 回授頻寬 → 能追多快的漂移", RED)]
    for k, (t, q, c) in enumerate(rows):
        y = 2.3 - 0.55 * k
        box(ax, 3.5, y - 0.21, 1.35, 0.42, t, ec=c, fc="white", fs=9.5, bold=True, color=c)
        ax.text(5.0, y, q, va="center", fontsize=9)
    save(fig, paths.FIG("paper/m1", "s3_concept.png"))

def s4():
    fig, ax = frame("輸入一直在變（每 100 ps 一組）時，轉態、skew 與消光比會占去多少可取樣的時間？",
                    ["M1 s1：一階估計\nskew 容許約 18.7 ps", "M1 s2：消光比規格", "課程 M1 的 5 組相位"],
                    ["window.json\n功率代價與 skew", "時間對齊規格\n（寫回 M1 s2）"],
                    "轉態與接收端頻寬本身就占去約 1 dB；skew 再加 1 dB 的點在約 18 ps，和一階估計同一量級（準則不同）。")
    import numpy as np
    t = np.linspace(0, 3, 300)
    for k, (y0, d) in enumerate(((4.55, 0.0), (4.25, 0.12), (3.95, 0.05))):
        e = np.clip((t - 1 - d) / 0.35, 0, 1)
        ax.plot(3.5 + t * 0.9, y0 + 0.22 * (1 - np.cos(np.pi * e)) / 2, color=ORANGE, lw=1.4)
    ax.text(4.85, 4.95, "x1–x4 的轉態（各差一點時間）", ha="center", fontsize=8.8, color=ORANGE)
    arrow(ax, (6.3, 4.3), (6.8, 4.3), GREY, 1.4)
    box(ax, 6.8, 3.85, 1.3, 0.9, "B7 干涉\n＋接收端濾波", BLUE, "#eaf1fa", fs=8.5)
    arrow(ax, (8.1, 4.3), (8.5, 4.3), GREY, 1.4)
    tt = np.linspace(-1, 1, 100)
    ax.plot(8.6 + (tt + 1) * 0.9, 3.95 + 0.7 * np.clip(1 - tt ** 2 * 2.2, -0.2, 1), color=PURPLE, lw=1.6)
    ax.add_patch(__import__("matplotlib").patches.Rectangle((9.3, 3.9), 0.4, 0.8, fc="#e8e0f5", ec="none", zorder=0))
    ax.text(9.5, 3.6, "取樣窗", ha="center", fontsize=8.5, color=PURPLE)
    rows = [("轉態＋頻寬", "各路同時到達時，取樣窗內的 margin 剩多少", BLUE),
            ("skew", "各路延遲 0–40 ps（16 個角落取最差），代價怎麼增加", RED),
            ("消光比", "「0」的殘留光在轉態時會不會多占去 margin", GREEN)]
    for k, (tt_, q, c) in enumerate(rows):
        y = 2.5 - 0.55 * k
        box(ax, 3.5, y - 0.21, 1.35, 0.42, tt_, ec=c, fc="white", fs=9.5, bold=True, color=c)
        ax.text(5.0, y, q, va="center", fontsize=9)
    save(fig, paths.FIG("paper/m1", "s4_concept.png"))

def s5():
    fig, ax = frame("整合成介面規格與總功率預算；作為完整版研究的簡化版，要強調哪幾個重點？",
                    ["M1 s1–s4 的結果\n（四個 JSON）", "完整版研究的\n三項貢獻"],
                    ["assess.json\n逐函數預算、三個重點", "介面規格、\n待解風險"],
                    "只留三個重點：時序分析、靜態校正、動態校正與校正後驗收；其餘壓縮成一句或一張表。")
    pts = [("重點一\n時序分析", BLUE), ("重點二\n靜態校正", GREEN), ("重點三\n動態校正與\n校正後驗收", PURPLE)]
    for k, (t_, c_) in enumerate(pts):
        box(ax, 3.6 + k * 2.4, 3.6, 2.1, 1.25, t_, ec=c_, fc="white", fs=10, bold=True, color=c_)
    box(ax, 3.6, 2.45, 7.0, 0.7, "壓縮：佈局 skew（不需補長）、延遲盒認證　｜　省略：串接、Monte Carlo、頻寬掃描", GREY, "#f6f6f2", fs=9)
    box(ax, 3.6, 1.35, 3.35, 0.75, "介面規格（7 項）\n逐函數總功率預算", ORANGE, "#fbf3df", fs=9)
    box(ax, 7.25, 1.35, 3.35, 0.75, "待解風險 X1–X6", RED, "#fde8e8", fs=9)
    save(fig, paths.FIG("paper/m1", "s5_concept.png"))

def flow():
    """論文延伸的流程：先用預算找問題，再用兩種校正處理兩類誤差，最後在校正後的條件下驗收時序並整合。"""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13.5, 4.6))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    steps = [("M1 s1", "10 Gb/s 預算\n問題在哪", "相位要求最嚴\n（模型下）", GREY, "時序分析（一階）"),
             ("M1 s2", "消光比的\n相位重解", "固定誤差：\n重新求相位吸收", BLUE, "靜態校正"),
             ("M1 s3", "輸入相位\n追蹤", "會漂的誤差：\n擺動＋同步偵測", GREEN, "動態校正"),
             ("M1 s4", "校正後的\n10 Gb/s 取樣窗", "完整時域模型\n驗收 skew 規格", PURPLE, "時序分析（完整）"),
             ("M1 s5", "介面規格、總預算\n與論文評估", "整合成規格\n與論文主張", ORANGE, "整合")]
    for k, (tag, title, res, c, part) in enumerate(steps):
        x = 0.2 + 2.68 * k
        box(ax, x, 1.9, 2.25, 1.35, title, ec=c, fc="white", fs=10.5, bold=True, color=c)
        ax.text(x + 1.125, 3.42, f"{tag}｜{part}", ha="center", fontsize=9.2, color=c)
        ax.text(x + 1.125, 1.45, res, ha="center", va="center", fontsize=9)
        if k < 4:
            arrow(ax, (x + 2.27, 2.57), (x + 2.66, 2.57), GREY, 1.6)
    ax.add_patch(__import__("matplotlib").patches.FancyBboxPatch((2.75, 0.55), 5.25, 0.42, boxstyle="round,pad=0.02",
                                                                 fc="#eef6ee", ec=GREEN, lw=1))
    ax.text(5.375, 0.76, "校正：只用晶片上原有的 heater，不加元件", ha="center", va="center", fontsize=9.5, color=GREEN)
    ax.text(6.75, 4.25, "論文延伸的流程：先找問題 → 兩種校正處理兩類誤差 → 在校正後的條件下驗收時序 → 整合", ha="center",
            fontsize=11.5, fontweight="bold")
    save(fig, paths.FIG("paper/m1", "flow.png"))

if __name__ == "__main__":
    s1()
    s2()
    s3()
    s4()
    s5()
    flow()
    print("寫出 figures/paper/m1/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png、s5_concept.png、flow.png")
