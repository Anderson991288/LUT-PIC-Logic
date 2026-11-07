r"""M0 s2：檔案索引產生器。

用途：掃描 design/ 與 figures/，產生 design/INDEX.md：每個檔案一列「檔案｜大小｜用途／產生者｜所屬步驟」。
  - .py 的用途取 docstring 第一行。
  - 其他檔案的產生者：同步驟資料夾（圖則為全部程式）中，docstring「輸出：」段落提到該檔名的程式。
  - 找不到產生者的非程式檔標「？」，提醒補 docstring 或刪除過時檔案。
輸入：design/**、figures/**。
輸出：design/INDEX.md、design/m0_env/s2_tools/out/index_stats.json（檔案數、找不到產生者的數目，供報告引用）。
執行：.\lab tools\make_index.py [--check]（--check：不寫檔，索引過時或有檔案找不到產生者時結束碼 1）
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", ".matplotlib"}


def doc_of(p):
    try:
        return ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
    except (SyntaxError, UnicodeDecodeError):
        return ""


def outputs_of(doc):
    """docstring 中「輸出：」到下一個「xx：」段落之間的文字。"""
    m = re.search(r"^輸出：(.*?)(?=\n\S+：|\Z)", doc, re.S | re.M)      # 只認行首的「輸出：」
    return m.group(1) if m else ""


def output_names(text):
    """「輸出：」段落中提到的完整檔名集合（只取檔名，不含資料夾）。
    只認完整檔名，避免檔名片段（例如 mmi、s1）把過時檔誤認為有產生者（M0 審查 R9）。"""
    return {Path(t).name for t in re.findall(r"[\w./*-]+\.[A-Za-z0-9]+", text) if not t.startswith(".")}


def size(p):
    n = p.stat().st_size
    return f"{n / 1024:.1f} KB" if n < 1024 ** 2 else f"{n / 1024 ** 2:.1f} MB"


def step_of(rel):
    m = re.match(r"design/(m\d+)_[^/]+/(s\d+)_", rel) or re.match(r"figures/(m\d+)/(s\d+)_", rel)
    return f"{m.group(1).upper()} {m.group(2)}" if m else "共用"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    files = [p for d in ("design", "figures") for p in sorted((ROOT / d).rglob("*"))
             if p.is_file() and not SKIP & set(p.parts) and p.name != "INDEX.md"]
    progs = {p: doc_of(p) for p in files if p.suffix == ".py"}
    tools = {p: doc_of(p) for p in sorted((ROOT / "tools").glob("*.py"))}   # 組裝與索引工具也可能是產生者
    rows, missing, course_missing = [], 0, 0
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        if p.name == "HISTORY.md":
            what = "修改歷史（人工維護，組裝時帶入附錄 B）"
        elif p.suffix == ".lydrc":
            what = "CORNERSTONE DRC deck（平台提供，不匯出）"
        elif p.suffix == ".py":
            what = (progs[p].strip().splitlines() or ["（缺 docstring）"])[0]
        else:
            cands = progs if rel.startswith("figures/") else {q: d for q, d in progs.items() if q.parent in (p.parent, p.parent.parent)}
            who = [q.name for q, d in {**cands, **tools}.items() if p.name in output_names(outputs_of(d))]
            what = "產生者：" + "、".join(who) if who else "？"
            missing += not who
            course_missing += not who and bool(re.match(r"design/(common|m\d_)|figures/m\d/", rel))
        rows.append(f"| `{rel}` | {size(p)} | {what.replace('|', '／')} | {step_of(rel)} |")
    text = ("# 檔案索引（由 tools/make_index.py 自動產生，不要手改）\n\n"
            "| 檔案 | 大小 | 用途／產生者 | 所屬步驟 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    idx = ROOT / "design" / "INDEX.md"
    if "--check" in sys.argv:                       # 只比對檔案清單、用途與產生者（大小隨重跑變動，不比）
        def key(t):
            return [re.sub(r"\| [\d.]+ [KM]B \|", "|", ln) for ln in t.splitlines()]
        same = idx.exists() and key(idx.read_text(encoding="utf-8")) == key(text)
        print(f"design/INDEX.md {'是最新的' if same else '過時，請重跑 make_index.py'}；{missing} 個找不到產生者")
        sys.exit(0 if same and missing == 0 else 1)
    idx.write_text(text, encoding="utf-8")
    stats = ROOT / "design" / "m0_env" / "s2_tools" / "out" / "index_stats.json"
    stats.parent.mkdir(parents=True, exist_ok=True)
    stats.write_text(json.dumps(dict(files=len(rows), missing=course_missing, missing_all=missing), ensure_ascii=False), encoding="utf-8")
    print(f"寫出 design/INDEX.md：{len(rows)} 個檔案，{missing} 個找不到產生者")
    sys.exit(0)


if __name__ == "__main__":
    main()
