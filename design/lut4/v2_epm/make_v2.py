r"""LUT4v2：由 report/LUT4_Study.html 複製出 report/LUT4v2_study.html，插入「v2 節」並在 OOK 數字處加註。
輸入：out/epm.json、out/noref.json、out/sample.json（先跑 epm_eval.py、noref_eval.py、sample_eval.py）。
執行：.\lab design\lut4\v2_epm\make_v2.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC, DST = ROOT / "report" / "LUT4_Study.html", ROOT / "report" / "LUT4v2_study.html"
J = lambda n: json.loads((HERE / "out" / n).read_text(encoding="utf-8"))
d, nr, sp = J("epm.json"), J("noref.json")["summary"], J("sample.json")["summary"]
fu = J("full.json")["summary"] if (HERE / "out" / "full.json").exists() else None
if fu:
    FULL_B = f"16 列都能各自設定，全部 65536 張都做得到（非常數 {fu['ok']}／{fu['n']} 張逐張驗證，另 2 張為常數）"
    FULL_L = (f"<li><b>逐張驗證：</b>E±＋R＝3 對全部非常數真值表逐張合成（24 個起點、找不到再以 100 個起點重試；裕量達 {fu['stop']:.2f} P<sub>u</sub> 即停，所以是下限），"
              f"<b>{fu['ok']}／{fu['n']} 張做得到</b>，其中 {fu['ge_stop']} 張裕量 ≥ {fu['stop']:.2f} P<sub>u</sub>，最小 {fu['min_margin']:.3f} P<sub>u</sub>（{fu['worst']}）"
              + (f"；找不到解的：{'、'.join(fu['fail'])}" if fu["fail"] else "")
              + f"。這個最小值是搜尋不足造成的：{fu['worst']} 不設停止門檻、改用 400 個起點重算，裕量提高到 0.29 P<sub>u</sub>（16 組中有 7 組收斂到同一值），"
              "所以全部真值表真正的最差裕量要再以更多起點搜尋才能確定。</li>")
    FULL_T = "已逐張驗證（見 ⑤）；裕量為下限，困難的真值表可再以更多起點求完整裕量"
else:
    FULL_B = f"16 列都能各自設定，抽樣 {sp['n']} 張全部做得到"
    FULL_L = ""
    FULL_T = "E±＋R＝3 目前只做抽樣，逐張驗證約需 45～60 分鐘（6 個 worker）"
t = SRC.read_text(encoding="utf-8")
FN = ["AND2", "OR2", "XOR2", "NAND2", "AND4", "XOR4", "MUX"]
HEX = {"AND2": "0x8888", "OR2": "0xEEEE", "XOR2": "0x6666", "NAND2": "0x7777", "AND4": "0x8000", "XOR4": "0x6996", "MUX": "0xCACA"}


def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:60], t.count(a))
    t = t.replace(a, b)


def m(c):
    return f"{c['margin']:.3f}" if c["margin"] > 0 else "✗"


def pc(c, k):
    return f"{100 * c[k]:.1f}%" if k in c else "—"


rows1, rows2, ratios, gains = [], [], [], []
for f in FN:
    r = d[f]
    o, e3, e1, e0 = r["ook_R3"], r["epm_R3"], r["epm_R1"], r["epm_R0"]
    gains.append(e3["margin"] / o["margin"]); ratios.append((e3["margin"] / 13) / (o["margin"] / 11))
    rows1.append(f"<tr><td>{f}（{HEX[f]}）</td><td>{m(o)}</td><td><b>{m(e3)}</b></td><td>{m(e1)}</td><td>{m(e0)}</td>"
                 f"<td>{'是' if r['comp_sym'] else '否'}</td><td>×{ratios[-1]:.1f}</td></tr>")
    rows2.append(f"<tr><td>{f}</td><td>{pc(o, 'phase_mc_0.05')}／{pc(o, 'phase_mc_0.1')}</td>"
                 f"<td>{pc(e3, 'phase_mc_0.05')}／{pc(e3, 'phase_mc_0.1')}</td><td>{pc(e0, 'phase_mc_0.05')}／{pc(e0, 'phase_mc_0.1')}</td></tr>")
G = f"{min(gains):.1f}～{max(gains):.1f}"
RT = f"{min(ratios):.1f}～{max(ratios):.1f}"
x4 = d["XOR4"]

SEC = f'''<h2 id="v2-epm">v2　E+／E− 二相位輸入：讀出方式與輸出架構</h2><span class="status">v2 新增</span>

<section class="step"><div class="bridge"><b>本節的 5 個重點</b><ol><li><b>二相位編碼：</b>位元 0 送 +E、1 送 −E，每路功率恆為 P<sub>u</sub>，資料只在相位。</li><li><b>差異在讀出方式：</b>OOK 的功率本身就是位元；E± 的單路功率不變，只能讓光場干涉，讀出光場之間的相對相位。</li><li><b>接收端不變：</b>同樣讀 o2、o3、o4，兩個差動對 P(o2)−P(o4)＞0、P(o3)−P(o4)＜0，接 AND。</li><li><b>不用參考光：</b>互補的兩列（例如 0000 與 1111）輸出必定相同，只有 8 個位元可設定；這 256 張真值表在 Model-7a 上全部做得到。</li><li><b>加參考光 R（＝+E）：</b>{FULL_B}；範例函數的裕量為 OOK 的 {G} 倍。</li></ol>
<p class="note">本頁由原版 LUT4 課程複製而來。光路（Model-7a、7 顆熱調 MZI、5 入 5 出）、接收端、佈局、PAD 與交付內容都不變；改變的是輸入編碼與相位設定。後面各節仍以 0／1 強度輸入（OOK）計算的數字，會在該處註明，v2 的對應數字以本節為準。</p></div>

<h3 id="v2-enc">① 兩種輸入編碼</h3>
<table class="logic-compact"><caption>表 v2-1｜OOK 與 E+／E− 輸入（每路資料的光場振幅以 1 正規化，P<sub>u</sub>＝振幅 1 的功率）</caption>
<tr><th>項目</th><th>OOK（原版）</th><th>E+／E−（v2）</th></tr>
<tr><td>位元 0／1 的光場</td><td>0／1</td><td>+1／−1（相位 0／π）</td></tr>
<tr><td>每路資料功率</td><td>0 或 P<sub>u</sub>，平均 0.5 P<sub>u</sub></td><td>恆為 P<sub>u</sub></td></tr>
<tr><td>輸入 0000</td><td>4 路資料全暗，只剩 R</td><td>4 路都亮，相位都是 0</td></tr>
<tr><td>參考光 R</td><td>振幅 3、不調變</td><td>振幅 3、不調變，與位元 0 同相（＝+E）</td></tr>
<tr><td>4 路資料＋R 的總入射功率</td><td>隨資料變化（9～13 P<sub>u</sub>）</td><td>固定 13 P<sub>u</sub></td></tr>
<tr><td>發射端（macro 外）</td><td>強度調變</td><td>相位調變（0／π）；macro 內仍只有熱調 MZI</td></tr>
</table>
<p>以 s<sub>k</sub>＝1−2x<sub>k</sub> 表示第 k 路的光場符號（x<sub>k</sub>＝0 時 s<sub>k</sub>＝+1）。16 列（0000～1111）的真值表定義不變，只是每列送進晶片的光場不同。</p>
<p><b>R 是 +E 還是 −E？</b>R 不調變，它的相位只是定義。把 R 反相，等於把 4 路資料全部反相（0 與 1 互換），相位重新合成後一樣做得到；本節固定取 R 與位元 0 同相（＝+E），也就是發射端相位調變器不加電壓時的光。重要的是 R 與資料光的相對相位要固定，並以 heater 校準。</p>

<h3 id="v2-read">② 讀出方式的差異</h3>
<table class="logic-compact"><caption>表 v2-2｜同一種讀出，兩種輸入讀到什麼（單位 P<sub>u</sub>）</caption>
<tr><th>讀出</th><th>OOK（x∈{{0, 1}}）</th><th>E±（s∈{{+1, −1}}）</th></tr>
<tr><td>單路光直接接 PD</td><td>P＝x：直接讀到位元</td><td>P＝1：讀不到資料</td></tr>
<tr><td>兩路 50:50 混合，一個輸出埠</td><td>(x<sub>1</sub>＋x<sub>2</sub>)／2 ± x<sub>1</sub>x<sub>2</sub>：有單一位元也有乘積</td><td>1 ± s<sub>1</sub>s<sub>2</sub>：只剩乘積</td></tr>
<tr><td>兩個輸出埠相減（差動對）</td><td>2x<sub>1</sub>x<sub>2</sub>：只有 11 不為 0</td><td>2s<sub>1</sub>s<sub>2</sub>＝±2：正負號就是 XNOR，擺幅為 OOK 的 2 倍</td></tr>
<tr><td>與參考光 R 干涉</td><td>2xR：位元本身（不必干涉也讀得到）</td><td>2sR：位元本身（唯一能讀出絕對位元的方法）</td></tr>
</table>
<p>一般情況下，第 j 個輸出的光場與功率為：</p>
<div class="formula">o<sub>j</sub> ＝ Σ<sub>k</sub> u<sub>jk</sub> s<sub>k</sub> ＋ u<sub>jR</sub> R<br>P(o<sub>j</sub>) ＝ [Σ<sub>k</sub>|u<sub>jk</sub>|² ＋ |u<sub>jR</sub>R|²] ＋ 2Σ<sub>k</sub> Re(u<sub>jk</sub>u<sub>jR</sub>*R)·s<sub>k</sub> ＋ 2Σ<sub>k&lt;l</sub> Re(u<sub>jk</sub>u<sub>jl</sub>*)·s<sub>k</sub>s<sub>l</sub></div>
<ul>
<li><b>OOK：</b>因為 x<sub>k</sub>²＝x<sub>k</sub>，資料光自己就產生單一位元的項；缺的是常數項（0000 全暗），所以需要 R。</li>
<li><b>E±：</b>因為 s<sub>k</sub>²＝1，常數項固定、不帶資料；資料光彼此干涉只產生 s<sub>k</sub>s<sub>l</sub>，也就是「兩路位元相同或不同」。單一位元的項只能由資料光與 R 干涉產生。</li>
<li><b>一個差動對讀到的是兩個光場的乘積：</b>兩路光場 F、G 混合後兩埠相減得 2Re(F·G*)。F、G 都是資料光的加權和時，結果的正負號就是兩個線性門檻的乘積，資料光彼此當參考；判讀門檻固定為 0，與雷射功率無關。</li>
</ul>

<h3 id="v2-rx">③ 接收端：兩個差動對</h3>
<div class="formula">D<sub>1</sub> ＝ P(o2) − P(o4) ＞ 0，　D<sub>2</sub> ＝ P(o3) − P(o4) ＜ 0，　y ＝ [D<sub>1</sub> ＞ 0] AND [D<sub>2</sub> ＜ 0]</div>
<p>與原版相同：y＝1 表示 P(o4) 落在 P(o3) 與 P(o2) 之間（原版寫成 D<sub>b</sub>＝P(o4)−P(o3)＞0，是同一個條件）。o4 是兩個差動對的共同端，所以三個輸出各接一顆 PD 與 TIA，再於電路端相減；兩個比較器門檻都是 0，第二個極性相反，最後接固定 AND。接收端不隨函數改變。</p>

<h3 id="v2-noref">④ 不用參考光：互補的兩列輸出相同</h3>
<p>R＝0 時，把 4 路輸入全部反相（s→−s），每個輸出光場只差一個負號，所有 PD 的功率完全不變，D<sub>1</sub>、D<sub>2</sub> 與 y 也不變。所以每一列與它的互補列（0000／1111、0001／1110、…，共 8 對）輸出必定相同，這與接收端怎麼接無關。16 列中只有 8 個位元可以設定，共 2<sup>8</sup>＝256 張真值表；另一個看法是：輸出只取決於 x1⊕x2、x1⊕x3、x1⊕x4 三個相對關係。</p>
<p>對這 256 張中的 {nr['n']} 張非常數真值表逐一合成（R＝0、每張 24 個起點、裕量達 0.05 P<sub>u</sub> 即停）：<b>{nr['ok']}／{nr['n']} 張全部做得到</b>，最小裕量 {nr['min_margin']:.2f} P<sub>u</sub>（下限）。XOR4 屬於這一類，完整搜尋的裕量 {x4['epm_R0']['margin']:.3f} P<sub>u</sub>，比原版 OOK＋R＝3 的 {x4['ook_R3']['margin']:.3f} P<sub>u</sub> 大，而且對輸入相位誤差更穩健（表 v2-4）。</p>
<p>需要全部 16 列時，就要一個絕對相位基準：參考光 R，或由指令把某一路輸入固定成 +E（此時其餘 3 路可做任意 LUT3）。</p>

<h3 id="v2-ref">⑤ 加參考光 R：16 列都能各自設定</h3>
<p>同一個 Model-7a（0.9 dB／MZI），每個範例函數以 24 個起點重新合成 14 個相位。OOK R＝3 是原版設定；E± 另試 R＝1 與 R＝0。</p>
<table class="logic-compact"><caption>表 v2-3｜最小裕量（P<sub>u</sub>；✗＝找不到 16 列全對的相位）</caption>
<tr><th>函數</th><th>OOK R＝3</th><th>E± R＝3</th><th>E± R＝1</th><th>E± R＝0</th><th>互補兩列輸出相同</th><th>同總功率比較（E± R3／OOK R3）</th></tr>
{chr(10).join(rows1)}
</table>
<p class="note">最後一欄把裕量除以總入射功率再相比（E± 固定 13 P<sub>u</sub>；OOK 取平均值 11 P<sub>u</sub>：4×0.5＋9），避免 E± 因為光一直亮而佔便宜。</p>
<table class="logic-compact"><caption>表 v2-4｜輸入相對相位誤差（5 路各加常態誤差，400 次）下 16 列全對的比例，σ＝0.05／0.1 rad</caption>
<tr><th>函數</th><th>OOK R＝3</th><th>E± R＝3</th><th>E± R＝0</th></tr>
{chr(10).join(rows2)}
</table>
<ul>
<li><b>R＝3 時全部可行，裕量提高 {G} 倍：</b>±E 的擺幅是 OOK 的 2 倍，乘積項的係數因此變大；以總入射功率公平比較仍有 {RT} 倍。</li>
<li><b>抽樣檢查：</b>E±＋R＝3 隨機抽 {sp['n'] - 2} 張，加上 OOK 時最難的 0x9667 與 XOR4，共 {sp['n']} 張，<b>{sp['ok']}／{sp['n']} 張全部做得到</b>，每張裕量至少 {sp['min_margin']:.2f} P<sub>u</sub>（裕量達 0.05 P<sub>u</sub> 即停，為下限）；0x9667 為 {sp['w9667']:.2f} P<sub>u</sub>（OOK 為 0.053 P<sub>u</sub>）。{'' if fu else '尚未逐張驗證全部真值表。'}</li>
{FULL_L}
<li><b>R 不宜調小：</b>R＝1 時 XOR4 找不到解，其餘裕量也比 R＝3 小。弱參考光無法被導到不判讀的輸出埠，反而干擾判讀；不需要 R 的函數（XOR 類）在 R＝0 時反而做得到。R 是固定的，不能隨函數改變，所以 v2 用 R＝3。</li>
<li><b>相位容許量與 OOK 相當：</b>E± 把資料放在相位上，但輸入相位誤差下的全對比例與 OOK 相近；五路輸入的相干與相位穩定仍是最主要的系統限制。</li>
</ul>

<h3 id="v2-cmp">⑥ 與加法器、ALU 的二相位設計一致</h3>
<table class="logic-compact"><caption>表 v2-5｜同一原則在加法器／ALU 的二相位設計中的表現</caption>
<tr><th>輸出</th><th>全部輸入反相後</th><th>讀出方式</th><th>需要參考光</th></tr>
<tr><td>XOR（a<sub>k</sub>⊕b<sub>k</sub>）</td><td>不變</td><td>a<sub>k</sub>、b<sub>k</sub> 50:50 混合，差埠減和埠＝−2Re(A·B*)</td><td>不需要</td></tr>
<tr><td>兩個進位的 XOR（例如溢位旗標）</td><td>不變</td><td>兩組進位的合波光直接干涉</td><td>不需要</td></tr>
<tr><td>進位、和位元</td><td>反相</td><td>合波光與參考光零差，讀正負號</td><td>需要</td></tr>
<tr><td>AND、OR 等逐位邏輯</td><td>改變</td><td>與參考光干涉</td><td>需要</td></tr>
</table>
<p>二相位的進位門檻本來就落在 0：以 ±1 表示時加權和必為奇數，正負號就是進位，不需要額外的常數項；但要讀出正負號，仍要有參考光。加法器在二相位輸入下的裕量約為強度輸入的 2.4 倍，與本節 LUT4 的結果一致。</p>

<h3 id="v2-out">⑦ 輸出架構評估</h3>
<table class="logic-compact"><caption>表 v2-6｜E± 輸入下的輸出架構選項</caption>
<tr><th>架構</th><th>做法</th><th>16 列能否各自設定</th><th>評估</th></tr>
<tr><td>A　兩個差動對＋AND（原版接收端）</td><td>o2−o4＞0、o3−o4＜0，接 AND</td><td>有 R：能；無 R：只有互補對（8 位元）</td><td><b>建議採用。</b>接收端完全不變；總功率固定，三路 TIA 的工作點也固定。</td></tr>
<tr><td>B　兩組獨立平衡 PD</td><td>o2／o4、o3／o4 各接一組平衡偵測器</td><td>同 A</td><td>o4 要先分光成兩半（損失 3 dB），除非 TIA 增益匹配不夠，否則不必改。</td></tr>
<tr><td>C　單一差動對＋1 個比較器</td><td>只讀一組功率差</td><td>不能（只有一個二次門檻）</td><td>零件最少，但 XOR4 等函數做不到。</td></tr>
<tr><td>D　只用零差判讀</td><td>每個輸出都與 R 零差</td><td>不能（判讀量變成一次式）</td><td>只能做線性門檻（AND、OR、多數決），做不到 XOR；適合加法器進位，不適合 LUT4。</td></tr>
<tr><td>E　輸出也是 E±（光直接串級）</td><td>輸出光場的正負號＝f(x)，振幅固定</td><td>不能</td><td>被動光路的輸出光場是 s 的一次式；要得到 E± 輸出必須判讀後再調變（O-E-O），本設計不採用。</td></tr>
</table>
<p><b>結論：</b>v2 改的是發射端與讀出的意義，不是接收端硬體。輸出沿用兩個差動對＋AND，輸出是電的 0／1；要做完整 LUT4 時保留 R＝3（+E），只做互補對型的函數時可以不用 R。</p>

<h3 id="v2-todo">⑧ v2 還要重做或驗證的項目</h3>
<table class="logic-compact"><caption>表 v2-7｜沿用與重做</caption>
<tr><th>項目</th><th>v2 處理</th></tr>
<tr><td>Model-7a 光路、佈局、PAD、DRC、交付</td><td>沿用，不必重做（光路與埠位相同）</td></tr>
<tr><td>相位設定（M1 s2 表 6、附錄 B）</td><td>重新合成：同一函數在 E± 下的 14 個相位與 OOK 不同</td></tr>
<tr><td>全部真值表</td><td>{FULL_T}</td></tr>
<tr><td>電路模擬（M2 s2，112 組判讀）</td><td>以 E± 輸入與新相位重跑</td></tr>
<tr><td>容許量與光功率預算（M2 s1 表 17～22）</td><td>以 E± 重算；裕量變大，預算應會放寬</td></tr>
<tr><td>時序窗</td><td>新增檢查：E± 由 +E 轉到 −E 時，相位調變器會經過 ±iE、推挽強度調變器會經過零光場，暫態與 OOK 不同</td></tr>
<tr><td>發射端</td><td>5 路需相干且 0／π 準確；相位調變器在 macro 外</td></tr>
</table>
<p class="note">程式：<code>design/lut4/v2_epm/</code> 的 epm_eval.py（範例函數）、noref_eval.py（不用參考光）、sample_eval.py（抽樣）、full_eval.py（逐張驗證）、make_v2.py（產生本頁）；結果在同目錄 out/。</p>
</section>

'''

rep("<title>Programmable Silicon Photonic 4-input LUT Design</title>", "<title>Programmable Silicon Photonic 4-input LUT Design v2</title>")
rep('<h1>Programmable Silicon Photonic 4-input LUT Design</h1><p class="sub">可程式化矽光子 4 輸入查找表（LUT4）設計｜Model-7a：7 顆熱調 MZI＋固定雙差值接收端</p>',
    '<h1>Programmable Silicon Photonic 4-input LUT Design v2</h1><p class="sub">可程式化矽光子 4 輸入查找表（LUT4）設計 v2｜E+／E− 二相位光輸入｜Model-7a：7 顆熱調 MZI＋固定雙差值接收端</p>')
rep('<hr><a class="nstep" href="#m1-s1">',
    '<hr><a class="nstep" href="#v2-epm">v2　E+／E− 讀出與輸出架構</a><div class="nsub"><a href="#v2-enc">① 兩種輸入編碼</a><a href="#v2-read">② 讀出方式的差異</a>'
    '<a href="#v2-rx">③ 接收端：兩個差動對</a><a href="#v2-noref">④ 不用參考光</a><a href="#v2-ref">⑤ 加參考光 R</a><a href="#v2-cmp">⑥ 與加法器、ALU 一致</a>'
    '<a href="#v2-out">⑦ 輸出架構評估</a><a href="#v2-todo">⑧ 重做項目</a></div><a class="nstep" href="#m1-s1">')
rep('<p><b>M2:</b> 光路模擬／佈局／DRC（IPKISS／Python／KLayout）</p></div>',
    '<p><b>M2:</b> 光路模擬／佈局／DRC（IPKISS／Python／KLayout）</p><p><b>v2:</b> 輸入改為 E+／E− 二相位光，說明讀出方式的差異並評估輸出架構（見 <a href="#v2-epm">v2 節</a>）</p></div>')
rep('<h2 id="m1-s1">', SEC + '<h2 id="m1-s1">')
rep("資料位元以光場振幅 0／1 表示，R＝3 為參考光振幅（功率 9 Pᵤ）。五路輸入來自同一顆雷射，相對相位固定。",
    "資料位元以光場振幅 0／1 表示，R＝3 為參考光振幅（功率 9 Pᵤ）。五路輸入來自同一顆雷射，相對相位固定。<b>v2：</b>位元 0／1 改為光場 +1／−1（E+／E−），R＝3 與位元 0 同相，見 <a href=\"#v2-enc\">v2 節 ①</a>。")
NOTE = '<p class="note"><b>v2 註：</b>本表數字以 0／1 強度輸入（OOK）計算；E+／E− 輸入的對應結果見 <a href="#v2-ref">v2 節 ⑤</a>，相位需重新合成。</p>'
rep('<table class="logic-compact"><caption>表 6｜', NOTE + '<table class="logic-compact"><caption>表 6｜')
rep('<table class="logic-compact"><caption>表 22｜', NOTE.replace("相位需重新合成", "光功率預算待以 E± 重算") + '<table class="logic-compact"><caption>表 22｜')
rep("｜靜態教材，圖示內嵌，無外部程式庫依賴。</footer>", " v2｜靜態教材，圖示內嵌，無外部程式庫依賴。</footer>")
for w in ("Lab0", "Claude", "Codex", "Grok", ":\\", "信號", "版圖"):
    assert w not in SEC, w
DST.write_text(t, encoding="utf-8")
print("寫出", DST.name, len(t))
