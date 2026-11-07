r"""論文 M3 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M3 各步的概念；只是示意，數字以各步結果為準。
輸入：無。
輸出：figures/paper/m3/s1_concept.png、s2_concept.png、s3_concept.png。
執行：.\lab design\paper\m3_align\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, RED, box, frame, save   # noqa: E402


def s1():
    fig, ax = frame("論文草稿的設定和我們目前的設定差在哪？XOR2 的雜訊護欄為何看起來差約 2 倍？",
                    ["論文草稿\n表 I、表 II、II-A", "論文 M1 的設定\n（預算、取樣窗、B7 模型）"],
                    ["align.json\n參數對照、護欄", "後續各步要改的設定"],
                    "比較護欄或功率之前，先確認兩邊的 P_u 量在同一個參考面。")
    box(ax, 3.75, 3.75, 3.2, 0.7, "草稿：P_u 在 macro 輸入端\n輸出到偵測器不計損耗", ec=GREY, fs=9)
    box(ax, 7.2, 3.75, 3.3, 0.7, "我們：P_u 在 B7 輸入端\n輸出側另有傳播＋EC 損耗", ec=BLUE, fs=9, color=BLUE)
    rows = [("接收端", "完全相同", GREEN), ("參考面", "不同 → 本步換算", ORANGE),
            ("損耗、邊緣、情境", "不同 → M3 s2、s3 改用草稿值", RED)]
    for k, (t, a, c) in enumerate(rows):
        y = 3.0 - 0.75 * k
        box(ax, 3.75, y - 0.3, 2.2, 0.6, t, ec=GREY, fc="#f7f7f7", fs=9, bold=True)
        box(ax, 6.1, y - 0.3, 4.4, 0.6, a, ec=c, fs=9, bold=True, color=c)
    save(fig, paths.FIG("paper/m3", "s1_concept.png"))


def s2():
    fig, ax = frame("用論文草稿的合成方法與 0.9 dB／MZI 損耗，能重現表 I 的 9 個函數嗎？",
                    ["論文草稿表 I\n9 個函數的 margin", "M3 s1 的參考面\n（偵測器端 −7 dBm）"],
                    ["synth.json\n14 個相位、margin、護欄", "M3 s3 的相位"],
                    "同一顆 macro、同一個目標，兩種最佳化方法都要找到同一個最佳值，才算重現。")
    steps = [("soft-min", "把「最差那組」換成\n可微分的平滑最小值"), ("L-BFGS", "16 個隨機起點\nβ 逐段加大"),
             ("交叉核對", "SLSQP 24 個起點\n取較大者")]
    for k, (t, a) in enumerate(steps):
        box(ax, 3.75 + 2.3 * k, 3.6, 2.1, 0.55, t, ec=BLUE, fs=10, bold=True, color=BLUE)
        box(ax, 3.75 + 2.3 * k, 2.75, 2.1, 0.75, a, ec=GREY, fs=9)
    box(ax, 3.75, 1.6, 6.7, 0.65, "比較：無損與 0.9 dB／MZI 的 margin、護欄 → 與表 I 相差 ≤ 0.02 P_u", ec=ORANGE, fs=9.5)
    save(fig, paths.FIG("paper/m3", "s2_concept.png"))


def s3():
    fig, ax = frame("用論文草稿的設定做時域模擬，對齊時與 13.2 ps 延遲盒內的窗寬，和表 III 一樣嗎？",
                    ["M3 s2 的相位\n（0.9 dB／MZI）", "論文草稿表 II\n（邊緣、情境、接收端）"],
                    ["detail.json\n對齊與盒內共同窗", "各項設定的影響"],
                    "盒內的窗有三種算法：共同窗、扣中點、各自取樣；要寫明用的是哪一種。")
    box(ax, 3.75, 3.7, 3.2, 0.8, "對齊：所有輸入同時到\n找 margin − 護欄 ≥ 0 的最長區間", ec=GREY, fs=9)
    box(ax, 7.2, 3.7, 3.3, 0.8, "延遲盒：每路 ±6.6 ps、41 點\n共同窗／扣中點／各自取樣", ec=BLUE, fs=9, color=BLUE)
    steps = ["邊緣", "護欄", "情境", "相位", "格點", "shot"]
    box(ax, 3.75, 2.55, 6.75, 0.55, "一次只改一項，換成論文 M1 的設定，看窗寬變多少", ec=ORANGE, fs=9.5)
    for k, t in enumerate(steps):
        box(ax, 3.75 + 1.15 * k, 1.7, 1.0, 0.6, t, ec=ORANGE, fs=9, bold=True, color=ORANGE)
    save(fig, paths.FIG("paper/m3", "s3_concept.png"))


if __name__ == "__main__":
    s1()
    s2()
    s3()
    print("寫出 figures/paper/m3/s1_concept.png、s2_concept.png、s3_concept.png")
