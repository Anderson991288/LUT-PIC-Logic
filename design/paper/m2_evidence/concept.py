r"""論文 M2 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M2 各步的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/paper/m2/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png、s5_concept.png。
執行：.\lab design\paper\m2_evidence\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, RED, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("只數 MZI 的延遲與損耗（固定加總），能不能預測 10 Gb/s 下的結果？",
                    ["固定加總的指標\n每顆 MZI 1 ps、0／1／3 dB", "M1 的時域流程結果\n（取樣窗、預算、校正）"],
                    ["baseline.json\n兩種預測的對照", "論文的比較基準"],
                    "同一顆 B7、同一組情境，兩種模型的預測逐項對照；不同之處就是時域流程必須存在的理由。")
    box(ax, 4.75, 4.15, 2.75, 0.55, "固定加總", ec=GREY, fc="#f1f2f4", fs=10.5, bold=True)
    box(ax, 7.7, 4.15, 2.8, 0.55, "時域流程", ec=BLUE, fc="#eaf1fa", fs=10.5, bold=True, color=BLUE)
    rows = [("skew\n容許", "UI − 邊緣 − 取樣\n各函數相同", "看干涉的取樣窗\n各函數不同"),
            ("功率", "數路徑上的 MZI", "由 margin 與雜訊反推"),
            ("相位\n殘留光", "沒有這兩項", "margin 下降，需要校正")]
    for k, (t, a, b) in enumerate(rows):
        y = 3.55 - 0.85 * k
        box(ax, 3.75, y - 0.33, 0.85, 0.66, t, ec=GREY, fc="#f7f7f7", fs=9, bold=True)
        box(ax, 4.75, y - 0.33, 2.75, 0.66, a, ec=GREY, fs=9)
        box(ax, 7.7, y - 0.33, 2.8, 0.66, b, ec=BLUE, fs=9, color=BLUE if k < 2 else RED)
    save(fig, paths.FIG("paper/m2", "s1_concept.png"))


def s2():
    fig, ax = frame("M1 的規格散在各步、修正後有幾項失去餘裕：整理成一張表，每項離失效還有多遠？",
                    ["M1 s1–s5 的結果\n（修正後）", "M2 s1 的各函數\nskew 容許"],
                    ["spec.json\n規格、依據、餘裕", "操作模式表\n（何時做哪種校正）"],
                    "每一項規格都要寫出依據的數字與餘裕；沒有餘裕或尚未建模的，明白列出來。")
    rows = [("時間對齊", "≤ 15 ps（1 dB 點 18 ps）", "餘裕 1.2 倍", ORANGE),
            ("監測偵測器", "5 個都要（只用 2 個追不上）", "餘裕 1.3 倍", ORANGE),
            ("相對相位", "幅度相加 ≤ 0.10 rad", "用滿", ORANGE),
            ("初始對準", "啟動時拉進追蹤範圍", "未建模", RED)]
    for k, (t, a, st, c) in enumerate(rows):
        y = 4.2 - 0.78 * k
        box(ax, 3.75, y - 0.3, 1.5, 0.6, t, ec=GREY, fc="#f7f7f7", fs=9, bold=True)
        box(ax, 5.4, y - 0.3, 3.4, 0.6, a, ec=GREY, fs=9)
        box(ax, 8.95, y - 0.3, 1.55, 0.6, st, ec=c, fs=9, bold=True, color=c)
    save(fig, paths.FIG("paper/m2", "s2_concept.png"))


def s3():
    fig, ax = frame("相位偏差讓取樣窗消失時，多給光能不能救回來？要多給多少？",
                    ["M1 s4 的時域模型\n（取樣窗）", "M1 s1 的雜訊模型\n（反推 P_u）"],
                    ["power.json\nP_u,min(δ) 與 W(P_u)", "相位與功率的分界"],
                    "窗內 margin 仍為正：加光可補；窗內已判錯：加光無效，只能校正。")
    rows = [("窗內 margin > 0", "判讀方向都對、只是太小", "加光可補", GREEN),
            ("窗內 margin ≤ 0", "窗內某時刻判讀方向錯了", "只能校正", RED)]
    for k, (t, a, st, c) in enumerate(rows):
        y = 3.9 - 1.1 * k
        box(ax, 3.75, y - 0.4, 1.9, 0.8, t, ec=c, fc="white", fs=9.5, bold=True, color=c)
        box(ax, 5.8, y - 0.4, 3.0, 0.8, a, ec=GREY, fs=9)
        box(ax, 8.95, y - 0.4, 1.55, 0.8, st, ec=c, fs=9.5, bold=True, color=c)
    save(fig, paths.FIG("paper/m2", "s3_concept.png"))


def s4():
    fig, ax = frame("用名義模型設計與校正、用有 MMI 分光誤差的硬體驗收，結果還一致嗎？",
                    ["名義模型的相位\n（M1 s2）", "名義模型的校正迴路\n（M1 s3）"],
                    ["deviation.json\n硬體上的 margin 與功率", "校正與驗收\n不一致之處"],
                    "驗收要在硬體上做：名義模型自己驗收自己，看不出模型偏差。")
    box(ax, 3.75, 3.6, 2.0, 0.9, "硬體\n每顆 MMI 分光 50% ± 3%", ec=RED, fs=9, color=RED)
    rows = [("名義相位", "直接用"), ("名義校正迴路", "只調 7 個 φ"), ("參考解", "已知硬體，調 14 個相位")]
    for k, (t, a) in enumerate(rows):
        y = 4.3 - 0.85 * k
        box(ax, 6.2, y - 0.32, 1.9, 0.64, t, ec=BLUE, fs=9.5, bold=True, color=BLUE)
        box(ax, 8.25, y - 0.32, 2.25, 0.64, a, ec=GREY, fs=9)
    box(ax, 3.75, 1.2, 6.75, 0.6, "在硬體上驗收：23 ps 窗內 margin、所需 P_u（同聯合驗收：含 δ_det 與擺動）", ec=ORANGE, fs=9.5)
    save(fig, paths.FIG("paper/m2", "s4_concept.png"))


def s5():
    fig, ax = frame("同一套流程能不能用在 B7 能做的所有函數？每一步要算多久？",
                    ["14 個二輸入函數\n（重新合成）", "AND4、OR4\n（M1 的相位）"],
                    ["general.json\n每個函數六步的結果", "各步執行時間"],
                    "流程結構不變，合成結果以取反等價交叉核對；決定光功率的是 XOR 類函數。")
    steps = ["合成", "功率", "時序", "靜態校正", "可觀測性", "聯合驗收"]
    for k, t in enumerate(steps):
        box(ax, 3.75 + 1.15 * k, 3.6, 1.0, 0.7, t, ec=BLUE, fs=9, bold=True, color=BLUE)
    box(ax, 3.75, 2.3, 6.75, 0.7, "每個函數依序做六步；平行執行，每個函數一個工作", ec=GREY, fs=9.5)
    save(fig, paths.FIG("paper/m2", "s5_concept.png"))


if __name__ == "__main__":
    s1()
    s2()
    s3()
    s4()
    s5()
    print("寫出 figures/paper/m2/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png、s5_concept.png")
