r"""M1 s5：只用交接檔重播——拿到 b7_netlist.json、phases.json、truth_tables.csv 的人，能不能自己算出同樣的結果？

用途：
  1. 不 import 本課程的任何模組，只依 b7_netlist.json 寫明的慣例重新實作 MZI 與 B7，確認交接檔「自足」：
     只靠三個檔案就能重算出同樣的結果。這證明交接檔完整、一致，不證明物理模型正確（模型的正確性由 M0 s1 的 PDK 對照負責）。
     檢查接線 SHA-256（不符就停下來，不往下算）、五個函數 80 組判讀、truth_tables.csv 的 ΔP、目標與判讀欄。
  2. 竄改測試：故意弄錯一件事，確認重播會失敗——
     (a) 交換 AND4 的 θ1、φ1；(b) 把 AND2 的相位拿來當 XOR2；(c) 把 MZI-6 移到波導 3、4（接線變了）；
     (d) 讀取埠 o2、o4 對調；(e) R 改成 2.9（參考光功率差 6.6%）；(f) θ 放在下臂（慣例弄錯）。
  3. 小實作：--func 名稱 --input 四個位元，印出該輸入的 y2、y4、P2、P4、ΔP 與判讀。
輸入：out/b7_netlist.json、out/phases.json、out/truth_tables.csv。
輸出：out/replay.json（核對與竄改測試結果）；用 --func 時只印出，不寫檔。
執行：.\lab design\m1_logic\s5_handoff\replay.py
      .\lab design\m1_logic\s5_handoff\replay.py --func XOR2 --input 1011
"""
import argparse
import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "out"


def mzi(theta, phi, theta_lower=False):
    """依 b7_netlist.json 的 mzi_convention：T＝H·diag(e^{iθ},1)·H·diag(e^{iφ},1)。
    theta_lower＝True 只給竄改測試 (f) 用：把 θ 錯放在下臂。"""
    H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    Dt = np.diag([1, np.exp(1j * theta)]) if theta_lower else np.diag([np.exp(1j * theta), 1])
    return H @ Dt @ H @ np.diag([np.exp(1j * phi), 1])


def b7(net, theta, phi, theta_lower=False):
    n = net["n_waveguides"]
    U = np.eye(n, dtype=complex)
    for k, m in sorted(enumerate(net["mzis"]), key=lambda t: t[1]["layer"]):   # 依層由左到右
        a, b = m["waveguides"][0] - 1, m["waveguides"][1] - 1
        E = np.eye(n, dtype=complex)
        E[np.ix_([a, b], [a, b])] = mzi(theta[k], phi[k], theta_lower)
        U = E @ U
    return U


def evaluate(net, ph, func, bits, read=("o2", "o4"), R=None, theta_lower=False):
    f = ph["functions"][func]
    v = np.array([int(c) for c in bits] + [ph["R"] if R is None else R], dtype=complex)
    y = b7(net, f["theta"], f["phi"], theta_lower) @ v
    idx = {o["name"]: o["index"] - 1 for o in net["outputs"]}
    P = np.abs(y) ** 2
    dP = float(P[idx[read[0]]] - P[idx[read[1]]])
    return y[idx[read[0]]], y[idx[read[1]]], float(P[idx[read[0]]]), float(P[idx[read[1]]]), dP


def target(func, bits):
    b = [int(c) for c in bits]
    return {"AND2": b[0] & b[1], "OR2": b[0] | b[1], "XOR2": b[0] ^ b[1],
            "AND4": int(all(b)), "OR4": int(any(b))}[func]


def load_csv():
    with open(OUT / "truth_tables.csv", encoding="utf-8-sig") as fh:
        return {(r["function"], r["x1"] + r["x2"] + r["x3"] + r["x4"]): r for r in csv.DictReader(fh)}


def score(net, ph, read=("o2", "o4"), **kw):
    """回傳 (判對組數, 總組數, 與真值表 ΔP 的最大差)；ΔP＝0 算判錯。
    只看判對組數抓不到「小錯」（例如 R 差 3%，margin 吸收掉了），所以同時比對 ΔP。"""
    table = load_csv()
    ok = n = 0
    err = 0.0
    for func in ph["functions"]:
        for k in range(16):
            bits = format(k, "04b")
            dP = evaluate(net, ph, func, bits, read, **kw)[4]
            ok += (dP > 0 and target(func, bits) == 1) or (dP < 0 and target(func, bits) == 0)
            n += 1
            err = max(err, abs(dP - float(table[(func, bits)]["dP"])))
    return ok, n, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--func")
    ap.add_argument("--input")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    net_bytes = (OUT / "b7_netlist.json").read_bytes()
    net = json.loads(net_bytes)
    ph = json.loads((OUT / "phases.json").read_text(encoding="utf-8"))

    if args.func:
        y2, y4, P2, P4, dP = evaluate(net, ph, args.func, args.input)
        bit = "邊界" if dP == 0 else int(dP > 0)
        print(f"{args.func}，輸入 {args.input}，R＝{ph['R']:g}")
        print(f"  y2＝{y2.real:+.3f}{y2.imag:+.3f}i → P2＝{P2:.3f}")
        print(f"  y4＝{y4.real:+.3f}{y4.imag:+.3f}i → P4＝{P4:.3f}")
        print(f"  ΔP＝{dP:+.3f} → 判讀 {bit}（目標 {target(args.func, args.input)}）")
        return

    sha_ok = hashlib.sha256(net_bytes).hexdigest() == ph["netlist_sha256"]
    if not sha_ok:                                   # 接線不是相位檔所搭配的版本：停下來，不往下算（M1 審查 R3）
        print("接線 SHA-256 與 phases.json 記錄的不符：這份相位不是給這份接線用的，停止重播。")
        sys.exit(1)
    ok, n, _ = score(net, ph)
    err, col_bad = 0.0, 0
    with open(OUT / "truth_tables.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            bits = r["x1"] + r["x2"] + r["x3"] + r["x4"]
            dP = evaluate(net, ph, r["function"], bits)[4]
            err = max(err, abs(dP - float(r["dP"])))
            col_bad += int(r["target"]) != target(r["function"], bits) or int(r["bit"]) != int(dP > 0)   # 目標與判讀欄也核對

    tamper = {}
    p = copy.deepcopy(ph)
    f = p["functions"]["AND4"]
    f["theta"][0], f["phi"][0] = f["phi"][0], f["theta"][0]
    tamper["a 交換 AND4 的 θ1、φ1"] = score(net, p)
    p = copy.deepcopy(ph)
    p["functions"]["XOR2"] = copy.deepcopy(ph["functions"]["AND2"])
    tamper["b AND2 的相位當 XOR2"] = score(net, p)
    nb = copy.deepcopy(net)
    nb["mzis"][5]["waveguides"] = [3, 4]
    nb_sha = hashlib.sha256((json.dumps(nb, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).hexdigest()
    tamper["c MZI-6 移到波導 3、4"] = score(nb, ph) + (nb_sha == ph["netlist_sha256"],)   # 正式重播會因 SHA 不符而停止；這裡強行計算看後果
    tamper["d 讀取埠 o2、o4 對調"] = score(net, ph, read=("o4", "o2"))
    tamper["e R 改成 2.9"] = score(net, ph, R=2.9)
    tamper["f θ 放在下臂"] = score(net, ph, theta_lower=True)

    res = dict(netlist_sha_ok=sha_ok, passed=ok, total=n, csv_max_dP_err=err, csv_target_bit_mismatch=col_bad,
               tamper={k: dict(passed=v[0], total=v[1], max_dP_diff=round(v[2], 6), **({"sha_match": v[3]} if len(v) > 3 else {}))
                       for k, v in tamper.items()})
    (OUT / "replay.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"接線 SHA-256 相符：{sha_ok}；重播 {ok}/{n}；與 truth_tables.csv 的 ΔP 最大差 {err:.1e}，目標／判讀欄不符 {col_bad} 列")
    for k, v in res["tamper"].items():
        extra = f"，SHA-256 相符：{v['sha_match']}" if "sha_match" in v else ""
        print(f"  竄改 {k}：{v['passed']}/{v['total']}，ΔP 與真值表最大差 {v['max_dP_diff']:.3f}{extra}")
    print("寫出 design/m1_logic/s5_handoff/out/replay.json")
    sys.exit(0 if sha_ok and ok == n and err < 1e-6 and col_bad == 0 else 1)     # CSV 的 ΔP 只存 6 位小數（捨入誤差 ≤ 5e-7）


if __name__ == "__main__":
    main()
