r"""LUT4 s1：只用交接檔重播——拿到 lut4_netlist.json、phases.json、truth_tables.csv 的人，能不能自己算出同樣的結果？

用途：
  1. 不 import 本專案的任何模組，只依 lut4_netlist.json 寫明的慣例重新實作 MZI 與 3142132 光路，確認交接檔「自足」：
     接線 SHA-256 不符就停下來；七個函數 112 組判讀；truth_tables.csv 的 P2、P3、P4、Da、Db、目標與判讀欄逐列核對。
     這證明交接檔完整、一致，不證明物理模型正確（模型由 LUT4 s2 的 PDK 對照負責）。
  2. 竄改測試：故意弄錯一件事，確認重播會失敗——
     (a) XOR4 的 θ、φ 順序交換；(b) 改接線：MZI-7 移到波導 1、2；(c) 輸入改用 E± 場向量 1−2x（相位編碼，不是 OOK）；
     (d) 讀取埠 o2、o4 對調；(e) R 改成 2.9；(f) θ 放在下臂（慣例弄錯）；(g) AND2 的相位拿來當 XOR2；(h) 讀取埠 o4、o3 對調。
     「抓到」＝判讀不再 112/112，或與 truth_tables.csv 的 Da／Db 最大差 > 1e-4（R＝2.9 這類小錯裕量會吸收，只能靠數值核對抓）。
  3. 小實作：--func 名稱 --input 四個位元（x1x2x3x4），印出該輸入的 P2、P3、P4、Da、Db 與判讀。
輸入：out/lut4_netlist.json、out/phases.json、out/truth_tables.csv。
輸出：out/replay.json；用 --func 時只印出，不寫檔。
執行：.\lab design\lut4\s1_handoff\replay.py
      .\lab design\lut4\s1_handoff\replay.py --func XOR4 --input 1011
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
TOL = 1e-4          # CSV 只存 6 位小數；超過這個差就是模型不一樣

FUNCS = {           # 與交接檔獨立的邏輯定義（x1 為最低位元）
    "AND2": lambda a, b, c, d: a & b, "OR2": lambda a, b, c, d: a | b, "XOR2": lambda a, b, c, d: a ^ b,
    "NAND2": lambda a, b, c, d: 1 - (a & b), "AND4": lambda a, b, c, d: a & b & c & d,
    "XOR4": lambda a, b, c, d: a ^ b ^ c ^ d, "MUX": lambda a, b, c, d: b if c else a,
}


def mzi(theta, phi, amp, theta_lower=False):
    """依 lut4_netlist.json 的 mzi_convention：T＝a·H·diag(e^{iθ},1)·H·diag(e^{iφ},1)。theta_lower 只給竄改測試 (f) 用。"""
    H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    Dt = np.diag([1, np.exp(1j * theta)]) if theta_lower else np.diag([np.exp(1j * theta), 1])
    return amp * (H @ Dt @ H @ np.diag([np.exp(1j * phi), 1]))


def circuit(net, theta, phi, amp, theta_lower=False):
    n = net["n_waveguides"]
    U = np.eye(n, dtype=complex)
    for k, m in sorted(enumerate(net["mzis"]), key=lambda t: t[1]["layer"]):   # 依層由左到右；同層可交換
        a, b = m["waveguides"][0] - 1, m["waveguides"][1] - 1
        E = np.eye(n, dtype=complex)
        E[np.ix_([a, b], [a, b])] = mzi(theta[k], phi[k], amp, theta_lower)
        U = E @ U
    return U


def inputs(net, bits, R, encoding="ook"):
    """bits：'x1x2x3x4' 字串。OOK：振幅 0／1；'pm'：E±＝1−2x（竄改測試 (c)）。"""
    x = np.array([int(c) for c in bits], float)
    data = x if encoding == "ook" else 1 - 2 * x
    v = np.zeros(net["n_waveguides"], complex)
    for p in net["inputs"]:
        v[p["index"] - 1] = R if p["signal"] == "R" else data[int(p["signal"][1]) - 1]
    return v


def evaluate(net, ph, func, bits, read=None, R=None, theta_lower=False, encoding="ook"):
    f = ph["functions"][func]
    amp = 10 ** (-ph["loss_db_per_mzi"] / 20)
    v = inputs(net, bits, ph["R"] if R is None else R, encoding)
    E = circuit(net, f["theta"], f["phi"], amp, theta_lower) @ v
    P = np.abs(E) ** 2
    idx = {o["name"]: o["index"] - 1 for o in net["outputs"]}
    ports = read or net["readout"]["ports"]                     # ["o2", "o4", "o3"]
    Pa, Pb, Pc = (float(P[idx[p]]) for p in ports)
    Da, Db = Pa - Pb, Pb - Pc
    return dict(P2=float(P[idx["o2"]]), P3=float(P[idx["o3"]]), P4=float(P[idx["o4"]]), Da=Da, Db=Db, bit=int(Da > 0 and Db > 0))


def target(func, bits):
    b = [int(c) for c in bits]
    return int(FUNCS[func](*b))


def score(net, ph, table, **kw):
    """回傳 (判對組數, 總組數, 與 CSV 的 P／D 最大差)。"""
    ok = n = 0; err = 0.0
    for func in ph["functions"]:
        for q in range(16):
            bits = "".join(str(q >> b & 1) for b in range(4))
            r = evaluate(net, ph, func, bits, **kw)
            ok += r["bit"] == target(func, bits); n += 1
            row = table[(func, bits)]
            err = max(err, *(abs(r[k] - float(row[k])) for k in ("P2", "P3", "P4", "Da", "Db")))
    return ok, n, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--func"); ap.add_argument("--input")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    net_bytes = (OUT / "lut4_netlist.json").read_bytes()
    net = json.loads(net_bytes)
    ph = json.loads((OUT / "phases.json").read_text(encoding="utf-8"))
    if args.func:
        r = evaluate(net, ph, args.func, args.input)
        print(f"{args.func}，輸入 x1x2x3x4＝{args.input}，R＝{ph['R']:g}，每顆 MZI {ph['loss_db_per_mzi']:g} dB")
        print(f"  P2＝{r['P2']:.4f}  P4＝{r['P4']:.4f}  P3＝{r['P3']:.4f}")
        print(f"  Da＝P2−P4＝{r['Da']:+.4f}  Db＝P4−P3＝{r['Db']:+.4f} → 判讀 {r['bit']}（目標 {target(args.func, args.input)}）")
        return
    sha = hashlib.sha256(net_bytes).hexdigest()
    sha_ok = sha == ph["netlist_sha256"]
    if not sha_ok:
        print("接線 SHA-256 與 phases.json 記錄的不符：這份相位不是給這份接線用的，停止重播。"); sys.exit(1)
    with open(OUT / "truth_tables.csv", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    table = {(r["function"], r["x1"] + r["x2"] + r["x3"] + r["x4"]): r for r in rows}
    hex_ok = all(int(f["truth_hex"], 16) == sum(target(n, "".join(str(q >> b & 1) for b in range(4))) << q for q in range(16))
                 for n, f in ph["functions"].items())
    col_bad = sum(int(r["target"]) != target(r["function"], r["x1"] + r["x2"] + r["x3"] + r["x4"]) or
                  int(r["bit"]) != evaluate(net, ph, r["function"], r["x1"] + r["x2"] + r["x3"] + r["x4"])["bit"] for r in rows)
    ok, n, err = score(net, ph, table)

    tamper = {}
    p = copy.deepcopy(ph); f = p["functions"]["XOR4"]; f["theta"], f["phi"] = f["phi"], f["theta"]
    tamper["a XOR4 的 θ、φ 順序交換"] = score(net, p, table)
    nb = copy.deepcopy(net); nb["mzis"][6]["waveguides"] = [1, 2]
    nb_sha = hashlib.sha256((json.dumps(nb, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).hexdigest()
    tamper["b 改接線：MZI-7 移到波導 1、2"] = score(nb, ph, table) + (nb_sha == ph["netlist_sha256"],)
    tamper["c 輸入改用 E± 場向量 1−2x"] = score(net, ph, table, encoding="pm")
    tamper["d 讀取埠 o2、o4 對調"] = score(net, ph, table, read=["o4", "o2", "o3"])
    tamper["e R 改成 2.9"] = score(net, ph, table, R=2.9)
    tamper["f θ 放在下臂"] = score(net, ph, table, theta_lower=True)
    p = copy.deepcopy(ph); p["functions"]["XOR2"] = copy.deepcopy(ph["functions"]["AND2"])
    tamper["g AND2 的相位當 XOR2"] = score(net, p, table)
    tamper["h 讀取埠 o4、o3 對調"] = score(net, ph, table, read=["o2", "o3", "o4"])
    tam = {k: dict(passed=v[0], total=v[1], max_diff=float(v[2]), caught=bool(v[0] < v[1] or v[2] > TOL),
                   **({"sha_match": v[3]} if len(v) > 3 else {})) for k, v in tamper.items()}
    res = dict(netlist_sha256=sha, netlist_sha_ok=sha_ok, truth_hex_consistent=hex_ok, passed=ok, total=n, csv_max_diff=float(err),
               csv_target_bit_mismatch=col_bad, rows=len(rows), tamper=tam, all_tamper_caught=all(v["caught"] for v in tam.values()),
               convention="T = a·H·diag(e^{iθ},1)·H·diag(e^{iφ},1), H=[[1,i],[i,1]]/√2；列＝輸出、第 1 列／行＝上方軌；U＝T̂7⋯T̂1；OOK 0/1；"
                          "Da=P(o2)−P(o4)、Db=P(o4)−P(o3)，皆＞0 判 1")
    (OUT / "replay.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"接線 SHA-256 相符：{sha_ok}；truth_hex 與邏輯定義一致：{hex_ok}；重播 {ok}/{n}；與 truth_tables.csv 最大差 {err:.1e}；目標／判讀欄不符 {col_bad} 列（共 {len(rows)} 列）")
    for k, v in tam.items():
        extra = f"，SHA 相符：{v['sha_match']}" if "sha_match" in v else ""
        print(f"  竄改 {k}：{v['passed']}/{v['total']}，最大差 {v['max_diff']:.3f}，抓到：{v['caught']}{extra}")
    good = sha_ok and hex_ok and ok == n and err < 1e-6 and col_bad == 0 and res["all_tamper_caught"]
    print("結論：", "本次通過" if good else "本次未通過")
    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()
