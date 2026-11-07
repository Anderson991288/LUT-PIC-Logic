r"""M3 各步的概念圖（每步開頭「本步概念」）。

用途：用固定版型（輸入 → 本步工作 → 輸出）說明 M3 各步的概念；只是示意，數字以各步結果為準。
輸入：無（B7 的位置取自 common/mzi.py 的 B7_OPS，與接線表相同）。
輸出：figures/m3/s1_concept.png、figures/m3/s2_concept.png、figures/m3/s3_concept.png、figures/m3/s4_concept.png、figures/m3/s5_concept.png、figures/m3/s6_concept.png。
執行：.\lab design\m3_layout\concept.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import numpy as np                                                   # noqa: E402
from matplotlib.patches import Rectangle                             # noqa: E402

import paths                                                         # noqa: E402
from common.concept import BLUE, GREEN, GREY, ORANGE, PURPLE, RED, arrow, box, frame, save   # noqa: E402
from common.draw import draw_b7                                      # noqa: E402
from common.mzi import B7_OPS                                        # noqa: E402


def s1():
    fig, ax = frame("電路連接（誰接誰）怎麼變成實體幾何（放在哪、怎麼彎）？",
                    ["接線表：7 顆 MZI 的\n（層, 上方波導）", "spec.json\n埠名、heater 編號", "元件清單：PDK MMI\n＋自建 heater"],
                    ["b7_core.gds", "layout_info.json\n埠位表、heater 落墊座標"],
                    "電路圖只說「誰接誰」；佈局要決定位置、彎法與金屬怎麼避開光路，再讀回 GDS 確認沒有畫錯。")
    sub = fig.add_axes([0.315, 0.3, 0.17, 0.42])
    draw_b7(sub, labels=False, fs=7, box_label=lambda k: f"{k}")
    sub.set_title("電路圖：接線", fontsize=9, color=PURPLE)
    arrow(ax, (6.75, 3.0), (7.25, 3.0), GREY, 2, "每層一欄\n每條波導一軌", fs=8.5, dy=0.15)
    # 右：幾何示意（每顆 MZI：S 彎 → MMI → 分開 → 相位區 → 合攏 → MMI → 回到軌上）
    x0, w, ys = 7.35, 0.8, [4.5, 3.8, 3.1, 2.4, 1.7]

    def bend(xa, xb, ya, yb):
        t = np.linspace(0, 1, 20)
        ax.plot(xa + (xb - xa) * t, ya + (yb - ya) * (1 - np.cos(np.pi * t)) / 2, color=BLUE, lw=1.2)

    busy = {(r, l) for rail, l in B7_OPS for r in (rail, rail + 1)}
    for l in range(4):
        for r, y in enumerate(ys):
            if (r, l) not in busy:
                ax.plot([x0 + l * w, x0 + (l + 1) * w], [y, y], color=BLUE, lw=1.2)
    for k, (rail, lay) in enumerate(B7_OPS, 1):
        xa = x0 + lay * w
        yt, yb = ys[rail], ys[rail + 1]
        ym = (yt + yb) / 2
        g = 0.05
        for y, yy in ((yt, ym + g), (yb, ym - g)):
            bend(xa, xa + 0.12, y, yy)
            bend(xa + 0.24, xa + 0.34, yy, y)
            ax.plot([xa + 0.34, xa + 0.44], [y, y], color=BLUE, lw=1.2)
            bend(xa + 0.44, xa + 0.54, y, yy)
            bend(xa + 0.66, xa + 0.8, yy, y)
        for xm in (xa + 0.12, xa + 0.54):
            ax.add_patch(Rectangle((xm, ym - 0.12), 0.12, 0.24, fc=BLUE))
        ax.plot([xa + 0.35, xa + 0.43], [yt + 0.07, yt + 0.07], color=ORANGE, lw=3)
        ax.plot([xa + 0.0, xa + 0.06], [yt + 0.07, yt + 0.07], color=ORANGE, lw=3)
        ax.text(xa + 0.4, ym, str(k), fontsize=7.5, ha="center", va="center", color=PURPLE)
    ax.text(x0 + 2 * w, 4.85, "佈局：幾何（示意）", ha="center", fontsize=9, color=PURPLE)
    ax.text(7.0, 1.05, "讀回 GDS：由 MMI 位置推回接線、由 heater 位置推回編號，與接線表、規格比對；再跑 DRC",
            ha="center", fontsize=8.8, color=RED)
    save(fig, paths.FIG("m3", "s1_concept.png"))


def s2():
    fig, ax = frame("佈局真的照電路圖接嗎？金屬、彎道、間距合理嗎？",
                    ["b7_core.gds\n（只看多邊形與文字標記）", "接線表＋相位設定檔", "spec.json\nheater 編號"],
                    ["review_checks.json\n審查表", "extracted.json\n抽出的光路", "交接事項\n給 M3 s3、M3 s5"],
                    "不相信畫圖時的變數：從 GDS 重新抽出光路、重算 U；和電路圖一致，才算照圖施工。")
    steps = [("① 抽光路", "波導聯集成\n一段一段；\n每段接兩個節點", BLUE),
             ("② 找 heater", "TiN 蓋在\n哪一段波導；\n編號看標記", ORANGE),
             ("③ 重算 U", "理想 MMI＋\nheater 相位\n→ 與 M1 比", PURPLE),
             ("④ 其他審查", "金屬離光路、\n熱串擾、埠距；\n故障注入", GREEN)]
    for k, (t1, t2, c) in enumerate(steps):
        x = 3.45 + 1.85 * k
        box(ax, x, 2.2, 1.6, 2.3, "", ec=c, fc="white")
        ax.text(x + 0.8, 4.15, t1, ha="center", fontsize=10, color=c, fontweight="bold")
        ax.text(x + 0.8, 3.1, t2, ha="center", va="center", fontsize=8.8)
        if k < 3:
            arrow(ax, (x + 1.6, 3.35), (x + 1.85, 3.35), GREY, 1.4)
    ax.text(7.0, 1.55, "結果分三類：通過；有處置（寫明交給哪一步）；未通過就回到 M3 s1 修改", ha="center", fontsize=9, color=RED)
    save(fig, paths.FIG("m3", "s2_concept.png"))


def s3():
    fig, ax = frame("光怎麼進出晶片？14 個 heater 怎麼用一層金屬接到 PAD？",
                    ["b7_core.gds", "layout_info.json\n光學埠、落墊座標", "spec.json\nH01→P01 對應"],
                    ["chip.gds\n整顆晶片", "chip_info.json\nPAD、EC、跨越次數\n電流密度"],
                    "光從兩側的 EC 進出、電從上下緣最外圍的 PAD 進出；只有一層金屬，走線順序先排好，線才不會交叉。")
    # 核心與 EC 扇出
    box(ax, 5.4, 2.55, 3.2, 0.9, "B7 核心", ec=PURPLE, fc="#f3eefa", fs=9.5)
    ys_core = np.linspace(3.35, 2.65, 5)
    ys_ec = np.linspace(4.4, 1.6, 5)
    t = np.linspace(0, 1, 30)
    for yc_, ye in zip(ys_core, ys_ec):
        ax.plot(4.2 + 1.2 * t, ye + (yc_ - ye) * (1 - np.cos(np.pi * t)) / 2, color=BLUE, lw=1.2)
        ax.plot(8.6 + 1.2 * t, yc_ + (ye - yc_) * (1 - np.cos(np.pi * t)) / 2, color=BLUE, lw=1.2)
        ax.add_patch(Rectangle((3.55, ye - 0.05), 0.65, 0.1, fc="#e377c2"))
        ax.add_patch(Rectangle((9.8, ye - 0.05), 0.65, 0.1, fc="#e377c2"))
    ax.text(3.85, 4.65, "EC×5\n間距 250 µm", ha="center", fontsize=8.3, color=BLUE)
    ax.text(10.1, 4.65, "EC×5", ha="center", fontsize=8.3, color=BLUE)
    ax.text(4.8, 1.25, "扇出：30 → 250 µm", ha="center", fontsize=8.3, color=BLUE)
    # PAD 與走線
    ax.plot([5.2, 8.8], [5.1, 5.1], color="#8c564b", lw=1.2)                      # 晶片邊緣：PAD 外側不再有金屬
    ax.text(5.15, 5.1, "晶片邊緣", fontsize=8, color="#8c564b", va="center", ha="right")
    for k, kind in enumerate("SGSSGS"):
        x = 5.4 + 0.55 * k
        ax.add_patch(Rectangle((x, 4.6), 0.34, 0.34, fc="#2ca02c", alpha=0.7))
        ax.text(x + 0.17, 4.77, "G" if kind == "G" else "P", ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        for dx in ((0.17,) if kind == "S" else (0.09, 0.25)):
            ax.plot([x + dx, x + dx], [3.45, 4.6], color="#2ca02c", lw=1.4, ls="-" if kind == "S" else "--")
    ax.text(7.0, 5.35, "PAD 一排在最外圍：實線＝訊號（P）；虛線＝地線，相鄰兩個 heater 共用 GND PAD（G）",
            fontsize=7.8, color="#2ca02c", va="center", ha="center")
    for k in range(2):
        x = 6.2 + 1.2 * k
        ax.add_patch(Rectangle((x, 1.35), 0.32, 0.32, fc="#2ca02c", alpha=0.7))
        ax.plot([x + 0.16, x + 0.16], [1.67, 2.55], color="#2ca02c", lw=1.4)
    ax.text(7.0, 1.0, "下面一軌的 heater 往南接（跨過的波導較少）", ha="center", fontsize=8.3, color=GREY)
    save(fig, paths.FIG("m3", "s3_concept.png"))


def s4():
    fig, ax = frame("這顆晶片能不能製造？每個 heater 真的接到對的 PAD、每個 EC 接到對的埠嗎？",
                    ["chip.gds\n（只看圖形與文字標記）", "spec.json\n原理圖：Hn→Pn＋GND", "b7_core.gds\n審查過的核心"],
                    ["drc_result.json", "connectivity.json\nLVS、光學、故障注入"],
                    "製造規則看 DRC；電路對不對看 LVS（從佈局抽出網路、和原理圖逐條比）；檢查本身要用故障注入證明抓得到錯。")
    cols = [("DRC", "平台規則 30 條\n設計區＝晶片\n只有一個外框", BLUE),
            ("核心未改動", "晶片裡的核心\n＝審查過的版本\n（多邊形雜湊）", PURPLE),
            ("LVS（電）", "Ti/AL、TiN 聯集\n重疊＝接點\n與原理圖逐條比", ORANGE),
            ("光學連接", "EC 端面所在那段\n恰含一個核心埠\n名稱與訊號一致", GREEN)]
    for k, (t1, t2, c) in enumerate(cols):
        x = 3.45 + 1.85 * k
        box(ax, x, 2.3, 1.6, 2.2, "", ec=c, fc="white")
        ax.text(x + 0.8, 4.15, t1, ha="center", fontsize=10, color=c, fontweight="bold")
        ax.text(x + 0.8, 3.15, t2, ha="center", va="center", fontsize=8.6)
    box(ax, 3.45, 1.15, 7.15, 0.8, "故障注入：短路、斷路（Ti/AL、TiN）、原理圖對調、PAD／EC 標記對調、DRC 違規\n→ 每一種都要被抓到",
        ec=RED, fc="#fdecea", fs=9)
    save(fig, paths.FIG("m3", "s4_concept.png"))


def s5():
    fig, ax = frame("交出去的東西，別人拿到能不能直接用？",
                    ["chip.gds", "規格、PAD／EC 對照", "DRC、LVS、模擬結果"],
                    ["delivery/\n交付包", "delivery_check.json\n交付檢查結果"],
                    "交付包要讓別人不必問作者：知道怎麼接光、接電、校正，並能自己確認檔案沒壞、彼此一致、結果算得出來。")
    items = [("layout/", "晶片 GDS", BLUE), ("interfaces/", "怎麼接：PAD、EC、\n相位起點、驗收答案", ORANGE),
             ("verification/", "為什麼可信：\nDRC、LVS、模擬", GREEN), ("README", "怎麼用、怎麼校正、\n有哪些風險", PURPLE)]
    for k, (t1, t2, c) in enumerate(items):
        x = 3.45 + 1.85 * k
        box(ax, x, 3.1, 1.6, 1.5, "", ec=c, fc="white")
        ax.text(x + 0.8, 4.3, t1, ha="center", fontsize=10, color=c, fontweight="bold")
        ax.text(x + 0.8, 3.6, t2, ha="center", va="center", fontsize=8.5)
    box(ax, 3.45, 1.2, 7.15, 1.4, "", ec=RED, fc="#fdecea")
    ax.text(7.0, 2.3, "交付檢查程式（放在交付包裡，只需 numpy）", ha="center", fontsize=9.5, color=RED, fontweight="bold")
    ax.text(7.0, 1.65, "雜湊對得上 → 沒有禁字 → PAD／EC 對照與規格一致 → 版本一致\n→ 自己重算 80 組真值表 → 驗證結果都通過\n"
            "自我測試：故意改壞一份副本，檢查必須失敗", ha="center", va="center", fontsize=8.6)
    save(fig, paths.FIG("m3", "s5_concept.png"))


def s6():
    fig, ax = frame("同一份交付 GDS，換成業界常用的 Virtuoso／Calibre，結果一樣嗎？",
                    ["delivery/ 的 chip.gds", "KLayout 平台 deck\n（24 個敘述、30 個類別）", "故意加違規的 GDS"],
                    ["commercial.json\n兩套工具的結果對照", "教訓：匯出參數、\n結果不同要追原因"],
                    "換工具不只是換按鈕：匯出參數會改變幾何，兩套規則看的形狀也可能不同；要用同一批檔案交叉驗證，並追出不同的原因。")
    box(ax, 3.45, 3.6, 2.1, 1.0, "KLayout deck\n→ 自動移植成\nCalibre 草案（16 個）", ec=BLUE, fc="#eaf1fa", fs=8.6)
    box(ax, 3.45, 2.1, 2.1, 1.0, "Virtuoso\nstrmin → OA\nstrmout（200／8191）", ec=PURPLE, fc="#f3eefa", fs=8.6)
    box(ax, 6.2, 2.1, 1.9, 2.5, "四份 GDS\n× 兩套規則\n\n交付檔\n故意違規\n匯出 200\n匯出 8191", ec=GREY, fc="white", fs=8.6)
    arrow(ax, (5.55, 4.1), (6.2, 3.8), BLUE, 1.5)
    arrow(ax, (5.55, 2.6), (6.2, 2.9), PURPLE, 1.5)
    box(ax, 8.7, 3.6, 1.9, 1.0, "結果一致？\n不一致就追原因", ec=RED, fc="#fdecea", fs=8.8)
    box(ax, 8.7, 2.1, 1.9, 1.0, "幾何比對\n（對稱差面積）", ec=GREEN, fc="#eaf5ee", fs=8.8)
    arrow(ax, (8.1, 3.8), (8.7, 4.1), GREY, 1.5)
    arrow(ax, (8.1, 2.9), (8.7, 2.6), GREY, 1.5)
    ax.text(7.0, 1.4, "在 EDA 伺服器以批次指令執行（不開 GUI，最多 4 執行緒）；結果只寫在本步資料夾", ha="center", fontsize=8.8, color=GREY)
    save(fig, paths.FIG("m3", "s6_concept.png"))


def main():
    s1()
    s2()
    s3()
    s4()
    s5()
    s6()
    print("寫出 figures/m3/s1_concept.png、s2_concept.png、s3_concept.png、s4_concept.png、s5_concept.png、s6_concept.png")


if __name__ == "__main__":
    main()
