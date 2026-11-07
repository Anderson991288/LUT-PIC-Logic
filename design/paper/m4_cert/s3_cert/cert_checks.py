r"""論文 M4 s3 的判定邏輯：必要檢查與研究結果分開，不重算、不寫檔。

用途：
  cert.py 算完後用 compute_checks 產生 cert.json 的 checks，並用 required_failures 決定結束碼。
  唯讀驗證時從現有 cert.json 重新推導同一組 checks，與檔內保存值比對，不載入計算模組。
必要檢查（任一不成立即非零結束）：見 REQUIRED。另有結構檢查：函數、序列、葉數不可缺，避免 all() 在空集合上成立。
研究結果（只回報，真假都合法，不影響結束碼）：與草稿表 III 的差距；de Bruijn 序列下的窗是否仍 ≥ T_req。
輸入：design/paper/m4_cert/s3_cert/out/cert.json（或 --json 指定的檔）。
輸出：無檔案。結束碼 0 全部必要檢查通過，1 有失敗。
執行：.\lab design\paper\m4_cert\s3_cert\cert.py --verify（約 0.1 秒）
"""
import json
import sys
from pathlib import Path

CERT_JSON = Path(__file__).resolve().parent / "out" / "cert.json"
REQUIRED = {
    "all_above_treq": "情境序列單葉認證窗 ≥ T_req（表 III 認證欄的主張）",
    "below_sampled_scenario": "情境序列認證窗 ≤ 41 點模擬最小值（下界不得超過模擬）",
    "below_sampled_history": "de Bruijn 序列認證窗 ≤ 同序列 41 點模擬窗",
    "no_violation_history": "de Bruijn 序列下界 margin 在每個取樣相位都 ≤ 模擬 margin",
    "more_leaves_wider": "葉數增加時情境序列認證窗不得變窄",
}


def compute_checks(F, funcs, orders, t_req):
    """cert.json 的 checks。F 是 functions 字典；cert.py 的記憶體結果與讀回的 JSON 都走這一支。"""
    def nondecreasing(values):
        return all(b >= a for a, b in zip(values, values[1:]))

    return dict(
        all_above_treq=all(F[fn]["scenario"]["configs"]["1"]["window"] >= t_req for fn in funcs),
        below_sampled_scenario=all(c["window"] <= F[fn]["box_min"] for fn in funcs for c in F[fn]["scenario"]["configs"].values()),
        below_sampled_history=all(c["window"] <= F[fn][f"order{o}"]["sampled_window"]
                                  for fn in funcs for o in orders for c in F[fn][f"order{o}"]["configs"].values()),
        no_violation_history=all(c["margin_violation"] <= 0 for fn in funcs for o in orders for c in F[fn][f"order{o}"]["configs"].values()),
        more_leaves_wider=all(nondecreasing([c["window"] for c in F[fn]["scenario"]["configs"].values()]) for fn in funcs))


def required_failures(checks):
    """未通過的必要檢查（缺項也算）；只有布林 True 算通過。"""
    return [k for k in REQUIRED if checks.get(k) is not True]


def structure_failures(res):
    """cert.json 必須含草稿列出的全部函數，每個序列都有葉盒結果；否則 all() 會在空集合上成立。"""
    bad = []
    F = res.get("functions") or {}
    expected = set((res.get("draft") or {}).get("cert") or {})
    if not expected or set(F) != expected:
        bad.append(f"函數 {sorted(F)} 與草稿 {sorted(expected)} 不符")
    if not res.get("orders"):
        bad.append("orders 是空的")
    for fn, f in F.items():
        for key in ["scenario"] + [f"order{o}" for o in res.get("orders") or []]:
            configs = (f.get(key) or {}).get("configs") or {}
            want = len(res.get("leaf_bins") or []) if key == "scenario" else 2
            if len(configs) != want:
                bad.append(f"{fn} {key} 有 {len(configs)} 組葉盒，應為 {want}")
    if set(res.get("checks") or {}) != set(REQUIRED):
        bad.append(f"checks 項目與必要清單不同：{sorted(res.get('checks') or {})}")
    return bad


def evaluate(res):
    """從 cert.json 的內容判定：回傳 (failures, recomputed)。failures 空才算通過。"""
    failures = [f"結構：{x}" for x in structure_failures(res)]
    saved = res.get("checks") or {}
    try:
        recomputed = compute_checks(res["functions"], list(res["functions"]), res["orders"], res["t_req_ps"])
    except (KeyError, TypeError) as ex:
        return failures + [f"無法重新推導：{type(ex).__name__} {ex}"], {}
    failures += [f"必要檢查未通過（重新推導）：{k}" for k in required_failures(recomputed)]
    failures += [f"必要檢查未通過（保存值）：{k}" for k in required_failures(saved)]
    failures += [f"保存值與重新推導不同：{k}" for k in recomputed if k in saved and saved[k] != recomputed[k]]
    return failures, recomputed


def research_results(res):
    """研究結果：列出比較，不做判定。"""
    rows = []
    t_req = res["t_req_ps"]
    for fn, f in res["functions"].items():
        one = f["scenario"]["configs"]["1"]["window"]
        rows.append(f"{fn}：單葉 {one} ps，草稿 {f['draft_cert']} ps，差 {one - f['draft_cert']:+.1f} ps")
        for o in res["orders"]:
            for n, c in f[f"order{o}"]["configs"].items():
                rows.append(f"   B(16,{o}) {n} 葉：W＝{c['window']} ps，{'≥' if c['window'] >= t_req else '＜'} T_req {t_req} ps")
    return rows


def main(argv):
    path = Path(argv[argv.index("--json") + 1]) if "--json" in argv else CERT_JSON
    try:
        res = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        print(f"讀不到 {path}：{ex}")
        return 1
    failures, recomputed = evaluate(res)
    print(f"M4 s3 認證唯讀驗證：{path.name}（不重算、不寫檔）")
    for k, text in REQUIRED.items():
        print(f"  {'通過' if recomputed.get(k) is True else '失敗'}  {k}：{text}")
    print("研究結果（只回報，不影響結束碼）：")
    if recomputed:
        print("\n".join("  " + r for r in research_results(res)))
    for x in failures:
        print("失敗：" + x)
    print("結果：" + ("全部必要檢查通過" if not failures else f"{len(failures)} 項失敗"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
