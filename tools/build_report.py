r"""M0 s2：報告組裝程式（入口頁＋分頁）。

用途：把步驟片段 report/src/<mN>/<sN>.html 組成分頁報告，並產生根目錄的讀者入口頁。
  - 入口頁：課程總覽（report/src/index/*.html）、學習路線（PLAN 進度表）、步驟目錄與進度（PLAN 步驟表）、附錄與交付連結。
  - 檢查每個片段：section.step、銜接框、①–⑥ 六節依序齊全。
  - <span class="num" data-json="…json" data-expr="d['a']['b']" data-fmt="{:.3f}">：由 JSON 重算數字並替換。
  - <div class="auto-code" data-files="a.py b.py">：帶入程式（可摺疊）。
  - <div class="auto-history" data-file="…/HISTORY.md">：修改歷史移到附錄 B，步驟內只留連結。
  - 圖片 src="figures/…"（根目錄相對）改寫成各頁的相對路徑。
  - 讀者文件禁字檢查、跨頁連結與錨點檢查。
輸入：PLAN.md、report/src/**、片段引用的 JSON、程式、HISTORY.md、圖。
輸出：LUT_Claude_index.html（入口）、report/m0.html…m3.html、report/appendix.html。有錯誤時不寫檔、結束碼 1（--force 仍寫檔）。
執行：.\lab tools\build_report.py [--force]
"""
import argparse
import ast
import html
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "src"
PAGES = ROOT / "report"
PLAN = ROOT / "PLAN.md"
INDEX_NAME = "LUT_Claude_index.html"          # 入口頁檔名（禁字檢查前先移除，避免自己命中計畫代號）
INDEX = ROOT / INDEX_NAME

TITLE = "光運算邏輯設計實作：從 B7 邏輯運算到一顆完整的 PIC"
SECTIONS = ["① 問題與範例", "② 原理與推導", "③ 動手做",
            "④ 結果與驗收", "⑤ 常見錯誤與自我檢查", "⑥ 程式與實驗條件"]

# 讀者文件禁字。樣式刻意用字元類別寫，讓本程式被帶入報告時不會自己命中。
FORBIDDEN = [
    # 本機路徑：磁碟代號開頭，接單一或兩個反斜線（Python 字串）或斜線（M0 審查 R3）；網址的協定名稱前面是字母，不會命中
    (r"(?<![A-Za-z])[A-Za-z]:(?:\\{1,2}|/)(?!/)[^\s<\"']*", "本機絕對路徑"),
    (r"(?<![\\\w])\\\\[A-Za-z][\w.$-]*\\[\w$]", "網路路徑（UNC）"),
    (r"%[A-Za-z_]+%[\\/]", "使用者環境變數路徑"),
    (r"(?<![\w.])~[\\/]", "使用者家目錄路徑"),
    (r"(?i)(?<![A-Za-z])la[b][0]\d", "計畫代號"),
    (r"(?i)cl[a]ude|co[d]ex|gr[o]k", "工具名稱"),             # 不分大小寫：小寫的資料夾名也算（M0 審查 R2）
    (r"版[圖]", "用「佈局」"),
    (r"逃[線]", "用「繞線」"),
    (r"裕[量]", "用 margin"),
    (r"信[號]", "用「訊號」"),
    (r"軟[件]", "用「軟體」"),
    (r"默[認]", "用「預設」"),
    (r"(?<![A-Za-z])A[l](?![A-Za-z])", "鋁寫 AL"),
    (r"質[量]", "用「品質」"),
    (r"(?<![A-Za-z])h[a]ns(?![A-Za-z])", "使用者帳號"),
]

SAFE_FUNCS = {"abs": abs, "min": min, "max": max, "len": len, "round": round, "sum": sum, "format": format}
STATUS = {"☐": ("未開始", "todo"), "◐": ("進行中", "doing"), "☑": ("完成", "done")}


# ---------- PLAN.md ----------
def table_rows(text, heading):
    """取 PLAN.md 某個 ## 標題下第一個表格的資料列（不含表頭與分隔列）。"""
    m = re.search(rf"^## {re.escape(heading)}[^\n]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    rows = [ln.strip().replace("\\|", "\0").strip("|").split("|")       # \| 是儲存格內的直線（例如 |y2|²）
            for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    return [[c.strip().replace("\0", "|") for c in r] for r in rows[2:]]


def read_plan():
    text = PLAN.read_text(encoding="utf-8")
    ms = {}
    for r in table_rows(text, "進度表"):        # | M0 | 主題 | 步驟數 | 狀態 | 關卡 |
        ms[r[0]] = dict(title=r[1], n=int(r[2]), status=r[3][:1])
    steps = []
    for r in table_rows(text, "步驟表"):        # | 步驟 | 標題 | 問題 | 成果 | 時數 | 對照 | 驗收 | 狀態 |
        mk, sk = r[0].split()
        steps.append(dict(m=mk, s=sk, id=f"{mk.lower()}-{sk}", title=r[1], question=r[2],
                          output=r[3], hours=r[4], status=r[7][:1]))
    symbols = table_rows(text, "符號表")          # | 符號 | 意義 | 單位 |
    terms = {r[0]: r[1].lower().replace(" ", "-") for r in table_rows(text, "名詞首次定義")}   # 名詞 → 'm1-s2'
    return ms, steps, symbols, terms


def check_terms(texts, order, terms, errors):
    """先定義才使用：名詞出現在定義步驟之前的步驟就報錯。
    texts：{步驟 id: 片段 HTML}；order：步驟 id 依課程順序；terms：{名詞: 定義步驟 id}。程式碼區塊不算。"""
    rank = {sid: i for i, sid in enumerate(order)}
    for sid, s in texts.items():
        plain = re.sub(r'<details class="code".*?</details>', "", s, flags=re.S)
        plain = re.sub(r"<(pre|code)[^>]*>.*?</\1>", "", plain, flags=re.S)
        plain = re.sub(r'<div class="auto-(code|history)"[^>]*></div>', "", plain)
        plain = html.unescape(re.sub(r"<[^>]+>", "", plain))
        for term, where in terms.items():
            if rank.get(sid, -1) < rank.get(where, -1):
                hit = (re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", plain) if term.isascii()
                       else re.search(re.escape(term), plain))
                if hit:
                    ctx = plain[max(0, hit.start() - 20): hit.end() + 20].replace("\n", " ")
                    errors.append(f"{sid}：「{term}」要到 {where[:2].upper()} {where[3:]} 才定義，這裡先用了：…{ctx}…")


def symbols_appendix(symbols):
    """附錄 A：由 PLAN 的符號表產生，報告與程式共用同一份定義。"""
    def sub(t):                                   # u_ij、P_u → 下標
        return re.sub(r"(?<=[^\s_])_([A-Za-z0-9]+)", r"<sub>\1</sub>", md_inline(t))
    rows = "".join(f"<tr><td>{sub(r[0])}</td><td>{sub(r[1])}</td><td>{sub(r[2])}</td></tr>" for r in symbols)
    return ('<h2 id="app-a">附錄 A　符號與埠名對照</h2>'
            '<p>全課程共用的符號。同一個符號只代表一件事；教學編號（x1–x4、R、o1–o5）與佈局埠名（in0–in4、out0–out4）的對應也列在這裡。</p>'
            f'<table><tr><th>符號</th><th>意義</th><th>單位</th></tr>{rows}</table>')


# ---------- 片段處理 ----------
def fragments():
    items = []
    for f in SRC.glob("m*/s*.html"):
        mm, ss = re.match(r"m(\d+)$", f.parent.name), re.match(r"s(\d+)$", f.stem)
        if mm and ss:
            items.append((int(mm.group(1)), int(ss.group(1)), f))
    return [f for _, _, f in sorted(items)]


def attrs(tag_text):
    return {k: html.unescape(v) for k, v in re.findall(r'([\w-]+)="([^"]*)"', tag_text)}


def check_format(name, s, errors):
    m = re.search(r'<section class="step"([^>]*)>', s)
    if not m:
        errors.append(f"{name}：缺 <section class=\"step\">")
        return {}
    a = attrs(m.group(1))
    for k in ("id", "data-milestone", "data-step", "data-title"):
        if k not in a:
            errors.append(f"{name}：section 缺屬性 {k}")
    if 'class="bridge"' not in s:
        errors.append(f"{name}：缺銜接框 <div class=\"bridge\">")
    elif 'class="terms"' not in s:
        print(f"警告：{name} 的銜接框沒有「名詞對照」")
    h3 = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h3>(.*?)</h3>", s, re.S)]
    if h3 != SECTIONS:
        errors.append(f"{name}：六節標題或順序不符，實際為 {h3}")
    return a


def fill_numbers(name, s, errors, notes):
    cache = {}

    def rep(m):
        a = attrs(m.group(1))
        old = m.group(2)
        try:
            p = ROOT / a["data-json"]
            if p not in cache:
                cache[p] = json.loads(p.read_text(encoding="utf-8"))
            v = eval(a["data-expr"], {"__builtins__": {}, **SAFE_FUNCS}, {"d": cache[p]})
            new = a.get("data-fmt", "{}").format(v)
            if re.fullmatch(r"[-+]0(\.0+)?", new):
                new = new[1:]
            if re.fullmatch(r"[-+0-9.eEi ]+", new):           # 純數字或複數（0.25-0.75i）：所有負號都用 U+2212
                new = re.sub(r"(?<![eE])-(?=\d)", "−", new)    # 指數的負號（1e-16）維持 ASCII
        except Exception as e:
            errors.append(f"{name}：數字 {a.get('data-expr')} 無法計算（{type(e).__name__}: {e}）")
            return m.group(0)
        if new != old:
            notes.append(f"{name}：{a['data-expr']} 片段寫 {old}，依 JSON 改為 {new}")
        return f'<span class="num">{new}</span>'

    return re.sub(r'<span class="num"([^>]*)>(.*?)</span>', rep, s, flags=re.S)


def code_block(rel_path, errors, name):
    p = ROOT / rel_path
    if not p.exists():
        errors.append(f"{name}：auto-code 找不到 {rel_path}")
        return ""
    text = p.read_text(encoding="utf-8")
    doc = ""
    if p.suffix == ".py":
        try:
            doc = (ast.get_docstring(ast.parse(text)) or "").strip().splitlines()[0]
        except (SyntaxError, IndexError):
            pass
    n = text.count("\n") + 1
    return (f'<details class="code"><summary><code>{html.escape(rel_path)}</code>'
            f'<span class="meta">{n} 行・{len(text.encode("utf-8")) / 1024:.1f} KB</span>'
            f'<span class="doc">{html.escape(doc)}</span></summary>'
            f'<pre><code>{html.escape(text)}</code></pre></details>')


def fill_code(name, s, errors):
    def rep(m):
        files = attrs(m.group(1)).get("data-files", "").split()
        if not files:
            errors.append(f"{name}：auto-code 沒有列檔案")
        return '<div class="auto-code">' + "".join(code_block(f, errors, name) for f in files) + "</div>"
    return re.sub(r'<div class="auto-code"([^>]*)></div>', rep, s)


def md_inline(t):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(t.strip()))


def fill_history(name, s, errors, store, a):
    def rep(m):
        rel_path = attrs(m.group(1)).get("data-file", "")
        p = ROOT / rel_path
        if not p.exists():
            errors.append(f"{name}：auto-history 找不到 {rel_path}")
            return m.group(0)
        rows = [[c.replace("\0", "|") for c in ln.strip().replace("\\|", "\0").strip("|").split("|")]
                for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip().startswith("|") and not re.match(r"^\|[\s|:-]+\|$", ln.strip())]
        if not rows:
            errors.append(f"{name}：{rel_path} 沒有表格")
            return m.group(0)
        head = "".join(f"<th>{md_inline(c)}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
        sid = a.get("id", "")
        label = f'{a.get("data-milestone", "")} {a.get("data-step", "")}'
        store.append(dict(id=sid, label=label, title=a.get("data-title", ""),
                          table=f'<table class="history"><tr>{head}</tr>{body}</table>'))
        return f'<p>本步驟的修改歷史（{len(rows) - 1} 筆）見<a href="#hist-{sid}">附錄 B　{html.escape(label)}</a>。</p>'
    return re.sub(r'<div class="auto-history"([^>]*)></div>', rep, s)


FOLDED = {"③": "do", "④": "result", "⑤": "check", "⑥": "code"}   # 預設收折的節（使用者 2026-10-30：避免篇幅太大）


def fold_sections(s, sid):
    """把 ③ 動手做、④ 結果與驗收、⑤ 常見錯誤與自我檢查、⑥ 程式與實驗條件 包成 <details>：標題是可點開的列，內容到下一個 h3 或 section 結束。"""
    parts = re.split(r"(<h3>.*?</h3>)", s, flags=re.S)
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        title, body = parts[i], parts[i + 1]
        text = re.sub(r"<[^>]+>", "", title).strip()
        key = FOLDED.get(text[:1])
        if key is None:
            out += [title, body]
            continue
        tail = ""
        if "</section>" in body:                         # 最後一節：</section> 留在 details 之外
            body, tail = body.split("</section>", 1)
            tail = "</section>" + tail
        out.append(f'<details class="sec" id="{sid}-{key}"><summary class="sec-toggle">{text}'
                   f'<span class="hint">（點開）</span></summary>{body}</details>{tail}')
    return "".join(out)


def fix_images(name, s, errors, prefix):
    """src="figures/…"（根目錄相對）→ 依頁面位置加前綴（分頁在 report/ 下用 ../）。"""
    def rep(m):
        rel_path = m.group(1)
        if not (ROOT / rel_path).exists():
            errors.append(f"{name}：找不到圖 {rel_path}")
            return m.group(0)
        return f'src="{prefix}{rel_path}"'
    return re.sub(r'src="(figures/[^"]+)"', rep, s)


def check_forbidden(fn, doc, errors):
    text = re.sub(r'src="data:[^"]+"', "", doc).replace(INDEX_NAME, "")
    for pat, why in FORBIDDEN:
        for m in re.finditer(pat, text):
            ctx = text[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            errors.append(f"{fn}：禁字「{m.group(0)}」（{why}）：…{ctx}…")


def check_links(outs, errors):
    """outs：{輸出路徑: HTML}。每個 頁面.html、頁面.html#錨點、同頁 #錨點 都要存在
    （目標是本次輸出就查本次內容，否則讀磁碟上的檔案；M0 審查 R4 補同頁錨點與磁碟頁的錨點）。"""
    for p, doc in outs.items():
        for t in re.findall(r'href="#([^"]+)"', doc):
            if f'id="{t}"' not in doc:
                errors.append(f"{p.name}：同頁連結 #{t} 找不到錨點")
        for href in re.findall(r'href="([^"#:]+\.html)(?:#([^"]+))?"', doc):
            tp = (p.parent / href[0]).resolve()
            target = outs.get(tp)
            if target is None:
                if not tp.exists():
                    errors.append(f"{p.name}：連結 {href[0]} 不存在")
                    continue
                target = tp.read_text(encoding="utf-8", errors="ignore")
            if href[1] and f'id="{href[1]}"' not in target:
                errors.append(f"{p.name}：連結 {href[0]}#{href[1]} 找不到錨點")


# ---------- 版面 ----------
CSS = """
:root{--bg:#fbfbf8;--fg:#1d1f21;--muted:#5f6368;--line:#d9d9d4;--card:#ffffff;--accent:#2f6fb5;
--bridge:#eef4fb;--code:#f4f4f0;--th:#efefea;--done:#2e7d4f;--doing:#b7791f;--todo:#8a8f96}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17191c;--fg:#e4e4e0;--muted:#a0a4a8;
--line:#3a3d42;--card:#1f2226;--accent:#7fb0e8;--bridge:#1f2a36;--code:#24272b;--th:#2a2d31;--done:#6cc28f;--doing:#e0b05a;--todo:#80868d}}
:root[data-theme="dark"]{--bg:#17191c;--fg:#e4e4e0;--muted:#a0a4a8;--line:#3a3d42;--card:#1f2226;--accent:#7fb0e8;
--bridge:#1f2a36;--code:#24272b;--th:#2a2d31;--done:#6cc28f;--doing:#e0b05a;--todo:#80868d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 "Microsoft JhengHei","Noto Sans TC",sans-serif}
a{color:var(--accent)}
math{font-family:"Cambria Math","STIX Two Math",serif;font-size:1.05em}
math[display="block"]{overflow-x:auto;overflow-y:hidden;max-width:100%;padding:4px 0}
.wrap{display:grid;grid-template-columns:260px minmax(0,1fr);max-width:1280px;margin:0 auto}
nav{position:sticky;top:0;height:100vh;overflow:auto;padding:24px 16px;border-right:1px solid var(--line);font-size:14px}
nav a{color:var(--fg);text-decoration:none;display:block;padding:2px 0}
nav a:hover{color:var(--accent)} nav .m{font-weight:700;margin-top:12px} nav .s{padding-left:12px;color:var(--muted)}
nav .home{font-weight:700;margin-bottom:8px}
main{padding:32px 40px;min-width:0}
h1{font-size:28px;margin:0 0 4px} h2{font-size:22px;border-bottom:2px solid var(--accent);padding-bottom:4px;margin-top:48px}
.step{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 28px 20px;margin:24px 0}
.step>h2.st{font-size:19px;border:0;margin-top:16px}
details.sec{border-top:1px solid var(--line);margin:22px 0 0}
details.sec[open]{padding-bottom:6px}
summary.sec-toggle{font-size:17px;font-weight:700;color:var(--accent);cursor:pointer;padding:10px 0 4px}
summary.sec-toggle .hint{font-size:13px;font-weight:400;color:var(--muted);margin-left:6px}
details.sec[open]>summary .hint{display:none}
.foldbar{display:flex;gap:8px;justify-content:flex-end;margin:4px 0 -8px}
.foldbar button{font:inherit;font-size:13px;color:var(--accent);background:var(--card);border:1px solid var(--line);
border-radius:4px;padding:2px 10px;cursor:pointer}
h3{font-size:17px;margin-top:28px;color:var(--accent)} h4{font-size:15.5px;margin:18px 0 6px}
.sub{color:var(--muted);margin:0 0 24px}
.bridge{background:var(--bridge);border-left:4px solid var(--accent);padding:8px 16px;border-radius:4px;margin:12px 0}
.bridge p{margin:4px 0}
.bridge .terms{font-size:13.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:6px;margin-top:8px}
table{border-collapse:collapse;margin:12px 0;width:100%;font-size:14.5px}
th,td{border:1px solid var(--line);padding:5px 10px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:var(--th)} td:first-child{width:22%;white-space:nowrap}
table.steps td:first-child{width:8%} table.history td:first-child{width:12%}
code{font-family:Consolas,"Cascadia Mono",monospace;font-size:.9em;background:var(--code);padding:0 3px;border-radius:3px}
pre{overflow-x:auto;max-width:100%}
details.code{border:1px solid var(--line);border-radius:6px;margin:8px 0}
details.code summary{cursor:pointer;padding:6px 12px;display:flex;gap:12px;flex-wrap:wrap;align-items:baseline}
details.code .meta,details.code .doc{color:var(--muted);font-size:13px}
details.code pre{margin:0;max-height:520px;overflow:auto;background:var(--code);padding:12px;font-size:13px;line-height:1.5}
details.code pre code{background:none;padding:0}
details.quiz{border-left:3px solid var(--accent);padding:4px 12px;margin:8px 0;background:var(--bridge)}
figure{margin:16px 0;text-align:center} figure img{max-width:100%;height:auto;background:#fff;border-radius:4px}
figcaption{font-size:14px;color:var(--muted);margin-top:6px;text-align:left}
figure.concept{border:1px solid var(--line);border-left:4px solid #8e6fb5;border-radius:6px;padding:10px 12px;margin:14px 0 18px}
.num{border-bottom:1px dotted var(--muted)}
.example{background:var(--code);border-left:4px solid #c08a2b;padding:6px 16px;border-radius:4px;margin:12px 0}
.route{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;text-decoration:none;color:var(--fg);display:block}
.card:hover{border-color:var(--accent)} .card b{color:var(--accent)} .card .meta{color:var(--muted);font-size:13.5px}
.bar{height:6px;background:var(--line);border-radius:3px;margin-top:8px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--done)}
.badge{font-size:12.5px;padding:1px 8px;border-radius:10px;border:1px solid currentColor;white-space:nowrap}
.badge.done{color:var(--done)} .badge.doing{color:var(--doing)} .badge.todo{color:var(--todo)}
.dim{color:var(--muted)}
footer{color:var(--muted);font-size:13px;margin:40px 0 20px}
@media (max-width:860px){.wrap{display:block} nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}
main{padding:16px} .step{padding:4px 16px 16px} td:first-child{width:auto;white-space:normal}
table{display:block;overflow-x:auto}}
@media(max-width:800px){table{display:block;overflow-x:auto;max-width:100%}pre{overflow-x:auto;max-width:100%}math{display:block;overflow-x:auto;max-width:100%}code{overflow-wrap:anywhere}}
"""


def badge(st):
    label, cls = STATUS.get(st, ("未開始", "todo"))
    return f'<span class="badge {cls}">{label}</span>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="有錯誤仍寫檔")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    ms, steps, symbols, terms = read_plan()
    errors, notes, hist = [], [], []
    by_m, done_ids = {}, set()
    raw = {}
    for f in fragments():
        name = f.relative_to(SRC).as_posix()
        s = f.read_text(encoding="utf-8")
        a = check_format(name, s, errors)
        raw[a.get("id", name)] = s
        s = fill_numbers(name, s, errors, notes)
        s = fill_code(name, s, errors)
        s = fill_history(name, s, errors, hist, a)
        s = fix_images(name, s, errors, "../")
        s = fold_sections(s, a.get("id", ""))
        t = html.escape(a.get("data-title", ""))
        s = s.replace(f'data-title="{t}">', f'data-title="{t}">\n<h2 class="st">{a.get("data-milestone", "")} '
                      f'{a.get("data-step", "")}　{t}</h2>', 1)
        by_m.setdefault(a.get("data-milestone", "?"), []).append((a, s))
        done_ids.add(a.get("id", ""))

    check_terms(raw, [st["id"] for st in steps], terms, errors)

    apps = []
    for f in sorted((SRC / "appendix").glob("*.html")):
        name = f.relative_to(SRC).as_posix()
        s = f.read_text(encoding="utf-8")
        m = re.search(r'<section class="appendix"([^>]*)>', s)
        if not m:
            errors.append(f"{name}：缺 <section class=\"appendix\" id=… data-title=…>")
            continue
        a = attrs(m.group(1))
        s = fix_images(name, fill_numbers(name, s, errors, notes), errors, "../")
        apps.append((a, f'<h2 id="{a.get("id", "")}">{html.escape(a.get("data-title", ""))}</h2>' + s))
    if symbols:
        apps.append((dict(id="app-a", **{"data-title": "附錄 A　符號與埠名對照"}), symbols_appendix(symbols)))
    if hist:
        hb =['<h2 id="app-b">附錄 B　修改的歷史</h2><p>每個步驟的修改紀錄（日期、修改、原因、影響），標題連回該步驟。本附錄是開發過程的紀錄，用語較為簡略，閱讀課程內容時不需要參考。</p>']
        for h in hist:
            hb.append(f'<h3 id="hist-{h["id"]}"><a href="#{h["id"]}">{html.escape(h["label"])}　{html.escape(h["title"])}</a></h3>{h["table"]}')
        apps.append((dict(id="app-b", **{"data-title": "附錄 B　修改的歷史"}), "".join(hb)))
    apps.sort(key=lambda t: t[0].get("id", ""))

    # 錨點 → 頁面（分頁在 report/ 下）
    page_of = {}
    pages = {}
    for mk in sorted(by_m, key=lambda k: int(k[1:]) if k[1:].isdigit() else 99):
        fn = f"{mk.lower()}.html"
        body = [f'<h2 id="{mk.lower()}">{mk}　{html.escape(ms.get(mk, {}).get("title", ""))}</h2>']
        page_of[mk.lower()] = fn
        for a, s in by_m[mk]:
            page_of[a.get("id", "")] = fn
            body.append(s)
        pages[fn] = (f"{mk}　{ms.get(mk, {}).get('title', '')}", "".join(body))
    if apps:
        for a, _ in apps:
            page_of[a.get("id", "")] = "appendix.html"
        for h in hist:
            page_of[f"hist-{h['id']}"] = "appendix.html"
        pages["appendix.html"] = ("附錄", "".join(s for _, s in apps))

    def link(target_id, from_index):
        fn = page_of.get(target_id)
        if fn is None:
            return None
        return (f"report/{fn}" if from_index else fn) + f"#{target_id}"

    def nav_html(cur):
        home = f"../{INDEX_NAME}"
        out = [f'<a class="home" href="{home}">← 課程入口</a>']
        for mk, info in ms.items():
            fn = f"{mk.lower()}.html"
            if fn in pages:
                out.append(f'<a class="m" href="{fn}">{mk}　{html.escape(info["title"])}</a>')
                if cur == fn:
                    for a, _ in by_m[mk]:
                        out.append(f'<a class="s" href="#{a.get("id", "")}">{a.get("data-step", "")}　{html.escape(a.get("data-title", ""))}</a>')
            else:
                out.append(f'<span class="m dim" style="display:block;margin-top:12px">{mk}　{html.escape(info["title"])}</span>')
        for a, _ in apps:
            out.append(f'<a class="m" href="appendix.html#{a.get("id", "")}">{html.escape(a.get("data-title", ""))}</a>')
        return "".join(out)

    def relink(cur, s):
        def rep(m):
            t = m.group(1)
            fn = page_of.get(t)
            return f'href="#{t}"' if fn in (None, cur) else f'href="{fn}#{t}"'
        return re.sub(r'href="#([^"]+)"', rep, s)

    stamp = time.strftime("%Y-%m-%d %H:%M")

    foldbar = ('<div class="foldbar"><button type="button" onclick="document.querySelectorAll(\'details.sec\')'
               '.forEach(d=>d.open=true)">全部展開</button><button type="button" onclick="document.querySelectorAll('
               '\'details.sec\').forEach(d=>d.open=false)">全部收合</button></div>')
    # 從別處連到被收折節裡的錨點（或網址帶 #…）時，自動展開它所在的節
    autoopen = ('<script>function openTo(h){const e=h&&document.getElementById(decodeURIComponent(h.slice(1)));'
                'for(let p=e;p;p=p.parentElement){if(p.tagName==="DETAILS")p.open=true}}'
                'openTo(location.hash);addEventListener("hashchange",()=>openTo(location.hash));</script>')

    def doc_of(title, nav, body, has_nav=True):
        if has_nav and 'class="sec"' in body:
            body = foldbar + body + autoopen
        wrap = (f'<div class="wrap"><nav>{nav}</nav><main>{body}' if has_nav else f'<div style="max-width:1100px;margin:0 auto"><main>{body}')
        return (f'<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
                f'<style>{CSS}</style></head><body>{wrap}'
                f'<footer>本報告由步驟片段自動組裝；數字加虛線者由計算結果帶入。組裝時間 {stamp}。</footer></main></div></body></html>\n')

    # ---------- 入口頁 ----------
    idx = [f'<h1>{TITLE}</h1><p class="sub">以學員的學習過程，從光訊號如何做邏輯開始，'
           f'一路完成電路模擬、佈局、DRC 與交付。共 {len(steps)} 個步驟，已完成 {sum(st["status"] == "☑" for st in steps)} 個。</p>']
    for f in sorted((SRC / "index").glob("*.html")):           # 課程總覽等手寫內容
        name = f"index/{f.name}"
        s = f.read_text(encoding="utf-8")
        idx.append(fix_images(name, fill_numbers(name, s, errors, notes), errors, ""))

    idx.append('<h2 id="route">學習路線</h2><div class="route">')
    paper_steps = [dict(m=f"論文 {r[0].split()[0]}", hours=r[4], status=r[7][:1])     # 論文步驟表與步驟表同欄位
                   for r in table_rows(PLAN.read_text(encoding="utf-8"), "論文步驟表")]
    for mk, info in ms.items():
        sts = [st for st in (paper_steps if mk.startswith("論文") else steps) if st["m"] == mk]
        nd = sum(st["status"] == "☑" for st in sts)
        hours = sum(float(re.sub(r"[^\d.]", "", st["hours"]) or 0) for st in sts)
        fn = f"{mk.lower()}.html"
        if mk.startswith("論文") and nd:                                  # 論文延伸：連到論文頁該里程碑第一步
            tag, end = f'<a class="card" href="report/paper.html#p-{mk.split()[1].lower()}-s1">', "</a>"
        else:
            tag, end = ((f'<a class="card" href="report/{fn}">', "</a>") if fn in pages else ('<div class="card">', "</div>"))
        idx.append(f'{tag}<b>{mk}</b>　{html.escape(info["title"])}<div class="meta">{len(sts)} 步・約 {hours:g} h・'
                   f'完成 {nd}／{len(sts)}</div><div class="bar"><span style="width:{100 * nd / max(len(sts), 1):.0f}%"></span></div>{end}')
    idx.append("</div>")

    idx.append('<h2 id="steps">步驟目錄與進度</h2><table class="steps"><tr><th>步驟</th><th>標題</th>'
               '<th>本步要回答的問題</th><th>成果</th><th>時數</th><th>狀態</th></tr>')
    for st in steps:
        href = link(st["id"], True)
        title = f'<a href="{href}">{html.escape(st["title"])}</a>' if href else html.escape(st["title"])
        idx.append(f'<tr><td>{st["m"]} {st["s"]}</td><td>{title}</td><td>{html.escape(st["question"])}</td>'
                   f'<td>{html.escape(st["output"])}</td><td>{html.escape(st["hours"])}</td><td>{badge(st["status"])}</td></tr>')
    idx.append("</table>")

    extra = []
    for a, _ in apps:
        extra.append(f'<li><a href="report/appendix.html#{a.get("id", "")}">{html.escape(a.get("data-title", ""))}</a></li>')
    for sub, label in (("review", "里程碑審查"), ("lessons", "學習心得")):
        for f in sorted((PAGES / sub).glob("*.html")):
            extra.append(f'<li><a href="report/{sub}/{f.name}">{label}：{html.escape(f.stem)}</a></li>')
    if (ROOT / "delivery" / "README.md").exists():
        extra.append('<li><a href="delivery/README.md">交付包說明</a></li>')
    if (PAGES / "paper.html").exists():                       # 課程之外的論文延伸（tools/build_paper.py 產生）
        extra.append('<li><a href="report/paper.html">論文延伸：10 Gb/s MZI／B7 時序分析與校正</a></li>')
    idx.append('<h2 id="more">附錄、審查與交付</h2>' +
               (f"<ul>{''.join(extra)}</ul>" if extra else '<p class="dim">尚未產生（完成各里程碑後會出現在這裡）。</p>'))

    outs = {INDEX: doc_of("光運算邏輯設計實作", "", "".join(idx), has_nav=False)}
    for fn, (title, body) in pages.items():
        outs[PAGES / fn] = doc_of(f"{title}｜光運算邏輯設計實作", nav_html(fn), relink(fn, body))

    # ---------- 檢查 ----------
    for p, doc in outs.items():
        check_forbidden(p.name, doc, errors)
    check_links(outs, errors)

    for n in notes:
        print("更新：", n)
    for e in errors:
        print("錯誤：", e)
    if errors and not args.force:
        print(f"共 {len(errors)} 個錯誤，未寫檔。")
        sys.exit(1)
    for p, doc in outs.items():
        p.write_text(doc, encoding="utf-8")
    sizes = "、".join(f"{p.relative_to(ROOT).as_posix()} {len(d.encode('utf-8')) / 1024:.0f} KB" for p, d in outs.items())
    print(f"寫出 {len(outs)} 頁（{sum(len(v) for v in by_m.values())} 個步驟片段）：{sizes}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
