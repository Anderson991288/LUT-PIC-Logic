r"""論文延伸頁組裝程式：report/src/paper/<mN>/<sN>.html → report/paper.html（單一頁）。

用途：課程（M0–M3）之外延伸成論文題材的工作，獨立成一頁，不放進課程的分頁與步驟目錄。
  - 沿用 build_report 的處理：數字由 JSON 帶入、圖片路徑、③–⑥ 收折、禁字、連結檢查、先定義才使用。
  - 編號自成一套（M0、M1…）；片段中提到課程步驟一律寫「課程 Mx sy」（或「課程 Mx」），組裝時自動連到課程分頁對應的段落。
  - 不嵌入程式原文（控制頁面大小）：auto-code 只列檔名與執行指令。
  - 頁尾附「論文符號表」（PLAN.md）與各步修改歷史。
輸入：PLAN.md 的「論文步驟表」「論文符號表」「論文名詞首次定義」；report/src/paper/m*/s*.html。
輸出：report/paper.html。有錯誤時不寫檔、結束碼 1（--force 仍寫檔）。
執行：.\lab tools\build_paper.py
"""
import argparse
import html
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as B                                             # noqa: E402

SRC = B.SRC / "paper"
OUT = B.PAGES / "paper.html"
TITLE = "論文延伸：10 Gb/s MZI／B7 時序分析與校正"
COURSE_REF = re.compile(r"課程 M([0-3])(?: s(\d))?(?![–\d])")
MILESTONES = {"M0": "study 重點提示", "M1": "10 Gb/s 時序分析與校正", "M2": "論文的核心證據", "M3": "對齊論文草稿的設定", "M4": "盒證明", "M5": "串接與蛇形選擇"}


def read_plan():
    text = B.PLAN.read_text(encoding="utf-8")
    steps = []
    for r in B.table_rows(text, "論文步驟表"):
        mk, sk = r[0].split()
        steps.append(dict(m=mk, s=sk, id=f"p-{mk.lower()}-{sk}", title=r[1], question=r[2], status=r[7][:1]))
    symbols = B.table_rows(text, "論文符號表")
    terms = {r[0]: "p-" + r[1].lower().replace(" ", "-") for r in B.table_rows(text, "論文名詞首次定義")}
    return steps, symbols, terms


def fragments():
    items = []
    for f in SRC.glob("m*/s*.html"):
        mm, ss = re.match(r"m(\d+)$", f.parent.name), re.match(r"s(\d+)$", f.stem)
        if mm and ss:
            items.append((int(mm.group(1)), int(ss.group(1)), f))
    return [f for _, _, f in sorted(items)]


def check_format(name, s, errors):
    """M0（課程重點提示）只要求 section 屬性；M1 起要求六節。"""
    m = re.search(r'<section class="step"([^>]*)>', s)
    if not m:
        errors.append(f"{name}：缺 <section class=\"step\">")
        return {}
    a = B.attrs(m.group(1))
    for k in ("id", "data-milestone", "data-step", "data-title"):
        if k not in a:
            errors.append(f"{name}：section 缺屬性 {k}")
    if not a.get("id", "").startswith("p-"):
        errors.append(f"{name}：論文片段的 id 要以 p- 開頭（避免與課程錨點混淆）")
    if a.get("data-milestone") != "M0":
        h3 = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h3>(.*?)</h3>", s, re.S)]
        if h3 != B.SECTIONS:
            errors.append(f"{name}：六節標題或順序不符，實際為 {h3}")
    return a


def list_code(name, s, errors):
    def rep(m):
        files = B.attrs(m.group(1)).get("data-files", "").split()
        if not files:
            errors.append(f"{name}：auto-code 沒有列檔案")
        rows = []
        for f in files:
            if not (B.ROOT / f).exists():
                errors.append(f"{name}：auto-code 找不到 {f}")
            rows.append(f"<li><code>{html.escape(f)}</code>（執行：<code>.\\lab {html.escape(f.replace('/', chr(92)))}</code>）</li>")
        return '<p>本步的程式（原文不嵌入本頁）：</p><ul class="code-list">' + "".join(rows) + "</ul>"
    return re.sub(r'<div class="auto-code"([^>]*)></div>', rep, s)


def link_course(s):
    """「課程 Mx sy」→ 連到課程分頁的段落；程式碼、公式、既有連結與標籤內不處理。"""
    parts = re.split(r"(<(?:pre|code|math|a)\b.*?</(?:pre|code|math|a)>|<[^>]+>)", s, flags=re.S)
    for i in range(0, len(parts), 2):
        def rep(m):
            mk, sk = m.group(1), m.group(2)
            href = f"m{mk}.html#m{mk}-s{sk}" if sk else f"m{mk}.html"
            return f'<a class="course" href="{href}">{m.group(0)}</a>'
        parts[i] = COURSE_REF.sub(rep, parts[i])
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="有錯誤仍寫檔")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    steps, symbols, terms = read_plan()
    titles = MILESTONES
    errors, notes, hist = [], [], []
    raw, body, by_m = {}, [], {}
    for f in fragments():
        name = "paper/" + f.relative_to(SRC).as_posix()
        s = f.read_text(encoding="utf-8")
        a = check_format(name, s, errors)
        raw[a.get("id", name)] = s
        s = B.fill_numbers(name, s, errors, notes)
        s = list_code(name, s, errors)
        s = B.fill_history(name, s, errors, hist, a)
        s = B.fix_images(name, s, errors, "../")
        s = B.fold_sections(s, a.get("id", ""))
        s = link_course(s)
        t = html.escape(a.get("data-title", ""))
        s = s.replace(f'data-title="{t}">', f'data-title="{t}">\n<h2 class="st">{a.get("data-milestone", "")} '
                      f'{a.get("data-step", "")}　{t}</h2>', 1)
        by_m.setdefault(a.get("data-milestone", "?"), []).append(a)
        body.append(s)
    B.check_terms(raw, [st["id"] for st in steps], terms, errors)

    # 頁尾：論文符號表＋修改歷史（同一頁）
    def sub(t):
        return re.sub(r"(?<=[^\s_])_([A-Za-z0-9]+)", r"<sub>\1</sub>", B.md_inline(t))
    tail = ['<h2 id="p-sym">論文符號表</h2><p>課程的符號見課程附錄 A；以下是論文延伸新增的符號。</p><table>'
            '<tr><th>符號</th><th>意義</th><th>單位</th></tr>' +
            "".join(f"<tr><td>{sub(r[0])}</td><td>{link_course(sub(r[1]))}</td><td>{sub(r[2])}</td></tr>" for r in symbols) + "</table>"]
    if hist:
        tail.append('<h2 id="app-b">附錄 B　修改的歷史</h2>')
        for h in hist:
            tail.append(f'<h3 id="hist-{h["id"]}"><a href="#{h["id"]}">{html.escape(h["label"])}　{html.escape(h["title"])}</a></h3>'
                        + link_course(h["table"]))

    # 開頭：步驟目錄
    head = [f'<h1>{html.escape(TITLE)}</h1><p class="sub">課程（M0–M3）完成一顆 B7 PIC 之後，延伸成論文題材的工作。'
            '本頁編號自成一套；提到課程的步驟寫成「課程 Mx sy」，點選可回到課程的對應段落。</p>',
            '<table class="steps"><tr><th>步驟</th><th>標題</th><th>本步要回答的問題</th><th>狀態</th></tr>']
    present = {a.get("id") for v in by_m.values() for a in v}
    for st in steps:
        t = (f'<a href="#{st["id"]}">{html.escape(st["title"])}</a>' if st["id"] in present else html.escape(st["title"]))
        head.append(f'<tr><td>{st["m"]} {st["s"]}</td><td>{t}</td><td>{link_course(html.escape(st["question"]))}</td>'
                    f'<td>{B.badge(st["status"])}</td></tr>')
    head.append("</table>")

    nav = [f'<a class="home" href="../{B.INDEX_NAME}">← 課程入口</a>']
    for mk, lst in by_m.items():
        nav.append(f'<a class="m" href="#{lst[0].get("id", "")}">{mk}　{html.escape(titles.get(mk, ""))}</a>')
        for a in lst:
            nav.append(f'<a class="s" href="#{a.get("id", "")}">{a.get("data-step", "")}　{html.escape(a.get("data-title", ""))}</a>')
    nav.append('<a class="m" href="#p-sym">論文符號表</a>')
    if hist:
        nav.append('<a class="m" href="#app-b">附錄 B　修改的歷史</a>')

    stamp = time.strftime("%Y-%m-%d %H:%M")
    content = "".join(head) + "".join(body) + "".join(tail)
    if 'class="sec"' in content:
        content = ('<div class="foldbar"><button type="button" onclick="document.querySelectorAll(\'details.sec\')'
                   '.forEach(d=>d.open=true)">全部展開</button><button type="button" onclick="document.querySelectorAll('
                   '\'details.sec\').forEach(d=>d.open=false)">全部收合</button></div>' + content +
                   '<script>function openTo(h){const e=h&&document.getElementById(decodeURIComponent(h.slice(1)));'
                   'for(let p=e;p;p=p.parentElement){if(p.tagName==="DETAILS")p.open=true}}'
                   'openTo(location.hash);addEventListener("hashchange",()=>openTo(location.hash));</script>')
    doc = (f'<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(TITLE)}</title>'
           f'<style>{B.CSS}.code-list code{{font-size:13px}}a.course{{text-decoration:underline dotted}}</style></head><body>'
           f'<div class="wrap"><nav>{"".join(nav)}</nav><main>{content}'
           f'<footer>本頁由步驟片段自動組裝；數字加虛線者由計算結果帶入。組裝時間 {stamp}。</footer></main></div></body></html>\n')

    B.check_forbidden(OUT.name, doc, errors)
    B.check_links({OUT: doc}, errors)
    for n in notes:
        print("更新：", n)
    for e in errors:
        print("錯誤：", e)
    if errors and not args.force:
        print(f"共 {len(errors)} 個錯誤，未寫檔。")
        sys.exit(1)
    OUT.write_text(doc, encoding="utf-8")
    n_links = len(re.findall(r'class="course"', doc))
    print(f"寫出 {OUT.relative_to(B.ROOT).as_posix()} {len(doc.encode('utf-8')) / 1024:.0f} KB（{len(body)} 個片段、{n_links} 個連回課程的連結）")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
