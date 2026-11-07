r"""M0 s2：報告組裝程式的故障注入測試——檢查真的抓得到錯嗎？

用途：拿 M0 s1 的真實片段，逐一注入一種常見錯誤，確認組裝程式（tools/build_report.py）的對應檢查會報錯或自動更正；
      另外以未注入的原片段確認不會誤報。任何一項沒抓到就結束碼 1。
輸入：report/src/m0/s1.html、design/m0_env/s1_check/out/env.json、PLAN.md。
輸出：out/tool_tests.json（每個案例：注入內容、預期反應、實際訊息、是否通過）。
執行：.\lab design\m0_env\s2_tools\test_tools.py
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)
import paths                                                         # noqa: E402

spec = importlib.util.spec_from_file_location("build_report", paths.ROOT / "tools" / "build_report.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

BS = "\\"
NAME = "m0/s1.html"


def refreshed(s):
    """把片段中每個 span.num 的備用值換成目前 JSON 算出的值（不同電腦的版本、通過數不同時，測試仍可重現；M0 審查 R1）。"""
    def rep(m):
        out = B.fill_numbers(NAME, m.group(0), [], [])
        val = re.search(r">(.*?)</span>", out, re.S).group(1)
        return m.group(1) + val + "</span>"
    return re.sub(r'(<span class="num"[^>]*>).*?</span>', rep, s, flags=re.S)


FRAG = refreshed((paths.REPORT / "src" / "m0" / "s1.html").read_text(encoding="utf-8"))
NUM = re.search(r'<span class="num"[^>]*d\[\'passed\'\][^>]*>(.*?)</span>', FRAG).group(0)
NUM_VAL = re.search(r">(.*?)</span>", NUM).group(1)
cases = []


def run_checks(s):
    """依組裝順序跑片段層級的檢查，回傳 (錯誤, 更正, 處理後文字)。"""
    errors, notes, hist = [], [], []
    a = B.check_format(NAME, s, errors)
    s = B.fill_numbers(NAME, s, errors, notes)
    s = B.fill_code(NAME, s, errors)
    s = B.fill_history(NAME, s, errors, hist, a)
    s = B.fix_images(NAME, s, errors, "../")
    B.check_forbidden("m0.html", s, errors)
    return errors, notes, s


def mask(t):
    """存檔前遮蔽注入的禁字（例如本機路徑、工具名稱），否則結果檔本身會違反讀者文件規則（GitHub 匯出時發現）。"""
    for pat, _ in B.FORBIDDEN:
        t = re.sub(pat, lambda m: m.group(0)[0] + "＊" * (len(m.group(0)) - 1), t)
    return t


def case(name, injected, expect, ok, msgs):
    cases.append(dict(name=name, injected=mask(injected), expect=expect, passed=bool(ok),
                      messages=[mask(m) for m in msgs[:3]]))
    print(f"[{'通過' if ok else '失敗'}] {name}：{(msgs or ['（無訊息）'])[0]}")


def main():
    # 0. 原片段：不應有任何錯誤或更正
    e, n, _ = run_checks(FRAG)
    case("原片段不誤報", "無", "0 錯誤、0 更正", not e and not n, e + n)

    # 1. 少一節
    e, _, _ = run_checks(FRAG.replace("<h3>⑤ 常見錯誤與自我檢查</h3>", ""))
    case("缺少一節", "刪除 ⑤ 的標題", "報錯：六節不符", any("六節" in x for x in e), e)

    # 2. 兩節順序顛倒
    s = FRAG.replace("<h3>③ 動手做</h3>", "@@").replace("<h3>④ 結果與驗收</h3>", "<h3>③ 動手做</h3>").replace("@@", "<h3>④ 結果與驗收</h3>")
    e, _, _ = run_checks(s)
    case("兩節順序顛倒", "③ ④ 對調", "報錯：六節不符", any("六節" in x for x in e), e)

    # 3. 手寫數字與 JSON 不符 → 自動改成 JSON 的值（備用值改成一定不同的 999／999）
    e, n, out = run_checks(FRAG.replace(NUM, NUM.replace(f">{NUM_VAL}<", ">999／999<")))
    case("手寫數字過時", f"{NUM_VAL} 改成 999／999", f"以 JSON 值 {NUM_VAL} 輸出並提示",
         not e and any("999／999" in x for x in n) and f'<span class="num">{NUM_VAL}</span>' in out, n + e)

    # 4. JSON 鍵名打錯
    e, _, _ = run_checks(FRAG.replace("d['versions']['ipkiss']", "d['version']['ipkiss']", 1))
    case("JSON 鍵名打錯", "versions 寫成 version", "報錯：數字無法計算", any("無法計算" in x for x in e), e)

    # 5. 讀者文件禁字（本機路徑、非台灣用語、鋁的寫法、工具名稱）
    for word, why in (("D" + ":" + BS + "LAB" + BS + "x.py", "本機絕對路徑"), ("版" + "圖", "用「佈局」"),
                      ("Ti/A" + "l 墊", "鋁寫 AL"), ("Co" + "dex", "工具名稱"),
                      ("." + "cl" + "aude/tools", "工具名稱"),
                      ('Path("C:' + BS * 2 + "EDA" + BS * 2 + 'x")', "本機絕對路徑"),
                      (BS * 2 + "server" + BS + "share", "網路路徑"),
                      ("%USERPROFILE%" + BS + "x", "使用者環境變數路徑"),
                      ("LA" + "B06", "計畫代號")):
        e, _, _ = run_checks(FRAG.replace("</section>", f"<p>{word}</p></section>"))
        case(f"禁字：{why}", word, "報錯：禁字", any(why in x for x in e), e)

    # 6. 圖檔不存在
    e, _, _ = run_checks(FRAG.replace("s1_mmi_layout.png", "s1_missing.png"))
    case("圖檔不存在", "圖檔名打錯", "報錯：找不到圖", any("找不到圖" in x for x in e), e)

    # 7. 程式清單指到不存在的檔
    e, _, _ = run_checks(FRAG.replace("design/paths.py", "design/path.py"))
    case("程式檔不存在", "paths.py 寫成 path.py", "報錯：auto-code 找不到", any("auto-code" in x for x in e), e)

    # 8. 跨頁連結的錨點不存在
    page = paths.REPORT / "m0.html"
    e = []
    B.check_links({page: '<a href="appendix.html#app-z">x</a>', paths.REPORT / "appendix.html": '<h2 id="app-a">A</h2>'}, e)
    case("連結錨點不存在", "連到 appendix.html#app-z", "報錯：找不到錨點", any("找不到錨點" in x for x in e), e)

    # 9. PLAN 表格儲存格內的 \|（實作時真的遇到：|y2|² 被切成兩欄）
    rows = B.table_rows("## 測試表\n| a | b |\n|---|---|\n| P2 | \\|y2\\|² |\n", "測試表")
    case("表格儲存格含直線", "\\|y2\\|²", "解析為 2 欄，內容 |y2|²", rows == [["P2", "|y2|²"]], [str(rows)])

    # 10. 標題後面有附註的 PLAN 段落（實作時真的遇到：「## 符號表（全計畫共用…）」抓不到）
    rows = B.table_rows("## 符號表（附註）\n| a | b |\n|---|---|\n| x | y |\n", "符號表")
    case("段落標題含附註", "## 符號表（附註）", "仍能讀到表格", rows == [["x", "y"]], [str(rows)])

    # 11. 名詞先用後定義（使用者審閱時真的發現：M0 s1 寫了「MMI 是 B7 中每顆 MZI 的…」，此時還沒教 B7、MZI）
    _, steps, _, terms = B.read_plan()
    order = [st["id"] for st in steps]
    e = []
    B.check_terms({"m0-s1": FRAG.replace("<h3>② 原理與推導</h3>", "<h3>② 原理與推導</h3><p>MMI 是 B7 中每顆 MZI 的分光元件。</p>")},
                  order, terms, e)
    case("名詞先用後定義", "M0 s1 寫入 B7、MZI", "報錯：B7、MZI 尚未定義",
         any("「B7」" in x for x in e) and any("「MZI」" in x for x in e), e)
    e = []
    B.check_terms({"m0-s1": FRAG.replace("design/paths.py", "design/paths.py B7")}, order, terms, e)
    case("程式碼中的名詞不算", "只在 auto-code 屬性裡出現 B7", "不報錯", not e, e)

    # 12. 收折：③④⑤⑥ 包成 details，①② 保持展開（使用者 2026-10-30 要求）
    folded = B.fold_sections(FRAG, "m0-s1")
    ids = re.findall(r'<details class="sec" id="([^"]+)"', folded)
    ok = (ids == ["m0-s1-do", "m0-s1-result", "m0-s1-check", "m0-s1-code"]
          and "<h3>① 問題與範例</h3>" in folded and "<h3>② 原理與推導</h3>" in folded
          and folded.count("<details") == folded.count("</details>") and folded.rstrip().endswith("</section>"))
    case("③④⑤⑥ 預設收折", "組裝 M0 s1", "4 個收折節、①② 展開、標籤成對", ok, ids)

    # 13. 同頁錨點不存在（M0 審查 R4）
    e = []
    B.check_links({paths.REPORT / "m0.html": '<p id="a"></p><a href="#nope">x</a>'}, e)
    case("同頁錨點不存在", "連到 #nope", "報錯：同頁連結找不到錨點", any("同頁連結" in x for x in e), e)

    # 14. 索引的產生者比對：只認完整檔名，不被檔名片段誤判（M0 審查 R9）
    spec_m = importlib.util.spec_from_file_location("make_index", paths.ROOT / "tools" / "make_index.py")
    M = importlib.util.module_from_spec(spec_m)
    spec_m.loader.exec_module(M)
    names = M.output_names("輸出：out/env.json、out/mmi_test.gds、figures/m0/s1_mmi_layout.png（圖 M0-1）。")
    ok = names == {"env.json", "mmi_test.gds", "s1_mmi_layout.png"} and "mmi.gds" not in names
    case("產生者只認完整檔名", "過時檔 mmi.gds、s1.png", "不被當成有產生者", ok, [str(sorted(names))])

    result = dict(step="M0 s2", passed=sum(c["passed"] for c in cases), total=len(cases), cases=cases)
    out = paths.OUT("m0_env/s2_tools", "tool_tests.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{result['passed']}/{result['total']} 個案例通過，寫出 {rt.rel(out)}")
    sys.exit(0 if result["passed"] == result["total"] else 1)


if __name__ == "__main__":
    main()
