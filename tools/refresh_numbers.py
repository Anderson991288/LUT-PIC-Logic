r"""把步驟片段中每個 span.num 的備用值，更新為目前結果 JSON 算出的值（重跑程式之後用）。

用途：組裝時數字一律由 JSON 帶入，備用值只是原稿裡的參考；重跑後備用值會過時，組裝會一直提示「片段寫 …，依 JSON 改為 …」。
      本工具把備用值改成和 JSON 一致，讓提示只在真的有新變化時出現。計算錯誤的數字不更動，並列出來。
輸入：report/src/**/*.html、片段引用的 JSON。
輸出：就地更新的片段（只改 span.num 的內文）。
執行：.\lab tools\refresh_numbers.py
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build_report", Path(__file__).with_name("build_report.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    changed = 0
    for f in sorted((ROOT / "report").glob("**/src/**/*.html")):
        name = f.relative_to(ROOT).as_posix()
        s = f.read_text(encoding="utf-8")
        n = [0]

        def rep(m):
            errors = []
            out = B.fill_numbers(name, m.group(0), errors, [])
            if errors:
                print("錯誤：", errors[0])
                return m.group(0)
            new = re.search(r">(.*?)</span>", out, re.S).group(1)
            if new != m.group(2):
                n[0] += 1
            return m.group(1) + new + "</span>"

        s2 = re.sub(r'(<span class="num"[^>]*>)(.*?)</span>', rep, s, flags=re.S)
        if s2 != s:
            f.write_text(s2, encoding="utf-8")
            print(f"{name}：更新 {n[0]} 個備用值")
            changed += n[0]
    print(f"共更新 {changed} 個備用值")


if __name__ == "__main__":
    main()
