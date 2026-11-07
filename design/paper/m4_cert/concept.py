r"""論文 M4 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M4 各步的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/paper/m4/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png。
執行：.\lab design\paper\m4_cert\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, RED, arrow, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("偵測功率差 D 是輸入包絡的精確二次式嗎？哪一項讓 XOR 成立？",
                    ["M3 s2 的相位\n（0.9 dB／MZI）", "M3 s3 的包絡\n（含轉態中間值）"],
                    ["quad.json\nd0、l、Q 與誤差", "M4 s2 的葉盒下界"],
                    "光場是線性的、偵測器取平方，所以 D 恰好是二次式；證明可以從它出發。")
    box(ax, 3.6, 3.75, 2.0, 0.75, "輸入包絡\nx1…x4、R", ec=BLUE, fs=9.5)
    arrow(ax, (5.65, 4.12), (6.35, 4.12))
    box(ax, 6.4, 3.75, 1.6, 0.75, "B7\n線性 U", ec=GREY, fs=9.5)
    arrow(ax, (8.05, 4.12), (8.75, 4.12))
    box(ax, 8.8, 3.75, 1.8, 0.75, "偵測器\n|·|² 相減", ec=GREY, fs=9.5)
    box(ax, 3.6, 2.35, 7.0, 0.8, "D(x)＝d0 ＋ lᵀx ＋ xᵀQx", ec=RED, fs=13, bold=True, color=RED)
    box(ax, 3.6, 1.1, 2.2, 0.85, "d0：參考光自己", ec=GREY, fs=9)
    box(ax, 6.0, 1.1, 2.2, 0.85, "l：參考光 × 資料", ec=GREEN, fs=9, color=GREEN)
    box(ax, 8.4, 1.1, 2.2, 0.85, "Q：資料 × 資料\n（XOR 靠它）", ec=ORANGE, fs=9, color=ORANGE)
    save(fig, paths.FIG("paper/m4", "s1_concept.png"))


def s2():
    fig, ax = frame("給一個延遲盒，判讀量的下界怎麼算才保守？",
                    ["M4 s1 的二次式\nd0、l、Q", "M3 s3 的模擬器\n與 41 個抽樣點"],
                    ["leaf.json\n各項與驗證", "M4 s3 的認證窗"],
                    "從葉盒中心展開：一階項先濾波再取絕對值，二階與曲率放進餘項；切小葉盒，兩項都變小。")
    box(ax, 3.6, 3.75, 2.2, 0.75, "葉盒中心的\n判讀量 h∗D(x̂)", ec=BLUE, fs=9.5)
    box(ax, 6.0, 3.75, 2.2, 0.75, "− 一階項\nΣρ|h∗(g ẋ)|", ec=ORANGE, fs=9.5, color=ORANGE)
    box(ax, 8.4, 3.75, 2.2, 0.75, "− 餘項 |h|∗R\n− E_w", ec=GREEN, fs=9.5, color=GREEN)
    box(ax, 3.6, 2.35, 7.0, 0.8, "下界 ≥ 盒內護欄上界（任意延遲、任意時刻）＋ E_in ＋ E_btw", ec=RED, fs=11, bold=True, color=RED)
    box(ax, 3.6, 1.1, 3.3, 0.85, "驗證：41 個抽樣點\n下界都不超過模擬值", ec=GREY, fs=9)
    box(ax, 7.3, 1.1, 3.3, 0.85, "1 葉 → 16 葉\n一階項、餘項都變小", ec=GREY, fs=9)
    save(fig, paths.FIG("paper/m4", "s2_concept.png"))


def s3():
    fig, ax = frame("整個 13.2 ps 盒、所有資料歷史下，共同取樣窗至少多寬？",
                    ["M4 s2 的下界\n與盒內護欄上界", "M3 s3 的\n41 點共同窗"],
                    ["cert.json\n認證窗與每側餘裕", "M4 s4 的 UI 預算"],
                    "下界減護欄減連續時間誤差 ≥ 0 的最長區間就是認證窗；它是保證值，必須不大於任何抽樣結果。")
    box(ax, 3.6, 3.75, 2.2, 0.75, "下界 V̲\n（各葉盒取最小）", ec=BLUE, fs=9.5)
    box(ax, 6.0, 3.75, 2.2, 0.75, "− 護欄上界 Γ̄\n− E_in − E_btw", ec=ORANGE, fs=9.5, color=ORANGE)
    box(ax, 8.4, 3.75, 2.2, 0.75, "− 較舊符號\n（全部歷史時）", ec=GREEN, fs=9.5, color=GREEN)
    box(ax, 3.6, 2.35, 7.0, 0.8, "認證窗 W＝最長的「全部 ≥ 0」區間；W ≥ T_req 即通過", ec=RED, fs=11, bold=True, color=RED)
    box(ax, 3.6, 1.1, 3.3, 0.85, "情境序列：1、16、256 葉", ec=GREY, fs=9)
    box(ax, 7.3, 1.1, 3.3, 0.85, "全部歷史：de Bruijn\nB(16,3)、B(16,4)", ec=GREY, fs=9)
    save(fig, paths.FIG("paper/m4", "s3_concept.png"))


def s4():
    fig, ax = frame("一個 UI 由哪些效應占去？接收端頻寬與位元率改變時，窗還夠嗎？",
                    ["M3 s3 的模擬器\n與盒內 41 點", "M4 s3 的認證窗"],
                    ["budget_ui.json\nsens.json", "M5 串接與補長度"],
                    "UI 預算要一路扣到保證值；只看一組延遲的窗，會高估頻寬與位元率的餘裕。")
    box(ax, 3.6, 3.75, 1.6, 0.75, "邊緣與 ISI", ec=GREY, fs=9.5)
    box(ax, 5.4, 3.75, 1.6, 0.75, "雜訊護欄", ec=RED, fs=9.5, color=RED)
    box(ax, 7.2, 3.75, 1.6, 0.75, "skew\n（一組）", ec=ORANGE, fs=9.5, color=ORANGE)
    box(ax, 9.0, 3.75, 1.6, 0.75, "盒內其他\n＋認證保守", ec=BLUE, fs=9, color=BLUE)
    box(ax, 3.6, 2.35, 7.0, 0.8, "UI ＝ 以上各項 ＋ T_req ＋ 剩餘（剩餘／2＝每側餘裕）", ec=GREEN, fs=11, bold=True, color=GREEN)
    box(ax, 3.6, 1.1, 3.3, 0.85, "頻寬 5–9 GHz：\n一組延遲與整盒認證", ec=GREY, fs=9)
    box(ax, 7.3, 1.1, 3.3, 0.85, "位元率 10–25 Gb/s：\n頻寬、邊緣一起縮放", ec=GREY, fs=9)
    save(fig, paths.FIG("paper/m4", "s4_concept.png"))


if __name__ == "__main__":
    s1()
    s2()
    s3()
    s4()
    print("寫出 figures/paper/m4/s1_concept.png … s4_concept.png")
