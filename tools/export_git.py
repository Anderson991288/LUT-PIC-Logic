r"""里程碑關卡：把可公開的檔案彙整到 git/（GitHub 上傳用快照），可重複執行；工作目錄不動。

收錄：LUT_Claude_index.html、lab.cmd（公開版：不含本機的 Python 位置）、design/（程式、結果、HISTORY、INDEX）、figures/、report/、delivery/、
      tools/*.py、整理過的進度表（PLAN.md 只留學習主線與進度表）、README.md、.gitignore（本程式產生）。
排除：平台專有（*.lydrc、design/common/drc/）、含 PDK 元件的 *.gds、KLayout 報告 *.lyrdb（含本機路徑，可重產）、
      __pycache__、內部核對（check_reference.py 與 reference_check.json：讀取課程原始資料，只供內部比對）、
      隱藏資料夾（課程原始資料、內部規則與備份）、完整的 PLAN.md（只匯出學習主線與進度表）。
檢查：先重新組裝步驟報告與各單頁報告，再用 build_report.py 的讀者文件禁字樣式掃描所有文字檔；
      有任何命中或組裝失敗就不動 git/、結束碼 1。
輸入：專案目錄。
輸出：git/ 快照、git/MANIFEST.tsv（路徑、位元組、sha256 前 12 碼）、design/m0_env/s2_tools/out/export.json（統計）。
      git/.git（版本紀錄）一律保留。
執行：.\lab tools\export_git.py [--dry-run]
"""
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "git"
TEXT = {".py", ".md", ".html", ".json", ".txt", ".tsv", ".csv", ".cmd"}
EXCLUDE = [   # (樣式, 原因)；比對相對路徑
    (re.compile(r"(^|/)__pycache__/|\.pyc$"), "Python 快取"),
    (re.compile(r"\.lydrc$|^design/common/drc/"), "平台專有 DRC deck"),
    (re.compile(r"\.gds$"), "含 PDK 元件的 GDS（可由程式重產）"),
    (re.compile(r"\.lyrdb$"), "KLayout 報告（含本機路徑，可重產）"),
    (re.compile(r"check_reference\.py$|reference_check\.json$"), "內部核對（讀取課程原始資料）"),
]
SOURCES = ["design", "figures", "report", "delivery"]
ROOT_FILES = ["LUT_Claude_index.html"]


def public_lab_cmd():
    """lab.cmd 的公開版：拿掉本機預設的 Python 位置，改為一定要設定 LAB_PYTHON。"""
    s = (ROOT / "lab.cmd").read_text(encoding="ascii")
    s2 = re.sub(r'if defined LAB_PYTHON \(set "PY=%LAB_PYTHON%"\) else \(set "PY=[^"]*"\)',
                'set "PY=%LAB_PYTHON%"', s)
    assert s2 != s, "lab.cmd 的預設路徑格式改了，請更新 public_lab_cmd()"
    return s2.replace("otherwise the default Luceda install.", "(required in this public copy).")

README = """# 光運算邏輯設計實作：從 B7 邏輯運算到一顆完整的 PIC

以學員的學習過程，從「光如何做邏輯」開始，依里程碑 M0–M3 完成電路模擬、佈局、DRC 與交付。
讀者入口：`LUT_Claude_index.html`（各里程碑分頁在 `report/`）。快照日期 {date}。

## 進度
{progress}

## 目錄
- `design/`：程式與結果（每個步驟一個資料夾，內含 `out/` 與 `HISTORY.md`；`design/INDEX.md` 是檔案索引）
- `figures/`：報告用圖
- `report/`：分頁報告、里程碑審查（`review/`）、學習心得（`lessons/`）
- `tools/`：報告組裝、索引、匯出工具

## 執行
需要 Luceda IPKISS（含 CORNERSTONE PDK）與 KLayout。在專案根目錄：`.\\lab <程式路徑>`
（`lab.cmd` 會呼叫 IPKISS 環境的 Python；位置不同時設定環境變數 `LAB_PYTHON`）。
PDK 的 GDS 與 DRC deck 屬平台專有，不在本快照中；GDS 可由佈局程式重產。
"""
GITIGNORE = "__pycache__/\n*.pyc\n*.gds\n*.lyrdb\n*.lydrc\n"
GITATTRIBUTES = "* -text\n"   # 不轉換換行：交接檔以位元組的 SHA-256 綁定，換行被改就會驗證失敗


def load_build():
    spec = importlib.util.spec_from_file_location("build_report", Path(__file__).with_name("build_report.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plan_progress():
    s = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    keep = []
    for title in ("## 學習主線", "## 進度表"):
        i = s.index(title)
        j = s.find("\n## ", i + 1)
        keep.append(s[i:j if j > 0 else len(s)].strip())
    rows = re.findall(r"^\| (M\d+) \| ([^|]+?) \| (\d+) \| ([^|]+?) \|", s, re.M)
    return "# 進度\n\n" + "\n\n".join(keep) + "\n", rows


def collect():
    files, skipped = [], Counter()
    for top in SOURCES:
        for p in sorted((ROOT / top).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            why = next((w for rx, w in EXCLUDE if rx.search(rel)), None)
            if why:
                skipped[why] += 1
            else:
                files.append((p, rel))
    for name in ROOT_FILES:
        files.append((ROOT / name, name))
    for p in sorted((ROOT / "tools").glob("*.py")):
        files.append((p, p.relative_to(ROOT).as_posix()))
    return files, skipped


def scan(texts, forbidden, index_name):
    hits = []
    for rel, s in texts:
        s = s.replace(index_name, "")
        for pat, why in forbidden:
            for m in re.finditer(pat, s):
                ln = s.count("\n", 0, m.start()) + 1
                hits.append(f"{rel}:{ln}：「{m.group(0)}」（{why}）")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只檢查與統計，不寫 git/")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    tools = Path(__file__).parent
    pages = sorted(str(p) for p in (ROOT / "report").glob("*/src/*.html") if p.parent.parent.name in ("review", "lessons"))
    cmds = [[sys.executable, str(tools / "build_report.py")]]
    if pages:
        cmds.append([sys.executable, str(tools / "build_page.py"), *pages])
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print("報告組裝失敗，未寫 git/：\n" + r.stdout[-2000:])
            sys.exit(1)
    files, skipped = collect()
    plan_md, rows = plan_progress()
    date = time.strftime("%Y-%m-%d")
    prog = "| 里程碑 | 主題 | 步驟數 | 狀態 |\n|---|---|---|---|\n" + "\n".join(f"| {m} | {t} | {n} | {s} |" for m, t, n, s in rows)
    generated = {"README.md": README.format(date=date, progress=prog), ".gitignore": GITIGNORE, ".gitattributes": GITATTRIBUTES,
                 "PLAN.md": plan_md,
                 "lab.cmd": public_lab_cmd()}
    B = load_build()
    texts = [(rel, p.read_text(encoding="utf-8", errors="ignore")) for p, rel in files if p.suffix.lower() in TEXT]
    texts += list(generated.items())
    hits = scan(texts, B.FORBIDDEN, B.INDEX_NAME)
    if hits:
        print(f"禁字檢查有 {len(hits)} 處，未寫 git/：")
        for h in hits[:40]:
            print("  ", h)
        sys.exit(1)

    total = sum(p.stat().st_size for p, _ in files) + sum(len(v.encode("utf-8")) for v in generated.values())
    cats = Counter(rel.split("/")[0] if "/" in rel else "根目錄" for _, rel in files)
    if not a.dry_run:
        OUT.mkdir(exist_ok=True)
        for child in OUT.iterdir():                    # 清掉舊快照，只保留版本紀錄
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        man = []
        for p, rel in files:
            d = OUT / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d)
            man.append((rel, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()[:12]))
        for rel, s in generated.items():
            d = OUT / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            d.write_text(s, encoding="utf-8")
            man.append((rel, len(s.encode("utf-8")), hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]))
        (OUT / "MANIFEST.tsv").write_text("path\tbytes\tsha256_12\n" + "\n".join(f"{r}\t{b}\t{h}" for r, b, h in sorted(man)) + "\n",
                                          encoding="utf-8")
    res = {"tool": "export_git", "date": date, "dry_run": a.dry_run, "n_files": len(files) + len(generated),
           "bytes": total, "by_top": dict(cats), "generated": sorted(generated), "skipped": dict(skipped), "forbidden_hits": 0}
    od = ROOT / "design" / "m0_env" / "s2_tools" / "out"
    (od / "export.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'（試跑）' if a.dry_run else ''}匯出 {res['n_files']} 個檔案、{total / 1024:.0f} KB：{dict(cats)}；"
          f"產生 {len(generated)} 個說明檔；排除 {dict(skipped)}；禁字 0")


if __name__ == "__main__":
    main()
