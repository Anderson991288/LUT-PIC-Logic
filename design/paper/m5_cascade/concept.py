r"""論文 M5 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M5 各步的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/paper/m5/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png。
執行：.\lab design\paper\m5_cascade\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, RED, arrow, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("4 顆 macro 不在中間判讀，光場直接送到下一級，能做 8 輸入函數嗎？",
                    ["M3 s2 的合成\n（soft-min、0.9 dB／MZI）", "M4 的二次式判讀"],
                    ["cascade.json\n14 個函數、8 組配對", "M5 s2 的補長度選擇"],
                    "前級只做線性運算、不判讀，後級看到的仍是 8 路光場的干涉；能做的函數由後級的二次式決定。")
    box(ax, 3.5, 4.05, 1.5, 0.6, "x1–x4", ec=BLUE, fs=9.5)
    box(ax, 3.5, 2.85, 1.5, 0.6, "x5–x8", ec=BLUE, fs=9.5)
    box(ax, 5.4, 3.95, 1.5, 0.8, "前級\nMacro 1", ec=GREY, fs=9.5)
    box(ax, 5.4, 2.75, 1.5, 0.8, "前級\nMacro 2", ec=GREY, fs=9.5)
    arrow(ax, (5.05, 4.35), (5.35, 4.35))
    arrow(ax, (5.05, 3.15), (5.35, 3.15))
    box(ax, 7.9, 3.95, 1.5, 0.8, "後級\nMacro 3", ec=ORANGE, fs=9.5, color=ORANGE)
    box(ax, 7.9, 2.75, 1.5, 0.8, "後級\nMacro 4", ec=RED, fs=9.5, color=RED)
    for y0 in (4.35, 3.15):
        arrow(ax, (6.95, y0 + 0.15), (7.85, 4.45), color=ORANGE, lw=1.2)
        arrow(ax, (6.95, y0 - 0.15), (7.85, 3.05), color=RED, lw=1.2)
    ax.text(7.4, 4.95, "光場直送、不判讀", ha="center", va="center", fontsize=8.5, color=GREY)
    box(ax, 9.65, 3.95, 1.0, 0.8, "判讀\nf", ec=ORANGE, fs=9, color=ORANGE)
    box(ax, 9.65, 2.75, 1.0, 0.8, "判讀\ng", ec=RED, fs=9, color=RED)
    arrow(ax, (9.45, 4.35), (9.6, 4.35))
    arrow(ax, (9.45, 3.15), (9.6, 3.15))
    box(ax, 3.5, 1.2, 3.4, 0.95, "單判讀：Macro 1、2、4\n21 顆 MZI、42 個相位", ec=GREY, fs=9)
    box(ax, 7.2, 1.2, 3.45, 0.95, "雙判讀：四顆一起\n兩個函數 f、g 聯合指派", ec=GREEN, fs=9, color=GREEN)
    save(fig, paths.FIG("paper/m5", "s1_concept.png"))


def s2():
    fig, ax = frame("輸入線長不一時要不要加蛇形？加多少？",
                    ["M5 s1 與 M3 s2 的相位", "M3 s3 的詳細模擬"],
                    ["meander.json\n選擇、窗寬、評估次數", "M5 s3 的串接盒證明"],
                    "蛇形同時延遲與衰減光場；從短到長逐一驗收，選第一個通過的，不追求完全等長。")
    box(ax, 3.5, 4.0, 2.0, 0.75, "早到的線\n補 κ(δ_max − δ_g)", ec=BLUE, fs=9)
    box(ax, 5.8, 4.0, 2.2, 0.75, "延遲 ＋n_g ΔL/c\n振幅 ×10^(−αΔL/20)", ec=ORANGE, fs=9, color=ORANGE)
    box(ax, 8.3, 4.0, 2.3, 0.75, "所有角落的\n詳細模擬窗", ec=GREY, fs=9)
    arrow(ax, (5.55, 4.37), (5.75, 4.37))
    arrow(ax, (8.05, 4.37), (8.25, 4.37))
    box(ax, 3.5, 2.55, 7.1, 0.85, "候選依總長排序：0 mm → … → 完整等長\n第一個「最差角落窗 ≥ T_req」即為選擇", ec=RED, fs=10.5, bold=True, color=RED)
    box(ax, 3.5, 1.15, 3.4, 0.9, "草稿表 IV：9 個案例\n（都不需要蛇形）", ec=GREY, fs=9)
    box(ax, 7.2, 1.15, 3.4, 0.9, "壓力案例：線長差放大\n（零長度不過時選什麼）", ec=GREEN, fs=9, color=GREEN)
    save(fig, paths.FIG("paper/m5", "s2_concept.png"))


def s3():
    fig, ax = frame("兩級串接後，13.2 ps 盒的保證窗還有多寬？",
                    ["M4 s2、s3 的盒證明\n（4 路）", "M5 s1 的相位\nM5 s2 的串接映射"],
                    ["cert_cascade.json\n認證窗與驗證", "M5 s4 的全類別篩選"],
                    "中間不判讀，後級讀到的光場仍是 8 路包絡的線性組合；判讀量還是二次式，證明只要把 4 路換成 8 路。")
    box(ax, 3.5, 3.95, 2.0, 0.8, "8 路包絡\nx1–x8", ec=BLUE, fs=9.5)
    arrow(ax, (5.55, 4.35), (6.05, 4.35))
    box(ax, 6.1, 3.95, 2.0, 0.8, "前級＋後級\ny＝M x＋c", ec=GREY, fs=9.5)
    arrow(ax, (8.15, 4.35), (8.65, 4.35))
    box(ax, 8.7, 3.95, 1.9, 0.8, "D＝d0＋lᵀx\n＋xᵀQx", ec=ORANGE, fs=9.5, color=ORANGE)
    box(ax, 3.5, 2.55, 7.1, 0.85, "M4 的葉盒下界與時變護欄：4 路 → 8 路（每路 ±6.6 ps）", ec=RED, fs=10.5, bold=True, color=RED)
    box(ax, 3.5, 1.15, 3.4, 0.9, "回歸：同一程式用在 AND4\n要得到 M4 的結果", ec=GREY, fs=9)
    box(ax, 7.2, 1.15, 3.4, 0.9, "宣告的抽樣序列\n（8 路的全部歷史太長）", ec=GREEN, fs=9, color=GREEN)
    save(fig, paths.FIG("paper/m5", "s3_concept.png"))


def s4():
    fig, ax = frame("靜態可實現的 4 輸入類別，有多少在 10 Gb/s 下真的有取樣窗？",
                    ["M3 s2 的合成\nM3 s3 的詳細模擬", "M5 s3 的「輸入係數」\n盒證明"],
                    ["screen.json\n每類三層結果", "M6 製程與校正"],
                    "先只用靜態量推測，再逐類實際驗收；認證不過記為「未確認」，不是失敗。")
    box(ax, 3.5, 3.95, 2.2, 0.8, "第 0 層：靜態\n222 類合成", ec=GREY, fs=9.5)
    arrow(ax, (5.75, 4.35), (6.05, 4.35))
    box(ax, 6.1, 3.95, 2.2, 0.8, "第 1 層：動態\n對齊與盒內 41 點", ec=BLUE, fs=9.5, color=BLUE)
    arrow(ax, (8.35, 4.35), (8.65, 4.35))
    box(ax, 8.7, 3.95, 1.9, 0.8, "第 2 層：認證\n單葉→切細", ec=RED, fs=9.5, color=RED)
    box(ax, 3.5, 2.55, 7.1, 0.85, "推測：只看靜態量（margin、m／g、有效輸入數），在動態結果之前先寫下", ec=ORANGE, fs=10.5, bold=True, color=ORANGE)
    box(ax, 3.5, 1.15, 3.4, 0.9, "校正組：表 I 的 9 個函數\n擬合「靜態量 → 窗」", ec=GREY, fs=9)
    box(ax, 7.2, 1.15, 3.4, 0.9, "檢驗：推測與實際的\n混淆表、推測錯的類別", ec=GREEN, fs=9, color=GREEN)
    save(fig, paths.FIG("paper/m5", "s4_concept.png"))


if __name__ == "__main__":
    s1()
    s2()
    s3()
    s4()
    print("寫出 figures/paper/m5/s1_concept.png … s4_concept.png")
