r"""組裝 report/LUT4_Study.html：沿用原課程頁的版型與 M1 s1，M1 s2 起改為 LUT4 架構（Model-7a＋雙差值判讀）。

輸入：study_src/（原課程頁的頁首樣式、M1 s1、M1 s2 ①②、M1 s3 ①、名詞表）；LUT4 s0–s7 的 out/*.json；figures/lut4、figures/study。
輸出：report/LUT4_Study.html。
規則：圖、表依出現順序重新編號；讀者文件不得有本機路徑與計畫代號（最後檢查）。
執行：.\lab design\lut4\build_study.py
"""
import html
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/
import paths                                                         # noqa: E402

SRC = Path(__file__).resolve().parent / "study_src"
OUTF = paths.REPORT / "LUT4_Study.html"
esc = html.escape


def J(step, name):
    return json.loads(paths.OUT(step, name).read_text(encoding="utf-8"))


def src(name):
    return (SRC / name).read_text(encoding="utf-8")


def code(path, start, end):
    """取專案程式的第 start–end 行（1 起算）當教學片段。"""
    lines = (paths.ROOT / path).read_text(encoding="utf-8").split("\n")
    name = Path(path).name
    return (f'<details><summary class="note-toggle">查看關鍵 Python 片段（{name}，第 {start}–{end} 行）</summary>'
            "<pre><code>" + esc("\n".join(lines[start - 1:end])) + "</code></pre></details>")


NET = J("lut4/s1_handoff", "lut4_netlist.json")
PH = J("lut4/s1_handoff", "phases.json")
TOL = J("lut4/s1_handoff", "tolerance.json")
SPEC = J("lut4/s1_handoff", "spec.json")
ALG = J("lut4/s0_algebra", "algebra.json")
SIM = J("lut4/s2_sim", "sim_results.json")
LI = J("lut4/s3_core", "layout_info.json")
REV = J("lut4/s4_review", "review_checks.json")
CHIP = J("lut4/s5_chip", "chip_info.json")
COM = J("lut4/s8_commercial", "commercial.json")
SYS = J("lut4/s9_system", "system.json")
GR = J("lut4/s9_system", "gain_robust.json")
GB = J("lut4/s9_system", "gain_box.json")
BAS = J("lut4/s0_basics", "basics.json")
COV = J("lut4/s0_coverage", "coverage.json")
REF = J("lut4/s0_coverage", "refine.json")
FULLREP = J("lut4/s0_coverage", "full_replay.json")
VER = "lut4"
ENC_NOTE = "輸入為 OOK（光場 0／1）"
BANK = J("lut4/s0_coverage", "bank_replay.json")
DRC = J("lut4/s6_verify", "drc_result.json")
CONN = J("lut4/s6_verify", "connectivity.json")
GN = CONN["electrical"]["gnd_network"]
PKG = J("lut4/s7_delivery", "package.json")
DCHK = J("lut4/s7_delivery", "delivery_check.json")
FN = PH["functions"]
OPS = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in NET["mzis"]]
GEO = LI["geometry"]

# ---------------------------------------------------------------- SVG
RY = [90, 154, 218, 282, 346]
CX = [205, 365, 525, 685]
IN_LAB = ["x1 / in0", "x2 / in1", "x3 / in2", "x4 / in3", "R / in4"]
OUT_LAB = ["o1 / out0（監看）", "o2 / out1（上界）", "o3 / out2（下界）", "o4 / out3（中間）", "o5 / out4（監看）"]


def wiring_svg(sid, title, hl=None, note=None, h=430):
    """Model-7a 接線；hl＝[(路徑步驟 [(MZI 編號, 列, 行)…], 起點波導, 顏色)]。"""
    s = [f'<svg viewBox="0 0 980 {h}" role="img" aria-labelledby="{sid}"><title id="{sid}">{esc(title)}</title>']
    for r in range(5):
        role = r in (1, 2, 3)
        s.append(f"<path d='M150 {RY[r]}H760' class='wire'/>")
        s.append(f"<text x='15' y='{RY[r] + 5}'>{IN_LAB[r]}</text>")
        s.append(f"<text x='772' y='{RY[r] + 5}'{' font-weight=\"700\"' if role else ' class=\"small\"'}>{OUT_LAB[r]}</text>")
    for l, cx in enumerate(CX):
        s.append(f"<text x='{cx}' y='40' text-anchor='middle' class='title'>第 {l + 1} 層</text>")
    for k, (r, l) in enumerate(OPS, 1):
        cx = CX[l]
        s.append(f"<rect x='{cx - 48}' y='{RY[r] - 13}' width='96' height='90' rx='7' class='box'/>")
        s.append(f"<text x='{cx}' y='{RY[r] + 24}' text-anchor='middle'>MZI-{k}</text>")
        s.append(f"<text x='{cx}' y='{RY[r] + 48}' text-anchor='middle' class='small'>θ{k}, φ{k}</text>")
    for steps, start, color in (hl or []):
        x, rail = 150, start
        pts = [(x, RY[rail])]
        q_of = {k: (r, l) for k, (r, l) in enumerate(OPS, 1)}
        for (q, row, col) in steps:
            r0, l = q_of[q]
            xl, xr = CX[l] - 48, CX[l] + 48
            pts.append((xl, RY[rail]))
            new = r0 + row - 1
            if new != rail:                                            # 換軌放在方框右緣，粗線不經過中央的編號與 θ、φ
                pts.append((xr - 16, RY[rail]))
            rail = new
            pts.append((xr, RY[rail]))
        pts.append((760, RY[rail]))
        s.append(f"<polyline points='{' '.join(f'{a},{b}' for a, b in pts)}' fill='none' stroke='{color}' stroke-width='5' stroke-opacity='0.85'/>")
    if note:
        s.append(f'<text x="150" y="{h - 18}" class="small">{esc(note)}</text>')
    s.append("</svg>")
    return "".join(s)


def receiver_svg():
    s = ['<svg viewBox="0 0 980 330" role="img" aria-labelledby="rxT"><title id="rxT">LUT4 固定接收端：三組 PD＋TIA、兩個比較器、AND</title>',
         '<defs><marker id="arR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#355f91"/></marker></defs>']
    ys = {"o2": 70, "o4": 165, "o3": 260}
    lab = {"o2": "o2（上界）", "o4": "o4（中間）", "o3": "o3（下界）"}
    for k, y in ys.items():
        s.append(f"<text x='10' y='{y + 5}'>{lab[k]}</text>")
        s.append(f"<path d='M120 {y}H178' class='wire' marker-end='url(#arR)'/>")
        s.append(f"<rect x='180' y='{y - 22}' width='130' height='44' rx='6' class='box'/><text x='245' y='{y + 6}' text-anchor='middle'>PD＋TIA</text>")
        s.append(f"<path d='M310 {y}H360' class='wire'/>")
    # 比較器 A：o2(+) o4(−)；B：o4(+) o3(−)
    s.append("<path d='M360 70V100H448' class='wire' marker-end='url(#arR)'/><path d='M360 165V130H448' class='wire' marker-end='url(#arR)'/>")
    s.append("<path d='M360 165V200H448' class='wire' marker-end='url(#arR)'/><path d='M360 260V230H448' class='wire' marker-end='url(#arR)'/>")
    for y0, nm, ex in ((85, "比較器 A", "P(o2) − P(o4) ＞ 0"), (185, "比較器 B", "P(o4) − P(o3) ＞ 0")):
        s.append(f"<polygon points='450,{y0 - 5} 450,{y0 + 55} 540,{y0 + 25}' class='box'/>")
        s.append(f"<text x='462' y='{y0 + 12}' class='small'>＋</text><text x='462' y='{y0 + 48}' class='small'>−</text>")
        s.append(f"<text x='560' y='{y0 + 52}'>{nm}</text><text x='560' y='{y0 + 72}' class='small'>{ex}；門檻 0</text>")
    s.append("<path d='M540 110H770V140H788' class='wire' marker-end='url(#arR)'/><path d='M540 210H770V180H788' class='wire' marker-end='url(#arR)'/>")
    s.append("<path d='M790 125H830A35 35 0 0 1 830 195H790Z' class='box'/><text x='818' y='166' text-anchor='middle'>AND</text>")
    s.append("<path d='M865 160H905' class='wire' marker-end='url(#arR)'/><text x='910' y='166' font-weight='700'>y</text>")
    s.append("<text x='120' y='318' class='small'>o4 同時參與兩個比較；兩個比較器只比較兩訊號大小，門檻 0、不需要參考電壓。換邏輯功能時接收端不變。</text></svg>")
    return "".join(s)


def boundary_svg():
    s = ['<svg viewBox="0 0 980 360" role="img" aria-labelledby="bdT"><title id="bdT">LUT4 PIC 與外部設備的邊界</title>',
         '<defs><marker id="arB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#355f91"/></marker></defs>']
    s.append("<rect x='10' y='60' width='160' height='200' rx='8' fill='#fff' stroke='#9aa7b5'/><text x='90' y='88' text-anchor='middle' class='title'>片外：光源</text>")
    s.append("<text x='90' y='122' text-anchor='middle'>同一顆雷射</text><text x='90' y='150' text-anchor='middle'>分成 5 路</text>")
    s.append("<text x='90' y='178' text-anchor='middle'>x1–x4 強度調變</text><text x='90' y='206' text-anchor='middle'>R：振幅 3</text><text x='90' y='240' text-anchor='middle' class='small'>相對相位須固定</text>")
    s.append("<path d='M170 160H248' class='wire' marker-end='url(#arB)'/><text x='207' y='144' text-anchor='middle' class='small'>5 根光纖</text>")
    s.append("<rect x='250' y='40' width='400' height='240' rx='10' fill='#eef4fb' stroke='#355f91' stroke-width='2'/>")
    s.append("<text x='450' y='68' text-anchor='middle' class='title'>PIC（本課程設計）</text>")
    s.append("<rect x='268' y='100' width='60' height='120' rx='5' class='box'/><text x='298' y='165' text-anchor='middle' class='small'>5 EC</text>")
    s.append("<rect x='346' y='100' width='208' height='120' rx='5' class='box'/><text x='450' y='150' text-anchor='middle'>LUT4 macro：Model-7a</text><text x='450' y='176' text-anchor='middle' class='small'>7 MZI、14 heater</text>")
    s.append("<rect x='572' y='100' width='60' height='120' rx='5' class='box'/><text x='602' y='165' text-anchor='middle' class='small'>5 EC</text>")
    s.append("<text x='450' y='255' text-anchor='middle' class='small'>PAD：14 訊號＋GND（上下緣）</text>")
    s.append("<path d='M650 130H748' class='wire' marker-end='url(#arB)'/><text x='697' y='113' text-anchor='middle' class='small'>o2、o4、o3</text>")
    s.append("<path d='M650 200H748' class='wire' stroke-dasharray='5 4' marker-end='url(#arB)'/><text x='697' y='228' text-anchor='middle' class='small'>o1、o5 監看</text>")
    s.append("<rect x='750' y='60' width='220' height='200' rx='8' fill='#fff' stroke='#9aa7b5'/><text x='860' y='88' text-anchor='middle' class='title'>片外：接收端（固定）</text>")
    s.append("<text x='860' y='124' text-anchor='middle'>3 組 PD＋TIA</text><text x='860' y='152' text-anchor='middle'>2 個比較器（門檻 0）</text><text x='860' y='180' text-anchor='middle'>1 個 AND → y</text><text x='860' y='214' text-anchor='middle' class='small'>監看 PD：功率核對、校正</text>")
    s.append("<rect x='340' y='300' width='220' height='44' rx='6' fill='#fff' stroke='#9aa7b5'/><text x='450' y='328' text-anchor='middle'>片外：14 通道 heater 驅動</text>")
    s.append("<path d='M450 300V282' class='wire' marker-end='url(#arB)'/></svg>")
    return "".join(s)


def flow_svg():
    """標準設計流程（直排兩欄）：左欄設計動作與工具、右欄該階段產生的結果／檔案；檢查不通過時回到對應階段修正。"""
    st = [
        ("m2-s1", "1. 功能與介面規格", "Specification", "接線表、相位設定、光學埠與 heater 通道",
         ["lut4_netlist.json：固定光路", "phases.json：各函數的 14 個相位", "spec.json／tolerance.json：介面與容許量"]),
        ("m2-s2", "2. 電路模擬", "Circuit simulation", "CORNERSTONE PDK＋IPKISS／Caphe",
         ["sim_results.json：U、裕量、故障注入", "sim_truth.csv：每組輸入的判讀"]),
        ("m2-s3", "3. IPKISS＋Python 佈局", "Physical layout", "依接線表放置 MZI、heater 與波導",
         ["l4_core.gds：核心佈局", "layout_info.json：座標、埠位與 heater 編號"]),
        ("m2-s4", "4. 佈局審查", "Layout review", "只讀 GDS，重建光路並重算判讀",
         ["review_checks.json：審查紀錄", "extracted.json：抽出的連接"]),
        ("m2-s5", "5. EC、PAD 與繞線", "Routing and interfaces", "光學 I/O、PAD、單層 Ti/AL 繞線",
         ["chip.gds：整顆晶片", "chip_info.json：PAD、EC、走線對照"]),
        ("m2-s6", "6. DRC 與連接檢查", "DRC／Connectivity", "平台規則檔、LVS、光學連通、故障注入",
         ["drc_result.json：DRC 結果", "connectivity.json：電氣與光學連接"]),
        ("m2-s7", "7. 交付與工具對照", "PIC delivery", "交付包；Virtuoso／Calibre 再檢查同一份 GDS",
         ["delivery_lut4/：GDS、介面表、README", "MANIFEST.json：SHA-256 清單", "commercial.json：Calibre 對照結果"]),
    ]
    RH, TOP, BH = 118, 78, 98
    H = TOP + RH * len(st) + 34
    F1, F2 = 19, 16
    s = [f'<svg viewBox="0 0 1000 {H}" role="img" aria-labelledby="flT"><title id="flT">LUT4 PIC 設計流程：每階段都留下可核對的檔案</title>',
         '<defs><marker id="arF" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto"><path d="M0 0L10 5L0 10z" fill="#355f91"/></marker>'
         '<marker id="arFr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto"><path d="M0 0L10 5L0 10z" fill="#b5532b"/></marker></defs>']
    s.append(f"<text x='500' y='30' text-anchor='middle' font-size='20' font-weight='700'>LUT4 PIC 設計流程：每階段都留下可核對的檔案</text>")
    s.append(f"<text x='265' y='62' text-anchor='middle' font-size='{F1}' font-weight='700'>設計動作</text>")
    s.append(f"<text x='755' y='62' text-anchor='middle' font-size='{F1}' font-weight='700'>產生的結果／檔案</text>")
    for k, (anc, nm, en, act, fil) in enumerate(st):
        y = TOP + k * RH
        s.append(f"<a href='#{anc}'><rect x='60' y='{y}' width='410' height='{BH}' rx='8' class='box'/>")
        s.append(f"<text x='78' y='{y + 30}' font-size='{F1}' font-weight='700'>{nm}</text>")
        s.append(f"<text x='78' y='{y + 56}' font-size='{F2}' fill='#526274'>{en}</text>")
        s.append(f"<text x='78' y='{y + 82}' font-size='{F2}'>{esc(act)}</text></a>")
        s.append(f"<path d='M470 {y + BH / 2}H516' fill='none' stroke='#355f91' stroke-width='2' marker-end='url(#arF)'/>")
        s.append(f"<rect x='520' y='{y}' width='460' height='{BH}' rx='6' fill='#fff8e8' stroke='#c9b27a'/>")
        n = len(fil)
        for i, line in enumerate(fil):
            yy = y + BH / 2 + (i - (n - 1) / 2) * 26 + 6
            s.append(f"<text x='536' y='{yy}' font-size='{F2}'>{esc(line)}</text>")
        if k < len(st) - 1:
            s.append(f"<path d='M265 {y + BH}V{y + RH - 2}' fill='none' stroke='#355f91' stroke-width='2' marker-end='url(#arF)'/>")
    # 回頭修正：檢查階段（審查、DRC）不通過時回到對應的設計階段
    y4, y2 = TOP + 5 * RH + BH / 2, TOP + 2 * RH + BH / 2
    s.append(f"<path d='M60 {y4}H24V{y2}H54' fill='none' stroke='#b5532b' stroke-width='2.5' stroke-dasharray='10 6' marker-end='url(#arFr)'/>")
    s.append(f"<text x='60' y='{H - 8}' font-size='{F2}' fill='#526274'>藍色為設計階段，米黃色為該階段產生的檔案；後一階段只讀前面階段的檔案。點左欄可跳到該步。</text>")
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- 編號
FIGS, TABS = {}, {}


def F(key):
    return f"@@F:{key}@@"


def FR(key):
    return f"@@FR:{key}@@"


def TB(key):
    return f"@@T:{key}@@"


def TR(key):
    return f"@@TR:{key}@@"


def fig_img(key, path, alt, cap, width="100%"):
    return (f'<figure><img src="{path}" alt="{esc(alt)}" style="display:block;width:{width};max-width:100%;height:auto;margin:0 auto">'
            f'<figcaption>圖 {F(key)}｜{cap}</figcaption></figure>')


def fig_svg(key, svg, cap):
    return f"<figure>{svg}<figcaption>圖 {F(key)}｜{cap}</figcaption></figure>"


def table(key, cap, head, rows, cls="logic-compact"):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><caption>表 {TB(key)}｜{cap}</caption><tr>{h}</tr>{b}</table>'


def f3(x, n=3):
    return f"{x:.{n}f}"


def c2s(z):
    a, b = (0.0 if abs(v) < 5e-7 else v for v in z)
    if abs(b) < 5e-7:
        return f"{a:g}"
    if abs(a) < 5e-7:
        return f"{b:g}i"
    return f"{a:g}{'+' if b >= 0 else '−'}{abs(b):g}i"


# ---------------------------------------------------------------- M1 s2
def m1s2():
    keep = src("m1s2_12.html")
    keep = keep.replace("M1 s2　MZI Macro 設計 (Brick 架構: B7)", "M1 s2　MZI Macro 設計（LUT4 架構：Model-7a）")
    keep = keep.replace("本步已編寫・等待 review", "依 LUT4 架構改寫")
    keep = keep.replace("認識 B7 組合架構", "認識 LUT4 macro Model-7a 與雙差值判讀")
    keep = re.sub(r'<p class="muted"><a href="#appendix-two-mzi">[^<]*</a></p>', "", keep)
    keep = keep.replace("四路資料的 B7 Macro", "四路資料的 Model-7a")
    keep = keep.replace("<h3 id=\"s2-two-mzi\">", f'<p class="muted">表中 6 種可實現的功能以 <a href="../design/lut4/s0_basics/basics.py">basics.py</a> 重算確認（相位隨機取樣 40 萬組，得 {BAS["single"]["count"]} 種）。</p><h3 id="s2-two-mzi">', 1)
    keep = keep.replace("<p>加入 R 後，", f'<p class="muted">以 basics.py 重算（相位隨機取樣 200 萬組）：{BAS["two_mzi_R"]["count"]}／16 種都出現。</p><p>加入 R 後，', 1)
    fl = FN
    xor_rows = [["s（1 的個數）", "0", "1", "2", "3", "4"],
                ["h₁＝[1 ≤ s ≤ 3]", "0", "1", "1", "1", "0"],
                ["h₂＝[s ≠ 2]", "1", "1", "0", "1", "1"],
                ["h₁ AND h₂＝XOR4", "0", "1", "0", "1", "0"]]
    new = f'''
<h3 id="s2-example">③ MZI Macro（7 MZIs）設計的邏輯功能涵蓋考量</h3>
<p>四路資料加上參考光 R 需要五條波導，五個輸出埠記為 o1–o5，P(o2) 是 o2 的功率。只比較一組功率差 P(o2)−P(o4) 時，判讀量是輸入的二次式（推導見下方「為什麼兩個比較接 AND 就能做 XOR4？」），四輸入中有一部分函數（例如 XOR3、XOR4）無法實現。因此本課程採用 LUT4 macro <b>Model-7a</b>（7 顆 MZI；拓樸代碼 3142132，讀法見下方）。七顆 MZI 排成四層，讀取三個輸出 o2、o4、o3，以兩個門檻 0 的比較器加一個固定的 AND 判讀。</p>
<div class="formula">Da＝P(o2)−P(o4)，Db＝P(o4)−P(o3)，y＝[Da＞0] AND [Db＞0]</div>
<p>y＝1 表示 P(o4) 落在 P(o3) 與 P(o2) 之間。此判讀方式稱為雙差值判讀。換邏輯功能時只改 14 個 θ／φ，接收端的接法、門檻與 AND 都不變。</p>
<p>下表使用的名詞定義如下：</p>
<ul><li><b>Pᵤ：</b>功率單位，等於一路資料「1」的功率。</li>
<li><b>裕量：</b>16 組輸入中離判讀邊界最近的距離，單位 Pᵤ。裕量為正代表 16 組全對，數值越大越不易受誤差影響。</li>
<li><b>合成：</b>給定一張真值表，以數值最佳化求出 14 個相位。</li>
<li><b>起點：</b>合成時隨機選取的初始相位。從多個起點各求解一次，取裕量最大的結果。</li>
<li><b>真值表代號：</b>16 組輸入的目標輸出寫成十六進位，第 x 位元是輸入 x＝x1＋2x2＋4x3＋8x4 的輸出，例如 XOR4＝0x6996。</li>
<li><b>dB：</b>功率比的對數單位。每顆 MZI 損耗 0.9 dB，表示功率剩約 81%。</li>
<li><b>標準磚牆排列：</b>每層依序混合相鄰波導的排法，本表的代碼為 1421324。</li>
<li><b>等價類估計：</b>把輸入經排列或反相後可互相轉換的真值表歸為一類，只計算代表再乘上類別大小。</li></ul>
<p>下表比較三種組合（每顆 MZI 0.9 dB 損耗；採用的 Model-7a 對 65,536 張真值表逐張合成）。</p>
{table("cov", "LUT4 macro 的邏輯功能涵蓋（每顆 MZI 0.9 dB）", ["架構與判讀", "可實現", "裕量 ≥ 0.1 Pᵤ", "裕量中位數", "XOR4", "接收端"],
      [["標準磚牆 1421324＋單一門檻 P(o2)−P(o4)（等價類估計）", "57,574", "42,454", "0.134 Pᵤ", "不可", "2 PD、1 比較器"],
       ["標準磚牆 1421324＋雙差值（等價類估計）", "65,536", "63,110（96.3%）", "0.225 Pᵤ", "可", "3 PD＋TIA、2 比較器、AND"],
       ["<b>Model-7a＋雙差值（採用，逐張合成）</b>", f"<b>{COV['realizable']:,}</b>", f"<b>{COV['ge_0p1']:,}（{COV['ge_0p1'] / 655.36:.1f}%）</b>", f"<b>{COV['median']:.3f} Pᵤ</b>", f"可（{COV['xor4']:.3f} Pᵤ）", "3 PD＋TIA、2 比較器、AND"]])}
<p class="muted">採用列由 <a href="../design/lut4/s0_coverage/cover4.py">cover4.py</a> 對 65,536 張真值表逐張合成（每張 24 個起點）。65,536 張全部可實現，最差 {COV['min']:.3f} Pᵤ（{COV['argmin']}）。起點較少，XOR4 在此為 {COV['xor4']:.3f} Pᵤ，略低於範例函數以 60 個起點求得的 {FN["XOR4"]["margin"]:.3f} Pᵤ，因此表中數字偏保守。最差的函數重新求相位後可再提高（下方「最差函數的相位再最佳化」）。標準磚牆兩列是等價類估計。Model-7a 對輸入的排列與反相不對稱，同一類的裕量不一定相同，這兩列僅供參考。</p>
<p>二輸入函數是四輸入真值表的特例（x3、x4 任意），16／16 種都可實現。</p>
<details id="s2-refine"><summary class="note-toggle">最差函數的相位再最佳化：增加起點的效果</summary>
<p>全表合成每張只用 24 個起點，最差的函數可能只是尚未找到較好的相位。對 24 個起點時最差的 {REF['n']} 張與 XOR4，再以 100、400 個起點重新求 14 個相位（同一模型：每顆 MZI 0.9 dB、雙差值＋AND），取最好的結果。下表列出原本最差的 10 張與 XOR4。</p>
{table("refine", "最差函數以更多起點重求相位的裕量（Pᵤ）", ["真值表", "24 個起點", "100 個起點", "400 個起點", "提高"],
      [[r["f"] + ("（XOR4）" if r["f"] == "0x6996" else ""), f"{r['m24']:.4f}", f"{r['m100']:.4f}", f"{r['m400']:.4f}", f"+{r['gain_pct']:.0f}%"] for r in REF["worst10"] + [REF["xor4"]]])}
<p>{REF['n']} 張平均提高 {REF['mean_gain_pct']:.0f}%，全部 65,536 張的最差裕量由 {COV['min']:.3f} 提高到 <b>{REF['new_min']:.3f} Pᵤ</b>（{REF['new_argmin']}）。多數函數在 100 個起點內就找到較好的解；0x7996、0x9679 加到 400 個起點仍只有約 0.058–0.059 Pᵤ，接近 Model-7a 對這類函數的上限，再提高要改架構或判讀方式，而不是增加起點。實務上，相位是換功能時離線算好再寫入 heater，常用或裕量偏低的函數可多給起點（每張約數秒）。程式：<a href="../design/lut4/s0_coverage/refine.py">refine.py</a>。</p>
</details>
{bank_note()}
<details id="s2-coverage-limit"><summary class="note-toggle">為什麼兩個比較接 AND 就能做 XOR4？</summary>
<p class="muted">輸入是二元，光路是線性，偵測是平方律（PD 讀到的是光場絕對值的平方），所以每個輸出功率都是 x 的二次多線性式（只含常數項、一次項與 xᵢxⱼ 項）。兩個功率相減仍是二次式，以門檻 0 判斷正負只能實現二次門檻函數（可寫成二次式正負的布林函數）。兩個二次門檻函數接 AND 就不再受此限制。以 XOR4 為例，令 s＝x1＋x2＋x3＋x4：</p>
{table("xor4", "XOR4 分解為兩個二次門檻函數的 AND", xor_rows[0], xor_rows[1:])}
<p class="muted">h₁、h₂ 都只含 s 的二次式（s² 展開後只有 xᵢxⱼ 項），所以各自可由一組功率差判讀；AND 由接收端的固定邏輯閘完成，不隨函數改變。這部分能力來自接收端的 AND，引用時應一併寫明。</p></details>
<details><summary class="note-toggle">為什麼不需要校準雷射功率？</summary><p class="muted">三個功率來自同一顆雷射，雷射功率漂移時 P(o2)、P(o4)、P(o3) 一起縮放，兩個差值的正負不變。需要注意的是三路 TIA 的增益要匹配（M2 s1 的容許量）。</p></details>

<h4>七顆 MZI 組成 Model-7a：五條波導、四層</h4>
<p>Model-7a 的拓樸代碼由輸入往輸出讀，數字 k 代表一顆混合第 k、k＋1 條波導的 MZI：MZI-1 接 3–4、MZI-2 接 1–2、MZI-3 接 4–5、MZI-4 接 2–3、MZI-5 接 1–2、MZI-6 接 3–4、MZI-7 接 2–3。每層分別為 2、2、2、1 顆；同一層的兩顆不共用波導，可以交換順序。第 1 層的 MZI-2、MZI-1 分別混合 (x1, x2) 與 (x3, x4)，第 2 層起把兩組結果與 R 彙整。</p>
{fig_svg("wiring", wiring_svg("s2w", "Model-7a 的七顆 MZI、四層、五條波導接線", note="光由左向右；空白位置直通。讀取 o2（上界）、o4（中間）、o3（下界）；o1、o5 引出作監看。"),
          "LUT4 macro Model-7a 的接線。每個方塊都有 φ、θ 兩個相位控制區，共 14 個；參考光 R 接第 5 條波導。左側「x1 / in0」為訊號名／佈局埠名，右側「o1 / out0」相同。")}
{fig_svg("rx", receiver_svg(), "固定接收端。三個輸出埠各接一組 PD＋TIA；比較器 A 判斷 P(o2)＞P(o4)、比較器 B 判斷 P(o4)＞P(o3)，再接 AND。")}
<p><b>選用 Model-7a 的原因：</b>Model-7a 與標準磚牆排列 1421324 同為 7 顆 MZI、深度 4。深度是層數，4 層是五條波導只接相鄰波導時，讓每個輸入都到達三個讀取埠的最少層數。重新排列後，困難真值表（例如 XOR4）的最小裕量較高；全表的裕量中位數與裕量 ≥ 0.1 Pᵤ 的比例也略高（表 {TR("cov")}，標準磚牆為等價類估計）。以等價類估計比較，8 顆 MZI 沒有明顯好處；6 顆雖可實現全部真值表，但裕量 ≥ 0.1 Pᵤ 的比例明顯較低。</p>
{table("ex", "本課程使用的範例函數（Model-7a、0.9 dB／MZI、60 個起點）", ["函數", "真值表", "使用輸入", "最小裕量", "16 組"],
      [[n, f"<code>{f['truth_hex']}</code>", "、".join(f["uses"]), f"{f['margin']:.3f} Pᵤ", f["verified"]] for n, f in fl.items()])}
<p class="muted">真值表以十六進位表示：第 x 位元是輸入 x＝x1＋2x2＋4x3＋8x4 的輸出。MUX 為 y＝x3 ? x2 : x1。XOR4 是範例中裕量最小的函數。全部 65,536 張中，第一輪最差的是 {COV["argmin"]}（{COV["min"]:.3f} Pᵤ），第二輪後最差的是 {REF["new_argmin"]}（{REF["new_min"]:.3f} Pᵤ）。相位設定見附錄 B。</p>
</section>
'''
    return keep + new


# ---------------------------------------------------------------- M1 s3
def m1s3():
    keep = src("m1s3_1.html")
    keep = keep.replace("本步已編寫・等待 review", "依 LUT4 架構改寫")
    keep = keep.replace("把資料代入 B7 的實際埠位後，怎麼算到 o2、o4 的光場、功率與邏輯值？",
                        "把資料代入 Model-7a 的實際埠位後，怎麼算到 o2、o4、o3 的光場、功率與邏輯值？")
    keep = keep.replace("已認識 B7 的七顆 MZI 接線", "已認識 Model-7a 的七顆 MZI 接線")
    keep = re.sub(r"能完整讀懂 v → o=Uv → 功率差 → 0／1。.*?本步建議 1 小時。",
                  '能完整讀懂 v → o＝Uv → 兩個功率差 → 0／1。範例函數的相位與完整判讀見<a href="#appx-phases">附錄 B</a>、<a href="#appx-truth">附錄 C</a>；主線接續 M2 的 PIC 設計流程。本步建議 1 小時。', keep, flags=re.S)
    keep = keep.replace("B7", "LUT4 macro")
    d = ALG["demo"]
    T = ALG["T"]
    colors = ["#c0392b", "#e67e22", "#8e44ad"]

    def steps(name):
        out = []
        for p in d[name]["paths"]:
            st = []
            for s in p["steps"]:
                m = re.match(r"T(\d)\[(\d),(\d)\]", s)
                st.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
            out.append(st)
        return out

    def demo_block(name, title, key, dst):
        ps = steps(name)
        svg = wiring_svg(f"pt{name}", title, hl=[(s, 3, colors[i % 3]) for i, s in enumerate(ps)], h=400)
        rows = [[f"路徑 {chr(65 + i)}", " × ".join(p["steps"]), c2s(p["value"])] for i, p in enumerate(d[name]["paths"])]
        return (fig_svg(key, svg, f"{title}：{len(ps)} 條路徑（不同顏色）。七顆都設 θ＝π/2、φ＝0，理想無損。")
                + table(key, f"{title} 的路徑係數", ["路徑", "沿途係數", "複數光場"], rows)
                + f'<p>相加：u<sub>{dst}4</sub>＝{c2s(d[name]["sum"])}；只有 x4＝1 時，該埠功率＝{d[name]["power"]:g}。整體矩陣算出的 U 元素為 {c2s(d[name]["U"])}（一致）。</p>')

    lay = ALG["layers_1100"]
    lay_rows = [[l["after"]] + [f"{p:g}" for p in l["power"]] + [f"{sum(l['power']):g}"] for l in lay]
    q = ALG["quadratic_XOR4"]
    qrows = [[t, f"{a:+.3f}", f"{b:+.3f}"] for t, a, b in zip(q["terms"], q["Da"], q["Db"])]
    new = f'''
<h3 id="s3-u">② Model-7a 輸出與輸入的關係矩陣運算</h3>
<p>依接線把七顆 MZI 的 2×2 矩陣嵌入 5×5，再依光路順序相乘，得到整體矩陣 U。同一層的兩顆 MZI 不共用波導，相乘順序可以交換：</p>
<div class="formula">U＝T̂7 · [T̂5 T̂6] · [T̂3 T̂4] · [T̂1 T̂2]，　o＝U v，　v＝[x1, x2, x3, x4, R]ᵀ</div>
<p>T̂k 是把第 k 顆 MZI 的 2×2 矩陣放到它所接的兩條波導（其餘為 1）。u<sub>jk</sub> 是第 k 個輸入到第 j 個輸出的光場權重；判讀用到 o2、o3、o4 三列：</p>
<div class="formula">o2＝Σ u<sub>2k</sub> v<sub>k</sub>，　o3＝Σ u<sub>3k</sub> v<sub>k</sub>，　o4＝Σ u<sub>4k</sub> v<sub>k</sub>，　P(oj)＝|oj|²</div>
<h4 id="s3-path-weights">沿路徑求 U：用 x4 到 o2、o4、o3 示範</h4>
<p>沿著光可以走的路找出經過的係數相乘，再把同一輸入到同一輸出的各路徑<b>複數相加</b>，就是 U 的元素。本例七顆 MZI 都設 θ＝π/2、φ＝0：T[1,1]＝{c2s(T["T11"])}、T[1,2]＝{c2s(T["T12"])}、T[2,1]＝{c2s(T["T21"])}、T[2,2]＝{c2s(T["T22"])}。T<sub>k</sub>[列,行] 的列是輸出、行是輸入，上方波導為 1。</p>
<p class="notice"><b>注意：</b>本步的 θ＝π/2、φ＝0 只是教學設定，用於說明路徑如何相加，不實現任何邏輯函數。各函數實際使用的 14 個相位見附錄 B。</p>
<div class="example" id="path-x4-o2"><h4 style="margin-top:4px">① x4 → o2：三條路徑同相相加</h4>{demo_block("x4_o2", "x4 → o2", "p_o2", 2)}</div>
<div class="example" id="path-x4-o4"><h4 style="margin-top:4px">② x4 → o4：兩條路徑完全抵消</h4>{demo_block("x4_o4", "x4 → o4", "p_o4", 4)}<p>兩條路徑的振幅相同、相位相反，相加為 0：這就是<b>破壞性干涉</b>。若把功率先各自平方再相加會得到 0.25，錯誤；一定要先加光場，再取模平方。</p></div>
<div class="example" id="path-x4-o3"><h4 style="margin-top:4px">③ x4 → o3：三條路徑部分抵消</h4>{demo_block("x4_o3", "x4 → o3", "p_o3", 3)}</div>

<h3 id="s3-layers">③ 逐層光場：輸入 1100</h3>
<p>同樣的教學設定下送入 x1＝x2＝1、x3＝x4＝0、R＝3，記錄每層之後五條波導的功率。理想無損時每層的總功率都等於輸入的 1＋1＋9＝11。</p>
{table("layers", "輸入 1100 的逐層功率（θ＝π/2、φ＝0，理想無損）", ["位置", "波導 1", "波導 2", "波導 3", "波導 4", "波導 5", "總和"], lay_rows)}
<p>最後一列就是 P(o1)～P(o5)。本例 P(o2)＝{lay[-1]["power"][1]:g}、P(o4)＝{lay[-1]["power"][3]:g}、P(o3)＝{lay[-1]["power"][2]:g}：P(o2)＞P(o4)＞P(o3)，所以兩個比較器都輸出 1，y＝1。這組相位不是為某個函數設計的，只用來練習計算。</p>

<h3 id="s3-quad">④ 判讀量為什麼是二次式</h3>
<p>把 o＝Uv 代入 P＝|o|²，xᵢ 只取 0、1（xᵢ²＝xᵢ），每個功率差都能寫成 1 個常數、4 個一次項、6 個二次項。以 XOR4 的相位（含 0.9 dB／MZI 損耗）為例，用 16 組輸入擬合 11 個係數，誤差 {q["fit_err"]:.0e}，表示兩個差值確實只有這些項：</p>
{table("quad", "XOR4 相位下 Da、Db 的多線性展開係數（單位 Pᵤ）", ["項", "Da 係數", "Db 係數"], qrows)}
<p>XOR4 需要四次項（x1x2x3x4），單一個二次式的正負表示不出來；Da、Db 各自是二次門檻函數，接 AND 後才得到 XOR4（M1 s2 的分解）。</p>

<h3 id="s3-check">⑤ 重點整理與自我檢查</h3>
{table("s3sum", "重點整理與自我檢查", ["觀念", "應能說出的答案"],
       [["2×2 與 5×5", "一顆 MZI 混合兩路；整顆 Model-7a 追蹤五路光場。"],
        ["光場與功率", "先做複數加權相加，最後取模平方；矩陣係數不是功率比例。"],
        ["多條路徑", "同一輸入到同一輸出可能有多條路徑，相加時可能抵消（x4 → o4 為 0）。"],
        ["雙差值", "兩個功率差各是二次式；AND 由接收端完成。"],
        ["功能驗證", "算出一筆只代表一組輸入，完整邏輯要檢查 16 組。"]])}
<details><summary>自我檢查：x4 → o4 的兩條路徑各是 −0.25−0.25i 與 0.25＋0.25i，P(o4) 是多少？</summary><p>先加光場得 0，P(o4)＝0；若先平方各得 0.125、相加 0.25 是錯的。</p></details>
<details><summary>自我檢查：為何 R 在 v 中寫 3，而不是 9？</summary><p>矩陣運算處理光場，R 的振幅為 3；9 是它的功率。</p></details>

<h3 id="s3-python">⑥ Python 小實作與計算證據</h3>
<p>以下函式列舉某個輸入波導到輸出波導的所有路徑，並與整體矩陣比對（完整程式 <a href="../design/lut4/s0_algebra/algebra.py">algebra.py</a>）：</p>
{code("design/lut4/s0_algebra/algebra.py", 34, 52)}
<p>在專案根目錄執行 <code>.\\lab design\\lut4\\s0_algebra\\algebra.py</code>。已核對：三組示範的路徑和都等於整體 U 的元素；逐層總功率守恆（11）；XOR4 的 Da、Db 以 11 項二次式表示的誤差 {q["fit_err"]:.0e}。結果存於 <a href="../design/lut4/s0_algebra/out/algebra.json">algebra.json</a>。</p>
</section>
'''
    return keep + new


# ---------------------------------------------------------------- M2 s1
def m2s1():
    ports = [[f"{k + 1}", f"{['x1', 'x2', 'x3', 'x4', 'R'][k]} → in{k}", f"out{k} → o{k + 1}", next(o["note"] for o in SPEC["optical_ports"] if o["port"] == f"out{k}")] for k in range(5)]
    ch = SPEC["phase_channels"]
    chrows = []
    for k in range(1, 8):
        a = next(c for c in ch if c["mzi"] == f"MZI-{k}" and c["kind"] == "theta")
        b = next(c for c in ch if c["mzi"] == f"MZI-{k}" and c["kind"] == "phi")
        m = NET["mzis"][k - 1]
        chrows.append([f"MZI-{k}", f"{m['waveguides'][0]}–{m['waveguides'][1]}／第 {m['layer']} 層", f"θ{k} → {a['heater']} → {a['pad']}", f"φ{k} → {b['heater']} → {b['pad']}"])
    # R2 以交付包的觀察性敘述為準（交接時的 R2 只是佔位，由 LUT4 s9 取代）
    d_r2 = next(r for r in json.loads((paths.ROOT / "delivery_lut4" / "interfaces" / "spec.json").read_text(encoding="utf-8"))["requirements"] if r["id"] == "R2")
    req = [[r["id"], r["item"], d_r2["value"] + "統計成功率見 ⑤，確定性增益盒見附錄 E-5。" if r["id"] == "R2" else r["value"]] for r in SPEC["requirements"]]
    t = TOL
    names = list(FN)
    in_rows = [[f"σ＝{s} rad"] + [f"{t['input_phase_pass'][s][n] * 100:.1f}%" for n in names] for s in t["input_phase_pass"]]
    ph_rows = [[f"σ＝{s} rad"] + [f"{t['heater_phase_pass'][s][n] * 100:.1f}%" for n in names] for s in t["heater_phase_pass"]]
    g_rows = [[n, f"{t['R_range_per_function'][n][0]:g}–{t['R_range_per_function'][n][1]:g}"]
              + [f"±{t['gain_tolerance'][n][c] * 100:.1f}%" for c in ("o2", "o4", "o3")]
              + [f"{t['heater_power'][n]['total_mW']:g}"] for n in names]
    gmin = min(min(v.values()) for v in t["gain_tolerance"].values())
    return f'''
<h2 id="m2-s1">M2 s1　LUT4 PIC 功能與介面規格</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><p><b>M2 要完成：</b>將 M1 的 LUT4 macro，依序做成電路模型、IPKISS＋Python 佈局、晶片 I/O 與控制繞線，再經審查、DRC 及連接檢查，完成可交付的 PIC 設計資料。</p><p><b>本步先定義：</b>哪些功能放在 PIC 上、哪些由外部設備完成；固定光學埠位、14 個相位通道與接收端判讀，並算出外部設備要多準。</p></div>
<h3 id="m2s1-system">① PIC 與外部設備的邊界</h3>
{fig_svg("bd", boundary_svg(), "PIC 只負責可設定的光場混合。雷射、資料調變、heater 驅動與接收判讀都在片外；接收端固定，不隨邏輯功能改變。")}
<p>本設計有 5 入、5 出，共 10 個 EC（邊緣耦合器，光纖與晶片波導的介面）。晶片上只有 EC、波導、MMI、TiN heater（兩顆 MMI 與 heater 組成 MZI）、Ti/AL 金屬與 PAD。雷射、調變器、heater 驅動、PD、TIA、比較器與 AND 都在片外。資料在片外調變完成後才進入晶片；晶片上沒有高速調變器。</p>
<h3 id="m2s1-ports">② 固定光學埠位：模型與佈局使用同一份表</h3>
<p>下表的 in0–in4、out0–out4 是佈局上的埠名；x1–x4、R 是輸入訊號；o1–o5 是輸出訊號。</p>
{table("ports", "光學埠位（規格檔 spec.json 與佈局共用）", ["波導", "輸入", "輸出", "輸出用途"], ports)}
<div class="formula">v＝[x1, x2, x3, x4, R]ᵀ → o＝Uv；Da＝|o2|²−|o4|²，Db＝|o4|²−|o3|² → y＝[Da＞0] AND [Db＞0]</div>
<p>資料位元以光場振幅 0／1 表示，R＝3 為參考光振幅（功率 9 Pᵤ）。五路輸入來自同一顆片外雷射。設計假設五路到達晶片入口時相對相位固定；維持相位固定屬於片外系統需求，本課程未實作（見 ⑤）。</p>
<h3 id="m2s1-control">③ 十四個相位如何對應到控制介面？</h3>
<p>θk、φk 是第 k 顆 MZI 的兩個相位。H01–H14 是 heater 編號，P01–P14 是對應的訊號 PAD 編號。</p>
{table("chan", "十四個相位通道：MZI → heater → PAD", ["元件", "接線／層", "θ 通道", "φ 通道"], chrows)}
<p>每個 heater 有訊號端與地端。訊號端接自己的訊號 PAD；地端由相鄰兩個 heater 共用一個 GND PAD，數量在晶片繞線時決定。</p>
<h3 id="m2s1-spec">④ 一份規格，同時供模擬與佈局使用</h3>
{table("req", "需求表（spec.json）", ["代號", "項目", "規格"], req)}
<p class="muted">代號的第一個字母表示類別：O 光學、E 電氣、R 接收端（與參考光 R 無關）、F 功能、K 校正。後文的「需求 K1」即本表的 K1 列。</p>
<p>容許範圍由 <a href="../design/lut4/s1_handoff/handoff.py">handoff.py</a> 計算。計算時每次只改一項，相位固定為交接值。交接值是 M1 求出、交給 M2 的相位與裕量（附錄 B）。σ 是誤差的標準差。</p>
{table("tol", "各範例函數的容許量：R 振幅、TIA 增益、heater 功率", ["函數", "R 範圍", "o2 增益", "o4 增益", "o3 增益", "heater 總功率（mW）"], g_rows)}
{table("inph", f"輸入相對相位誤差（5 路各加常態誤差，{t['trials']} 次）下真值表全對的比例", ["誤差"] + names, in_rows)}
{table("htph", f"heater 相位誤差（14 個各加常態誤差，{t['trials']} 次）下真值表全對的比例", ["誤差"] + names, ph_rows)}
<p><b>表格說明：</b>R 在 {t["R_range_all"][0]:g}–{t["R_range_all"][1]:g}（功率 {t["R_power_range_pct"][0]:+g}%～{t["R_power_range_pct"][1]:+g}%）內七個函數都對。單獨偏一路 TIA 增益時，容許量最小為 ±{gmin * 100:.1f}%（XOR4 的 o4 通道）；三路同時偏差的容許量更小，見 ⑤。XOR4 裕量只有 {FN["XOR4"]["margin"]:.3f} Pᵤ，輸入相位與 heater 相位都要控制在 σ≈0.02 rad；其他函數在 0.05 rad 時幾乎全對。P_π 是使相位改變 π 所需的 heater 功率。heater 功率依 P_π≈{t["P_pi_mW"]:g} mW 估計，最壞情況為 14 個都接近 2π，約 {t["worst_mW"]:g} mW。</p>
<h3 id="m2s1-sysreq">⑤ 系統層級的容許量與光功率</h3>
{system_sec()}
<h3 id="m2s1-check">⑥ 本步驗收與後續流程</h3>
<ul><li>能從光學表找到每個訊號，知道 o2、o4、o3 各接哪一個比較器輸入。</li><li>能從 heater 編號找到對應 MZI 的 θ 或 φ，以及 PAD 名稱。</li><li>知道容許量是單項評估：晶片完成後要依量測重新求相位，並在校正後的相位下重算。</li></ul>
<p>功能與介面規格 → 電路模擬 → IPKISS＋Python 佈局 → 佈局審查 → EC／PAD／繞線 → DRC＋連接檢查 → 交付。製程平台（後文簡稱平台）為 CORNERSTONE SOI 220 nm 被動製程，被動表示晶片上沒有雷射、高速調變器與 PD。DRC 以平台提供的 KLayout 規則檔執行。</p>
<h3 id="m2s1-sources">⑦ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s1_handoff/handoff.py">handoff.py</a>（產生接線表、相位、規格與容許量）；產物 <a href="../design/lut4/s1_handoff/out/lut4_netlist.json">lut4_netlist.json</a>（接線表）、<a href="../design/lut4/s1_handoff/out/phases.json">phases.json</a>（範例函數的相位）、<a href="../design/lut4/s1_handoff/out/spec.json">spec.json</a>（規格）、<a href="../design/lut4/s1_handoff/out/tolerance.json">tolerance.json</a>（容許量）、<a href="../design/lut4/s1_handoff/out/truth_tables.csv">truth_tables.csv</a>（每組輸入的判讀）。接線表的 SHA-256（檔案內容的指紋，內容改變指紋即不同）記在相位檔與規格檔中，用於確認版本一致。</p>
</section>
'''


def system_sec():
    y = SYS
    names = list(FN)
    tia = [[f"σ＝{float(sg) * 100:g}%"] + [f"{y['tia_mc'][sg][n] * 100:.1f}%" for n in names] for sg in y["tia_mc"]]
    wl = [["雷射波長偏移 Δλ（nm）"] + [("≥ " if y["dlambda_tol_nm"][n] >= 2 else "") + f"±{y['dlambda_tol_nm'][n]:g}" for n in names],
          ["晶片溫度偏移 ΔT（K）"] + [("≥ " if y["dT_tol_K"][n] >= 40 else "") + f"±{y['dT_tol_K'][n]:g}" for n in names]]
    er = [[f"{e} dB"] + [("✓ " if y["er"][e][n]["pass"] else "✗ ") + f"{y['er'][e][n]['margin']:.3f}" for n in names] for e in y["er"]]
    b = y["budget"]
    a = b["assumptions"]
    brow = [[k, n, f"{v['margin']:.3f}", f"{v['Pu_uW']:.3g}", f"{v['per_data_fiber_dBm']:+.1f}", f"{v['R_fiber_dBm']:+.1f}", f"{v['total_mW']:.3g}"]
            for k, c in b["cases"].items() for n, v in c.items()]
    return f"""<p>以下每項只改一個因素，相位固定為交接值。N(1, σ²) 表示平均 1、標準差 σ 的常態分布（程式 <a href="../design/lut4/s9_system/system.py">system.py</a>）。</p>
{table("tiamc", f"三路 TIA 增益同時偏差：各路 N(1, σ²)、2,000 次，真值表全對的比例", ["增益誤差"] + names, tia)}
<p>上表是指定函數與樣本數下的統計觀察：σ 在 {y["tia_sigma_ok"] * 100:g}% 以內時，七個函數 2,000 次都全對；5% 時 XOR4 降到 {y["tia_mc"]["0.05"]["XOR4"] * 100:.1f}%。其他函數的結果可能不同。例如 0x0069 需要三次項，單一比較器無法實現，它在 3% 時 {y["tia_hard"]["0x0069"]["mc"]["0.03"] * 100:.1f}% 全對、1% 時 {y["tia_hard"]["0x0069"]["mc"]["0.01"] * 100:.1f}% 全對。這些成功率不是全部真值表的規格，常態分布的標準差也不是最大誤差界；各函數的確定性增益盒半寬見附錄 E-5。量測增益後重求相位，或合成時選擇耐增益誤差的解，可以提高成功率（附錄 E-5：TIA 增益失配的容許量）。</p>
{table("wlt", "波長與溫度的容許範圍（光走 MZI 比走同層直波導多出的長度造成共同相位；正負兩方向都掃描）", ["項目"] + names, wl)}
<p>光走一顆 MZI 比走同層的直波導多 {REV["mzi_extra_gds_um"]:.2f} µm。波長偏移時，這段長度使每顆 MZI 多 {y["k_lambda_rad_per_nm"]:.3f} rad/nm 的共同相位；溫度偏移時多 {REV["dphi_dT_rad_K"]:.4f} rad/K。最嚴的是 XOR4：雷射波長要穩定在 ±{y["dlambda_tol_nm"]["XOR4"]:g} nm、晶片溫度 ±{y["dT_tol_K"]["XOR4"]:g} K 以內（掃描上限 2 nm、40 K）。此模型不含 MMI 分光比與 heater 效率隨波長、溫度的變化，實際容許量會更小；晶片需溫控。</p>
{table("er", "資料「0」的消光比（「0」的振幅＝10^(−ER/20)，與「1」同相位）：判讀全對（✓）與最小裕量", ["消光比"] + names, er)}
<p>消光比（ER）是調變器輸出「1」與「0」的功率比，單位 dB，數值越大表示「0」越暗。片外調變器的消光比至少要 {y["er_min_db"]} dB，XOR4 的裕量才保持為正（{y["er_min_db"]} dB 時剩 {y["er"][str(y["er_min_db"])]["XOR4"]["margin"]:.3f} Pᵤ）。</p>
{table("budget", "光功率預算（只計 TIA 雜訊；裕量 ≥ 7 倍差值雜訊）", ["頻寬", "函數", "裕量（Pᵤ）", "Pᵤ（µW，macro 入口）", "每根資料光纖（dBm）", "R 光纖（dBm）", "5 路合計（mW）"], brow)}
<p class="muted">假設：PD 響應度 {a["PD_A_per_W"]:g} A/W、TIA 輸入雜訊 {a["TIA_pA_rtHz"]:g} pA/√Hz、EC 每端 2 dB（輸入側含扇出，即拉開波導間距的彎曲段，共 {a["in_loss_db"]:g} dB、輸出側 {a["out_loss_db"]:g} dB）；shot 雜訊（光電流的統計起伏）、RIN（雷射的相對強度雜訊）與比較器偏移未計。dBm 是以 1 mW 為基準的功率單位，0 dBm＝1 mW。靜態讀取（1 MHz）時每根資料光纖約 {b["cases"]["1 MHz"]["XOR4"]["per_data_fiber_dBm"]:+.0f} dBm 即可；若要 10 GHz，XOR4 需要每根約 {b["cases"]["10 GHz"]["XOR4"]["per_data_fiber_dBm"]:+.0f} dBm、R 約 {b["cases"]["10 GHz"]["XOR4"]["R_fiber_dBm"]:+.0f} dBm。</p>
<div class="notice"><b>五路輸入的相干與相位穩定（最主要的系統限制，屬於片外系統）：</b>相干指五路光來自同一顆雷射，彼此的相位關係固定，因此能穩定干涉。五路從 5 根光纖進入，光纖之間的相對相位會隨溫度與振動漂移，而 XOR4 要求輸入相位誤差 σ ≤ {TOL["input_phase_sigma_ok"]:g} rad。本課程未實作相位穩定。量測時需要下列其中一種做法，三者都不是這顆晶片已有的功能：片外相位鎖定（量測相位漂移並回授修正）；改用保偏光纖陣列並加溫控，以減少漂移；以監看埠 o1、o5 搭配 heater 擾動與同步偵測追蹤相位。此外，五路輸入須為同一偏振（TE，晶片波導使用的偏振），由片外設定；晶片上沒有偏振控制元件。</div>"""


# ---------------------------------------------------------------- M2 s2
def m2s2():
    s = SIM
    rows = [[n, f"{v['passed']}/16", f"{v['margin']:.4f}", f"{v['margin_handoff']:.4f}", f"{v['U_err_pdk']:.1e}", f"{v['U_err_lossy']:.1e}"] for n, v in s["functions"].items()]
    fr = [["只把 MMI 輸出端上下接反", f"{s['faults']['swap_out']['U_err_max']:.2f}", f"{s['faults']['swap_out']['passed']}/{s['total']}", "抓到" if s["faults"]["swap_out"]["caught"] else "未抓到"],
          ["φ 接到 MZI 下方輸入", f"{s['faults']['phi_low']['U_err_max']:.2f}", f"{s['faults']['phi_low']['passed']}/{s['total']}", "抓到" if s["faults"]["phi_low"]["caught"] else "未抓到"]]
    lr = [[f"{x['loss_db']:.1f}", f"{x['passed']}/{s['total']}", f"{x['margin_min']:.4f}"] for x in s["loss_sweep"]]
    ok_l = [x for x in s["loss_sweep"] if x["passed"] == s["total"]]
    bad_l = [x for x in s["loss_sweep"] if x["passed"] != s["total"]]
    low_l = min(ok_l, key=lambda x: x["margin_min"])
    ref_l = next(x for x in ok_l if abs(x["loss_db"] - 0.9) < 1e-6)
    return f'''
<h2 id="m2-s2">M2 s2　PIC 設計流程與電路模擬</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><b>本步重點</b><ol><li><b>完整流程：</b>從規格到交付的七個階段，各做什麼、產生哪些檔案。</li><li><b>電路模擬：</b>把理想 MMI 換成 CORNERSTONE PDK 的 2×2 MMI，用 IPKISS 電路模擬（Caphe）求散射矩陣，確認 112 組判讀與 M1 相同。</li><li><b>故障注入與損耗敏感度：</b>常見接錯能不能被抓到；MMI 損耗與假設不同時，相位還能不能用。</li></ol></div>
<h3 id="m2s2-flow">① 完整 PIC 設計流程圖</h3>
{fig_svg("flow", flow_svg(), "規格 → 電路模擬 → IPKISS＋Python 佈局 → 佈局審查 → EC、PAD 與繞線 → DRC 與連接檢查 → 交付。藍色為設計階段，米黃色為產生的結果與檔案。")}
<h3 id="m2s2-inputs">② 輸入檔案、參數與執行環境</h3>
{table("simin", "電路模擬的輸入與參數", ["項目", "內容"],
       [["接線表", "lut4_netlist.json：5 條波導、7 顆 MZI 的位置與層、輸入輸出埠名"],
        ["相位設定", "phases.json：7 個函數各 14 個相位"],
        ["MMI", "PDK：SOI220nm_1550nm_TE_STRIP_2x2_MMI；含損耗模型：每顆 0.45 dB（每顆 MZI 0.9 dB）"],
        ["相位區", "自建理想相位元件 e^(iφ)（尚未加入 heater 的電壓／熱模型）"],
        ["波長", f"{s['model']['wavelength_um']:g} µm"]])}
<p>執行環境：IPKISS 2026.03、CORNERSTONE PDK（SOI 220 nm）、Python 3（ipkiss3 環境）、NumPy。</p>
<h3 id="m2s2-build">③ 建立 PDK 電路並求 S 矩陣</h3>
<p>PDK（製程設計套件）提供元件模型與幾何；Caphe 是 IPKISS 的電路模擬器。2 顆 PDK MMI＋φ、θ 理想相位區 → 1 顆 MZI；7 顆 MZI 依接線表接成五入五出的電路。程式追蹤每條波導目前的來源埠，依 MZI 順序把上一顆的輸出接到下一顆的輸入；同一份接線表也給佈局使用。</p>
{code("design/lut4/s2_sim/sim.py", 70, 90)}
<p>Caphe 在 1.55 µm 回傳 10 埠 S 矩陣（散射矩陣，列出任兩埠之間的光場係數）。由 S[out0～out4, in0～in4] 取出 5×5 的 U，與接線表＋相位的矩陣乘法比較；再以 U 算 16 組輸入的 P(o2)、P(o4)、P(o3) 與雙差值判讀。</p>
<h3 id="m2s2-result">④ 批次模擬與完整真值表驗證</h3>
{table("simres", "電路模擬結果（7 個函數 × 16 組）：U 差分 PDK MMI 與含損耗 MMI 兩欄；判讀與裕量來自含損耗模型", ["函數", "判讀", "最小裕量（Pᵤ）", "M1 交接值", "U 差（PDK MMI）", "U 差（含損耗）"], rows)}
<p><b>結果：</b>{s["passed"]}/{s["total"]} 全對；U 與矩陣乘法最大差 {s["U_err_pdk"]:.1e}（無損耗）、{s["U_err_lossy"]:.1e}（含損耗）；反射 {s["reflection_max"]:.0e}。112 組是 7 個範例函數 × 16 組輸入。</p>
<p>結果分兩部分說明。第一，PDK MMI 的電路模型在 1.55 µm 等於理想 H（U 的差只有數值誤差），表示 PDK 元件與本課程的矩陣慣例一致。第二，PDK 電路模型不含損耗，所以判讀與裕量採用自建的含損耗模型（每顆 MMI 0.45 dB）。這個模型與 M1 相同，因此裕量與 M1 交接值完全相同。此外，PDK 電路模型不含波長相依性與製程誤差，這部分要以量測校正。</p>
<h3 id="m2s2-fault">⑤ 故障注入：接線錯誤的檢出能力</h3>
<p>故障注入是故意放入已知錯誤，確認檢查程式能夠檢出。</p>
{table("simfault", "接線故障注入", ["故障", "U 最大差", "判讀", "結果"], fr)}
<p>這裡只測了兩種接錯，都會讓 U 與參考不同。只把 MMI 輸出接反時仍有 {s["faults"]["swap_out"]["passed"]} 組判對，表示只看「某幾組輸出對不對」不夠，要比對整個 U 或全部 112 組。</p>
<h3 id="m2s2-loss">⑥ 損耗與假設不同時（不重新求相位）</h3>
{table("simloss", "每顆 MZI 損耗改變時的判讀（相位固定為 0.9 dB 下的解）", ["每顆 MZI 損耗（dB）", "判讀", "最小裕量（Pᵤ）"], lr)}
<p>雷射功率整體縮放不影響判讀，但各路徑經過的 MZI 數不同（波導 1–5 為 2、4、4、3、1 顆），所以損耗改變不等於整體縮放。表中 {ok_l[0]['loss_db']:.1f}–{ok_l[-1]['loss_db']:.1f} dB 都全對，但最小裕量由 0.9 dB 時的 {ref_l['margin_min']:.3f} Pᵤ 降到 {low_l['margin_min']:.3f} Pᵤ（{low_l['loss_db']:.1f} dB）。損耗為 {bad_l[0]['loss_db']:g} dB 時有 {s['total'] - bad_l[0]['passed']} 組判錯。因此相位要依實測損耗重新求解（需求 K1：晶片完成後依量測重新求 14 個相位）。</p>
<h3 id="m2s2-sources">⑦ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s2_sim/sim.py">sim.py</a>（電路模擬與故障注入）（IPKISS 電路建構函式 build_ipkiss 由共用模組匯入）；產物 <a href="../design/lut4/s2_sim/out/sim_results.json">sim_results.json</a>（模擬結果）、<a href="../design/lut4/s2_sim/out/sim_truth.csv">sim_truth.csv</a>（每組輸入的模擬判讀）。執行：<code>.\\lab design\\lut4\\s2_sim\\sim.py</code>。</p>
</section>
'''


# ---------------------------------------------------------------- M2 s3
def m2s3():
    g = GEO
    rb = LI["readback"]
    ck = LI["checks"]
    pl = [[p["mzi"], f"第 {p['layer']} 層", f"{p['waveguides'][0]}–{p['waveguides'][1]}", f"({p['origin_um'][0]:g}, {p['origin_um'][1]:g})"] for p in LI["placement"]]
    return f'''
<h2 id="m2-s3">M2 s3　IPKISS＋Python 佈局：LUT4 核心</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><p><b>這一步要回答：</b>電路連接怎麼變成實體幾何？同一份接線表要畫出 Model-7a 的 7 顆 MZI、14 個 heater 與 10 個光學埠。</p><p><b>交給下一步：</b>l4_core.gds 與 layout_info.json；佈局審查只讀 GDS，不用畫圖時的變數。</p></div>
<h3 id="m2s3-flow">① 從電路連接走到實體幾何</h3>
<ol><li><b>取得 PDK 幾何與埠位：</b>PDK 2×2 MMI 的四個埠座標與波導寬（{g["waveguide_width_um"]:g} µm）。</li>
<li><b>建立單顆 MZI：</b>φ 相位區在上方波導的輸入段，θ 相位區在上臂（兩顆 MMI 之間的上方波導）。MMI 前後以 cosine S 彎（餘弦形狀的 S 形彎曲波導）接回波導。上下兩臂等長。</li>
<li><b>依接線表放置七顆：</b>第 l 層、上方波導 p 的 MZI 放在 (l·L<sub>MZI</sub>, −p·軌距)；該層沒有 MZI 的波導以直波導通過。軌（rail）在本頁與圖中都指波導，軌距是相鄰波導的中心距。</li>
<li><b>定義外部埠並輸出 GDS：</b>西側（左）in0–in4、東側（右）out0–out4；文字標記 MZI、heater（H01–H14）與埠名。</li></ol>
{code("design/lut4/s3_core/layout.py", 158, 166)}
<p>放置迴圈只讀接線表的（上方波導, 層）。不同拓樸只要更換接線表，就能以同一支程式產生佈局。</p>
<h3 id="m2s3-result">② 實際佈局</h3>
{fig_img("core", "../figures/lut4/s1_core.png", "LUT4 核心佈局全圖，七顆 MZI 四層", f"LUT4 核心 {g['core_size_um'][0]:g}×{g['core_size_um'][1]:g} µm（縱向放大）。由 GDS 讀回繪製：藍色矽波導、橙色 TiN heater、綠色 Ti/AL 接點；標出 MZI 與 heater 編號。")}
{table("place", "七顆 MZI 的放置（由佈局程式寫出，GDS 讀回核對）", ["MZI", "層", "波導", "原點（µm）"], pl)}
{fig_img("mzi", "../figures/lut4/s1_mzi.png", "單顆 MZI 尺寸", f"單顆 MZI：長 {g['mzi_length_um']:g} µm（相位區 {g['phase_section_um']:g}、S 彎 {g['sbend_um']:g}、MMI {g['mmi_length_um']:g} µm），軌距 {g['pitch_um']:g} µm。")}
{fig_img("heater", "../figures/lut4/s1_heater.png", "heater 端點放大", f"heater 端點：TiN 加熱條 {g['heater_length_um']:g}×{g['heater_width_um']:g} µm，兩端以 TiN 引到落墊（連接金屬用的方塊），再蓋 Ti/AL 接點（金屬層直接壓在 TiN 上，中間沒有層間導通孔 via）；金屬不蓋在波導上。", "80%")}
<h3 id="m2s3-check">③ 讀回 GDS 核對</h3>
<p class="muted">GDS 是晶片佈局的檔案格式。本頁「GDS 3」等寫法是圖層編號：3 矽波導、39 TiN、41 Ti/AL、4 與 5 是 EC 專用圖層、99 晶片外框。DRC 是設計規則檢查，說明見 M2 s6。</p>
{table("rb", "核心佈局的核對（只看 GDS 中的實際位置）", ["項目", "結果"],
       [["MMI／heater 個數", f"{rb['n_mmi']}／{rb['n_heater']}"],
        ["由 MMI 位置推回 MZI（層, 波導），與接線表比對", "一致" if ck["mzi_match_netlist"] else "不一致"],
        ["由加熱條位置推回（MZI, θ／φ），與規格的 heater 編號比對", "一致" if ck["heater_match_spec"] else "不一致"],
        ["光學埠名稱、邊緣與上下順序", "一致" if ck["ports_match_spec"] else "不一致"],
        ["波導端點與 MMI 埠的接點誤差", f"{g['join_err_um']:.1e} µm"],
        ["上下臂長度", f"{g['arm_len_um'][0]:.4f}／{g['arm_len_um'][1]:.4f} µm"],
        ["S 彎最小曲率半徑", f"{g['sbend_rmin_um']:.1f} µm（≥ 10 µm；由 cosine S 彎公式計算，M2 s4 由 GDS 擬合得 {REV['sbend_rmin_gds_um']:.1f} µm）"],
        ["光走一顆 MZI 比走同層直波導多", f"{g['rail_vs_bypass_extra_um']:g} µm"],
        ["KLayout DRC（核心）", f"{LI['drc']['n_rules']} 類檢查，違規 {LI['drc']['total']}（格點檢查依圖層展開；核心沒有 EC 的 GDS 4、5，比晶片少兩類）"],
        ["故障注入（MZI 換層、H01／H02 對調、in0／in1 標記對調）", "全部抓到" if ck["faults_caught"] else "未全抓到"]])}
<h3 id="m2s3-sources">④ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s3_core/layout.py">layout.py</a>（繪製核心佈局並讀回核對）、<a href="../design/lut4/s3_core/figs.py">figs.py</a>（繪製本步的圖）；產物 <a href="../design/lut4/s3_core/out/l4_core.gds">l4_core.gds</a>（核心佈局）、<a href="../design/lut4/s3_core/out/layout_info.json">layout_info.json</a>（座標、埠位與 heater 編號）。執行：<code>.\\lab design\\lut4\\s3_core\\layout.py</code>。</p>
</section>
'''


# ---------------------------------------------------------------- M2 s4
def m2s4():
    C = {c["id"]: c for c in REV["checks"]}
    rows = []
    for c in REV["checks"]:
        res = "通過" if c["ok"] else ("處置" if c["ok"] is None else "未通過")
        rows.append([c["id"], c["item"], c["result"], res + ("：" + c["disposition"] if c.get("disposition") else "")])
    return f'''
<h2 id="m2-s4">M2 s4　佈局審查（Layout Review）</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><b>本步的 6 個檢查重點</b>（只讀 GDS）<ol>
<li><b>看全圖：</b>光路連通，沒有短路、斷路；埠數與埠序正確。</li>
<li><b>看接點：</b>每段波導都接到 MMI 埠或晶片埠。</li>
<li><b>看 S 彎：</b>曲率半徑高於下限。</li>
<li><b>分層看金屬：</b>金屬不蓋波導，與其他波導、heater 保持距離。</li>
<li><b>用資料核對：</b>由佈局重算 U 與 112 組判讀，並以故障注入確認抓得到錯。</li>
<li><b>列待修項目：</b>固定相位差、埠距、熱串擾，交給後續步驟。</li></ol></div>
<h3 id="m2s4-overview">① 由 GDS 抽出光路</h3>
<p>把所有矽波導（MMI 內部除外）聯集成連通塊，彼此相連的圖形算一塊。節點是 MMI 的埠與晶片光學埠：MMI 的四個埠由 MMI 自身的多邊形找出，晶片光學埠取最近的文字標記。每個連通塊必須恰好接兩個節點，多於兩個為短路，少於兩個為斷路。蓋在波導上的 TiN 依「H」標記對應到 heater，再由規格查到（MZI, θ／φ）。</p>
{fig_img("ext", "../figures/lut4/s2_extract.png", "由 GDS 抽出的光路連通塊", "由 GDS 抽出的光路：每個連通塊一種顏色，節點為 MMI 埠與晶片埠。")}
{fig_img("zoom", "../figures/lut4/s2_zoom.png", "MMI 與 heater 局部放大", "局部放大：MMI 接點、S 彎與 heater 的相對位置。")}
<h3 id="m2s4-u">② 由佈局重算 U 與判讀</h3>
<p>MMI 用理想 H，蓋 heater 的段乘上該 heater 的相位，從輸入傳到輸出；損耗以每顆 MMI 0.45 dB 計入（與相位設定檔相同）。七個函數的 U 與接線表＋相位算出的 U 最大差 {REV["U_err_max"]:.1e}，判讀 {REV["passed"]}/112。</p>
{fig_img("revchk", "../figures/lut4/s2_checks.png", "佈局審查表", "佈局審查：左為由佈局重算的 U 與參考的差；右為審查表。")}
<h3 id="m2s4-table">③ 審查表</h3>
{table("rev", "佈局審查項目", ["代號", "項目", "結果", "判定"], rows)}
<p>V1–V11（含 V8b，共 12 項）是必須通過的檢查。P1–P3 不是錯誤，而是記錄下來、由後續步驟處理的項目。</p>
<p>P1 是 Model-7a 的特性：波導 1–5 分別經過 {REV["mzi_per_rail"]} 顆 MZI，光走一顆 MZI 比走同層直波導多 {REV["mzi_extra_gds_um"]:.2f} µm，所以各波導之間有固定相位差（約 {REV["dphi_dlam_rad_nm"]:.2f} rad/nm、{REV["dphi_dT_rad_K"]:.4f} rad/K）。固定相位差由晶片完成後的 14 個相位校正吸收（需求 K1），不修改佈局。</p>
<h3 id="m2s4-sources">④ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s4_review/review.py">review.py</a>（只讀 GDS 的佈局審查）、<a href="../design/lut4/s4_review/figs.py">figs.py</a>（繪製本步的圖）；產物 <a href="../design/lut4/s4_review/out/review_checks.json">review_checks.json</a>（審查紀錄）、<a href="../design/lut4/s4_review/out/extracted.json">extracted.json</a>（由 GDS 抽出的連接）。</p>
</section>
'''


# ---------------------------------------------------------------- M2 s5
def m2s5():
    c = CHIP
    pads = [[p["name"], "北" if p["side"] == "N" else "南", f"{p['xy_um'][0]:.0f}", p["heater"] or "GND（" + "＋".join(sorted(p["heaters"])) + "）"] for p in c["pads"]]
    loss = [[f"波導 {x['rail']}", f"{x['length_um']:g}", f"{x['n_mzi']}", f"{x['prop_db'][0]:g}–{x['prop_db'][1]:g}", f"{x['mmi_db']:g}", f"{x['total_db'][0]:g}–{x['total_db'][1]:g}"] for x in SYS["rails_unified"]]
    rt_ = SYS["route"]
    rrow = [[k, "、".join(f"{p} {v:g}" for p, v in r["rel_loss_db"].items()), "全對" if r["all_pass"] else "有錯", f"{r['margin']['XOR4']:.4f}"] for k, r in rt_.items()]
    cur = [[f"{x['R_kohm']:g} kΩ", f"{x['I_heater_max_mA']:g} mA", f"{x['V_heater_max_V']:g} V", f"{x['J_line_mA_um2']:g} mA/µm²", f"{x['I_gnd_pad_mA']:g} mA", f"{x['I_gnd_pad_worst_mA']:g} mA"] for x in c["current_density"]]
    return f'''
<h2 id="m2-s5">M2 s5　EC I/O、PAD 與繞線</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><p><b>這一步要回答：</b>光怎麼進出晶片？14 個 heater 怎麼以單層 Ti/AL 繞線到最外圍的 PAD？</p><p><b>做法：</b>直接匯入審查過的核心 GDS，不重畫；外加 EC、扇出波導、PAD 與繞線。</p></div>
<h3 id="m2s5-overview">① 實際全圖：左右光學 I/O，上下電氣 PAD</h3>
{fig_img("chip", "../figures/lut4/s3_chip.png", "整顆晶片佈局", f"整顆晶片 {c['die_um'][0]:g}×{c['die_um'][1]:g} µm：西緣 5 個輸入 EC、東緣 5 個輸出 EC（間距 {c['ec_pitch_um']:g} µm）；PAD {c['n_pads']} 個在上下緣最外圍。")}
<h3 id="m2s5-ec">② 光學 I/O：EC 與扇出</h3>
<ul><li><b>EC：</b>100 nm 薄矽尖端邊緣耦合器（尖端 {c['ec_params']['tip_w']:g} µm、錐形 {c['ec_params']['taper_len']:g} µm），配 {c['ec_pitch_um']:g} µm 間距的光纖陣列。</li>
<li><b>扇出（把波導間距拉開）：</b>核心埠距 30 µm → EC 間距 {c['ec_pitch_um']:g} µm，以 {c['fan_length_um']:g} µm 的 cosine S 彎；最小曲率半徑 {c['fan_rmin_um']:.1f} µm。</li>
<li><b>輸入等長：</b>輸入側加 {c['comp_length_um']:g} µm 補長段（{c['comp_n']} 個往上的凸起），5 個輸入從 EC 到核心等長（差 {c['fan_in_spread_um']:.4f} µm）。輸入之間的長度差會變成隨溫度、波長漂移的相位差；輸出只量功率，不需等長。</li></ul>
{fig_img("ec", "../figures/lut4/s3_ec.png", "EC 放大", "EC 與扇出局部放大。", "85%")}
{table("loss", "各波導損耗估計（不含 EC；傳播 3–4 dB/cm、每顆 MMI 0.45 dB，與相位設定的模型相同）", ["波導", "長度（µm）", "經過 MZI", "傳播（dB）", "MMI（dB）", "合計（dB）"], loss)}
<p><b>晶片走線會不會改變判讀？</b>輸入側 5 路等長，只造成共同縮放，不影響雙差值。輸出側 o1–o5 的扇出長度不同，讀取埠之間的損耗差換成相對增益後重算判讀（相位不變）：</p>
{table("route", "輸出扇出長度差對判讀的影響（相對最短的一路）", ["傳播損耗", "各輸出相對損耗（dB）", "7 個函數", "XOR4 裕量（Pᵤ）"], rrow)}
<p>讀取埠 o2、o4、o3 之間的差不到 0.03 dB，7 個函數都全對；核心內各波導的長度差每顆 MZI 只有約 {REV["mzi_extra_gds_um"]:.0f} µm，損耗差可忽略。實際晶片的 EC 損耗差與 PD 響應度差，與 TIA 增益差相同，由出廠修整處理（出廠時量測並調整增益）。</p>
<h3 id="m2s5-route">③ 電氣：PAD 與單層繞線</h3>
<ul><li>北指晶片上緣，南指下緣。金屬只有一層（Ti/AL），訊號線與地線不能交叉。heater 在第 r 條波導時，往北跨 r 條波導、往南跨 5−r 條，取跨越較少的一側（北 {c['n_pads_side']['N']}、南 {c['n_pads_side']['S']} 個 PAD）。</li>
<li>直走會碰到其他 heater 的 TiN 時，先在落墊高度橫移（{c['n_jog']} 條）。PAD 依走線的左右順序排列，所以走線不交叉。</li>
<li>相鄰兩個 heater 的地端排在一起、共用一個 GND PAD（逐一試每個 heater 哪端接訊號，取 PAD 數最少者；{c['n_heater_flipped']} 個改成右端接訊號），共 {c['n_gnd_pads']} 個 GND PAD。</li></ul>
{fig_img("route", "../figures/lut4/s3_route.png", "繞線放大", "繞線局部放大：橫移、轉折與共用 GND。")}
<div class="notice"><b>設計提示：</b>若所有走線都在同一高度轉折再斜接到 PAD，DRC 會出現 6 處 Ti/AL 間距只有 8.84 µm（規則 10 µm）。這些位置都在第 1 層 MZI-1、MZI-2 兩個 φ heater 的走線轉角。Model-7a 第 1 層這兩個 φ heater 位在同一個 x，兩條相鄰走線的斜率不同，轉角附近距離過近。<b>修正：</b>同一側往左走的走線越靠左越早轉折，往右走的越靠右越早轉折，相鄰轉折高度錯開 12 µm。修正後 DRC 違規為 0，Ti/AL 不同網最小距離 {c['al_min_net_spacing_um']:g} µm。</div>
{code("design/lut4/s5_chip/chip.py", 186, 196)}
<p class="muted">P01–P14 是訊號 PAD；GN、GS 開頭分別是北側、南側的 GND PAD。</p>
{table("pads", "PAD 表（由西往東；GND PAD 標出共用的兩個 heater）", ["PAD", "側", "x（µm）", "連接"], pads)}
<h3 id="m2s5-current">④ 電流密度估算</h3>
<p>平台未公開 TiN 片電阻，heater 電阻取三個假設值；每個 heater 需要 2π 時（約 {2 * TOL['P_pi_mW']:g} mW）的電流：</p>
{table("cur", "heater 電流與 Ti/AL 走線電流密度（線寬 10 µm、厚 0.22 µm）", ["heater 電阻", "最大電流", "最大電壓", "走線電流密度", "GND PAD 電流（設定值）", "GND PAD 電流（兩個都 2π）"], cur)}
<p>每個 heater 的地線各自走到 GND PAD，兩條地線只在 PAD 上會合。依每段線長、線寬與厚度建立電阻網路並解節點方程式（程式 <a href="../design/lut4/s6_verify/gnd_net.py">gnd_net.py</a>；由幾何與假設值推算的模型值，不是寄生萃取或量測），heater {GN["worst"]["R_h_kohm"]:g} kΩ 時 2π 的相位不足最差 {GN["worst"]["single_rad"]:.3f} rad（{GN["worst"]["multi_heater"]}），單路驅動與 14 路同時驅動相同，單路校正後殘差為 {GN["worst"]["residual_rad"]:.3f} rad。此結果的前提是 PAD 等電位、片外地阻抗為零；探針、打線與片外共地的阻抗未計入。</p>
<p class="muted">電遷移是電流密度過高造成金屬劣化的現象。平台未公布 Ti/AL 的電遷移上限，表中電流密度未與上限比對。PAD 尺寸沿用 PDK HeaterPad（80×100 µm）。打線、探針與 ESD（靜電放電）保護不在本課程範圍。</p>
<p>Ti/AL 跨越波導 {c['n_crossings']} 次。金屬在上包覆層中從矽波導上方通過，兩者不接觸；光路本身沒有波導交叉。</p>
<h3 id="m2s5-sources">⑤ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s5_chip/chip.py">chip.py</a>（加入 EC、扇出、PAD 與繞線）、<a href="../design/lut4/s5_chip/figs.py">figs.py</a>（繪製本步的圖）；產物 <a href="../design/lut4/s5_chip/out/chip.gds">chip.gds</a>（整顆晶片佈局）、<a href="../design/lut4/s5_chip/out/chip_info.json">chip_info.json</a>（PAD、EC 與走線對照）。</p>
</section>
'''


# ---------------------------------------------------------------- M2 s6
def m2s6():
    d = DRC
    ck = CONN["checks"]
    fl = CONN["faults"]
    frows = [[k, "抓到" if v else "未抓到"] for k, v in fl.items()]
    return f'''
<h2 id="m2-s6">M2 s6　DRC 與連接檢查</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><p><b>這一步要回答：</b>幾何符合平台規則嗎（DRC）？電氣接線與原理圖一致嗎（LVS）？光學埠接對了嗎？檢查本身抓得到錯嗎？</p></div>
<h3 id="m2s6-flow">① DRC 與連接檢查的範圍</h3>
{table("vflow", "三種檢查", ["檢查", "回答的問題", "方法"],
       [["DRC", "線寬、間距、包覆是否符合平台規則", f"KLayout 批次執行平台被動製程規則檔（{d['n_rules']} 類檢查），設計區＝晶片外框"],
        ["LVS（電氣）", "每個 heater 是否恰好接到自己的訊號 PAD 與一個 GND PAD", "Ti/AL 聯集成網、TiN 聯集成 heater，重疊處為接點；與規格的原理圖比對"],
        ["光學連通", "10 個 EC 是否接到對的核心埠", "矽波導聯集成連通塊（MMI 不展開），由 EC 標記追到核心埠"]])}
<h3 id="m2s6-result">② 結果</h3>
{table("vres", "晶片驗證結果", ["項目", "結果"],
       [["DRC 違規", f"{d['total']}（{d['n_rules']} 類檢查；外框外 {d['outside']}）"],
        ["GDS 99 外框", f"{d['n_gds99']} 個，等於晶片外框"],
        ["核心未被改動", f"多邊形 {CONN['core_polygons'][0]}／{CONN['core_polygons'][1]} 相同"],
        ["電氣網／heater", f"Ti/AL {CONN['electrical']['al_nets']} 網、TiN {CONN['electrical']['tin_regions']} 塊"],
        ["LVS", "14/14 一致，每個 heater 2 個接點" if ck["lvs_clean"] and ck["every_heater_two_contacts"] else "有錯"],
        ["GND 配對", "與 PAD 表一致" if ck["gnd_pairing"] else "不一致"],
        ["光學", "10/10 個 EC 接到對的核心埠" if ck["optical_clean"] else "有錯"]])}
{fig_img("nets", "../figures/lut4/s4_nets.png", "抽出的電氣網", f"由 GDS 抽出的 {CHIP['al_components']} 個 Ti/AL 網（每網一種顏色）與 14 個 TiN heater。")}
<h3 id="m2s6-fault">③ 故障注入：檢查程式的檢出能力</h3>
{table("vfault", "在讀回的圖形與標記上注入故障", ["故障", "結果"], frows)}
{fig_img("vchk", "../figures/lut4/s4_checks.png", "LVS 與故障注入", "左：14 個 heater 的接點與網；右：故障注入 8/8 抓到。")}
<div class="notice"><b>注意：</b>故障注入的切口必須真的落在走線上。若在 y＝200 µm 切斷最左側訊號線，因該處走線為斜線，切口不會切到它，「Ti/AL 斷路」就檢不出來。本例改在 PAD 下方的垂直段（y＝390 µm）切斷，8/8 全部檢出。佈局改變時，故障注入的位置也要一併檢查。</div>
<h3 id="m2s6-scope">④ 檢查範圍</h3>
<p>DRC 使用平台提供的 KLayout 被動製程規則檔；同一份交付 GDS 再以 Virtuoso 與 Calibre 檢查，見 M2 s7 ⑥～⑧。LVS 為本課程以幾何聯集實作的接點檢查；熱串擾與光學損耗由模擬與審查另外評估。</p>
<h3 id="m2s6-sources">⑤ 程式與產物</h3>
<p>程式 <a href="../design/lut4/s6_verify/verify.py">verify.py</a>（DRC、LVS、光學連通與故障注入）、<a href="../design/lut4/s6_verify/gnd_net.py">gnd_net.py</a>（heater 回路的電阻網路與節點分析）；產物 <a href="../design/lut4/s6_verify/out/drc_result.json">drc_result.json</a>（DRC 結果）、<a href="../design/lut4/s6_verify/out/connectivity.json">connectivity.json</a>（電氣與光學連接結果）。</p>
</section>
'''


# ---------------------------------------------------------------- M2 s7
FILE_USE = {"figures/s1_core.png": "核心佈局圖", "figures/s3_chip.png": "整顆晶片佈局圖", "figures/s3_ec.png": "EC 放大圖", "figures/s3_route.png": "繞線放大圖",
            "function/lut4_netlist.json": "接線表", "function/phases.json": "七個範例函數的相位", "function/tolerance.json": "容許量", "function/truth_tables.csv": "每組輸入的判讀",
            "interfaces/optical_ports.csv": "光學埠對照表", "interfaces/pads.csv": "PAD 對照表", "interfaces/spec.json": "規格", "interfaces/system_requirements.json": "片外系統需求",
            "layout/LUT4_chip.gds": "交付的晶片佈局", "README.md": "交付包說明", "check_delivery.py": "交付檢查程式", "verification/connectivity.json": "電氣與光學連接結果", "verification/drc_result.json": "DRC 結果",
            "verification/review_checks.json": "佈局審查紀錄", "verification/sim_results.json": "電路模擬結果",
            "verification/gnd_segments.json": "heater 回路電阻網路的逐段資料", "verification/gain_box.json": "確定性增益盒 ε", "verification/gain_robust.json": "增益失配補強研究與相位"}


def m2s7():
    g = PKG["gate"]
    files = json.loads((paths.ROOT / "delivery_lut4" / "MANIFEST.json").read_text(encoding="utf-8"))["files"]
    frows = [[f"<a href=\"../delivery_lut4/{f['path']}\">{f['path']}</a>", FILE_USE.get(f['path'], ""), f"{f['bytes']:,}", f"<code>{f['sha256'][:12]}…</code>"] for f in files]
    return f'''
<h2 id="m2-s7">M2 s7　完成整個 PIC 設計：最終佈局與交付</h2><span class="status">依 LUT4 架構改寫</span>
<section class="step"><div class="bridge"><p><b>這一步要回答：</b>拿到交付包的人，能不能只靠裡面的檔案知道晶片怎麼接、怎麼設定、驗證到哪裡？</p></div>
<h3 id="m2s7-layout">① 最終佈局：從功能核心到完整介面</h3>
{fig_img("final", "../figures/lut4/s3_chip.png", "最終晶片佈局", f"最終晶片：Model-7a 核心＋10 個 EC＋{CHIP['n_pads']} 個 PAD。")}
{fig_img("final_core", "../figures/lut4/s1_core.png", "核心放大", "核心放大：對照 M1 s2 的接線圖，MZI-1～MZI-7 與 H01～H14 的位置。")}
<h3 id="m2s7-results">② 檢查結果總表：每個通過都對應一個範圍</h3>
{table("gate", "交付前檢查", ["檢查", "範圍", "結果"],
       [["電路模擬", "PDK MMI 確認 U；判讀用每顆 MMI 0.45 dB 模型；1.55 µm、7 個函數 × 16 組；不含晶片走線", f"{SIM['passed']}/{SIM['total']}" + ("　通過" if g["sim"] else "")],
        ["佈局審查", "只讀核心 GDS：連通、U、判讀、金屬、間距、曲率", "V1–V11 通過（M2 s4 ③ 的審查表）" if g["review"] else "未通過"],
        ["DRC", "整顆晶片、平台被動規則檔", f"違規 {DRC['total']}"],
        ["LVS", f"14 個 heater、{CHIP['n_pads']} 個 PAD", "14/14" if g["lvs"] else "有錯"],
        ["光學連通", "10 個 EC", "10/10" if g["optical"] else "有錯"],
        ["故障注入", f"核心與審查各組，模擬 {len(SIM['faults'])}＋晶片 {len(CONN['faults'])}", "全部抓到" if g["faults"] else "未全抓到"],
        ["Calibre DRC（規則草案）", "交付 GDS、16 條線寬／間距規則；故障檔 2 種", f"{COM['calibre']['chip']['total']}；故障檔 {COM['calibre']['fault']['total']} 筆抓到{com_tag()}"],
        ["Virtuoso 來回", "strmin → strmout（maxVertices 8191）", ("與原檔逐層相同" if COM["checks"]["roundtrip_8191_identical"] else "不同") + com_tag()],
        ["交付檢查", f"check_delivery.py：檔案清單與雜湊、{CHIP['n_pads']} 個 PAD、10 個 EC、由相位重算 112 列真值表，以及上列結果檔的固定項目；另以 {len(DCHK['self_test'])} 種竄改副本驗證檢查本身", "全部通過" if g["delivery_check"] and DCHK["all_ok"] else "未通過"]])}
<h3 id="m2s7-io">③ 兩張介面對照表</h3>
<p><a href="../delivery_lut4/interfaces/pads.csv">pads.csv</a>：PAD 名稱、座標、訊號或 GND、對應的 heater、MZI 與相位。<a href="../delivery_lut4/interfaces/optical_ports.csv">optical_ports.csv</a>：EC 端面座標、訊號與用途（o2、o4、o3 判讀；o1、o5 監看）。</p>
<h3 id="m2s7-delivery">④ 交付檔案與可追溯性</h3>
{table("files", f"交付包內容（表列 {PKG['n_files'] - 1} 個檔，另加 MANIFEST.json 本身）", ["檔案", "用途", "位元組", "SHA-256"], frows)}
<p>SHA-256 是檔案內容的指紋，用於確認檔案未被更動；MANIFEST.json 是全部檔案的指紋清單。README.md 依序說明晶片、輸入、判讀、範例函數、驗證、校正與限制。交付包由 <a href="../design/lut4/s7_delivery/package.py">package.py</a> 產生。打包完成後，以 <a href="../design/lut4/s7_delivery/check_delivery.py">check_delivery.py</a> 檢查整包，通過後才算完成交付。</p>
<p>此程式隨交付包提供，收件者可自行執行。檢查所用的檔案、PAD、EC、函數、故障案例與審查項目皆為程式內的固定清單，不由受檢檔案推得，因此缺列、重複列、空集合與鍵名錯誤都不會通過。真值表由 phases.json 獨立重算（OOK 的資料光場為 0／1）。DRC、LVS、光學連通、故障注入、佈局審查與電路模擬僅核對結果檔的紀錄，並未重新執行；重新執行 DRC 需另備 KLayout 與平台規則檔。</p>
<h3 id="m2s7-handoff">⑤ 完成課程設計，銜接實體驗證</h3>
<ul><li><b>量測校正：</b>以監看埠與三個讀取埠量測 MMI 損耗與分光、heater P_π、各軌固定相位差，再重新求 14 個相位；容許量在校正後重算。</li>
<li><b>接收端：</b>三路 TIA（含 PD、EC）增益由出廠修整調整，容許量依函數而定。確定性增益盒半寬（相位固定的模型值）：XOR4 ±{GB["functions"]["XOR4"]["eps_pct"]:.2f}%、0x0069 ±{GB["functions"]["0x0069"]["eps_pct"]:.2f}%，全表相位庫逐表最小 ±{GB["library"]["eps_min_pct"]:.2f}%；裕量不足的真值表以量測增益重求相位或耐增益誤差的相位解補強（附錄 E-5）；比較器門檻 0；調變消光比 ≥ {SYS["er_min_db"]} dB。</li>
<li><b>片外系統需求：</b>五路輸入相干、同一偏振、相對相位穩定（需片外相位鎖定或追蹤，本課程未實作）；雷射波長 ±{SYS["dlambda_tol_nm"]["XOR4"]:g} nm、晶片溫度 ±{SYS["dT_tol_K"]["XOR4"]:g} K 以內（XOR4，模型值）。</li>
<li><b>尚未完成（以下均未實作）：</b>五路輸入的相位穩定方案；只靠 o1–o5 量測時如何辨識每顆 MZI 的參數、14×14 熱串擾矩陣的校正；熱串擾的溫度分布模擬；完整雜訊預算（shot、RIN、比較器偏移）；MMI 與 heater 的波長、溫度相依；高速時序；晶圓廠驗證過的 Calibre 規則檔（本課程只移植線寬與間距）；打線、探針、ESD 與電遷移上限。</li></ul>
{commercial()}
</section>
'''


# ---------------------------------------------------------------- 全表資料的輪次、門檻與相位庫
def bank_note():
    """全表結果來自哪一輪、用什麼門檻、相位存在哪裡，都由 full_replay.json 帶入。"""
    r1, r2 = FULLREP["round1_24_starts"], FULLREP["merged_round1_plus_refine"]
    neg = FULLREP["negative_tests"]
    mg = lambda x: f"{x:.4f}" if abs(x) >= 1e-3 else f"{x:.1e}"              # 接近 0 的負值不能四捨五入成 0
    wrong = [v for k, v in neg.items() if k != "R_2p9"]
    rows = [["第一輪", f"{r1['tables']:,} 張真值表，每張 24 個起點", f"{r1['passed_tables']:,}", f"{r1['wrong_rows']:,}", f"{mg(r1['min_margin_pu'])}（{r1['worst_mask']}）", f"{r1['ge_0p1']:,}"],
            ["第二輪後的合併相位庫", f"裕量最低的 {FULLREP['refined_masks']} 張改用 {REF['starts'][0]}、{REF['starts'][1]} 個起點，每張保留裕量最高的解", f"{r2['passed_tables']:,}", f"{r2['wrong_rows']:,}", f"{mg(r2['min_margin_pu'])}（{r2['worst_mask']}）", f"{r2['ge_0p1']:,}"]]
    EXTRA_TXT = (f"<li><b>另一份相位檔的交叉檢查：</b>另一份獨立求得的相位檔（SHA-256 前 16 碼 <code>{BANK['bank']['sha256'][:16]}</code>）以同一模型重播 {BANK['n_rows']:,} 列，"
                 f"判錯 {BANK['n_row_errors']} 列，最低裕量 {BANK['margin']['min']:.4f} Pᵤ（{BANK['margin']['argmin']}）。此項僅供交叉檢查，不屬於上表兩輪，數字不合併。</li>")
    return f"""<h4 id="bank-source">資料來源：輪次、門檻與相位庫</h4>
<p>上面的全表數字來自兩輪相位合成。合成是為每張真值表求出 14 個相位，條件為每顆 MZI 損耗 {FULLREP['loss_db_per_mzi']:g} dB、參考光 R＝{FULLREP['R']:g}、{ENC_NOTE}。本節使用的名詞如下：Pᵤ 是功率單位，等於一路資料光（振幅 1）的功率；裕量是 16 組輸入中離判讀邊界最近的距離，單位 Pᵤ，數值越大越不易受誤差影響。</p>
<p>下表是獨立重播的結果。每輪檢查 {r1['rows']:,} 列，即 {r1['tables']:,} 張真值表 × 16 組輸入。</p>
{table("bankrounds", "兩輪全表結果（獨立重播；裕量單位 Pᵤ）", ["輪次", "範圍", "通過的真值表", "判錯列", "最低裕量", "裕量 ≥ 0.1 的張數"], rows)}
<ul><li><b>門檻：</b>合成時，裕量大於 {COV['real_threshold']:g} Pᵤ 才算找到解。獨立重播時，裕量要大於 10<sup>{round(math.log10(r1['tolerance_pu']))}</sup> Pᵤ，而且 16 列全部判對，才算通過。這兩個門檻只判斷是否為解，不代表裕量足夠；裕量大小以表中的最低裕量與 ≥ 0.1 Pᵤ 的張數為準。</li>
<li><b>相位庫：</b>相位庫是存放全部 {r2['tables']:,} 張真值表各 14 個相位的檔案，即 <a href="../design/{VER}/s0_coverage/out/merged_phases.npz">merged_phases.npz</a>（SHA-256 前 16 碼 <code>{FULLREP['merged_bank_sha256'][:16]}</code>；SHA-256 是檔案內容的指紋）。七個範例函數另有自己的相位（附錄 B），不能代替相位庫。</li>
<li><b>獨立重播：</b>獨立重播是以另一支程式重新計算存下來的相位，用來確認結果不依賴合成程式本身。<a href="../design/{VER}/s0_coverage/replay_full.py">replay_full.py</a> 不呼叫合成器，逐顆 MZI 算出光場與判讀，結果存在 <a href="../design/{VER}/s0_coverage/out/full_replay.json">full_replay.json</a>。</li>
<li><b>反向測試：</b>反向測試是故意放入錯誤，確認重播能夠檢出。換用另一種編碼、對調 θ 與 φ、改用另一種 MZI 接線時，重播分別判錯 {wrong[0]['wrong_rows']:,}、{wrong[1]['wrong_rows']:,}、{wrong[2]['wrong_rows']:,} 列。把 R 改成 2.9 時判錯 {neg['R_2p9']['wrong_rows']} 列，因為這個偏差沒有使任何一列的判讀翻轉；這項只能由裕量偏移（最大 {neg['R_2p9']['max_margin_shift_pu']:.3f} Pᵤ）看出。</li>{EXTRA_TXT}</ul>
<p class="muted">以上是 {FULLREP['loss_db_per_mzi']:g} dB／MZI 模型下的靜態全表結果，不含實際佈局與製程變異。</p>"""


# ---------------------------------------------------------------- 商用工具結果的範圍
def com_scope():
    """依 commercial.json 寫結果來源：實跑才寫實跑，既有紀錄要明講。"""
    limit = "這裡的 Calibre 規則是教學草案，平台沒有提供正式簽核規則，所以不構成製程簽核。"
    if COM.get("run_record"):
        return "strmin、strmout、Calibre 與下方截圖都是對這份交付 GDS 實際執行的結果（檔案 SHA-256 相同）。" + limit
    return "Calibre、strmin、strmout 的數字是先前的執行紀錄，未對這份檔案重新執行。這份 GDS 去掉時間戳後與該紀錄使用的 GDS 幾何相同，所以結果適用。" + limit


def com_tag():
    return "（實際執行）" if COM.get("run_record") else "（先前紀錄，未對此檔重新執行）"


# ---------------------------------------------------------------- M2 s7 ⑥～⑧（Virtuoso／Calibre）
def commercial():
    c = COM
    cal = c["calibre"]
    names = {"chip": "交付的 LUT4_chip.gds", "fault": "故障檔（加兩種違規）", "strmout_200": "Virtuoso 匯出 maxVertices 200", "strmout_8191": "Virtuoso 匯出 maxVertices 8191"}
    kl = {"chip": DRC["total"], "fault": 2, "strmout_200": c["klayout"]["strmout_200"]["total"], "strmout_8191": c["klayout"]["strmout_8191"]["total"]}
    rows = []
    for t in ("chip", "fault", "strmout_200", "strmout_8191"):
        hit = "、".join(f"{k} {v}" for k, v in cal[t]["by_rule"].items() if v) or "—"
        rows.append([names[t], str(kl[t]), str(cal[t]["total"]), hit])
    rrows = [[f"GDS {L}", str(v["n_orig"]), str(c["roundtrip"]["strmout_200"]["layers"][L]["n_out"]), f'{c["roundtrip"]["strmout_200"]["layers"][L]["sym_diff_um2"]:g}',
              str(c["roundtrip"]["strmout_8191"]["layers"][L]["n_out"]), f'{c["roundtrip"]["strmout_8191"]["layers"][L]["sym_diff_um2"]:g}']
             for L, v in c["roundtrip"]["strmout_8191"]["layers"].items()]
    rules = [[r["svrf_name"], f"GDS {r['layer']}", "線寬" if r["kind"] == "width" else "間距", f"{r['value_um']:g} µm"] for r in c["rules"]]
    rv = c["raw_vs_clean"]["strmout_200"]
    lg = c["logs"]
    return f"""
<h3 id="m2s7-virtuoso">⑥ {"" if COM.get("run_record") else "先前紀錄："}Virtuoso 匯入並顯示交付的 GDS</h3>
<div class="notice"><b>本節資料來源：</b>{com_scope()}</div>
<p>Virtuoso 與 Calibre 是商用 EDA（電子設計自動化）工具。strmin 把 GDS 匯入 Virtuoso 的資料庫（OA library），strmout 則把資料庫匯出成 GDS。本節在 EDA 伺服器上以 strmin 匯入交付的 LUT4_chip.gds（頂層 cell L4_CHIP），以唯讀方式開啟。顯示設定改為 filterSize＝0、displayResolution＝Very High，因為預設值會在縮小時濾掉 0.45 µm 的波導，使波導看似斷開。為便於辨識，套用與前面相同的配色（GDS 3 藍、39 橘、41 綠、4 淺黃、5 粉紅）、隱藏 GDS 99 外框，並只在暫存副本中放大文字標記；交付的 GDS 不變。匯入紀錄：錯誤 {lg["strmin.log"]["errors"]}、警告 {lg["strmin.log"]["warnings"]}。</p>
{fig_img("v_chip", "../figures/lut4/s8_v_chip.png", "Virtuoso 開啟交付晶片的全圖", "Virtuoso 開啟交付的 LUT4 晶片（全圖）：西緣 5 個輸入 EC 與補長段、東緣 5 個輸出 EC、上下緣 21 個 PAD 與 Ti/AL 繞線。")}
{fig_img("v_core", "../figures/lut4/s8_v_core.png", "Virtuoso 核心放大", f"Virtuoso 核心放大：MZI、TiN heater（橙）與 Ti/AL 接點、走線（綠）；畫面是整片晶片的核心區，含通往 PAD 的走線，可對照 M2 s5 的整片佈局圖（圖 {FR('chip')}）。")}
{fig_img("v_mzi", "../figures/lut4/s8_v_mzi.png", "Virtuoso 第 1 層放大", "第 1 層放大：MZI-2（上）與 MZI-1（下），每顆有 φ（第一顆 MMI 之前）與 θ（兩顆 MMI 之間）兩個 heater；標記 H01～H04。")}
<h3 id="m2s7-calibre">⑦ Calibre DRC：以第二套工具檢查同一份 GDS</h3>
<p>平台只提供 KLayout 規則檔，因此由它自動產生 Calibre 規則草案（SVRF 是 Calibre 的規則語言）。草案移植 {c["coverage"]} 個輸出敘述，即各層的最小線寬與最小間距（門檻沿用 KLayout 版，再減 {abs(c["feature_margin_um"]):g} µm）；未移植 {c["deck_outputs"] - c["ported"]} 個：格點、設計區，以及 {"、".join(c["not_ported"])}。KLayout 規則檔的格點檢查以迴圈對每一層各產生一類，所以 {c["deck_outputs"]} 個輸出敘述在執行時是 {c["deck_categories"]} 個檢查類別。這份草案不是晶圓廠驗證過的規則檔，只用來確認兩套工具對線寬、間距的判斷一致。Calibre 以批次方式檢查四份 GDS：</p>
{table("calrun", "KLayout 平台規則檔與 Calibre 草案的結果", ["GDS", "KLayout 違規", "Calibre 結果", "Calibre 命中的規則"], rows)}
{fig_img("rve_chip", "../figures/lut4/s8_rve_chip.png", "Calibre RVE 交付晶片", "Calibre RVE（Calibre 的結果檢視介面）開啟交付晶片的結果：16 項檢查全部 0（No Results Found）。", "60%")}
{fig_img("rve_fault", "../figures/lut4/s8_rve_fault.png", "Calibre RVE 故障檔", "Calibre RVE 開啟故障檔的結果：L39_S（TiN 間距）與 L41_W（Ti/AL 線寬）各 1 筆，就是故意加入的兩種違規。", "60%")}
{fig_img("v_fault", "../figures/lut4/s8_v_fault.png", "Virtuoso 故障位置", "Virtuoso 放大故障檔的兩處：左為 1 µm 寬的 Ti/AL（規則 ≥ 2 µm），右為相距 5 µm 的兩塊 TiN（規則 ≥ 10 µm）；下方為 PAD。")}
<details><summary class="note-toggle">查看移植的 16 條規則</summary>{table("calrules", "Calibre 草案移植的規則", ["名稱", "層", "種類", "平台值"], rules)}</details>
<h3 id="m2s7-roundtrip">⑧ Virtuoso 匯出 GDS 時的 maxVertices 設定</h3>
<p>maxVertices 是單一多邊形允許的最多頂點數。把 OA library 再以 strmout 匯出兩次。預設 maxVertices＝200 時，超過 200 個頂點的曲線（扇出 S 彎、補長凸起）被切成多塊（紀錄檔 XSTRM-275 警告 {lg["strmout_200.log"]["xstrm275"]} 次），GDS 3 由 {c["roundtrip"]["strmout_200"]["layers"]["3"]["n_orig"]} 塊變成 {c["roundtrip"]["strmout_200"]["layers"]["3"]["n_out"]} 塊；指定 8191 時與原檔逐層完全相同。</p>
{table("roundtrip", "來回比對：原 GDS 與兩份匯出檔（多邊形數、幾何對稱差面積 µm²）", ["層", "原檔", "200 匯出", "200 差", "8191 匯出", "8191 差"], rrows)}
{fig_img("calcmp", "../figures/lut4/s8_compare.png", "KLayout 與 Calibre 的結果比較", "四份 GDS 的違規數。maxVertices＝200 的匯出檔只有 KLayout 平台規則檔報錯，Calibre 為 0。")}
{fig_img("seam", "../figures/lut4/s8_seam.png", "切割接縫放大", "切割接縫放大（x≈-300 µm，x1 扇入 S 彎）：原檔的曲線是一整塊，200 匯出檔在接縫處分塊；KLayout 的標記落在接縫上。")}
<p><b>只有 KLayout 報錯的原因：</b>平台規則檔對 GDS 3 使用 .raw（不合併），之後的線寬、間距改成逐塊檢查，切割後的細長小塊就被判為過窄（{rv["after_raw_width"]} 處線寬、{rv["after_raw_space"]} 處間距）；合併後檢查或改用 .clean 時都是 0，Calibre 也先合併再檢查。這些是假違規，幾何本身沒變（對稱差 {c["roundtrip"]["strmout_200"]["layers"]["3"]["sym_diff_um2"]:g} µm² 只是切割處的數值誤差）。<b>做法：</b>由 Virtuoso 匯出要送件的 GDS 時，明確指定 maxVertices 8191。</p>
<p class="muted">程式 <a href="../design/lut4/s8_commercial/commercial.py">commercial.py</a>（規則草案、批次腳本、比對）、<a href="../design/lut4/s8_commercial/virtuoso_view.py">virtuoso_view.py</a>（Virtuoso 與 RVE 截圖）；產物 <a href="../design/lut4/s8_commercial/out/commercial.json">commercial.json</a>（比對結果）、<a href="../design/lut4/s8_commercial/out/run.sh">run.sh</a>（批次腳本）、<a href="../design/lut4/s8_commercial/out/calibre_chip.summary">calibre_chip.summary</a>、<a href="../design/lut4/s8_commercial/out/calibre_fault.summary">calibre_fault.summary</a>（Calibre 結果摘要）。注意：若波導在畫面上看似斷開，原因是 Virtuoso 的顯示過濾：filterSize 預設 6 像素，小於此值的形狀不顯示，0.45 µm 的波導與 MMI 漸變段在縮小時被略過。設成 filterSize＝0、displayResolution＝Very High 後，波導連續顯示。GDS 本身沒有斷開（光學連通 10/10、Calibre 0）。</p>
"""


# ---------------------------------------------------------------- 附錄 E：光電判讀分析
WINDOW_SVG = """<svg viewBox="0 0 760 196" role="img" aria-labelledby="winT"><title id="winT">比例式窗口：P(o4) 是否落在 P(o3) 與 P(o2) 之間</title>
<path d="M60 150H720" stroke="#526274" stroke-width="1.5"/><text x="726" y="154" class="small">功率</text>
<text x="10" y="66">輸入 A</text>
<path d="M150 40V80" stroke="#8a96a3" stroke-width="3"/><text x="150" y="30" text-anchor="middle" class="small">P(o3)</text>
<path d="M330 40V80" stroke="#d08a1f" stroke-width="3"/><text x="330" y="30" text-anchor="middle" class="small">P(o4)</text>
<path d="M520 40V80" stroke="#2f6fb5" stroke-width="3"/><text x="520" y="30" text-anchor="middle" class="small">P(o2)</text>
<rect x="150" y="50" width="370" height="20" fill="#2f6fb5" opacity=".18"/><text x="540" y="66">順序正確 → y＝1</text>
<text x="10" y="133">輸入 B</text>
<path d="M240 108V146" stroke="#8a96a3" stroke-width="3"/><path d="M420 108V146" stroke="#2f6fb5" stroke-width="3"/><path d="M560 108V146" stroke="#d08a1f" stroke-width="3"/>
<rect x="240" y="118" width="180" height="20" fill="#2f6fb5" opacity=".18"/><text x="580" y="133">P(o4) 在窗口外 → y＝0</text>
<text x="60" y="184" class="small">窗口的上下邊界 P(o2)、P(o3) 也由 heater 設定並隨輸入改變；所有功率同比例縮放時，大小順序不變。</text></svg>"""


def gbox_block():
    """確定性增益盒（gain_box.json）與統計成功率分開呈現。"""
    fs, rb, lb, st = GB["functions"], GB["robust"], GB["library"], GB["self_test"]["counterexample"]
    row = lambda name, ph, r: [name, ph, f"±{r['eps_pct']:.2f}%", f"x＝{r['binding']['row']}（目標 {r['binding']['target']}）", f"{r['margin_at_3pct_box']:.3f}"]
    rows = [row(n, "標稱解", r) for n, r in fs.items()] + [row(n, "B　耐增益誤差的解", r) for n, r in rb.items()]
    gap = max(abs(r["corner_only_first_fail_eps"] - r["eps"]) - r["corner_scan_step"] for r in list(fs.values()) + list(rb.values()))
    assert gap <= 1e-6, gap                                           # 本段文字的前提：這些相位沒有被角落判定漏掉
    return f"""<p>上述成功率隨函數、樣本數與分布假設改變，常態分布的標準差也不是最大誤差界。以下另算確定性的增益盒半寬 ε：三路增益各自落在 [1−ε, 1+ε] 內的任何組合下，16 組判讀都正確（程式 <a href="../design/{VER}/s9_system/gain_box.py">gain_box.py</a>）。目標 1 的列要 Da、Db 都為正，兩者對增益是線性函數，最小值在盒的角落。目標 0 的列裕量為 max(−Da, −Db)，這是凸函數，最小值可能落在盒內，所以以線性規劃檢查盒內是否存在 Da＞0 且 Db＞0，再以二分搜尋求 ε。只查八個角落並不足夠：(P2, P3, P4)＝({st["P2_P3_P4"][0]:g}, {st["P2_P3_P4"][1]:g}, {st["P2_P3_P4"][2]:g})、增益各在 1±{st["delta"] * 100:g}% 時，八個角落全判 0，線性規劃仍找到兩個差值都為正的增益 (g2, g3, g4)＝({st["review_gain"][0]:g}, {st["review_gain"][1]:g}, {st["review_gain"][2]:g})。此例是檢查方法的反例，不是保存相位的結果。</p>
{table("appx_gainbox", "確定性增益盒半寬 ε（相位固定、每顆 MZI 0.9 dB、R＝3、只有三路增益誤差；模型值）", ["函數", "相位", "ε", "決定 ε 的列", "±3% 盒內最差裕量（Pᵤ，負值表示盒內有判錯）"], rows)}
<p>全表相位庫 {lb["n_tables"]:,} 張逐表計算（封閉式，最緊的一張再以線性規劃二分搜尋核對）：最小 ε＝{lb["eps_min_pct"]:.2f}%（{lb["mask"]}，x＝{lb["row"]}），中位數 {lb["percentiles_pct"]["50"]:.2f}%，小於 3% 的有 {lb["n_below"]["3%"]:,} 張。{lb["mask"]} 在 σ＝1%、2%、3% 時 2,000 次全對的比例為 {lb["worst_table_mc"]["0.01"] * 100:.1f}%、{lb["worst_table_mc"]["0.02"] * 100:.1f}%、{lb["worst_table_mc"]["0.03"] * 100:.1f}%。這些數字屬於保存的相位解，換一組相位解 ε 也會改變。上表的相位中，八角落判定與線性規劃得到的 ε 在掃描步長內相同，沒有保存解因此判錯；這只說明這些函數沒有踩到角落判定的缺口，不表示八角落方法足夠。</p>"""


def gfix_rows():
    rows = []
    for n in ("0x0069", "XOR4"):
        g = GR[n]
        nom, rob, re_ = g["nominal"], g["robust"], g["remeasure"]
        rows.append([n, "標稱解"] + [f"{nom['mc'][k] * 100:.1f}%" for k in ("0.02", "0.03", "0.05")] + [f"{nom['margin']:.3f}", f"±{min(nom['single'].values()) * 100:.1f}%"])
        rows.append(["", "A　量測增益後重求"] + [f"{re_[k]['resolved_pass'] * 100:.0f}%" for k in ("0.02", "0.03", "0.05")] + [f"每次 ≥ {min(v['resolved_margin_min'] for v in re_.values()):.3f}", "（依量測值）"])
        rows.append(["", "B　耐增益誤差的解"] + [f"{rob['mc'][k] * 100:.1f}%" for k in ("0.02", "0.03", "0.05")] + [f"{rob['margin']:.3f}", f"±{min(rob['single'].values()) * 100:.1f}%"])
    return rows


def appx_readout():
    names = list(FN)
    gt = TOL["gain_tolerance"]
    single = [[n, f"<code>{FN[n]['truth_hex']}</code>", f"{FN[n]['margin']:.3f}"] + [f"±{gt[n][c] * 100:.1f}%" for c in ("o2", "o4", "o3")] for n in names]
    h = SYS["tia_hard"]["0x0069"]
    single.append(["需要三次項（單一比較器無法實現）", "<code>0x0069</code>", f"{h['margin']:.3f}"] + [f"±{h['single'][c] * 100:.1f}%" for c in ("o2", "o4", "o3")])
    mc = [[f"σ＝{float(k) * 100:g}%", f"{min(SYS['tia_mc'][k].values()) * 100:.1f}%", f"{h['mc'][k] * 100:.1f}%"] for k in SYS["tia_mc"]]
    xor_rows = [["s（1 的個數）", "0", "1", "2", "3", "4"], ["h₁＝[(s−1)(3−s)＋0.5＞0]，即 1 ≤ s ≤ 3", "0", "1", "1", "1", "0"],
                ["h₂＝[(s−2)²−0.5＞0]，即 s ≠ 2", "1", "1", "0", "1", "1"], ["h₁ AND h₂＝XOR4", "0", "1", "0", "1", "0"]]
    return f"""
<details class="appendix-group"><summary class="appendix-title" id="appx-readout">附錄 E　光電判讀分析</summary>
<p>本附錄整理雙差值判讀的原理：光路與偵測器能算出什麼、接收端的比較器與 AND 補上什麼，以及哪些不理想會改變判讀。</p>
<details><summary class="section-toggle" id="appx-readout-1">E-1　單一比較只能做二次門檻函數</summary>
<p>輸入是二元（xᵢ 只取 0、1）、光路是線性（o＝Uv）、偵測是平方律（P＝|o|²），所以每個輸出功率都是輸入的二次多線性式：1 個常數、4 個一次項、6 個二次項（xᵢ²＝xᵢ，不會出現更高次）。兩個功率相減仍是同樣形式的二次式；比較器以門檻 0 判斷它的正負，能實現的就只有「二次門檻函數」（PTF2）。M1 s3 ④ 以 XOR4 的相位擬合 11 個係數，誤差為數值誤差，就是這個性質的驗證。</p>
<p>XOR3、XOR4 等函數需要三次以上的項，任何一個功率差的正負都表示不出來；多加 MZI 也不會改變，因為串接後仍是一個線性的 U。</p></details>
<details><summary class="section-toggle" id="appx-readout-2">E-2　兩個比較接 AND 突破二次的限制</summary>
<p>令 h₁＝[Da＞0]、h₂＝[Db＞0]，各自是一個二次門檻函數；接收端以固定的 AND 輸出 y＝h₁ AND h₂。兩個二次門檻函數的 AND 已不受二次的限制。以 XOR4 為例，令 s＝x1＋x2＋x3＋x4：</p>
{table("appx_xor4", "XOR4 分解為兩個二次門檻函數的 AND", xor_rows[0], xor_rows[1:])}
<p>h₁、h₂ 都只含 s 的二次式（s² 展開後只有 xᵢxⱼ 項）。實際晶片上 Da、Db 共用同一組 14 個相位與同一個 o4，兩者不能任意獨立選擇；Model-7a 能實現全部 65,536 張真值表是逐張合成的結果（M1 s2 ③），不是由這個分解直接保證。這部分能力來自接收端的 AND，引用時應寫明「光路＋固定接收端」。</p></details>
<details><summary class="section-toggle" id="appx-readout-3">E-3　為什麼不需要校準雷射功率</summary>
<figure>{WINDOW_SVG}<figcaption>圖 {F("window")}｜雙差值判讀等於「以兩個輸出功率當邊界的窗口」：y＝1 表示 P(o4) 落在 P(o3) 與 P(o2) 之間。</figcaption></figure>
<p>三個讀取功率來自同一顆雷射，雷射功率改變 k 倍時三者一起乘 k，Da、Db 的正負不變，所以比較器不需要隨光功率調整的參考電壓。會破壞這個比例關係的是各讀取路徑的增益不一致：</p>
<ul><li>三路 TIA 與 PD 響應度的差（E-5）。</li><li>輸出 EC 與扇出波導的損耗差：本晶片讀取埠之間不到 0.03 dB（M2 s5）。</li><li>各路徑經過的 MZI 數不同：損耗模型改變時不是整體縮放，相位要依實測損耗重求（M2 s2 ⑥）。</li></ul></details>
<details><summary class="section-toggle" id="appx-readout-4">E-4　接收端：三組 PD＋TIA、兩個比較器、AND</summary>
<p>o4 的訊號同時用在兩個比較，所以三個輸出埠各接一顆 PD 與 TIA，再於電路端比較（M1 s2 ③ 的接收端圖）。與單一門檻（2 個 PD、1 個比較器）相比，只多一組 PD＋TIA、一個比較器與一個固定 AND；兩個比較器都只比較兩個訊號的大小，門檻 0，不需要另外產生參考電壓。換邏輯功能時接收端完全不變，只改 14 個 heater 相位。</p></details>
<details><summary class="section-toggle" id="appx-readout-5">E-5　TIA 增益失配的容許量</summary>
<p>三個功率等比例縮放不影響結果，但三路增益不一致會。先單獨改變一路增益，找出不讓任何一組判讀翻轉的最大誤差（相位固定為交接值）：</p>
{table("appx_gain", "單一通道增益誤差的容許量（0.9 dB／MZI）", ["函數", "真值表", "裕量（Pᵤ）", "o2 通道", "o4 通道", "o3 通道"], single)}
<p>最嚴格的通常是 o4（同時參與兩個比較）。容許量與合成出的相位解有關，不只看裕量：0x0069 的裕量（{h["margin"]:.3f} Pᵤ）比 XOR4 大，單路容許量卻只有約 ±{min(h["single"].values()) * 100:.0f}%。三路同時偏差時容許量更小：</p>
{table("appx_gainmc", "三路增益同時偏差（各路 N(1, σ²)、2,000 次）：真值表全對的比例", ["增益誤差", "7 個範例函數中最低", "0x0069"], mc)}
<p>上表只含七個範例函數與 0x0069，不能推廣到全部真值表。增益差是固定的（不隨時間、光功率漂移），所以有兩種補強做法，比提高硬體匹配有效（程式 <a href="../design/lut4/s9_system/gain_robust.py">gain_robust.py</a>）：</p>
<ul><li><b>A　量測增益後重求相位：</b>出廠時量出三路的實際增益，合成 14 個相位時把增益放進模型。</li>
<li><b>B　合成時挑耐增益誤差的解：</b>目標改成三路增益在 1±3% 的增益盒內最差的裕量最大（盒內最差點含目標 0 的內部點，不只 8 個角落）。</li></ul>
{table("appx_gainfix", "增益失配的補強效果（三路增益同時偏差；A 各 σ 抽 100 次，標稱解與 B 用 2,000 次蒙地卡羅）", ["函數", "相位", "σ＝2%", "σ＝3%", "σ＝5%", "無增益誤差時的裕量（Pᵤ）", "單路容許量（最嚴）"], gfix_rows())}
<p>在這兩個函數上，兩種做法都提高了成功率：A 在 σ＝5% 時 100 次全對、每次裕量至少 {GR["0x0069"]["remeasure"]["0.05"]["resolved_margin_min"]:.3f} Pᵤ；B 讓 0x0069 的單路容許量由 ±{min(GR["0x0069"]["nominal"]["single"].values()) * 100:.1f}% 提高到 ±{min(GR["0x0069"]["robust"]["single"].values()) * 100:.1f}%，代價是裕量由 {GR["0x0069"]["nominal"]["margin"]:.3f} 降到 {GR["0x0069"]["robust"]["margin"]:.3f} Pᵤ。這是兩個函數、指定樣本數下的觀察，不是全部真值表的規格。A 的效果取決於增益量測的準確度，本分析假設量測無誤差。</p>
{gbox_block()}</details>
</details>
"""


# ---------------------------------------------------------------- 附錄
def appendix():
    progs = [["s1_handoff/handoff.py", "接線表、相位合成、規格、容許量", "M1 s2、M2 s1"],
             ["s0_algebra/algebra.py", "路徑展開、逐層光場、二次式", "M1 s3"],
             ["s2_sim/sim.py", "PDK 電路模擬、故障注入、損耗掃描", "M2 s2"],
             ["s3_core/layout.py", "核心佈局、讀回核對、核心 DRC", "M2 s3"],
             ["s4_review/review.py", "只讀 GDS 的佈局審查", "M2 s4"],
             ["s5_chip/chip.py", "EC、扇出、PAD、繞線、晶片 DRC", "M2 s5"],
             ["s6_verify/verify.py", "DRC、LVS、光學連通、故障注入", "M2 s6"],
             ["s6_verify/gnd_net.py", "heater 回路的電阻網路與多路同時驅動的節點分析（模型值）", "M2 s5"],
             ["s7_delivery/package.py", "交付包與 SHA-256 清單", "M2 s7"],
             ["s7_delivery/check_delivery.py", "交付檢查與反向測試", "M2 s7"],
             ["s0_basics/basics.py", "單顆、二顆 MZI＋R 的二輸入能力（重算 M1 s2 ①②）", "M1 s2"],
             ["s0_coverage/cover4.py", "65,536 張真值表逐張合成（約 2–3 小時，6 個平行程序）", "M1 s2"],
             ["s0_coverage/refine.py", f"最差 {REF['n']} 張與 XOR4 以 100、400 個起點重求相位", "M1 s2"],
             ["s9_system/system.py", "走線損耗、TIA 三路偏差、波長溫度、消光比、光功率", "M2 s1、M2 s5"],
             ["s9_system/gain_robust.py", "增益失配補強：量測增益後重求相位、耐增益誤差的相位解", "附錄 E-5"],
             ["s9_system/gain_box.py", "確定性增益盒 ε：目標 1 用角落極值、目標 0 用線性規劃，二分搜尋", "附錄 E-5"],
             ["s8_commercial/commercial.py", "Virtuoso strmin／strmout、Calibre DRC 批次與比對（需 Virtuoso、Calibre 與授權）", "M2 s7"],
             ["s8_commercial/virtuoso_view.py", "Virtuoso 顯示與 Calibre RVE 截圖（需圖形介面）", "M2 s7"],
             ["synth4.py", "雙差值判讀的相位合成（批次向量化、數值梯度）", "共用"],
             ["../m1_logic/s1_signal/and2_readout.py", "M1 s1 的 AND2 判讀練習", "M1 s1"]]
    prow = [[f'<a href="../design/lut4/{p}">{p}</a>', a, b] for p, a, b in progs]
    phrows = []
    for n, f in FN.items():
        phrows.append([n] + [f"{v:.3f}" for v in f["theta"]] + [""])
        phrows.append([""] + [f"{v:.3f}" for v in f["phi"]] + [""])
    phrows = [[r[0], "θ" if i % 2 == 0 else "φ"] + r[1:8] for i, r in enumerate(phrows)]
    tt = []
    import csv
    with open(paths.OUT("lut4/s1_handoff", "truth_tables.csv"), encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    blocks = ""
    for n in FN:
        rr = [[f"{r['x1']}{r['x2']}{r['x3']}{r['x4']}", r["target"], f"{float(r['P2']):.3f}", f"{float(r['P4']):.3f}", f"{float(r['P3']):.3f}",
               f"{float(r['Da']):+.3f}", f"{float(r['Db']):+.3f}", r["bit"]] for r in rows if r["function"] == n]
        blocks += (f'<details><summary>{n}（{FN[n]["expr"]}，{FN[n]["truth_hex"]}）</summary>'
                   + table(f"tt_{n}", f"{n} 的 16 組判讀（x1x2x3x4）", ["輸入", "目標", "P(o2)", "P(o4)", "P(o3)", "Da", "Db", "y"], rr) + "</details>")
    glo = src("glossary.html")
    glo = re.sub(r"B7 為本專案七顆 MZI 組成的單元[^<]*", "LUT4 macro Model-7a 為本課程七顆 MZI 組成的單元；磚牆排列指每層只混合相鄰兩條波導。", glo)
    glo = glo.replace("附錄 D　專有名詞", "附錄 D　專有名詞").replace("B7", "LUT4 macro")
    extra = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in [
        ("查找表／LUT4", "Look-Up Table (4 inputs)", "任意 4 輸入真值表都可設定的邏輯單元；本課程以 14 個相位設定。"),
        ("Model-7a", "7-MZI macro, version a", "本課程的 LUT4 macro：7 顆 MZI，每層 2、2、2、1 顆，讀取 o2、o4、o3。"),
        ("拓樸代碼", "Topology code", "由輸入往輸出讀，數字 k 表示一顆混合第 k、k＋1 條波導的 MZI（定義見 M1 s2 ③）。"),
        ("雙差值判讀", "Dual-difference readout", "Da＝P(o2)−P(o4)、Db＝P(o4)−P(o3)，兩者都大於 0 時判 1。"),
        ("二次門檻函數／PTF2", "Polynomial threshold function (degree 2)", "可寫成二次多項式正負的布林函數；單一功率差只能實現這類。"),
        ("轉阻放大器／TIA", "Transimpedance amplifier", "把光電流轉成電壓。三路增益需匹配。"),
        ("邊緣耦合器／EC", "Edge coupler", "在晶片側面與光纖耦合的元件。"),
        ("佈局規則檢查／DRC", "Design Rule Check", "檢查線寬、間距等幾何是否符合製程規則。"),
        ("佈局與原理圖比對／LVS", "Layout Versus Schematic", "由佈局抽出接線，與原理圖比對。"),
        ("故障注入", "Fault injection", "故意放入已知錯誤，確認檢查程式能夠檢出。"),
        ("Pᵤ", "Unit power", "本課程的功率單位，等於一路資料光（振幅 1）的功率。"),
        ("裕量", "Margin", "16 組輸入中離判讀邊界最近的距離，單位 Pᵤ；為正代表 16 組全對。"),
        ("合成／起點", "Synthesis／Starting point", "合成是為一張真值表求出 14 個相位；起點是求解時的隨機初始相位。"),
        ("交接值", "Handoff value", "M1 求出、交給 M2 使用的相位與裕量（附錄 B）。"),
        ("相位庫／獨立重播／反向測試", "Phase bank／Independent replay／Negative test", "存放全部真值表相位的檔案；以另一支程式重算這些相位；故意放入錯誤以確認重播能檢出。"),
        ("dB／dBm", "Decibel／dB-milliwatt", "功率比的對數單位；dBm 以 1 mW 為基準，0 dBm＝1 mW。0.9 dB 損耗表示功率剩約 81%。"),
        ("P_π", "Pi-shift power", "使相位改變 π 所需的 heater 功率。"),
        ("軌／軌距", "Rail／Pitch", "軌指波導；軌距是相鄰波導的中心距。"),
        ("扇出／落墊", "Fan-out／Landing pad", "把波導間距拉開的彎曲段；TiN 引線末端連接金屬的方塊。"),
        ("TE／偏振", "Transverse electric／Polarization", "光場振動的方向；本設計的輸入須為 TE，由片外設定，晶片上沒有偏振控制元件。"),
        ("出廠修整", "Factory trim", "出廠時量測接收端三路增益並加以調整。"),
        ("S 矩陣", "Scattering matrix", "列出任兩埠之間光場係數的矩陣；U 取自其中的輸入到輸出部分。"),
        ("Virtuoso／Calibre／strmin／strmout", "Commercial EDA tools", "商用佈局與驗證工具；strmin 匯入 GDS，strmout 匯出 GDS。"),
        ("SHA-256", "Secure hash", "檔案內容的指紋，內容改變指紋即不同。"),
        ("強度編碼／OOK", "On-Off Keying", "本頁採用的輸入編碼：有光＝1、無光＝0。"),
        ("消光比／ER", "Extinction ratio", "調變器輸出「1」與「0」的功率比，單位 dB。"),
        ("等價類", "Equivalence class", "輸入經排列或反相後可互相轉換的一組真值表。")])
    glo = glo.replace("</table>", extra + "</table>", 1)
    glo = re.sub(r"表 \d+｜", "表 " + TB("glo") + "｜", glo, count=1)
    return f'''
<details class="appendix-group"><summary class="appendix-title" id="appx-programs">附錄 A　程式與產物對照</summary>
{table("progs", "程式與產物（皆在 design/lut4/ 之下）", ["程式", "用途", "對應步驟"], prow)}
<p>每支程式的 out/ 是它的產物，後面的步驟一律讀前面步驟的 out/，不重算。在專案根目錄依序執行 basics、cover4 → handoff → algebra → sim → layout → review → chip → verify → system → package → commercial（需 EDA 伺服器），最後以 build_study.py 組裝本頁。程式路徑以 design/lut4/ 為準（and2_readout.py 在 design/m1_logic/）。</p></details>
<details class="appendix-group"><summary class="appendix-title" id="appx-phases">附錄 B　範例函數的相位設定</summary>
{table("phases", "七個範例函數的 θ、φ（rad，0–2π；每顆 MZI 0.9 dB 損耗模型）", ["函數", "", "MZI-1", "MZI-2", "MZI-3", "MZI-4", "MZI-5", "MZI-6", "MZI-7"], phrows)}
<p class="muted">θ_k 為兩顆 MMI 之間上臂的相位、φ_k 為第一顆 MMI 之前上臂的相位；heater 編號 H(2k−1)＝θ_k、H(2k)＝φ_k。相位是模型值，實際晶片要依量測重新求解。</p></details>
<details class="appendix-group"><summary class="appendix-title" id="appx-truth">附錄 C　範例函數的完整判讀</summary>
<p>每組輸入列出三個讀取埠功率（Pᵤ）與兩個差值；y＝[Da＞0] AND [Db＞0]。</p>{blocks}</details>
{glo}
{appx_readout()}
'''


# ---------------------------------------------------------------- 組裝
def renumber_kept(seg, counters):
    m = {}
    for kind in ("圖", "表"):
        for old in re.findall(kind + r" (\d+)｜", seg):
            counters[kind] += 1
            m[(kind, old)] = counters[kind]
    def sub(mt):
        k, n = mt.group(1), mt.group(3)
        return f"{k}{mt.group(2)}{m[(k, n)]}" if (k, n) in m else mt.group(0)
    return re.sub(r"(圖|表)( ?)(\d+)", sub, seg)


def renumber_new(seg, counters, assigned):
    for kind, tok in (("圖", "F"), ("表", "T")):
        for key in re.findall(r"@@" + tok + r":([^@]+)@@", seg):
            counters[kind] += 1
            assigned[(tok, key)] = counters[kind]
            seg = seg.replace(f"@@{tok}:{key}@@", str(counters[kind]), 1)
    return seg


STEPS = [("m1-s1", "M1 s1　光訊號與邏輯"), ("m1-s2", "M1 s2　MZI Macro 設計（Model-7a）"), ("m1-s3", "M1 s3　MZI 矩陣運算"),
         ("m2-s1", "M2 s1　LUT4 PIC 功能與介面規格"), ("m2-s2", "M2 s2　設計流程與電路模擬"), ("m2-s3", "M2 s3　IPKISS＋Python 佈局"),
         ("m2-s4", "M2 s4　佈局審查（Layout Review）"), ("m2-s5", "M2 s5　EC、PAD 與繞線"), ("m2-s6", "M2 s6　DRC 與連接檢查"),
         ("m2-s7", "M2 s7　最終佈局與交付")]
APPX = [("appx-programs", "附錄 A　程式與產物"), ("appx-phases", "附錄 B　相位設定"), ("appx-truth", "附錄 C　完整判讀"), ("glossary", "附錄 D　專有名詞"), ("appx-readout", "附錄 E　光電判讀分析")]
NAV_CSS = ("nav .nstep{display:block;font-weight:700;padding:5px 0}nav .nsub{display:none;margin:0 0 6px 12px}"
           "nav .nsub a{font-size:13px;padding:3px 0;color:var(--muted)}nav .nstep.open+.nsub{display:block}"
           "nav .nstep::before{content:'▸ ';color:var(--muted)}nav .nstep.open::before{content:'▾ '}")
NAV_JS = """<script>
// 左側目錄：只列步驟；點步驟才展開該步的 ①②…；捲動或錨點到某步時自動展開該步
(function(){var st=[].slice.call(document.querySelectorAll('nav .nstep'));
function show(a){st.forEach(function(x){x.classList.toggle('open',x===a);});}
st.forEach(function(a){a.addEventListener('click',function(){show(a.classList.contains('open')?null:a);if(!a.classList.contains('open'))return;});});
function stepOf(id){var e=document.getElementById(id);if(!e)return null;var best=null;st.forEach(function(a){var h=document.getElementById(a.getAttribute('href').slice(1));
if(h&&(h.compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING||h===e))best=a;});return best;}
function sync(){var id=decodeURIComponent(location.hash.slice(1));if(id){var a=stepOf(id);if(a)show(a);}}
window.addEventListener('hashchange',sync);window.addEventListener('load',sync);})();
</script>"""


def nav(html_):
    """由組裝後的內容自動列出每一步的小節（h3 與收合區的 summary），每一步規則相同。"""
    pos = [(html_.find(f'<h2 id="{k}"'), k, t) for k, t in STEPS]
    pos.append((html_.find('class="appendix-group"'), None, None))
    out = '<nav><b>可程式化矽光子 4 輸入 LUT 設計</b><a href="#intro">課程主線</a><hr>'
    for (a, k, t), (b, _, _) in zip(pos, pos[1:]):
        seg = html_[a:b]
        subs = re.findall(r'<(?:h3|summary)[^>]*?id="([^"]+)"[^>]*class="section-toggle"[^>]*>(.*?)</summary>|<h3 id="([^"]+)">(.*?)</h3>'
                          r'|<summary class="section-toggle" id="([^"]+)">(.*?)</summary>|<details id="([^"]+)"><summary class="section-toggle">(.*?)</summary>', seg, re.S)
        items = []
        for g in subs:
            sid, txt = next((g[i], g[i + 1]) for i in (0, 2, 4, 6) if g[i])
            txt = re.sub(r"<[^>]+>", "", txt).strip()
            if re.match(r"[①-⑳]", txt):
                items.append(f'<a href="#{sid}">{esc(txt)}</a>')
        out += f'<a class="nstep" href="#{k}">{t}</a><div class="nsub">{"".join(items)}</div>'
        if k in ("m1-s3",):
            out += "<hr>"
    out += "<hr>" + "".join(f'<a href="#{k}">{t}</a>' for k, t in APPX) + "</nav>"
    return out


def m1s1_fixed():
    s = src("m1s1.html")
    s = s.replace("<h1>Optical Computing Logic Design （1）</h1>", "<h1>Programmable Silicon Photonic 4-input LUT Design</h1>")
    s = s.replace("Programmable GHz Optical Computing : 7 MZIs for 4-bit Logic PIC Design",
                  "可程式化矽光子 4 輸入查找表（LUT4）設計｜Model-7a：7 顆熱調 MZI＋固定雙差值接收端")
    s = s.replace("<p><b>M2:</b> 光路模擬/Layout/DRC (IPKISS/Python/Virtuoso)</p>", "<p><b>M2:</b> 光路模擬／佈局／DRC（IPKISS／Python／KLayout）</p><p><b>目的：</b>設計一顆矽光子晶片，只改變 14 個相位設定，即可實現任意一種 4 輸入邏輯函數（共 65,536 種），也就是 4 輸入查找表（LUT4）。</p><p><b>範圍：</b>晶片上有 EC（邊緣耦合器）、波導、MMI、MZI、TiN heater、Ti/AL 金屬與 PAD。雷射、資料調變器、heater 驅動、PD（光偵測器）、TIA（轉阻放大器）、比較器與 AND 都在片外。本頁完成到設計資料與檢查，不含實體晶片量測。</p><p><b>輸入編碼：</b>本頁全部採用強度編碼 OOK（On-Off Keying）：有光＝1、無光＝0。二相位編碼（E+／E−）的相位與數字不同，不可互換。</p><p><b>閱讀順序：</b>本頁分為 M1（邏輯設計）與 M2（晶片設計）兩個模組，每個模組再分為數步。例如「M2 s5 ③」指 M2 第 5 步的第 ③ 小節。每步開頭列出前一步交付、本步目的與本步交付。收合的小節可點選標題展開。</p>")
    s = s.replace("以七顆 MZI 組成 B7", "以七顆 MZI 組成 LUT4 macro")
    s = s.replace("4-bit 輸入的 B7", "4 輸入的 LUT4 macro")
    s = s.replace("與 B7 的 o2／o4 埠位分開命名", "與 macro 的 o2／o3／o4 埠位分開命名")
    s = s.replace("B7 相位設定的求解與驗證見後續章節", "macro 相位設定的求解與驗證見後續章節")
    s = s.replace("B7", "LUT4 macro")
    s = s.replace("已依 review 補充英文名詞", "基礎觀念")
    s = re.sub(r"在\s*LUT_Codex 根目錄（啟動器為 <code>tools/lab.cmd</code>）開啟 PowerShell，執行：", "在專案根目錄開啟 PowerShell，執行：", s)
    s = re.sub(r"<pre><code>&amp; C:/[^<]*</code></pre>", r"<pre><code>.\\lab design\\m1_logic\\s1_signal\\and2_readout.py</code></pre>", s)
    s = s.replace("../../LUT_Claude/", "../")
    s = re.sub(r'<p class="muted cross-page-link">.*?</p>', "", s, flags=re.S)
    s = re.sub(r'<a href="paper\.html[^"]*">(.*?)</a>', r"\1", s)
    s = s.replace('src="../figures/', 'src="../figures/study/')
    s = s.replace('src="../figures/study/m1/', 'src="../figures/m1/')
    return s


H3 = re.compile(r'<h3(?: id="([^"]*)")?>(.*?)</h3>', re.S)


def collapse(html_):
    """比照 M1 s1：每一步只保留第一個小節（h3）展開，其餘小節改成預設收合的 details（summary 沿用原 id）。"""
    out, pos = [], 0
    for m in re.finditer(r'<section class="step">(.*?)</section>', html_, re.S):
        body = m.group(1)
        hs = list(H3.finditer(body))
        if len(hs) < 2:
            continue
        new = body[:hs[1].start()]
        for k, h in enumerate(hs[1:], 1):
            end = hs[k + 1].start() if k + 1 < len(hs) else len(body)
            sid = f' id="{h.group(1)}"' if h.group(1) else ""
            new += f'<details><summary{sid} class="section-toggle">{h.group(2)}</summary>{body[h.end():end]}</details>' + chr(10)
        out.append(html_[pos:m.start(1)] + new)
        pos = m.end(1)
    out.append(html_[pos:])
    return "".join(out)


OPEN_JS = """<script>
// 連到收合區內的錨點時，先展開所有上層 details 再捲動
function openTo(id){var e=document.getElementById(id);if(!e)return;var d=e.closest('details');while(d){d.open=true;d=d.parentElement.closest('details');}
if(e.tagName==='SUMMARY'&&e.parentElement.tagName==='DETAILS')e.parentElement.open=true;e.scrollIntoView();}
window.addEventListener('hashchange',function(){openTo(decodeURIComponent(location.hash.slice(1)));});
window.addEventListener('load',function(){if(location.hash)openTo(decodeURIComponent(location.hash.slice(1)));});
</script>"""


BRIDGES = {
    "m1-s1": ["光訊號編碼：用光場振幅表示 0／1，分清光場與功率。",
              "光場混合與判讀：相位決定相加或抵消，功率再轉成邏輯值。",
              "可程式化邏輯：資料不變，只改相位就換邏輯功能。",
              "加入參考光 R：讓 NAND2 在 00 時輸出 1。"],
    "m1-s2": ["單顆 MZI：固定門檻下只能做部分二輸入邏輯。",
              "二顆 MZI＋R：16 種二輸入邏輯都能實現。",
              "Model-7a：7 顆 MZI、5 條波導、4 層。",
              "雙差值判讀：兩個比較器接 AND，任意 4 輸入真值表都可實現。"],
    "m1-s3": ["單顆 MZI：用 2×2 傳輸矩陣描述 θ、φ 的作用。",
              "沿路徑求 U：同一輸入到同一輸出的各路徑光場相加。",
              "逐層光場：理想無損時總功率守恆。",
              "判讀量是二次式：兩個差值接 AND 才能做 XOR4。",
              "Python 小實作：路徑和與整體矩陣一致。"],
    "m2-s1": ["PIC 與外部設備的邊界：晶片只做光場混合。",
              "光學埠：5 入 5 出；o2、o4、o3 判讀。",
              "相位通道：14 個 heater 對應 14 個訊號 PAD。",
              "規格與容許量：R、相位、TIA 增益的容許範圍。",
              "系統層級：TIA 三路偏差、波長與溫度、消光比、光功率，以及輸入相位穩定的限制。"],
    "m2-s2": ["完整流程：七個階段與各自的產物。",
              "電路模擬：換成 PDK MMI，112 組判讀（7 個函數 × 16 組輸入）與 M1 相同。",
              "故障注入：兩種常見的接線錯誤都能檢出。",
              "損耗敏感度：損耗改變時相位要重新求解。"],
    "m2-s3": ["從接線表到幾何：同一支程式依接線表放置 MZI。",
              "實際佈局：單顆 MZI、heater 與接點的尺寸。",
              "讀回 GDS 核對：位置、heater 編號、埠位與核心 DRC。"],
    "m2-s4": ["看全圖：光路連通，沒有短路、斷路；埠數與埠序正確。",
              "看接點：每段波導都接到 MMI 埠或晶片埠。",
              "看 S 彎：曲率半徑高於下限。",
              "分層看金屬：金屬不蓋波導，與其他波導、heater 保持距離。",
              "用資料核對：由佈局重算 U 與 112 組判讀，並以故障注入確認抓得到錯。",
              "列待修項目：固定相位差、埠距、熱串擾，交給後續步驟。"],
    "m2-s5": ["全圖：西緣輸入、東緣輸出，PAD 在上下緣最外圍。",
              "EC 與扇出：埠距拉開到光纖間距，輸入等長。",
              "PAD 與繞線：單層 Ti/AL 不交叉，相鄰 heater 共用 GND。",
              "電流密度：依 heater 電阻的假設值估算。"],
    "m2-s6": ["DRC：幾何符合平台規則。",
              "LVS（佈局與原理圖比對）：每個 heater 接到自己的 PAD 與 GND。",
              "光學連通：每個 EC 接到對的核心埠。",
              "故障注入：檢查程式能檢出已知錯誤。"],
    "m2-s7": ["最終佈局：核心、EC 與 PAD 組成完整晶片。",
              "檢查總表：每項通過都寫明檢查範圍。",
              "交付包：介面表、README 與 SHA-256 清單。",
              "工具對照：Virtuoso 顯示、Calibre DRC 檢查同一份 GDS。",
              "送件注意：由 Virtuoso 匯出時指定 maxVertices 8191。"],
}


FLOW = {
    "m1-s1": ["無。本步為起點，讀者需具備 AND／OR／XOR 真值表與複數運算的基礎。",
              "說明光如何表示 0／1，以及兩路光混合後如何讀成邏輯值。",
              "光場與功率的區別、門檻判讀、參考光 R 的用途。"],
    "m1-s2": ["單顆 MZI 的概念與參考光 R。",
              "確認單顆、二顆 MZI 能實現哪些邏輯，並決定實現任意 4 輸入真值表所需的架構。",
              "Model-7a 的接線、雙差值判讀與 14 個相位（θ、φ）的角色。"],
    "m1-s3": ["Model-7a 的接線與判讀規則。",
              "代入資料後，逐步算出 o2、o4、o3 的光場、功率與邏輯值。",
              "v → o＝Uv → 兩個功率差 → 0／1 的完整計算；主線接續 M2。"],
    "m2-s1": ["M1 定案的 Model-7a、OOK 編碼、7 個範例函數的相位與判讀規則。M2 要把它們做成可交付的晶片設計資料。",
              "定義哪些功能在晶片上、哪些在片外，固定光學埠位與 14 個相位通道，並計算片外設備的精度要求。",
              "一份規格與接線表（lut4_netlist.json，記錄每顆 MZI 接哪兩條波導），模擬與佈局都依此進行。"],
    "m2-s2": ["M2 s1 的接線表、相位設定與規格。",
              "換成 PDK 的 MMI 模型後，確認 112 組判讀（7 個範例函數 × 16 組輸入）仍然正確，並確認接線錯誤能被檢出。",
              "已驗證的電路與相位；佈局依同一份接線表繪製。"],
    "m2-s3": ["通過模擬的接線表與規格。",
              "把電路連接轉成實體幾何：7 顆 MZI、14 個 heater 與 10 個光學埠。",
              "核心佈局 l4_core.gds 與座標資料 layout_info.json。"],
    "m2-s4": ["核心佈局 l4_core.gds。",
              "只讀 GDS，確認佈局的光路與接線表一致。",
              "審查過的核心佈局，以及待處理項目 P1–P3。"],
    "m2-s5": ["審查過的核心佈局。",
              "決定光如何進出晶片，以及 14 個 heater 如何以單層 Ti/AL 繞線到 PAD。",
              "整顆晶片佈局 chip.gds 與對照資料 chip_info.json。"],
    "m2-s6": ["整顆晶片佈局 chip.gds。",
              "確認幾何符合平台規則（DRC）、電氣接線與原理圖一致（LVS）、光學埠接線正確，並確認檢查本身能檢出錯誤。",
              "通過檢查的 GDS 與檢查紀錄。"],
    "m2-s7": ["通過檢查的 GDS 與各步紀錄。",
              "整理交付包，使收件者僅憑包內檔案即可得知晶片的接法、設定方式與驗證範圍。",
              "交付包。本頁到此結束；量測校正等實體驗證不在本頁範圍。"],
}


def bridges(html_):
    """每一步開頭的框統一成「本步的 N 個重點」，每項一句（數字與細節留在內文）。"""
    for sid, items in BRIDGES.items():
        i = html_.find(f'<h2 id="{sid}"')
        a = html_.find('<div class="bridge"', i)
        b = html_.find("</div>", a) + len("</div>")
        lis = "".join(f"<li><b>{t.split('：', 1)[0]}：</b>{t.split('：', 1)[1]}</li>" for t in items)
        fp, fq, fn = FLOW[sid]
        head = f'<p><b>前一步交付：</b>{fp}</p><p><b>本步目的：</b>{fq}</p><p><b>本步交付：</b>{fn}</p>'
        extra = "（只讀 GDS）" if sid == "m2-s4" else ""
        html_ = html_[:a] + f'<div class="bridge">{head}<b>本步的 {len(items)} 個重點</b>{extra}<ol>{lis}</ol></div>' + html_[b:]
    return html_


def main():
    head = src("head.html")
    head = re.sub(r"<title>.*?</title>", "<title>Programmable Silicon Photonic 4-input LUT Design</title>", head)
    head = head.replace("</style>", ".num{font-variant-numeric:tabular-nums}" + NAV_CSS + "</style>")
    segs = [("kept", m1s1_fixed()), ("mixed", m1s2()), ("mixed", m1s3()), ("new", m2s1()), ("new", m2s2()), ("new", m2s3()),
            ("new", m2s4()), ("new", m2s5()), ("new", m2s6()), ("new", m2s7()), ("new", appendix())]
    counters, assigned, body = {"圖": 0, "表": 0}, {}, []
    for kind, seg in segs:
        seg = seg.replace('src="../figures/two_mzi', 'src="../figures/study/two_mzi').replace('src="../figures/mzi_', 'src="../figures/study/mzi_') \
                 .replace('src="../figures/mmi_', 'src="../figures/study/mmi_').replace('src="../figures/phase_arrows', 'src="../figures/study/phase_arrows')
        if kind in ("kept", "mixed"):
            # 保留段落：只對尚未改成代號的編號重新編號（新段落用 @@ 代號）
            parts = re.split(r"(@@[FT]R?:[^@]+@@)", seg)
            # 依原順序處理：先保留段落的原始編號，再新段落
            if kind == "kept":
                seg = renumber_kept(seg, counters)
            else:
                i = seg.find("@@")
                seg = renumber_kept(seg[:i], counters) + renumber_new(seg[i:], counters, assigned)
        else:
            seg = renumber_new(seg, counters, assigned)
        body.append(seg)
    html_ = "\n".join(body)
    for (tok, key), n in assigned.items():
        html_ = html_.replace(f"@@{tok}R:{key}@@", str(n))
    left = re.findall(r"@@[^@]+@@", html_)
    assert not left, left[:5]
    html_ = re.sub(r'<span class="status">[^<]*</span>', "", html_)                  # 工作狀態標籤不給讀者看
    html_ = collapse(bridges(html_)).replace("歸一化", "正規化").replace("抓到", "檢出").replace("抓得到", "檢得出").replace("附錄 E-5", '<a href="#appx-readout-5">附錄 E-5</a>')
    foot = OPEN_JS + '<footer>Programmable Silicon Photonic 4-input LUT Design｜靜態教材，圖示內嵌，無外部程式庫依賴。</footer></main></div></body></html>'
    out = head + '<div class="wrap">' + nav(html_) + "<main>\n" + html_ + NAV_JS + foot
    bad = [w for w in ("C:/", "C:\\", "D:/", "D:\\", "Lab0", "Codex", "Claude", "Grok", "版圖", "逃線", "信號", "軟件", "默認", "EDA_Server", "MZM", "FPGA", "本次", "WSL", "使用者")
           if w in out]
    al = re.findall(r"(?<![A-Za-z])Al(?![A-Za-z])", re.sub(r"<[^>]+>", "", out))
    print("禁字：", bad, "Al：", len(al))
    OUTF.write_text(out, encoding="utf-8")
    print("寫出", OUTF.relative_to(paths.ROOT), len(out), "bytes；圖", counters["圖"], "表", counters["表"])


if __name__ == "__main__":
    main()
