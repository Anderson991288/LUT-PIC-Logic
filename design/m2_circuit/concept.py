r"""M2 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M2 s1–s3 的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/m2/s1_concept.png、s2_concept.png、s3_concept.png。
執行：.\lab design\m2_circuit\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

from matplotlib.patches import Rectangle                             # noqa: E402

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, PURPLE, RED, arrow, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("晶片和外部設備的邊界在哪？外部設備要多準，晶片才會正確運作？",
                    ["接線表", "相位設定檔", "真值表"],
                    ["spec.json\n介面規格與需求", "tolerance.json\n容許範圍"],
                    "像家電說明書：晶片不含光源與偵測器，但要寫清楚外部要提供什麼、可以差多少。")
    ax.add_patch(Rectangle((5.55, 1.35), 2.9, 3.0, fc="#f3eefa", ec=PURPLE, lw=2, ls="--"))
    ax.text(5.7, 4.1, "晶片", fontsize=10.5, color=PURPLE, fontweight="bold")
    box(ax, 6.25, 2.2, 1.5, 1.2, "B7\n14 個 heater", ec=PURPLE, fc="white", fs=9)
    box(ax, 3.45, 2.45, 1.7, 0.95, "雷射、調變\n參考光 R", ec=GREEN, fc="#eaf5ee", fs=8.8)
    box(ax, 8.85, 2.45, 1.7, 0.95, "偵測器\n判讀 ΔP", ec=RED, fc="#fdecea", fs=8.8)
    box(ax, 6.1, 4.55, 1.8, 0.5, "heater 驅動", ec=ORANGE, fc="#fbf3df", fs=8.8)
    arrow(ax, (5.15, 2.9), (6.25, 2.9), GREEN, 2)
    arrow(ax, (7.75, 2.9), (8.85, 2.9), RED, 2)
    ax.text(4.3, 3.55, "光從 5 個 EC 進", ha="center", fontsize=8.5, color=GREEN)
    ax.text(9.7, 3.55, "光從 5 個 EC 出", ha="center", fontsize=8.5, color=RED)
    arrow(ax, (7.0, 4.55), (7.0, 3.4), ORANGE, 1.6)
    ax.text(7.1, 3.75, "電：14 個\nPAD＋GND", fontsize=8.3, color=ORANGE, va="center")
    ax.text(4.3, 1.95, "R 可以差多少？\n各路相位可以差多少？", ha="center", fontsize=8.8, color=GREEN, va="top")
    ax.text(7.0, 1.95, "heater 要多少功率、\n多準？", ha="center", fontsize=8.8, color=ORANGE, va="top")
    ax.text(9.7, 1.95, "讀哪兩個埠？\n極性不能接反", ha="center", fontsize=8.8, color=RED, va="top")
    save(fig, paths.FIG("m2", "s1_concept.png"))


def s2():
    fig, ax = frame("從規格到 GDS 要經過哪些步驟？每個元件用 PDK 的哪個 cell？",
                    ["spec.json\n介面規格"],
                    ["components.json\n元件清單與理由", "flow.json\n8 步流程"],
                    "先查型錄（PDK）並跑 DRC：合格的就用；沒有或不合格的才自建，並寫清楚理由、風險與在哪一步處理。")
    need = ["MMI ×14", "相位區 ×14", "heater ×14", "PAD ×15", "EC ×10", "波導、繞線"]
    ax.text(4.35, 4.8, "需要的元件", ha="center", fontsize=9.5, color=GREY, fontweight="bold")
    for k, t in enumerate(need):
        box(ax, 3.45, 4.2 - 0.55 * k, 1.8, 0.45, t, ec=GREY, fc="white", fs=8.8)
    box(ax, 5.8, 1.8, 1.5, 2.6, "查 PDK\n（晶圓廠\n型錄）", ec=PURPLE, fc="#f3eefa", fs=9.5, bold=True)
    arrow(ax, (5.25, 3.0), (5.8, 3.0), GREY, 1.8)
    box(ax, 7.9, 3.0, 2.7, 1.5, "有 cell 且過 DRC → 直接用\nMMI、PAD、波導模板", ec=BLUE, fc="#eaf1fa", fs=8.8)
    box(ax, 7.9, 1.2, 2.7, 1.5, "沒有或過不了 DRC\n→ 自建＋理由\n相位模型、heater、繞線、EC", ec=ORANGE, fc="#fbf3df", fs=8.8)
    arrow(ax, (7.3, 3.3), (7.9, 3.75), BLUE, 1.6)
    arrow(ax, (7.3, 2.7), (7.9, 1.95), ORANGE, 1.6)
    ax.text(6.55, 1.45, "每個 cell 記下：GDS 層、尺寸、\n埠、電路模型、單獨跑 DRC", ha="center", fontsize=8.3, color=GREY, va="top")
    save(fig, paths.FIG("m2", "s2_concept.png"))


def s3():
    fig, ax = frame("換成 PDK 的元件模型後，電路還對嗎？元件不完美時呢？",
                    ["接線表＋相位", "元件清單：PDK MMI\n＋理想相位區"],
                    ["sim_results.json\n80/80、U 的差", "mmi_sweep.json\n容許範圍", "結論：晶片做好後\n要重新校正相位"],
                    "兩條獨立的路算出同一個 U，才相信接線；再問元件不完美時還剩多少餘裕。")
    box(ax, 3.45, 3.75, 2.8, 0.8, "路 1：矩陣乘法（M1）\nU_ref＝M7 ⋯ M1", ec=BLUE, fc="#eaf1fa", fs=8.8)
    box(ax, 3.45, 2.55, 2.8, 0.8, "路 2：電路模擬\nPDK 元件逐一接線 → S → U", ec=GREEN, fc="#eaf5ee", fs=8.8)
    box(ax, 6.85, 2.9, 1.6, 1.3, "比較\n‖U − U_ref‖\n真值表 80 組", ec=PURPLE, fc="#f3eefa", fs=8.8)
    arrow(ax, (6.25, 4.15), (6.85, 3.8), BLUE, 1.6)
    arrow(ax, (6.25, 2.95), (6.85, 3.3), GREEN, 1.6)
    box(ax, 9.0, 3.1, 1.6, 0.9, "一致\n→ 接線正確", ec=PURPLE, fc="white", fs=8.8)
    arrow(ax, (8.45, 3.55), (9.0, 3.55), PURPLE, 1.6)
    ax.plot([3.45, 10.6], [2.25, 2.25], color=GREY, lw=0.8, ls=":")
    box(ax, 3.45, 1.0, 2.8, 0.95, "MMI 不完美\n損耗、分光不均", ec=RED, fc="#fdecea", fs=8.8)
    box(ax, 6.85, 1.0, 1.6, 0.95, "margin\n變小", ec=RED, fc="white", fs=8.8)
    box(ax, 9.0, 1.0, 1.6, 0.95, "重新找相位\n（校正）", ec=ORANGE, fc="#fbf3df", fs=8.8)
    arrow(ax, (6.25, 1.48), (6.85, 1.48), RED, 1.6)
    arrow(ax, (8.45, 1.48), (9.0, 1.48), ORANGE, 1.6)
    save(fig, paths.FIG("m2", "s3_concept.png"))


def main():
    for f in (s1, s2, s3):
        f()
    print("寫出 figures/m2/s1_concept.png、s2_concept.png、s3_concept.png")


if __name__ == "__main__":
    main()
