r"""交付檢查（M3 s5）：拿到交付包的人，用這支程式確認檔案完整、彼此一致、結果可以重算。

用途：只讀交付包本身（標準函式庫＋numpy），逐項檢查。集合一律和本程式寫死的完整清單比對：不只比數量，也比鍵；重複、缺少、多出、鍵打錯、
      空集合都算未通過；資料讀不到或缺欄位時該項判未通過，不會中斷其他項目。
  K1 檔案完整：MANIFEST.json 恰好列出固定的 18 個檔案（不重複），檔案都在、SHA-256 與大小相符，也沒有多出未列的檔案。
  K2 讀者文件：README、JSON、CSV、本程式不含本機路徑、計畫代號、工具名稱等禁字；固定清單裡的文字檔都要掃到。
  K3 README 章節：恰好 8 個固定標題，順序正確、不重複、每節有內容。
  K4 PAD 對照：pads.csv 恰好是 P01–P14 與 7 個 GND PAD，一列一個；14 個 heater 各有一個訊號 PAD，且與規格的 heater→PAD、MZI、相位相同；
     GND PAD 的 heater 欄（以 + 分隔）恰好涵蓋 14 個 heater 各一次，且與連接檢查的配對相同；座標與 chip_info.json 相同。
  K5 光學埠對照：optical_ports.csv 恰好是 in0–in4、out0–out4，一列一埠；埠名、訊號、方向與規格相同，輸入在西、輸出在東；端面座標與 chip_info.json 相同。
  K6 佈局版本：chip.gds 的 SHA-256 與 DRC、連接檢查結果、README 記錄的相同。
  K7 接線版本：接線表的 SHA-256 與相位設定檔、規格、README 記錄的相同；接線表恰好是 5 軌、7 顆 MZI、10 個埠，判讀埠為 o2、o4。
  K8 重算真值表：只用 b7_netlist.json 與 phases.json（本程式自己的矩陣運算）算 80 組 ΔP；truth_tables.csv 的鍵恰好是 5 個函數 × 16 組輸入，
     target 與函數定義相同，判讀與 target 全同、ΔP 差 < 1e-4。
  K9 驗證結果：DRC 0（30 條規則）、LVS 14 個 heater 全對且無錯誤、光學 10 個 EC 全對且無錯誤、固定的 8 種故障注入全部抓到、
     連接檢查、佈局審查、電路模擬的固定項目全部通過。
  K10（選用）重跑 DRC：有 KLayout 與平台 deck 時（--klayout、--deck）再跑一次，違規須為 0，且 30 條規則都要出現在報告裡；
     都沒提供時印「略過」；指定了卻找不到時判未通過。
  --self-test：先確認未改動的副本全部通過；再把交付包複製到暫存資料夾，逐一注入錯誤，對應的檢查都必須失敗。
     基本 10 種：改內容、刪檔、寫入本機路徑、對調 PAD、改相位、改 GDS、README 少一節、對調 EC、改接線表、驗證結果有違規。
     反向測試：刪一列、複製一列、空集合、缺故障案例、鍵打錯等。除了 K1 自己的案例，副本都已更新 MANIFEST（K1 必須仍通過），所以只能靠語意檢查攔下。
  可以自己重算的：K1、K4–K8、K10；K9 只能確認結果檔記錄的 LVS 與光學連接結果（重算需要課程的抽取程式）。
輸入：交付包資料夾（預設為本程式所在資料夾；在課程原始碼樹中執行時為根目錄的 delivery/）。
輸出：檢查結果（印出；--out 指定時另寫 JSON）。在課程原始碼樹中執行時寫 out/delivery_check.json。
執行：python check_delivery.py [交付包資料夾] [--self-test] [--klayout KLayout 執行檔 --deck DRC deck] [--out 結果.json]
      課程內：.\lab design\m3_layout\s5_delivery\check_delivery.py --self-test
"""
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import numpy as np

FORBIDDEN = [
    (r"(?<![A-Za-z])[A-Za-z]:(?:\\{1,2}|/)(?!/)[^\s<\"']*", "本機絕對路徑"),
    (r"(?<![\\\w])\\\\[A-Za-z][\w.$-]*\\[\w$]", "網路路徑"),
    (r"%[A-Za-z_]+%[\\/]", "環境變數路徑"),
    (r"(?i)(?<![A-Za-z])la[b][0]\d", "計畫代號"),
    (r"(?i)cl[a]ude|co[d]ex|gr[o]k", "工具名稱"),
    (r"版[圖]", "用「佈局」"),
    (r"(?<![A-Za-z])A[l](?![A-Za-z])", "鋁寫 AL"),
]
SECTIONS = ["## 1　晶片概要", "## 2　檔案", "## 3　光學介面", "## 4　電氣介面", "## 5　操作與校正（需求 K1）",
            "## 6　驗證結果", "## 7　已知限制與風險", "## 8　版本"]

# ---------- 這顆晶片的固定清單：完整集合寫在這裡，不從受檢的檔案推出來 ----------
REQUIRED_FILES = {"README.md", "check_delivery.py", "layout/chip.gds", "figures/chip.png", "figures/core.png", "figures/nets.png",
                  "interfaces/spec.json", "interfaces/tolerance.json", "interfaces/chip_info.json", "interfaces/pads.csv",
                  "interfaces/optical_ports.csv", "interfaces/b7_netlist.json", "interfaces/phases.json", "interfaces/truth_tables.csv",
                  "verification/drc_result.json", "verification/connectivity.json", "verification/review_checks.json",
                  "verification/sim_results.json"}
HEATER_PAD = {f"H{i:02d}": f"P{i:02d}" for i in range(1, 15)}         # 14 個 heater 與各自的訊號 PAD
GND_PADS = {"GN1", "GN2", "GN3", "GN4", "GN5", "GS1", "GS2"}
ALL_PADS = set(HEATER_PAD.values()) | GND_PADS
EC_SIGNAL = {"in0": "x1", "in1": "x2", "in2": "x3", "in3": "x4", "in4": "R",
             "out0": "o1", "out1": "o2", "out2": "o3", "out3": "o4", "out4": "o5"}
LOGIC = {"AND2": lambda a, b, c, d: a & b, "OR2": lambda a, b, c, d: a | b, "XOR2": lambda a, b, c, d: a ^ b,
         "AND4": lambda a, b, c, d: a & b & c & d, "OR4": lambda a, b, c, d: a | b | c | d}
WORDS = [format(w, "04b") for w in range(16)]
TT_KEYS = {(fn, w) for fn in LOGIC for w in WORDS}                    # 函數 × 16 個輸入＝80 個鍵
N_MZI = 7
N_DRC_RULES = 30
FAULTS = {"Ti/AL 短路", "Ti/AL 斷路", "TiN 斷路", "原理圖對調", "PAD 標記對調", "EC 標記對調", "DRC：Ti/AL 太窄", "DRC：TiN 太近"}
CONN_CHECKS = {"drc_clean", "one_gds99", "core_unchanged", "n_al_nets", "n_heaters", "lvs_clean", "every_heater_two_contacts",
               "optical_clean", "gnd_pairing", "faults_caught"}
REVIEW_PASS = {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V8b", "V9", "V10", "V11"}
REVIEW_DISPOSITION = {"P1", "P2", "P3"}                               # 沒有通過與否，要有處置說明
REVIEW_FAULTS = {"open", "short", "heater_swap"}
SIM_CHECKS = {"netlist_sha", "ops_from_netlist_match_common", "pdk_mmi_is_H", "all_80", "U_err_lt_1e12", "no_reflection", "energy",
              "symmetric_swap_harmless", "faults_caught", "nonideal_model_match"}
PAD_COLS = ["pad", "side", "x_um", "y_um", "x_die_um", "y_die_um", "role", "heater", "mzi", "phase"]
EC_COLS = ["ec", "signal", "core_port", "side", "facet_x_um", "facet_y_um", "x_die_um", "y_die_um", "use"]
TT_COLS = ["function", "x1", "x2", "x3", "x4", "target", "P2", "P4", "dP", "bit"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def J(d, rel):
    """嚴格讀 JSON：同一層的重複鍵（預設只留最後一個）與 NaN、Infinity 都算錯。"""
    def pairs(items):
        dup = [k for k, n in Counter(k for k, _ in items).items() if n > 1]
        if dup:
            raise ValueError(f"{rel} 有重複鍵 {dup}")
        return dict(items)

    def constant(c):
        raise ValueError(f"{rel} 含 {c}")
    return json.loads((d / rel).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def rows(d, rel):
    with open(d / rel, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def table(d, rel, cols):
    """讀 CSV，並要求欄名與順序完全相同、每列欄數相同。"""
    with open(d / rel, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != cols:
            raise ValueError(f"{rel} 欄名不符：{rd.fieldnames}")
        out = list(rd)
    if any(None in r or None in r.values() for r in out):
        raise ValueError(f"{rel} 有欄數不符的列")
    return out


def same_set(name, got, want):
    """got 必須和 want 完全相同（數量與鍵都比）；回傳問題清單，空的表示相符。"""
    count, want = Counter(list(got)), set(want)                       # got 可能是 dict：只數它的鍵
    dup = sorted(str(k) for k, n in count.items() if n > 1)
    lack = sorted(str(k) for k in want - set(count))
    more = sorted(str(k) for k in set(count) - want)
    return ([f"{name}重複 {dup[:3]}"] if dup else []) + ([f"{name}缺 {lack[:3]}（共 {len(lack)}）"] if lack else []) + \
           ([f"{name}多出 {more[:3]}"] if more else [])


def near(a, b, tol=1e-3):
    return abs(float(a) - float(b)) < tol                             # NaN 比較永遠為假，所以也算不符


def verdict(bad, text):
    return (not bad, text if not bad else text + "；" + "；".join(str(b) for b in bad[:4]))


def guarded(fn, *args):
    """一項檢查讀不到檔案或缺欄位時，判這一項未通過，其他項目照常跑。"""
    try:
        return fn(*args)
    except Exception as e:
        return False, f"資料不完整（{type(e).__name__}：{str(e)[:160]}）"


def replay(net, ph):
    """自己的矩陣運算：T(θ,φ)＝H·diag(e^{iθ},1)·H·diag(e^{iφ},1)，依層序相乘。"""
    H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    n = net["n_waveguides"]
    order = sorted(range(len(net["mzis"])), key=lambda k: net["mzis"][k]["layer"])
    read = [o["index"] - 1 for o in net["outputs"] if o["role"] == "判讀"]
    out = {}
    for fn, f in ph["functions"].items():
        U = np.eye(n, dtype=complex)
        for k in order:
            r = net["mzis"][k]["waveguides"][0] - 1
            T = H @ np.diag([np.exp(1j * f["theta"][k]), 1]) @ H @ np.diag([np.exp(1j * f["phi"][k]), 1])
            M = np.eye(n, dtype=complex)
            M[r:r + 2, r:r + 2] = T
            U = M @ U
        for w in range(16):
            bits = [int(c) for c in format(w, "04b")]
            v = np.array(bits + [ph["R"]], dtype=complex)
            P = np.abs(U @ v) ** 2
            out[(fn, "".join(map(str, bits)))] = float(P[read[0]] - P[read[1]])
    return out


def k1_files(d):
    entries = J(d, "MANIFEST.json")["files"]
    listed = {f["path"]: f for f in entries}
    actual = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts
              and p.name != "MANIFEST.json"} - {"layout/chip_drc.lyrdb"}          # K10 的暫存報告
    missing = sorted(k for k in listed if k not in actual)
    bad = [k for k in sorted(listed) if k in actual
           and (sha(d / k) != listed[k]["sha256"] or (d / k).stat().st_size != listed[k]["bytes"])]
    extra = sorted(actual - set(listed))
    ok, detail = verdict(same_set("清單", [f["path"] for f in entries], REQUIRED_FILES), f"缺 {missing}、雜湊不符 {bad}、多出 {extra}")
    return ok and not missing and not bad and not extra, detail


def k2_words(d):
    hits, seen = [], set()
    for p in sorted(d.rglob("*")):
        if p.suffix in (".md", ".json", ".csv", ".py") and p.is_file():
            seen.add(p.relative_to(d).as_posix())
            text = p.read_text(encoding="utf-8-sig", errors="replace")
            if p.name == Path(__file__).name:
                text = re.sub(r"(?ms)^FORBIDDEN = \[.*?^\]$", "", text)         # 只跳過本程式的禁字樣式本身
            for pat, why in FORBIDDEN:
                hits += [f"{p.relative_to(d).as_posix()}：{m.group(0)}（{why}）" for m in re.finditer(pat, text)]
    lack = sorted(f for f in REQUIRED_FILES if Path(f).suffix in (".md", ".json", ".csv", ".py") and f not in seen)
    return not hits and not lack, f"{hits[:5]}" + (f"；掃不到 {lack}" if lack else "")


def k3_readme(d):
    text = (d / "README.md").read_text(encoding="utf-8")
    found = re.findall(r"(?m)^## .*$", text)
    bad = same_set("章節", found, SECTIONS)
    if not bad and found != SECTIONS:
        bad.append("章節順序不符")
    body = re.split(r"(?m)^## .*$", text)[1:]
    bad += [f"{h} 沒有內容" for h, b in zip(found, body) if not b.strip()]
    return verdict(bad, f"{len(found)} 節")


def k4_pads(d):
    spec, chip, conn = J(d, "interfaces/spec.json"), J(d, "interfaces/chip_info.json"), J(d, "verification/connectivity.json")
    pads = table(d, "interfaces/pads.csv", PAD_COLS)
    chan = spec["phase_channels"]
    bad = same_set("規格的 heater", [c["heater"] for c in chan], HEATER_PAD)
    bad += [f"規格的 {c['heater']} 接 {c['pad']}" for c in chan if HEATER_PAD.get(c["heater"]) != c["pad"]]
    want = {c["heater"]: c for c in chan}
    sig = [r for r in pads if r["role"] == "訊號"]
    gnd = [r for r in pads if r["role"] == "地"]
    bad += [f"{r['pad']} 的角色是 {r['role']}" for r in pads if r["role"] not in ("訊號", "地")]
    bad += same_set("PAD 名稱", [r["pad"] for r in pads], ALL_PADS)
    bad += same_set("訊號 PAD 的 heater", [r["heater"] for r in sig], HEATER_PAD)
    bad += same_set("GND PAD", [r["pad"] for r in gnd], GND_PADS)
    differ = [r["heater"] for r in sig if r["heater"] not in want
              or (r["pad"], r["mzi"], r["phase"]) != tuple(want[r["heater"]][k] for k in ("pad", "mzi", "phase"))]
    bad += [f"與規格不符 {differ[:3]}"] if differ else []
    # 每個 heater 恰好出現在一個 GND PAD 的 heater 欄（以 + 分隔），也要和連接檢查抽出的配對相同
    bad += same_set("GND PAD 的 heater", [h for r in gnd for h in r["heater"].split("+")], HEATER_PAD)
    paired = {k: set(v) for k, v in conn["electrical"]["gnd_pairing"].items()}
    if {r["pad"]: set(r["heater"].split("+")) for r in gnd} != paired:
        bad.append("GND 配對與連接檢查不符")
    bad += same_set("chip_info 的 PAD", [p["name"] for p in chip["pads"]], ALL_PADS)
    at = {p["name"]: p for p in chip["pads"]}
    x0, y0 = chip["die_x_um"][0], chip["die_y_um"][0]
    moved = [r["pad"] for r in pads if r["pad"] not in at or r["side"] != {"N": "北", "S": "南"}.get(at[r["pad"]]["side"])
             or not near(r["x_um"], at[r["pad"]]["xy_um"][0]) or not near(r["y_um"], at[r["pad"]]["xy_um"][1])
             or not near(r["x_die_um"], at[r["pad"]]["xy_um"][0] - x0) or not near(r["y_die_um"], at[r["pad"]]["xy_um"][1] - y0)]
    bad += [f"座標或側邊與 chip_info 不符 {moved[:3]}"] if moved else []
    return verdict(bad, f"訊號 {len(sig)}、地 {len(gnd)}")


def k5_ports(d):
    spec, chip = J(d, "interfaces/spec.json"), J(d, "interfaces/chip_info.json")
    ecs = table(d, "interfaces/optical_ports.csv", EC_COLS)
    ports = spec["optical_ports"]
    bad = same_set("規格的埠", [o["port"] for o in ports], EC_SIGNAL)
    bad += [f"規格的 {o['port']} 不符" for o in ports if EC_SIGNAL.get(o["port"]) != o["signal"]
            or o["direction"] != ("輸入" if o["port"].startswith("in") else "輸出")]
    bad += same_set("EC 的埠", [e["core_port"] for e in ecs], EC_SIGNAL)
    sp = {o["port"]: o for o in ports}
    differ = [e["ec"] for e in ecs if e["core_port"] not in sp or e["signal"] != sp[e["core_port"]]["signal"]
              or e["ec"] != f"{e['signal']}_{e['core_port']}" or e["use"] != sp[e["core_port"]]["note"]
              or e["side"] != ("西" if sp[e["core_port"]]["direction"] == "輸入" else "東")]
    bad += [f"與規格不符 {differ[:3]}"] if differ else []
    bad += same_set("chip_info 的 EC", [e["port"] for e in chip["ec"]], EC_SIGNAL)
    at = {e["port"]: e for e in chip["ec"]}
    x0, y0 = chip["die_x_um"][0], chip["die_y_um"][0]
    moved = [e["ec"] for e in ecs if e["core_port"] not in at or {"W": "西", "E": "東"}.get(at[e["core_port"]]["side"]) != e["side"]
             or not near(e["facet_x_um"], at[e["core_port"]]["facet_um"][0]) or not near(e["facet_y_um"], at[e["core_port"]]["facet_um"][1])
             or not near(e["x_die_um"], at[e["core_port"]]["facet_um"][0] - x0) or not near(e["y_die_um"], at[e["core_port"]]["facet_um"][1] - y0)]
    bad += [f"座標或側邊與 chip_info 不符 {moved[:3]}"] if moved else []
    return verdict(bad, f"{len(ecs)} 個 EC")


def k6_layout(d):
    g = sha(d / "layout/chip.gds")
    recorded = {"DRC 結果": J(d, "verification/drc_result.json")["gds_sha256"],
                "連接檢查": J(d, "verification/connectivity.json")["gds_sha256"]}
    bad = [f"{k} 記錄的雜湊不同" for k, v in recorded.items() if v != g]
    bad += [] if g in (d / "README.md").read_text(encoding="utf-8") else ["README 記錄的雜湊不同"]
    return verdict(bad, g[:12])


def k7_netlist(d):
    net, ph, spec = J(d, "interfaces/b7_netlist.json"), J(d, "interfaces/phases.json"), J(d, "interfaces/spec.json")
    ns = sha(d / "interfaces/b7_netlist.json")
    bad = [f"{k} 記錄的雜湊不同" for k, v in (("相位設定檔", ph["netlist_sha256"]), ("規格", spec["source"]["netlist_sha256"])) if v != ns]
    bad += [] if ns in (d / "README.md").read_text(encoding="utf-8") else ["README 記錄的雜湊不同"]
    if net["n_waveguides"] != 5:
        bad.append(f"波導 {net['n_waveguides']} 軌")
    bad += same_set("MZI", [m["name"] for m in net["mzis"]], {f"MZI-{i}" for i in range(1, N_MZI + 1)})
    bad += [f"{m['name']} 的軌不相鄰" for m in net["mzis"] if len(m["waveguides"]) != 2 or m["waveguides"][1] != m["waveguides"][0] + 1
            or not 1 <= m["waveguides"][0] < net["n_waveguides"]]
    ends = [(p["layout_port"], p["signal"]) for p in net["inputs"]] + [(p["layout_port"], p["name"]) for p in net["outputs"]]
    bad += same_set("埠", ends, EC_SIGNAL.items())
    read = [o["name"] for o in net["outputs"] if o["role"] == "判讀"]
    if read != ["o2", "o4"] or net["readout"]["ports"] != read:
        bad.append(f"判讀埠 {read}")
    return verdict(bad, ns[:12])


def k8_truth(d):
    net, ph = J(d, "interfaces/b7_netlist.json"), J(d, "interfaces/phases.json")
    tt = table(d, "interfaces/truth_tables.csv", TT_COLS)
    bad = same_set("相位設定檔的函數", ph["functions"], LOGIC)
    bad += [f"{fn} 的 {k} 不是 {N_MZI} 個有限值" for fn, f in ph["functions"].items() for k in ("theta", "phi")
            if len(f[k]) != N_MZI or not all(math.isfinite(x) for x in f[k])]
    if bad:
        return False, f"0/{len(TT_KEYS)}；" + "；".join(bad[:4])
    bits = ("x1", "x2", "x3", "x4")
    odd = [i for i, r in enumerate(tt) if any(r[k] not in ("0", "1") for k in bits + ("target", "bit"))]
    keys = [(r["function"], "".join(r[k] for k in bits)) for r in tt]
    bad = same_set("（函數, 輸入）", keys, TT_KEYS) + ([f"位元欄有 {len(odd)} 列不是 0／1"] if odd else [])
    dp = replay(net, ph)
    good, errs = set(), []                                            # good 記鍵，不記列：同一列重複不會多算
    for i, (r, key) in enumerate(zip(tt, keys)):
        if i in odd or key not in dp:
            continue
        want = LOGIC[r["function"]](*(int(r[k]) for k in bits))
        if int(r["target"]) == int(r["bit"]) == want and (dp[key] > 0 if want else dp[key] < 0):
            good.add(key)
        errs.append(abs(dp[key] - float(r["dP"])))
    if good != TT_KEYS:
        bad.append("有判讀與函數定義不符的列")
    if not errs or not all(e < 1e-4 for e in errs):                   # 逐筆比：max() 會漏掉 NaN
        bad.append("ΔP 差超過 1e-4 或不是數字")
    if not all(near(float(r["P2"]) - float(r["P4"]), r["dP"], 1e-4) for r in tt):
        bad.append("P2−P4 與 dP 不符")
    err = max((e for e in errs if math.isfinite(e)), default=math.inf)
    return verdict(bad, f"{len(good)}/{len(TT_KEYS)}，ΔP 最大差 {err:.1e}")


def k9_results(d):
    drc_r, conn = J(d, "verification/drc_result.json"), J(d, "verification/connectivity.json")
    rev, sim = J(d, "verification/review_checks.json"), J(d, "verification/sim_results.json")
    die = J(d, "interfaces/chip_info.json")["die_um"]
    bad = []
    if type(drc_r["total"]) is not int or drc_r["total"] != 0 or drc_r["counts"] != {} or drc_r["outside"] != 0:
        bad.append(f"DRC 有違規（{drc_r['total']}、{drc_r['counts']}、區外 {drc_r['outside']}）")
    if drc_r["n_rules"] != N_DRC_RULES or len(drc_r["rules"]) != N_DRC_RULES or len(set(drc_r["rules"])) != N_DRC_RULES:
        bad.append(f"DRC 規則不是 {N_DRC_RULES} 條")
    if drc_r["n_gds99"] != 1 or drc_r["gds99_is_die"] is not True or drc_r["design_area_um"] != die:
        bad.append("DRC 的外框或設計區不符")
    fi = drc_r["fault_injection"]
    if not fi["caught"]:
        bad.append("DRC 故障注入沒有結果")
    bad += same_set("DRC 故障注入", fi["caught"], fi["counts"])

    e = conn["electrical"]
    if e["errors"] != []:
        bad.append(f"LVS 錯誤 {len(e['errors'])}")
    bad += same_set("LVS 的 heater", [c["heater"] for c in e["channels"]], HEATER_PAD)
    bad += same_set("LVS 的 PAD", e["pads"], ALL_PADS)
    bad += same_set("LVS 的 GND PAD", e["gnd_pads"], GND_PADS)
    bad += same_set("GND 配對的 PAD", e["gnd_pairing"], GND_PADS)
    bad += same_set("GND 配對的 heater", [h for hs in e["gnd_pairing"].values() for h in hs], HEATER_PAD)
    pair = {h: g for g, hs in e["gnd_pairing"].items() for h in hs}
    wrong = [c["heater"] for c in e["channels"] if c["ok"] is not True or c["contacts"] != 2
             or len(c["nets"]) != 2 or set(c["nets"]) != {HEATER_PAD.get(c["heater"]), pair.get(c["heater"])}]
    bad += [f"LVS 不符 {wrong[:3]}"] if wrong else []
    if e["al_nets"] != len(ALL_PADS) or e["tin_regions"] != len(HEATER_PAD):
        bad.append("LVS 抽出的網數不符")

    o = conn["optical"]
    if o["errors"] != []:
        bad.append(f"光學錯誤 {len(o['errors'])}")
    bad += same_set("光學 EC", [r["ec"] for r in o["ec"]], {f"{s}_{p}" for p, s in EC_SIGNAL.items()})
    wrong = [r["ec"] for r in o["ec"] if r["ok"] is not True or len(r["core_port"]) != 1
             or r["ec"] != f"{EC_SIGNAL.get(r['core_port'][0])}_{r['core_port'][0]}"
             or r["side"] != ("W" if r["core_port"][0].startswith("in") else "E")]
    bad += [f"光學不符 {wrong[:3]}"] if wrong else []

    bad += same_set("故障案例", conn["faults"], FAULTS)
    missed = [k for k, v in conn["faults"].items() if v is not True]
    bad += [f"故障沒抓到 {missed[:3]}"] if missed else []
    bad += same_set("連接檢查項目", conn["checks"], CONN_CHECKS)
    failed = [k for k, v in conn["checks"].items() if v is not True]
    bad += [f"連接檢查未通過 {failed[:3]}"] if failed else []
    n = conn["core_polygons"]
    if conn["core_sha_match"] is not True or len(n) != 2 or n[0] != n[1] or not n[0] > 0:
        bad.append("核心與審查版本不同")

    bad += same_set("審查項目", [c["id"] for c in rev["checks"]], REVIEW_PASS | REVIEW_DISPOSITION)
    failed = [c["id"] for c in rev["checks"] if (c["ok"] is not True if c["id"] in REVIEW_PASS else not c.get("disposition"))]
    bad += [f"審查未通過 {failed[:3]}"] if failed else []
    bad += same_set("審查的函數", rev["per_function"], LOGIC)
    bad += same_set("審查的故障案例", rev["faults"], REVIEW_FAULTS)
    if (rev["all_ok"] is not True or rev["passed"] != len(TT_KEYS) or not all(v["passed"] == len(WORDS) for v in rev["per_function"].values())
            or not all(v is True for v in rev["faults"].values())):
        bad.append(f"審查真值表 {rev['passed']}/{len(TT_KEYS)}")

    bad += same_set("模擬的函數", sim["functions"], LOGIC)
    bad += same_set("模擬檢查項目", sim["checks"], SIM_CHECKS)
    if (sim["passed"] != len(TT_KEYS) or sim["total"] != len(TT_KEYS) or not all(v is True for v in sim["checks"].values())
            or not all(v["passed"] == v["total"] == len(WORDS) for v in sim["functions"].values())):
        bad.append(f"模擬 {sim['passed']}/{sim['total']}")
    n_ec = len({r["ec"] for r in o["ec"] if r["ok"] is True} & {f"{s}_{p}" for p, s in EC_SIGNAL.items()})
    n_fault = sum(v is True for k, v in conn["faults"].items() if k in FAULTS)
    return verdict(bad, f"DRC {drc_r['total']}、LVS 錯誤 {len(e['errors'])}、光學 {n_ec}/{len(EC_SIGNAL)}、故障注入 {n_fault}/{len(FAULTS)}")


def k10_drc(d, klayout, deck):
    if not klayout and not deck:
        return None, "略過（未提供 KLayout 與平台 deck）"             # 略過不算通過，也不算失敗（M3 審查 R16）
    if not klayout or not deck or not Path(klayout).exists() or not Path(deck).exists():
        return False, "指定了重跑 DRC，但找不到 KLayout 或平台 deck"
    die = J(d, "interfaces/chip_info.json")["die_um"]
    gds = (d / "layout/chip.gds").resolve()
    rep = gds.with_name("chip_drc.lyrdb")
    try:
        subprocess.run([str(klayout), "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={rep}",
                        "-rd", f"dw={die[0]:g}", "-rd", f"dh={die[1]:g}"], check=True, capture_output=True)
        root = ET.parse(rep).getroot()
    finally:
        rep.unlink(missing_ok=True)
    tags = [(el.tag.split("}")[-1], el) for el in root.iter()]
    n = sum(1 for t, _ in tags if t == "item")
    ran = [c.text for t, el in tags if t == "category" for c in el if c.tag.split("}")[-1] == "name"]   # 違規項目裡的 category 沒有 name
    ok, detail = verdict(same_set("DRC 報告的規則", ran, J(d, "verification/drc_result.json")["rules"]),   # 空報告不算 0 違規
                         f"違規 {n}，{len(ran)} 條規則都有跑")
    return ok and n == 0, detail


def checks(d, klayout=None, deck=None):
    steps = (("K1 檔案完整", k1_files), ("K2 讀者文件禁字", k2_words), ("K3 README 章節", k3_readme), ("K4 PAD 對照", k4_pads),
             ("K5 光學埠對照", k5_ports), ("K6 佈局版本", k6_layout), ("K7 接線版本", k7_netlist), ("K8 重算真值表", k8_truth),
             ("K9 驗證結果", k9_results))
    res = {name: guarded(fn, d) for name, fn in steps}
    res["K10 重跑 DRC"] = guarded(k10_drc, d, klayout, deck)
    return res


def self_test(d, work):
    """注入錯誤：每一種都要讓對應的檢查失敗。除了 K1 自己的案例，其餘都更新 MANIFEST，K1 必須仍通過，證明攔下來的是語意檢查。"""
    PADS, ECS, TT = "interfaces/pads.csv", "interfaces/optical_ports.csv", "interfaces/truth_tables.csv"
    SPEC, PH, NET = "interfaces/spec.json", "interfaces/phases.json", "interfaces/b7_netlist.json"
    DRC, CONN = "verification/drc_result.json", "verification/connectivity.json"
    REV, SIM = "verification/review_checks.json", "verification/sim_results.json"
    K1, K2, K3, K4, K5 = "K1 檔案完整", "K2 讀者文件禁字", "K3 README 章節", "K4 PAD 對照", "K5 光學埠對照"
    K6, K7, K8, K9, K10 = "K6 佈局版本", "K7 接線版本", "K8 重算真值表", "K9 驗證結果", "K10 重跑 DRC"

    def fresh():
        t = Path(tempfile.mkdtemp(dir=work))
        shutil.copytree(d, t / "pkg")
        return t / "pkg"

    def remanifest(p, rel):
        m = J(p, "MANIFEST.json")
        for f in m["files"]:
            if f["path"] == rel:
                f["sha256"], f["bytes"] = sha(p / rel), (p / rel).stat().st_size
        (p / "MANIFEST.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")

    def text(rel, fn):                                                # 改文字，更新 MANIFEST
        def go(p):
            enc = "utf-8-sig" if rel.endswith(".csv") else "utf-8"
            (p / rel).write_text(fn((p / rel).read_text(encoding=enc)), encoding=enc)
            remanifest(p, rel)
        return go

    def tab(rel, fn):                                                 # 改 CSV 的列（fn 就地修改，或回傳新的列），更新 MANIFEST
        def go(p):
            with open(p / rel, encoding="utf-8-sig") as fh:
                head = next(csv.reader(fh))
            r = rows(p, rel)
            new = fn(r)
            with open(p / rel, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=head, lineterminator="\n")
                w.writeheader()
                w.writerows(new if isinstance(new, list) else r)
            remanifest(p, rel)
        return go

    def js(rel, fn):                                                  # 改 JSON（fn 就地修改），更新 MANIFEST
        def go(p):
            obj = J(p, rel)
            fn(obj)
            (p / rel).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            remanifest(p, rel)
        return go

    def man(fn):                                                      # 直接改 MANIFEST
        def go(p):
            m = J(p, "MANIFEST.json")
            fn(m, p)
            (p / "MANIFEST.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        return go

    def both(*fns):
        def go(p):
            for f in fns:
                f(p)
        return go

    def rename(obj, old, new):
        obj[new] = obj.pop(old)

    def flip_gds(p):
        b = bytearray((p / "layout/chip.gds").read_bytes())
        b[-10] ^= 0xFF
        (p / "layout/chip.gds").write_bytes(bytes(b))
        remanifest(p, "layout/chip.gds")

    def swap_pad(r):
        s = [x for x in r if x["role"] == "訊號"]
        s[0]["pad"], s[1]["pad"] = s[1]["pad"], s[0]["pad"]

    def swap_ec(r):
        r[0]["core_port"], r[1]["core_port"] = r[1]["core_port"], r[0]["core_port"]

    def drop_file(m, p):
        (p / "figures/chip.png").unlink()
        m["files"] = [f for f in m["files"] if f["path"] != "figures/chip.png"]

    def add_file(m, p):
        (p / "figures/extra.png").write_bytes(b"x")
        m["files"].append(dict(path="figures/extra.png", sha256=sha(p / "figures/extra.png"), bytes=1, source=""))

    def resync_netlist(p):                                            # 接線表改了，三處雜湊也跟著改
        ns = sha(p / NET)
        js(PH, lambda o: o.update(netlist_sha256=ns))(p)
        js(SPEC, lambda o: o["source"].update(netlist_sha256=ns))(p)
        text("README.md", lambda t: re.sub(r"(接線表 SHA-256：`)[0-9a-f]{64}", lambda m: m.group(1) + ns, t))(p)

    def swap_fn_phases(o):
        f = o["functions"]
        f["AND4"], f["OR4"] = f["OR4"], f["AND4"]

    def swap_fn_rows(r):
        for x in r:
            x["function"] = {"AND4": "OR4", "OR4": "AND4"}.get(x["function"], x["function"])

    basic = [
        ("改內容未更新 MANIFEST", K1, lambda p: (p / PADS).write_text((p / PADS).read_text(encoding="utf-8-sig") + "\n", encoding="utf-8-sig")),
        ("刪掉一個檔案", K1, lambda p: (p / "figures/chip.png").unlink()),
        ("README 寫入本機路徑", K2, text("README.md", lambda t: t + "\n原始檔在 " + "C" + ":" + "\\" + "work" + "\\" + "chip.gds\n")),
        ("PAD 對照對調", K4, tab(PADS, swap_pad)),
        ("相位被改", K8, js(PH, lambda o: o["functions"]["AND4"]["theta"].__setitem__(0, o["functions"]["AND4"]["theta"][0] + 1.0))),
        ("GDS 被改", K6, flip_gds),
        ("README 少一節", K3, text("README.md", lambda t: t.replace("## 5", "## 五"))),
        ("EC 對照對調", K5, tab(ECS, swap_ec)),
        ("接線表被改", K7, text(NET, lambda t: t + " ")),
        ("驗證結果有違規", K9, js(DRC, lambda o: o.update(total=1))),
    ]
    reverse = [
        # K1：清單本身
        ("刪檔並同時刪清單項", K1, man(drop_file)),
        ("多一個檔並列入清單", K1, man(add_file)),
        ("清單複製一項", K1, man(lambda m, p: m["files"].append(dict(m["files"][0])))),
        ("清單清空", K1, man(lambda m, p: m["files"].clear())),
        ("清單的鍵打錯", K1, man(lambda m, p: rename(m["files"][0], "sha256", "sha265"))),
        ("清單的大小不符", K1, man(lambda m, p: m["files"][0].update(bytes=1))),
        # K2、K3
        ("程式說明寫入本機路徑", K2, text("check_delivery.py", lambda t: "# " + "C" + ":" + "\\" + "work\n" + t)),
        ("README 章節重複", K3, text("README.md", lambda t: t + "\n## 8　版本\n\n重複\n")),
        ("README 多一節", K3, text("README.md", lambda t: t + "\n## 9　附錄\n\n多的\n")),
        ("README 章節沒有內容", K3, text("README.md", lambda t: re.sub(r"(?ms)(^## 7　[^\n]*\n).*?(?=^## 8)", r"\1", t))),
        # K4：PAD
        ("PAD 刪一列", K4, tab(PADS, lambda r: r.pop(0) and None)),
        ("PAD 複製一列", K4, tab(PADS, lambda r: r.__setitem__(0, dict(r[1])))),
        ("PAD 多一列重複", K4, tab(PADS, lambda r: r.append(dict(r[0])))),
        ("PAD 清空", K4, tab(PADS, lambda r: [])),
        ("GND PAD 全部刪除", K4, tab(PADS, lambda r: [x for x in r if x["role"] != "地"])),
        ("同一 heater 多一個 PAD", K4, tab(PADS, lambda r: r.insert(0, dict(next(x for x in r if x["heater"] == "H01"), pad="P99")))),
        ("多一列不明角色的 PAD", K4, tab(PADS, lambda r: r.append(dict(r[0], pad="X99", role="備用")))),
        ("PAD 的 heater 打錯", K4, tab(PADS, lambda r: next(x for x in r if x["heater"] == "H01").update(heater="H1"))),
        ("PAD 的角色打錯", K4, tab(PADS, lambda r: r[0].update(role="訊號線"))),
        ("PAD 欄名打錯", K4, text(PADS, lambda t: t.replace("heater", "heatr", 1))),
        ("GND 的 heater 重複", K4, tab(PADS, lambda r: next(x for x in r if x["pad"] == "GN1").update(heater="H01+H01"))),
        ("PAD 座標被改", K4, tab(PADS, lambda r: r[0].update(x_um="11.0"))),
        ("規格與 PAD 同時少 H14", K4, both(
            tab(PADS, lambda r: [dict(x, heater="H13") if x["pad"] == "GS2" else x for x in r if x["heater"] != "H14"]),
            js(SPEC, lambda o: o.update(phase_channels=[c for c in o["phase_channels"] if c["heater"] != "H14"])))),
        # K5：EC
        ("EC 第二筆複製成第一筆", K5, tab(ECS, lambda r: r.__setitem__(0, dict(r[1])))),
        ("EC 刪一列", K5, tab(ECS, lambda r: r.pop() and None)),
        ("EC 多一列重複", K5, tab(ECS, lambda r: r.append(dict(r[0])))),
        ("EC 清空", K5, tab(ECS, lambda r: [])),
        ("EC 埠名打錯", K5, tab(ECS, lambda r: r[0].update(core_port="inO"))),
        ("EC 欄名打錯", K5, text(ECS, lambda t: t.replace("core_port", "core_prot", 1))),
        ("EC 側邊打錯", K5, tab(ECS, lambda r: r[-1].update(side="北"))),
        ("EC 座標被改", K5, tab(ECS, lambda r: r[0].update(facet_y_um="441.0"))),
        ("規格與 EC 同時少 out4", K5, both(
            tab(ECS, lambda r: [x for x in r if x["core_port"] != "out4"]),
            js(SPEC, lambda o: o.update(optical_ports=[x for x in o["optical_ports"] if x["port"] != "out4"])))),
        # K6、K7
        ("連接檢查的 GDS 雜湊鍵打錯", K6, js(CONN, lambda o: rename(o, "gds_sha256", "gds_sha265"))),
        ("相位設定檔的雜湊鍵打錯", K7, js(PH, lambda o: rename(o, "netlist_sha256", "netlist_sha265"))),
        ("判讀埠被改且雜湊同步", K7, both(js(NET, lambda o: o["outputs"][2].update(role="判讀")), resync_netlist)),
        ("MZI 少一顆且雜湊同步", K7, both(js(NET, lambda o: o["mzis"].pop()), resync_netlist)),
        # K8：真值表
        ("真值表同一列重複 80 次", K8, tab(TT, lambda r: [dict(r[-1]) for _ in r])),
        ("真值表刪一列", K8, tab(TT, lambda r: r.pop() and None)),
        ("真值表複製一列", K8, tab(TT, lambda r: r.__setitem__(0, dict(r[1])))),
        ("真值表多一列重複", K8, tab(TT, lambda r: r.append(dict(r[0])))),
        ("真值表清空", K8, tab(TT, lambda r: [])),
        ("真值表函數名打錯", K8, tab(TT, lambda r: r[0].update(function="AND3"))),
        ("真值表欄名打錯", K8, text(TT, lambda t: t.replace("target", "targat", 1))),
        ("真值表位元放錯欄", K8, tab(TT, lambda r: r[0].update(x1="00", x2=""))),
        ("真值表的 ΔP 不是數字", K8, tab(TT, lambda r: r[5].update(dP="nan"))),
        ("真值表的 bit 與 target 不同", K8, tab(TT, lambda r: r[0].update(bit="1"))),
        ("AND4 與 OR4 對調（相位與真值表同時）", K8, both(js(PH, swap_fn_phases), tab(TT, swap_fn_rows))),
        ("少一個函數（相位與真值表同時）", K8, both(
            js(PH, lambda o: o["functions"].pop("XOR2")), tab(TT, lambda r: [x for x in r if x["function"] != "XOR2"]))),
        ("相位的 θ 少一個", K8, js(PH, lambda o: o["functions"]["AND2"]["theta"].pop())),
        # K9：驗證結果
        ("光學驗證列清空", K9, js(CONN, lambda o: o["optical"]["ec"].clear())),
        ("故障注入結果清空", K9, js(CONN, lambda o: o["faults"].clear())),
        ("光學與故障注入同時清空", K9, js(CONN, lambda o: (o["optical"]["ec"].clear(), o["faults"].clear()))),
        ("光學驗證刪一列", K9, js(CONN, lambda o: o["optical"]["ec"].pop())),
        ("光學驗證複製一列", K9, js(CONN, lambda o: o["optical"]["ec"].__setitem__(0, dict(o["optical"]["ec"][1])))),
        ("光學驗證的 EC 打錯", K9, js(CONN, lambda o: o["optical"]["ec"][0].update(ec="x1_inO"))),
        ("光學驗證的 ok 不是真值", K9, js(CONN, lambda o: o["optical"]["ec"][0].update(ok="yes"))),
        ("光學錯誤清單不是空的", K9, js(CONN, lambda o: o["optical"]["errors"].append("x1_in0 接錯"))),
        ("缺一個故障案例", K9, js(CONN, lambda o: o["faults"].pop("TiN 斷路"))),
        ("故障案例的鍵打錯", K9, js(CONN, lambda o: rename(o["faults"], "TiN 斷路", "TiN 短路"))),
        ("多一個未知的故障案例", K9, js(CONN, lambda o: o["faults"].update({"未知案例": True}))),
        ("一個故障案例沒抓到", K9, js(CONN, lambda o: o["faults"].update({"TiN 斷路": False}))),
        ("故障結果有重複鍵", K9, text(CONN, lambda t: re.sub(r'"faults":\s*\{', '"faults": {"TiN 斷路": false,', t, count=1))),
        ("頂層的 faults 鍵打錯", K9, js(CONN, lambda o: rename(o, "faults", "fault"))),
        ("heater 通道清空", K9, js(CONN, lambda o: o["electrical"]["channels"].clear())),
        ("heater 通道刪一列", K9, js(CONN, lambda o: o["electrical"]["channels"].pop())),
        ("heater 通道複製一列", K9, js(CONN, lambda o: o["electrical"]["channels"].__setitem__(0, dict(o["electrical"]["channels"][1])))),
        ("heater 通道的鍵打錯", K9, js(CONN, lambda o: o["electrical"]["channels"][0].update(heater="H1"))),
        ("連接檢查項目清空", K9, js(CONN, lambda o: o["checks"].clear())),
        ("連接檢查少一項", K9, js(CONN, lambda o: o["checks"].pop("lvs_clean"))),
        ("DRC 違規表與總數不一致", K9, js(DRC, lambda o: o["counts"].update({"某規則": 1}))),
        ("DRC 規則清單清空", K9, js(DRC, lambda o: o["rules"].clear())),
        ("佈局審查少一組", K9, js(REV, lambda o: o.update(passed=79))),
        ("佈局審查項目清空", K9, js(REV, lambda o: o["checks"].clear())),
        ("佈局審查少一個函數", K9, js(REV, lambda o: o["per_function"].pop("OR4"))),
        ("電路模擬少一組", K9, js(SIM, lambda o: o.update(passed=79))),
        ("電路模擬函數清空", K9, js(SIM, lambda o: o["functions"].clear())),
        ("電路模擬檢查少一項", K9, js(SIM, lambda o: o["checks"].pop("all_80"))),
        # K10
        ("指定的 KLayout 不存在", K10, lambda p: None, dict(klayout="不存在的程式", deck="不存在的 deck")),
    ]
    p = fresh()
    base = checks(p)
    shutil.rmtree(p.parent, ignore_errors=True)
    baseline = dict(ok=all(v[0] is not False for v in base.values()), failed=[k for k, v in base.items() if v[0] is False])
    out = {}
    for group, cases in (("基本", basic), ("反向", reverse)):
        for name, key, fn, *kw in cases:
            p = fresh()
            fn(p)
            r = checks(p, **(kw[0] if kw else {}))
            shutil.rmtree(p.parent, ignore_errors=True)
            out[name] = dict(check=key, caught=r[key][0] is False and (key == K1 or r[K1][0] is True), group=group,
                             detail=r[key][1] if r[K1][0] is True or key == K1 else f"K1 未通過：{r[K1][1]}")
    return out, baseline


def main():
    args = sys.argv[1:]
    here = Path(__file__).resolve().parent
    in_tree = not (here / "MANIFEST.json").exists() and (here.parents[2] / "delivery").exists()
    klayout = deck = out = None
    if "--klayout" in args:
        klayout = args[args.index("--klayout") + 1]
    if "--deck" in args:
        deck = args[args.index("--deck") + 1]
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--klayout", "--deck", "--out"))]
    if pos:
        d = Path(pos[0]).resolve()
    elif in_tree:                                                     # 在課程原始碼樹中：檢查根目錄的 delivery/，用課程設定的 KLayout 與 deck
        d = here.parents[2] / "delivery"
        sys.path.insert(0, str(here.parents[1]))
        import paths
        if paths.KLAYOUT_EXE.exists() and paths.DRC_DECK.exists():    # 這台電腦沒有時印「略過」；命令列指定的路徑找不到才算未通過
            klayout = klayout or paths.KLAYOUT_EXE
            deck = deck or paths.DRC_DECK
        if "--self-test" in args:                                     # 只有完整檢查（含自我測試）才寫入課程的結果檔（M3 審查 R1）
            out = out or paths.OUT("m3_layout/s5_delivery", "delivery_check.json")
    else:
        d = here
    sys.stdout.reconfigure(encoding="utf-8")
    res = checks(d, klayout, deck)
    for k, (ok, detail) in res.items():
        print(f"{'略過' if ok is None else ('通過' if ok else '未通過')}　{k}：{detail}")
    st = baseline = None
    if "--self-test" in args:
        work = Path(tempfile.mkdtemp())
        st, baseline = self_test(d, work)
        shutil.rmtree(work, ignore_errors=True)
        print(f"{'通過' if baseline['ok'] else '未通過'}　未改動的副本不誤報：{baseline['failed']}")
        for k, v in st.items():
            label = "故障注入" if v["group"] == "基本" else "反向測試"
            print(f"{'抓到' if v['caught'] else '漏掉'}　{label}「{k}」→ {v['check']}" + ("" if v["group"] == "基本" else f"：{v['detail'][:90]}"))
        print(f"自我測試 {sum(v['caught'] for v in st.values())}/{len(st)} 被檢出（基本 {sum(v['group'] == '基本' for v in st.values())}、"
              f"反向 {sum(v['group'] == '反向' for v in st.values())}）")
    allok = all(v[0] is not False for v in res.values()) and (st is None or (baseline["ok"] and all(v["caught"] for v in st.values())))
    if out:
        Path(out).write_text(json.dumps(dict(checks={k: dict(ok=v[0], detail=v[1]) for k, v in res.items()}, self_test=st, baseline=baseline,
                                             all_ok=allok), ensure_ascii=False, indent=2), encoding="utf-8")
    print("交付檢查全部通過" if allok else "交付檢查有未通過項目")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
