r"""里程碑關卡：單頁報告組裝（里程碑審查、心得報告），與步驟報告同樣式、同檢查。

用途：把 report/<類別>/src/<名稱>.html 片段包成完整頁面 report/<類別>/<名稱>.html。
  沿用 build_report.py 的 CSS、JSON 數字帶入（span.num）、圖片路徑改寫、讀者文件禁字與連結檢查；不檢查六節格式。
  片段第一行若是 <!-- title: … -->，作為頁面標題。頁首有回到課程入口的連結。
輸入：report/<類別>/src/*.html（可指定多個）。
輸出：report/<類別>/<名稱>.html。有錯誤時不寫檔、結束碼 1。
執行：.\lab tools\build_page.py report\review\src\m1_review.html [其他片段…]
"""
import importlib.util
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build_report", Path(__file__).with_name("build_report.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def build(src):
    src = Path(src).resolve()
    name = src.relative_to(ROOT).as_posix()
    s = src.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--\s*title:\s*(.*?)\s*-->", s)
    title = m.group(1) if m else src.stem
    errors, notes = [], []
    s = B.fill_numbers(name, s, errors, notes)
    s = B.fix_images(name, s, errors, "../../")          # 頁面在 report/<類別>/ 下
    stamp = time.strftime("%Y-%m-%d %H:%M")
    doc = (f'<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>'
           f'<style>{B.CSS}\nmain{{max-width:1000px;margin:0 auto}}</style></head>'
           f'<body><main><p><a href="../../{B.INDEX_NAME}">← 課程入口</a></p><h1>{title}</h1>'
           f'<p class="sub">組裝時間 {stamp}；數字加虛線者由計算結果帶入。</p>\n{s}\n</main></body></html>\n')
    out = src.parent.parent / (src.stem + ".html")
    B.check_forbidden(out.name, doc, errors)
    B.check_links({out: doc}, errors)
    for n in notes:
        print("更新：", n)
    for e in errors:
        print("錯誤：", e)
    if errors:
        print(f"{name}：{len(errors)} 個錯誤，未寫檔。")
        return False
    out.write_text(doc, encoding="utf-8")
    print(f"寫出 {out.relative_to(ROOT).as_posix()}（{len(doc.encode('utf-8')) / 1024:.0f} KB）")
    return True


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok = all([build(a) for a in sys.argv[1:]])
    sys.exit(0 if ok else 1)
