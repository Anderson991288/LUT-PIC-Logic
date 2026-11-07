r"""交付檢查（LUT4 s7）：拿到交付包的人，用這支程式確認檔案完整、彼此一致、結果可以重算。

用途：只讀交付包本身（標準函式庫＋numpy），逐項檢查。集合一律和本程式寫死的完整清單比對：不只比數量，也比鍵；重複、缺少、多出、鍵打錯、
      空集合都算未通過；資料讀不到或缺欄位時該項判未通過，不會中斷其他項目。本包的輸入編碼是 OOK：資料光場 0／1。
  K1 檔案完整：MANIFEST.json 恰好列出固定的 22 個檔案（不重複），檔案都在、SHA-256 與大小相符，也沒有多出未列的檔案；gate 的鍵固定且全為 true。
  K2 讀者文件：README、JSON、CSV、本程式不含本機路徑、計畫代號、工具名稱等禁字；固定清單裡的文字檔都要掃到。
  K3 README：恰好 7 個固定標題，順序正確、不重複、每節有內容；記有 GDS 與接線表的 SHA-256；驗證句的數字與固定集合相同。
  K4 PAD 對照：pads.csv 恰好是 P01–P14 與 7 個 GND PAD，一列一個，共 21 列；14 個 heater 各有一個訊號 PAD，且與本程式固定的 heater→PAD、MZI、
     相位相同，規格也相同；GND PAD 的 heater 恰好涵蓋 14 個 heater 各一次，且與固定配對、連接檢查相同；座標與交付 GDS 裡 PAD 的文字標記相同。
  K5 光學埠對照：optical_ports.csv 恰好是 in0–in4、out0–out4，一列一埠，共 10 列；埠名、訊號、用途與規格相同，輸入在西、輸出在東；
     資料埠的用途說明是 OOK；端面座標與交付 GDS 裡 EC 的文字標記相同。
  K6 佈局版本：交付 GDS 的 SHA-256 等於本程式固定的值，也和 DRC、連接檢查記錄的相同；佈局審查記錄的核心 GDS 雜湊等於固定值。
  K7 接線版本：接線表的 SHA-256 等於本程式固定的值，也和相位設定檔、規格記錄的相同；接線表恰好是 5 軌、7 顆 MZI、10 個埠、拓樸 3142132，
     判讀埠為 o2、o4、o3，輸入振幅標示為 OOK。
  K8 重算真值表：只用接線表與 phases.json（本程式自己的矩陣運算，光場 0／1、R＝3、每顆 MZI 0.9 dB）算 112 組 P2、P3、P4；
     truth_tables.csv 的鍵恰好是 7 個函數 × 16 組輸入，target 與函數定義相同，判讀 y＝[Da＞0] AND [Db＞0] 與 target 全同，各欄差 ＜ 1e-5，
     每個函數的裕量與 phases.json 記錄的相同。
  K9 DRC：違規 0、區外 0、30 條規則、一個 GDS 99 外框且等於固定的晶片尺寸。
  K10 LVS：21 個 PAD、14 個 heater 全對且無錯誤；GND 配對、抽出的網數、核心未變動；連接檢查的固定項目全部通過。
  K11 光學：10 個 EC 全對且無錯誤。
  K12 故障注入：連接檢查 8 種、DRC 2 條規則、佈局審查 3 種、電路模擬 2 種，固定清單全部抓到。
  K13 佈局審查：V1–V8、V8b、V9–V11 全部通過，P1–P3 有處置說明；7 個函數各 16/16，共 112。
  K14 電路模擬：7 個函數各 16/16，passed＝total＝112；固定的檢查項目全部通過；裕量為正且與交接值相同。
  K15（選用）重跑 DRC：有 KLayout 與平台 deck 時（--klayout、--deck）再跑一次，違規須為 0，且 30 條規則都要出現在報告裡；
     都沒提供時印「略過」；指定了卻找不到時判未通過。
  --self-test：先確認未改動的副本全部通過；再把交付包複製到暫存資料夾，逐一注入錯誤，對應的檢查都必須失敗。
     基本：改內容、刪檔、寫入本機路徑、對調 PAD、改相位、改 GDS、README 少一節、對調 EC、改接線表、驗證結果有違規。
     反向：刪一列、複製一列、空集合、缺故障案例、鍵打錯等。除了 K1 自己的案例，副本都已重算 MANIFEST 的合法雜湊（K1 必須仍通過），所以只能靠語意檢查攔下。
  可以自己重算的：K1、K3–K8、K15；K9–K14 只能確認結果檔的紀錄（重算需要 PDK 與課程的抽取程式）。
輸入：交付包資料夾（預設為本程式所在資料夾；在課程原始碼樹中執行時為根目錄的 delivery_lut4/）。
輸出：檢查結果（印出；--out 指定時另寫 JSON）。在課程原始碼樹中加 --self-test 時寫 out/delivery_check.json。
執行：python check_delivery.py [交付包資料夾] [--self-test] [--klayout KLayout 執行檔 --deck DRC deck] [--out 結果.json]
      課程內：.\lab design\lut4\s7_delivery\check_delivery.py --self-test
"""
import csv
import hashlib
import json
import math
import re
import shutil
import struct
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
SECTIONS = ["## 1. 晶片", "## 2. 輸入", "## 3. 判讀", "## 4. 範例函數", "## 5. 驗證", "## 6. 校正與限制", "## 7. 檔案"]

# ---------- 這顆晶片的固定清單：完整集合寫在這裡，不從受檢的檔案推出來 ----------
ENCODING = "OOK"
GDS_SHA = "c6286b4caddee6daeef4cb6b51d74b2deadd85ccb48ce12c66f3ef13bdc1809f"            # 交付的晶片 GDS
CORE_SHA = "8c0dab016b6f297073c718a5bcd441523b01ff79c25a930a166fc55f486a3fb4"           # 佈局審查讀的核心 GDS
NET_SHA = "ece36c2a7d0a96a0353aed56c55cc953cbf89a4ca66fb6221e59d384e7a2a10a"            # 接線表
DATA_USE = "資料光 0／1"                                              # 資料埠的用途說明
INPUT_AMP = "0／1（√P_u）"                                            # 接線表的資料振幅標示
GDS_FILE = "layout/LUT4_chip.gds"
REQUIRED_FILES = {"README.md", "check_delivery.py", GDS_FILE, "figures/s1_core.png", "figures/s3_chip.png", "figures/s3_ec.png", "figures/s3_route.png",
                  "function/lut4_netlist.json", "function/phases.json", "function/tolerance.json", "function/truth_tables.csv",
                  "interfaces/optical_ports.csv", "interfaces/pads.csv", "interfaces/spec.json", "interfaces/system_requirements.json",
                  "verification/connectivity.json", "verification/drc_result.json", "verification/gain_box.json", "verification/gain_robust.json",
                  "verification/gnd_segments.json", "verification/review_checks.json", "verification/sim_results.json"}
GATE_KEYS = {"drc", "lvs", "gds_sha", "optical", "faults", "sim", "review", "delivery_check"}
N_MZI = 7
TOPOLOGY = "3142132"
LAYERS = [1, 1, 2, 2, 3, 3, 4]                                        # MZI-1…MZI-7 所在的層
HEATERS = {}                                                          # H01–H14 → (訊號 PAD, MZI, 相位)；奇數號 θ、偶數號 φ
for _k in range(1, N_MZI + 1):
    HEATERS[f"H{2 * _k - 1:02d}"] = (f"P{2 * _k - 1:02d}", f"MZI-{_k}", f"θ{_k}")
    HEATERS[f"H{2 * _k:02d}"] = (f"P{2 * _k:02d}", f"MZI-{_k}", f"φ{_k}")
GND_PAIRING = {"GN1": {"H02", "H04"}, "GN2": {"H01", "H03"}, "GN3": {"H07", "H08"}, "GN4": {"H10", "H12"}, "GN5": {"H09", "H11"},
               "GN6": {"H13", "H14"}, "GS1": {"H05", "H06"}}
GND_PADS = set(GND_PAIRING)
SIGNAL_PADS = {v[0] for v in HEATERS.values()}
ALL_PADS = SIGNAL_PADS | GND_PADS                                     # 21 個
EC_SIGNAL = {"in0": "x1", "in1": "x2", "in2": "x3", "in3": "x4", "in4": "R",
             "out0": "o1", "out1": "o2", "out2": "o3", "out3": "o4", "out4": "o5"}
EC_NAMES = {f"{s}_{p}" for p, s in EC_SIGNAL.items()}
EC_LABEL_DX, EC_LABEL_DY = 40.0, 15.0                                 # EC 文字標記相對端面：往晶片內 40 µm、往上 15 µm
TOP_CELL = "L4_CHIP"
DIE = [4280.0, 1200.0]
LOGIC = {"AND2": lambda a, b, c, d: a & b, "OR2": lambda a, b, c, d: a | b, "XOR2": lambda a, b, c, d: a ^ b,
         "NAND2": lambda a, b, c, d: 1 - (a & b), "AND4": lambda a, b, c, d: a & b & c & d, "XOR4": lambda a, b, c, d: a ^ b ^ c ^ d,
         "MUX": lambda a, b, c, d: b if c else a}
TRUTH_HEX = {"AND2": "0x8888", "OR2": "0xEEEE", "XOR2": "0x6666", "NAND2": "0x7777", "AND4": "0x8000", "XOR4": "0x6996", "MUX": "0xCACA"}
WORDS = ["".join(str(w >> b & 1) for b in range(4)) for w in range(16)]   # x1 x2 x3 x4，x1 是真值表索引的最低位
TT_KEYS = {(fn, w) for fn in LOGIC for w in WORDS}                    # 函數 × 16 個輸入＝112 個鍵
R_AMP = 3.0
LOSS_DB = 0.9
N_DRC_RULES = 30
N_CORE_POLYGONS = 226
FAULTS = {"Ti/AL 短路", "Ti/AL 斷路", "TiN 斷路", "原理圖對調", "PAD 標記對調", "EC 標記對調", "DRC：Ti/AL 太窄", "DRC：TiN 太近"}
DRC_FAULTS = {"Minimum gap violate (GDS39<10micro)", "Minimum feature size violate (GDS41<2micro)"}
CONN_CHECKS = {"drc_clean", "one_gds99", "core_unchanged", "n_al_nets", "n_heaters", "lvs_clean", "every_heater_two_contacts",
               "optical_clean", "gnd_pairing", "gnd_model_matches_gds", "faults_caught"}
REVIEW_PASS = {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V8b", "V9", "V10", "V11"}
REVIEW_DISPOSITION = {"P1", "P2", "P3"}                               # 沒有通過與否，要有處置說明
REVIEW_FAULTS = {"open", "short", "heater_swap"}
SIM_CHECKS = {"pdk_U_match", "lossy_U_match", "no_reflection", "all_pass", "faults_caught"}
SIM_FAULTS = {"swap_out", "phi_low"}
PAD_COLS = ["pad", "side", "x_um", "y_um", "kind", "heater", "mzi", "phase", "heaters_on_gnd"]
EC_COLS = ["port", "signal", "edge", "facet_x_um", "facet_y_um", "use"]
TT_COLS = ["function", "x1", "x2", "x3", "x4", "target", "P2", "P3", "P4", "Da", "Db", "bit"]


def field(bits):
    """OOK：位元直接是資料光場，0＝無光、1＝有光。"""
    return [float(b) for b in bits]


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


def gds_labels(d):
    """讀交付 GDS 頂層 cell 的文字標記：{字串: (x_um, y_um)}。同一個字串出現兩次算錯。"""
    data = (d / GDS_FILE).read_bytes()
    i, cell, el, um, out = 0, None, None, None, {}
    while i + 4 <= len(data):
        n = int.from_bytes(data[i:i + 2], "big")
        code = int.from_bytes(data[i + 2:i + 4], "big")
        p = data[i + 4:i + n]
        if n < 4 or code == 0x0400:
            break
        if code == 0x0305:                                            # UNITS：第二個實數是資料庫單位（公尺）
            b = p[8:16]
            um = int.from_bytes(b[1:], "big") / float(1 << 56) * 16.0 ** ((b[0] & 0x7F) - 64) / 1e-6
        elif code == 0x0606:
            cell = p.rstrip(b"\0").decode("ascii")
        elif code == 0x0C00:
            el = {}
        elif el is not None and code == 0x1003:
            el["xy"] = struct.unpack(">2i", p[:8])
        elif el is not None and code == 0x1906:
            el["s"] = p.rstrip(b"\0").decode("ascii")
        elif code == 0x1100:
            if el is not None and cell == TOP_CELL:
                if el["s"] in out:
                    raise ValueError(f"GDS 標記 {el['s']} 重複")
                out[el["s"]] = (el["xy"][0] * um, el["xy"][1] * um)
            el = None
        i += n
    return out


def replay(net, ph, enc=field):
    """自己的矩陣運算：T(θ,φ)＝a·H·diag(e^{iθ},1)·H·diag(e^{iφ},1)，依層序相乘；回傳 {(函數, 輸入): (P2, P3, P4)}。"""
    H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    a = 10 ** (-ph["loss_db_per_mzi"] / 20)
    n = net["n_waveguides"]
    order = sorted(range(len(net["mzis"])), key=lambda k: net["mzis"][k]["layer"])
    out = {}
    for fn, f in ph["functions"].items():
        U = np.eye(n, dtype=complex)
        for k in order:
            r = net["mzis"][k]["waveguides"][0] - 1
            T = a * H @ np.diag([np.exp(1j * f["theta"][k]), 1]) @ H @ np.diag([np.exp(1j * f["phi"][k]), 1])
            M = np.eye(n, dtype=complex)
            M[r:r + 2, r:r + 2] = T
            U = M @ U
        for w in WORDS:
            P = np.abs(U @ np.array(enc([int(c) for c in w]) + [ph["R"]], dtype=complex)) ** 2
            out[(fn, w)] = (float(P[1]), float(P[2]), float(P[3]))
    return out


def k1_files(d):
    m = J(d, "MANIFEST.json")
    entries = m["files"]
    listed = {f["path"]: f for f in entries}
    actual = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts
              and p.name != "MANIFEST.json"} - {"layout/chip_drc.lyrdb"}          # K15 的暫存報告
    missing = sorted(k for k in listed if k not in actual)
    bad = [k for k in sorted(listed) if k in actual
           and (sha(d / k) != listed[k]["sha256"] or (d / k).stat().st_size != listed[k]["bytes"])]
    extra = sorted(actual - set(listed))
    problems = same_set("清單", [f["path"] for f in entries], REQUIRED_FILES)
    problems += same_set("gate", m["gate"], GATE_KEYS)
    problems += [f"gate 未通過 {k}" for k, v in m["gate"].items() if v is not True]
    ok, detail = verdict(problems, f"缺 {missing}、雜湊不符 {bad}、多出 {extra}")
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
    bad += [f"沒有記錄 {what} 的 SHA-256" for what, h in (("GDS", GDS_SHA), ("接線表", NET_SHA)) if h not in text]
    want = (f"{len(TT_KEYS)}/{len(TT_KEYS)}", "V1–V11 通過", "DRC 違規 0", f"LVS {len(HEATERS)}/{len(HEATERS)}", f"光學 {len(EC_SIGNAL)}/{len(EC_SIGNAL)}",
            "故障注入全部抓到", "check_delivery.py")
    bad += [f"驗證敘述沒有「{w}」" for w in want if w not in text]
    return verdict(bad, f"{len(found)} 節")


def k4_pads(d):
    spec, conn = J(d, "interfaces/spec.json"), J(d, "verification/connectivity.json")
    pads = table(d, "interfaces/pads.csv", PAD_COLS)
    chan = spec["phase_channels"]
    bad = same_set("規格的 heater", [c["heater"] for c in chan], HEATERS)
    bad += [f"規格的 {c['heater']} 不符" for c in chan if HEATERS.get(c["heater"]) != (c["pad"], c["mzi"], c["phase"])]
    sig = [r for r in pads if r["kind"] == "訊號"]
    gnd = [r for r in pads if r["kind"] == "GND"]
    bad += [f"{r['pad']} 的種類是 {r['kind']}" for r in pads if r["kind"] not in ("訊號", "GND")]
    bad += same_set("PAD 名稱", [r["pad"] for r in pads], ALL_PADS)
    bad += same_set("訊號 PAD 的 heater", [r["heater"] for r in sig], HEATERS)
    bad += same_set("GND PAD", [r["pad"] for r in gnd], GND_PADS)
    differ = [r["pad"] for r in sig if HEATERS.get(r["heater"]) != (r["pad"], r["mzi"], r["phase"]) or r["heaters_on_gnd"]]
    bad += [f"訊號 PAD 與固定對照不符 {differ[:3]}"] if differ else []
    differ = [r["pad"] for r in gnd if r["heater"] or r["mzi"] or r["phase"]]
    bad += [f"GND PAD 不應有 heater、MZI、相位 {differ[:3]}"] if differ else []
    # 每個 heater 恰好出現在一個 GND PAD，也要和固定配對、連接檢查抽出的配對相同
    bad += same_set("GND PAD 的 heater", [h for r in gnd for h in r["heaters_on_gnd"].split("＋")], HEATERS)
    if {r["pad"]: set(r["heaters_on_gnd"].split("＋")) for r in gnd} != GND_PAIRING:
        bad.append("GND 配對與固定配對不符")
    if {k: set(v) for k, v in conn["electrical"]["gnd_pairing"].items()} != GND_PAIRING:
        bad.append("GND 配對與連接檢查不符")
    at = gds_labels(d)
    moved = [r["pad"] for r in pads if r["pad"] not in at or not near(r["x_um"], at[r["pad"]][0]) or not near(r["y_um"], at[r["pad"]][1])
             or r["side"] != ("N" if at[r["pad"]][1] > 0 else "S")]
    bad += [f"座標或側邊與 GDS 標記不符 {moved[:3]}"] if moved else []
    return verdict(bad, f"訊號 {len(sig)}、GND {len(gnd)}")


def k5_ports(d):
    spec = J(d, "interfaces/spec.json")
    ecs = table(d, "interfaces/optical_ports.csv", EC_COLS)
    ports = spec["optical_ports"]
    bad = same_set("規格的埠", [o["port"] for o in ports], EC_SIGNAL)
    bad += [f"規格的 {o['port']} 不符" for o in ports if EC_SIGNAL.get(o["port"]) != o["signal"]
            or o["direction"] != ("輸入" if o["port"].startswith("in") else "輸出")]
    bad += same_set("EC 的埠", [e["port"] for e in ecs], EC_SIGNAL)
    sp = {o["port"]: o for o in ports}
    differ = [e["port"] for e in ecs if e["port"] not in sp or e["signal"] != sp[e["port"]]["signal"] or e["use"] != sp[e["port"]]["note"]
              or e["edge"] != ("W" if sp[e["port"]]["direction"] == "輸入" else "E")]
    bad += [f"與規格不符 {differ[:3]}"] if differ else []
    wrong = [e["port"] for e in ecs if e["signal"] in ("x1", "x2", "x3", "x4") and e["use"] != DATA_USE]
    bad += [f"資料埠的用途不是 {ENCODING} {wrong[:3]}"] if wrong else []
    at = gds_labels(d)
    moved = []
    for e in ecs:
        lab = at.get(f"{e['signal']}_{e['port']}")
        dx = EC_LABEL_DX if e["edge"] == "W" else -EC_LABEL_DX
        if lab is None or not near(e["facet_x_um"], lab[0] - dx) or not near(e["facet_y_um"], lab[1] - EC_LABEL_DY):
            moved.append(e["port"])
    bad += [f"座標與 GDS 標記不符 {moved[:3]}"] if moved else []
    bad += same_set("GDS 的文字標記", at, ALL_PADS | EC_NAMES)
    return verdict(bad, f"{len(ecs)} 個 EC")


def k6_layout(d):
    g = sha(d / GDS_FILE)
    recorded = {"DRC 結果": J(d, "verification/drc_result.json")["gds_sha256"],
                "連接檢查": J(d, "verification/connectivity.json")["gds_sha256"]}
    bad = [] if g == GDS_SHA else ["GDS 與固定的雜湊不同"]
    bad += [f"{k} 記錄的雜湊不同" for k, v in recorded.items() if v != g]
    if J(d, "verification/review_checks.json")["gds_sha256"] != CORE_SHA:
        bad.append("佈局審查的核心 GDS 雜湊不同")
    return verdict(bad, g[:12])


def k7_netlist(d):
    net, ph, spec = J(d, "function/lut4_netlist.json"), J(d, "function/phases.json"), J(d, "interfaces/spec.json")
    ns = sha(d / "function/lut4_netlist.json")
    bad = [] if ns == NET_SHA else ["接線表與固定的雜湊不同"]
    bad += [f"{k} 記錄的雜湊不同" for k, v in (("相位設定檔", ph["netlist_sha256"]), ("規格", spec["source"]["netlist_sha256"])) if v != ns]
    if net["n_waveguides"] != 5 or net["topology"] != TOPOLOGY:
        bad.append(f"波導 {net['n_waveguides']} 軌、拓樸 {net['topology']}")
    bad += same_set("MZI", [m["name"] for m in net["mzis"]], {f"MZI-{i}" for i in range(1, N_MZI + 1)})
    if [m["name"] for m in net["mzis"]] != [f"MZI-{i}" for i in range(1, N_MZI + 1)]:
        bad.append("MZI 順序不符")
    want = [([int(c), int(c) + 1], layer) for c, layer in zip(TOPOLOGY, LAYERS)]
    if [(m["waveguides"], m["layer"]) for m in net["mzis"]] != want:
        bad.append("MZI 的軌或層與拓樸不符")
    ends = [(p["layout_port"], p["signal"]) for p in net["inputs"]] + [(p["layout_port"], p["name"]) for p in net["outputs"]]
    bad += same_set("埠", ends, EC_SIGNAL.items())
    read = [o["name"] for o in net["outputs"] if "判讀" in o["role"]]
    if sorted(read) != ["o2", "o3", "o4"] or net["readout"]["ports"] != ["o2", "o4", "o3"]:
        bad.append(f"判讀埠 {read}")
    wrong = [p["signal"] for p in net["inputs"] if p["signal"] != "R" and p["amplitude"] != INPUT_AMP]
    bad += [f"輸入振幅不是 {ENCODING} {wrong[:3]}"] if wrong else []
    return verdict(bad, ns[:12])


def k8_truth(d):
    net, ph = J(d, "function/lut4_netlist.json"), J(d, "function/phases.json")
    tt = table(d, "function/truth_tables.csv", TT_COLS)
    bad = same_set("相位設定檔的函數", ph["functions"], LOGIC)
    bad += [f"{fn} 的 {k} 不是 {N_MZI} 個有限值" for fn, f in ph["functions"].items() for k in ("theta", "phi")
            if len(f[k]) != N_MZI or not all(math.isfinite(x) for x in f[k])]
    bad += [f"{fn} 的 truth_hex 不是 {TRUTH_HEX.get(fn)}" for fn, f in ph["functions"].items() if f["truth_hex"] != TRUTH_HEX.get(fn)]
    if ph["R"] != R_AMP or ph["loss_db_per_mzi"] != LOSS_DB:
        bad.append(f"R {ph['R']}、損耗 {ph['loss_db_per_mzi']} 不是固定值")
    if bad:
        return False, f"0/{len(TT_KEYS)}；" + "；".join(bad[:4])
    bits = ("x1", "x2", "x3", "x4")
    odd = [i for i, r in enumerate(tt) if any(r[k] not in ("0", "1") for k in bits + ("target", "bit"))]
    keys = [(r["function"], "".join(r[k] for k in bits)) for r in tt]
    bad = same_set("（函數, 輸入）", keys, TT_KEYS) + ([f"位元欄有 {len(odd)} 列不是 0／1"] if odd else [])
    P = replay(net, ph)
    good, errs, margin = set(), [], {}
    for i, (r, key) in enumerate(zip(tt, keys)):
        if i in odd or key not in P:
            continue
        p2, p3, p4 = P[key]
        da, db = p2 - p4, p4 - p3
        xs = [int(r[k]) for k in bits]
        want = LOGIC[r["function"]](*xs)
        index = sum(x << b for b, x in enumerate(xs))
        y = int(da > 0 and db > 0)
        if int(r["target"]) == int(r["bit"]) == want == y == int(TRUTH_HEX[r["function"]], 16) >> index & 1:
            good.add(key)                                             # good 記鍵，不記列：同一列重複不會多算
        errs += [abs(float(r[c]) - v) for c, v in (("P2", p2), ("P3", p3), ("P4", p4), ("Da", da), ("Db", db))]
        m = min(da, db) if want else max(-da, -db)
        margin[r["function"]] = min(margin.get(r["function"], math.inf), m)
    if good != TT_KEYS:
        bad.append("有判讀與函數定義不符的列")
    if not errs or not all(e < 1e-5 for e in errs):                   # 逐筆比：max() 會漏掉 NaN
        bad.append("P、Da、Db 差超過 1e-5 或不是數字")
    wrong = [fn for fn, f in ph["functions"].items() if f["verified"] != "16/16" or not f["margin"] > 0 or fn not in margin or not near(margin[fn], f["margin"], 1e-5)]
    bad += [f"裕量與重算值不符 {wrong[:3]}"] if wrong else []
    err = max((e for e in errs if math.isfinite(e)), default=math.inf)
    return verdict(bad, f"{len(good)}/{len(TT_KEYS)}，最大差 {err:.1e}")


def k9_drc(d):
    drc_r = J(d, "verification/drc_result.json")
    bad = []
    if type(drc_r["total"]) is not int or drc_r["total"] != 0 or drc_r["counts"] != {} or drc_r["outside"] != 0:
        bad.append(f"DRC 有違規（{drc_r['total']}、{drc_r['counts']}、區外 {drc_r['outside']}）")
    if drc_r["n_rules"] != N_DRC_RULES or len(drc_r["rules"]) != N_DRC_RULES or len(set(drc_r["rules"])) != N_DRC_RULES:
        bad.append(f"DRC 規則不是 {N_DRC_RULES} 條")
    if drc_r["n_gds99"] != 1 or drc_r["gds99_is_die"] is not True or drc_r["design_area_um"] != DIE or drc_r["design_area_source"] != "declared":
        bad.append("DRC 的外框或設計區不符")
    return verdict(bad, f"違規 {drc_r['total']}、{len(drc_r['rules'])} 條規則")


def k10_lvs(d):
    conn = J(d, "verification/connectivity.json")
    e = conn["electrical"]
    bad = [f"LVS 錯誤 {len(e['errors'])}"] if e["errors"] != [] else []
    bad += same_set("LVS 的 heater", [c["heater"] for c in e["channels"]], HEATERS)
    bad += same_set("LVS 的 PAD", e["pads"], ALL_PADS)
    bad += same_set("LVS 的 GND PAD", e["gnd_pads"], GND_PADS)
    bad += same_set("GND 配對的 PAD", e["gnd_pairing"], GND_PADS)
    bad += same_set("GND 配對的 heater", [h for hs in e["gnd_pairing"].values() for h in hs], HEATERS)
    pair = {h: g for g, hs in GND_PAIRING.items() for h in hs}
    wrong = [c["heater"] for c in e["channels"] if c["ok"] is not True or c["contacts"] != 2 or c["heater"] not in HEATERS
             or len(c["nets"]) != 2 or set(c["nets"]) != {HEATERS[c["heater"]][0], pair[c["heater"]]}]
    bad += [f"LVS 不符 {wrong[:3]}"] if wrong else []
    if e["al_nets"] != len(ALL_PADS) or e["tin_regions"] != len(HEATERS):
        bad.append("LVS 抽出的網數不符")
    bad += same_set("連接檢查項目", conn["checks"], CONN_CHECKS)
    failed = [k for k, v in conn["checks"].items() if v is not True]
    bad += [f"連接檢查未通過 {failed[:3]}"] if failed else []
    if conn["core_sha_match"] is not True or conn["core_polygons"] != [N_CORE_POLYGONS, N_CORE_POLYGONS]:
        bad.append("核心與審查版本不同")
    n = sum(c["ok"] is True for c in e["channels"] if c["heater"] in HEATERS)
    return verdict(bad, f"heater {n}/{len(HEATERS)}、錯誤 {len(e['errors'])}")


def k11_optical(d):
    o = J(d, "verification/connectivity.json")["optical"]
    bad = [f"光學錯誤 {len(o['errors'])}"] if o["errors"] != [] else []
    bad += same_set("光學 EC", [r["ec"] for r in o["ec"]], EC_NAMES)
    wrong = [r["ec"] for r in o["ec"] if r["ok"] is not True or len(r["core_port"]) != 1
             or r["ec"] != f"{EC_SIGNAL.get(r['core_port'][0])}_{r['core_port'][0]}"
             or r["side"] != ("W" if r["core_port"][0].startswith("in") else "E")]
    bad += [f"光學不符 {wrong[:3]}"] if wrong else []
    n = len({r["ec"] for r in o["ec"] if r["ok"] is True} & EC_NAMES)
    return verdict(bad, f"{n}/{len(EC_SIGNAL)}")


def k12_faults(d):
    conn, drc_r = J(d, "verification/connectivity.json"), J(d, "verification/drc_result.json")
    rev, sim = J(d, "verification/review_checks.json"), J(d, "verification/sim_results.json")
    bad = same_set("故障案例", conn["faults"], FAULTS)
    bad += [f"故障沒抓到 {k}" for k, v in conn["faults"].items() if v is not True]
    if conn["checks"]["faults_caught"] is not True:
        bad.append("連接檢查的 faults_caught 不是 true")
    fi = drc_r["fault_injection"]
    bad += same_set("DRC 故障注入", fi["caught"], DRC_FAULTS) + same_set("DRC 故障的違規數", fi["counts"], DRC_FAULTS)
    bad += [f"DRC 故障 {k} 違規 {v}" for k, v in fi["counts"].items() if type(v) is not int or v < 1]
    bad += same_set("審查的故障案例", rev["faults"], REVIEW_FAULTS)
    bad += [f"審查故障沒抓到 {k}" for k, v in rev["faults"].items() if v is not True]
    bad += same_set("模擬的故障案例", sim["faults"], SIM_FAULTS)
    bad += [f"模擬故障沒抓到 {k}" for k, v in sim["faults"].items() if v["caught"] is not True]
    n = sum(v is True for k, v in conn["faults"].items() if k in FAULTS)
    return verdict(bad, f"連接 {n}/{len(FAULTS)}、DRC {len(fi['caught'])}、審查 {len(rev['faults'])}、模擬 {len(sim['faults'])}")


def k13_review(d):
    rev = J(d, "verification/review_checks.json")
    bad = same_set("審查項目", [c["id"] for c in rev["checks"]], REVIEW_PASS | REVIEW_DISPOSITION)
    failed = [c["id"] for c in rev["checks"] if (c["ok"] is not True if c["id"] in REVIEW_PASS else not c.get("disposition"))]
    bad += [f"審查未通過 {failed[:3]}"] if failed else []
    bad += same_set("審查的函數", rev["per_function"], LOGIC)
    if (rev["all_ok"] is not True or rev["passed"] != len(TT_KEYS) or not all(v["passed"] == len(WORDS) for v in rev["per_function"].values())
            or rev["n_pass"] != len(REVIEW_PASS) or rev["n_disposition"] != len(REVIEW_DISPOSITION)):
        bad.append(f"審查真值表 {rev['passed']}/{len(TT_KEYS)}")
    return verdict(bad, f"V 項 {sum(c.get('ok') is True for c in rev['checks'] if c['id'] in REVIEW_PASS)}/{len(REVIEW_PASS)}、真值表 {rev['passed']}/{len(TT_KEYS)}")


def k14_sim(d):
    sim, ph = J(d, "verification/sim_results.json"), J(d, "function/phases.json")
    bad = same_set("模擬的函數", sim["functions"], LOGIC)
    bad += same_set("模擬檢查項目", sim["checks"], SIM_CHECKS)
    if (sim["passed"] != len(TT_KEYS) or sim["total"] != len(TT_KEYS) or not all(v is True for v in sim["checks"].values())
            or not all(v["passed"] == len(WORDS) for v in sim["functions"].values())):
        bad.append(f"模擬 {sim['passed']}/{sim['total']}")
    wrong = [fn for fn, v in sim["functions"].items() if not v["margin"] > 0 or not near(v["margin_handoff"], ph["functions"][fn]["margin"], 1e-5)]
    bad += [f"模擬裕量不符 {wrong[:3]}"] if wrong else []
    return verdict(bad, f"{sim['passed']}/{sim['total']}")


def k15_drc(d, klayout, deck):
    if not klayout and not deck:
        return None, "略過（未提供 KLayout 與平台 deck）"             # 略過不算通過，也不算失敗
    if not klayout or not deck or not Path(klayout).exists() or not Path(deck).exists():
        return False, "指定了重跑 DRC，但找不到 KLayout 或平台 deck"
    gds = (d / GDS_FILE).resolve()
    rep = gds.with_name("chip_drc.lyrdb")
    try:
        subprocess.run([str(klayout), "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={rep}",
                        "-rd", f"dw={DIE[0]:g}", "-rd", f"dh={DIE[1]:g}"], check=True, capture_output=True)
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
    steps = (("K1 檔案完整", k1_files), ("K2 讀者文件禁字", k2_words), ("K3 README", k3_readme), ("K4 PAD 對照", k4_pads),
             ("K5 光學埠對照", k5_ports), ("K6 佈局版本", k6_layout), ("K7 接線版本", k7_netlist), ("K8 重算真值表", k8_truth),
             ("K9 DRC", k9_drc), ("K10 LVS", k10_lvs), ("K11 光學", k11_optical), ("K12 故障注入", k12_faults),
             ("K13 佈局審查", k13_review), ("K14 電路模擬", k14_sim))
    res = {name: guarded(fn, d) for name, fn in steps}
    res["K15 重跑 DRC"] = guarded(k15_drc, d, klayout, deck)
    return res


def self_test(d, work):
    """注入錯誤：每一種都要讓對應的檢查失敗。除了 K1 自己的案例，其餘都重算 MANIFEST，K1 必須仍通過，證明攔下來的是語意檢查。"""
    PADS, ECS, TT = "interfaces/pads.csv", "interfaces/optical_ports.csv", "function/truth_tables.csv"
    SPEC, PH, NET = "interfaces/spec.json", "function/phases.json", "function/lut4_netlist.json"
    DRC, CONN = "verification/drc_result.json", "verification/connectivity.json"
    REV, SIM = "verification/review_checks.json", "verification/sim_results.json"
    K1, K2, K3, K4, K5 = "K1 檔案完整", "K2 讀者文件禁字", "K3 README", "K4 PAD 對照", "K5 光學埠對照"
    K6, K7, K8, K9, K10 = "K6 佈局版本", "K7 接線版本", "K8 重算真值表", "K9 DRC", "K10 LVS"
    K11, K12, K13, K14, K15 = "K11 光學", "K12 故障注入", "K13 佈局審查", "K14 電路模擬", "K15 重跑 DRC"

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

    def text(rel, fn):                                                # 改文字，重算 MANIFEST
        def go(p):
            enc = "utf-8-sig" if rel.endswith(".csv") else "utf-8"
            (p / rel).write_text(fn((p / rel).read_text(encoding=enc)), encoding=enc)
            remanifest(p, rel)
        return go

    def tab(rel, fn):                                                 # 改 CSV 的列（fn 就地修改，或回傳新的列），重算 MANIFEST
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

    def js(rel, fn):                                                  # 改 JSON（fn 就地修改），重算 MANIFEST
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
        b = bytearray((p / GDS_FILE).read_bytes())
        b[-10] ^= 0xFF
        (p / GDS_FILE).write_bytes(bytes(b))
        remanifest(p, GDS_FILE)

    def resync_gds(p):                                                # GDS 改了，DRC、連接檢查、README 的雜湊也跟著改
        g = sha(p / GDS_FILE)
        js(DRC, lambda o: o.update(gds_sha256=g))(p)
        js(CONN, lambda o: o.update(gds_sha256=g))(p)
        text("README.md", lambda t: t.replace(GDS_SHA, g))(p)

    def swap_pad(r):
        s = [x for x in r if x["kind"] == "訊號"]
        s[0]["pad"], s[1]["pad"] = s[1]["pad"], s[0]["pad"]

    def swap_ec(r):
        r[0]["port"], r[1]["port"] = r[1]["port"], r[0]["port"]

    def drop_file(m, p):
        (p / "figures/s3_chip.png").unlink()
        m["files"] = [f for f in m["files"] if f["path"] != "figures/s3_chip.png"]

    def add_file(m, p):
        (p / "figures/extra.png").write_bytes(b"x")
        m["files"].append(dict(path="figures/extra.png", sha256=sha(p / "figures/extra.png"), bytes=1))

    def resync_netlist(p):                                            # 接線表改了，相位設定檔、規格、README 的雜湊也跟著改
        ns = sha(p / NET)
        js(PH, lambda o: o.update(netlist_sha256=ns))(p)
        js(SPEC, lambda o: o["source"].update(netlist_sha256=ns))(p)
        text("README.md", lambda t: t.replace(NET_SHA, ns))(p)

    def swap_fn_phases(o):
        f = o["functions"]
        f["AND4"], f["XOR4"] = f["XOR4"], f["AND4"]

    def swap_fn_rows(r):
        for x in r:
            x["function"] = {"AND4": "XOR4", "XOR4": "AND4"}.get(x["function"], x["function"])

    def wrong_encoding(p):
        """用另一種編碼（E±）重算全部 112 列的 P、Da、Db，判讀與 target 也跟著新結果寫，再重算 MANIFEST。"""
        P = replay(J(p, NET), J(p, PH), enc=lambda bits: [1.0 - 2 * b for b in bits])

        def fill(r):
            for x in r:
                p2, p3, p4 = P[(x["function"], x["x1"] + x["x2"] + x["x3"] + x["x4"])]
                x.update(P2=f"{p2:.6f}", P3=f"{p3:.6f}", P4=f"{p4:.6f}", Da=f"{p2 - p4:.6f}", Db=f"{p4 - p3:.6f}", bit=str(int(p2 > p4 and p4 > p3)))
                x["target"] = x["bit"]
        tab(TT, fill)(p)

    basic = [
        ("改內容未更新 MANIFEST", K1, lambda p: (p / PADS).write_text((p / PADS).read_text(encoding="utf-8-sig") + "\n", encoding="utf-8-sig")),
        ("刪掉一個檔案", K1, lambda p: (p / "figures/s3_chip.png").unlink()),
        ("README 寫入本機路徑", K2, text("README.md", lambda t: t + "\n原始檔在 " + "C" + ":" + "\\" + "work" + "\\" + "chip.gds\n")),
        ("PAD 對照對調", K4, tab(PADS, swap_pad)),
        ("相位被改", K8, js(PH, lambda o: o["functions"]["XOR4"]["theta"].__setitem__(3, o["functions"]["XOR4"]["theta"][3] + 1.0))),
        ("GDS 被改", K6, flip_gds),
        ("README 少一節", K3, text("README.md", lambda t: t.replace("## 5.", "## 五."))),
        ("EC 對照對調", K5, tab(ECS, swap_ec)),
        ("接線表被改", K7, text(NET, lambda t: t + " ")),
        ("DRC 有違規", K9, js(DRC, lambda o: o.update(total=1))),
    ]
    reverse = [
        # K1：清單本身
        ("刪檔並同時刪清單項", K1, man(drop_file)),
        ("多一個檔並列入清單", K1, man(add_file)),
        ("清單複製一項", K1, man(lambda m, p: m["files"].append(dict(m["files"][0])))),
        ("清單清空", K1, man(lambda m, p: m["files"].clear())),
        ("清單的鍵打錯", K1, man(lambda m, p: rename(m["files"][0], "sha256", "sha265"))),
        ("清單的大小不符", K1, man(lambda m, p: m["files"][0].update(bytes=1))),
        ("gate 清空", K1, man(lambda m, p: m["gate"].clear())),
        ("gate 少交付檢查", K1, man(lambda m, p: m["gate"].pop("delivery_check"))),
        ("gate 有一項未通過", K1, man(lambda m, p: m["gate"].update(gds_sha=False))),
        ("gate 的值是空值", K1, man(lambda m, p: m["gate"].update(drc=None))),
        # K2、K3
        ("程式說明寫入本機路徑", K2, text("check_delivery.py", lambda t: "# " + "C" + ":" + "\\" + "work\n" + t)),
        ("README 章節重複", K3, text("README.md", lambda t: t + "\n## 7. 檔案\n\n重複\n")),
        ("README 多一節", K3, text("README.md", lambda t: t + "\n## 8. 附錄\n\n多的\n")),
        ("README 章節沒有內容", K3, text("README.md", lambda t: re.sub(r"(?ms)(^## 3\. [^\n]*\n).*?(?=^## 4)", r"\1", t))),
        ("README 的 GDS 雜湊被刪", K3, text("README.md", lambda t: t.replace(GDS_SHA, "0" * 64))),
        ("README 的驗證數字被改", K3, text("README.md", lambda t: t.replace(f"{len(TT_KEYS)}/{len(TT_KEYS)}", f"{len(TT_KEYS) - 1}/{len(TT_KEYS)}"))),
        # K4：PAD
        ("PAD 刪一列", K4, tab(PADS, lambda r: r.pop(0) and None)),
        ("PAD 複製一列", K4, tab(PADS, lambda r: r.__setitem__(0, dict(r[1])))),
        ("PAD 多一列重複", K4, tab(PADS, lambda r: r.append(dict(r[0])))),
        ("PAD 清空", K4, tab(PADS, lambda r: [])),
        ("GND PAD 全部刪除", K4, tab(PADS, lambda r: [x for x in r if x["kind"] != "GND"])),
        ("同一 heater 多一個 PAD", K4, tab(PADS, lambda r: r.insert(0, dict(next(x for x in r if x["heater"] == "H01"), pad="P99")))),
        ("多一列不明種類的 PAD", K4, tab(PADS, lambda r: r.append(dict(r[0], pad="X99", kind="備用")))),
        ("PAD 的 heater 打錯", K4, tab(PADS, lambda r: next(x for x in r if x["heater"] == "H01").update(heater="H1"))),
        ("PAD 的種類打錯", K4, tab(PADS, lambda r: r[0].update(kind="訊號線"))),
        ("PAD 欄名打錯", K4, text(PADS, lambda t: t.replace("heater", "heatr", 1))),
        ("GND 的 heater 重複", K4, tab(PADS, lambda r: next(x for x in r if x["kind"] == "GND").update(heaters_on_gnd="H01＋H01"))),
        ("PAD 座標被改", K4, tab(PADS, lambda r: r[0].update(x_um="11.0"))),
        ("PAD 的相位與規格同時被改", K4, both(
            tab(PADS, lambda r: next(x for x in r if x["heater"] == "H01").update(phase="φ1")),
            js(SPEC, lambda o: next(c for c in o["phase_channels"] if c["heater"] == "H01").update(phase="φ1")))),
        ("規格與 PAD 同時少 H14", K4, both(
            tab(PADS, lambda r: [x for x in r if x["heater"] != "H14"]),
            js(SPEC, lambda o: o.update(phase_channels=[c for c in o["phase_channels"] if c["heater"] != "H14"])))),
        # K5：EC
        ("EC 第二筆複製成第一筆", K5, tab(ECS, lambda r: r.__setitem__(0, dict(r[1])))),
        ("EC 刪一列", K5, tab(ECS, lambda r: r.pop() and None)),
        ("EC 多一列重複", K5, tab(ECS, lambda r: r.append(dict(r[0])))),
        ("EC 清空", K5, tab(ECS, lambda r: [])),
        ("EC 埠名打錯", K5, tab(ECS, lambda r: r[0].update(port="inO"))),
        ("EC 欄名打錯", K5, text(ECS, lambda t: t.replace("port", "prot", 1))),
        ("EC 側邊打錯", K5, tab(ECS, lambda r: r[-1].update(edge="N"))),
        ("EC 座標被改", K5, tab(ECS, lambda r: r[0].update(facet_y_um="441.0"))),
        ("規格與 EC 同時少 out4", K5, both(
            tab(ECS, lambda r: [x for x in r if x["port"] != "out4"]),
            js(SPEC, lambda o: o.update(optical_ports=[x for x in o["optical_ports"] if x["port"] != "out4"])))),
        ("規格與 EC 同時改成另一種編碼的用途", K5, both(
            tab(ECS, lambda r: [x.update(use="資料光 其他編碼") for x in r if x["signal"] == "x1"] and None),
            js(SPEC, lambda o: next(x for x in o["optical_ports"] if x["signal"] == "x1").update(note="資料光 其他編碼")))),
        # K6、K7
        ("連接檢查的 GDS 雜湊鍵打錯", K6, js(CONN, lambda o: rename(o, "gds_sha256", "gds_sha265"))),
        ("DRC 的 GDS 雜湊鍵打錯", K6, js(DRC, lambda o: rename(o, "gds_sha256", "gds_sha265"))),
        ("GDS 被改且雜湊紀錄全部同步", K6, both(flip_gds, resync_gds), dict(must="固定的雜湊")),
        ("審查的核心 GDS 雜湊被改", K6, js(REV, lambda o: o.update(gds_sha256="0" * 64))),
        ("相位設定檔的雜湊鍵打錯", K7, js(PH, lambda o: rename(o, "netlist_sha256", "netlist_sha265"))),
        ("判讀埠被改且雜湊同步", K7, both(js(NET, lambda o: o["outputs"][0].update(role="判讀")), resync_netlist), dict(must="判讀埠")),
        ("MZI 少一顆且雜湊同步", K7, both(js(NET, lambda o: o["mzis"].pop()), resync_netlist), dict(must="MZI缺")),
        ("拓樸被改且雜湊同步", K7, both(js(NET, lambda o: o["mzis"][0].update(waveguides=[1, 2])), resync_netlist), dict(must="拓樸不符")),
        ("輸入編碼被改且雜湊同步", K7, both(js(NET, lambda o: o["inputs"][0].update(amplitude="其他編碼")), resync_netlist), dict(must="輸入振幅")),
        # K8：真值表
        ("真值表同一列重複 112 次", K8, tab(TT, lambda r: [dict(r[-1]) for _ in r])),
        ("真值表刪一列", K8, tab(TT, lambda r: r.pop() and None)),
        ("真值表複製一列", K8, tab(TT, lambda r: r.__setitem__(0, dict(r[1])))),
        ("真值表多一列重複", K8, tab(TT, lambda r: r.append(dict(r[0])))),
        ("真值表清空", K8, tab(TT, lambda r: [])),
        ("真值表函數名打錯", K8, tab(TT, lambda r: r[0].update(function="AND3"))),
        ("真值表欄名打錯", K8, text(TT, lambda t: t.replace("target", "targat", 1))),
        ("真值表位元放錯欄", K8, tab(TT, lambda r: r[0].update(x1="00", x2=""))),
        ("真值表的 Da 不是數字", K8, tab(TT, lambda r: r[5].update(Da="nan"))),
        ("真值表的 P4 被改", K8, tab(TT, lambda r: r[5].update(P4="9.0"))),
        ("真值表的 bit 與 target 不同", K8, tab(TT, lambda r: r[0].update(bit="1"))),
        ("真值表用另一種編碼重算", K8, wrong_encoding),
        ("AND4 與 XOR4 對調（相位與真值表同時）", K8, both(js(PH, swap_fn_phases), tab(TT, swap_fn_rows))),
        ("少一個函數（相位與真值表同時）", K8, both(
            js(PH, lambda o: o["functions"].pop("XOR2")), tab(TT, lambda r: [x for x in r if x["function"] != "XOR2"]))),
        ("相位的 θ 少一個", K8, js(PH, lambda o: o["functions"]["AND2"]["theta"].pop())),
        ("函數定義被改", K8, js(PH, lambda o: o["functions"]["AND2"].update(truth_hex="0x8889"))),
        ("裕量被改", K8, js(PH, lambda o: o["functions"]["AND2"].update(margin=9.0))),
        ("損耗參數被改", K8, js(PH, lambda o: o.update(loss_db_per_mzi=0.0))),
        ("參考光振幅被改", K8, js(PH, lambda o: o.update(R=2.5))),
        # K9：DRC
        ("DRC 缺 total", K9, js(DRC, lambda o: o.pop("total"))),
        ("DRC 的 total 不是整數", K9, js(DRC, lambda o: o.update(total="0"))),
        ("DRC 違規表與總數不一致", K9, js(DRC, lambda o: o["counts"].update({"某規則": 1}))),
        ("DRC 規則清單清空", K9, js(DRC, lambda o: o["rules"].clear())),
        ("DRC 規則少一條", K9, js(DRC, lambda o: o["rules"].pop())),
        ("DRC 設計區被改", K9, js(DRC, lambda o: o.update(design_area_um=[1.0, 1.0]))),
        # K10：LVS
        ("heater 通道清空", K10, js(CONN, lambda o: o["electrical"]["channels"].clear())),
        ("heater 通道刪一列", K10, js(CONN, lambda o: o["electrical"]["channels"].pop())),
        ("heater 通道複製一列", K10, js(CONN, lambda o: o["electrical"]["channels"].__setitem__(0, dict(o["electrical"]["channels"][1])))),
        ("heater 通道的鍵打錯", K10, js(CONN, lambda o: o["electrical"]["channels"][0].update(heater="H1"))),
        ("heater 通道接到別的網", K10, js(CONN, lambda o: o["electrical"]["channels"][0].update(nets=["P01", "P02"]))),
        ("LVS 的 PAD 少一個", K10, js(CONN, lambda o: o["electrical"]["pads"].pop())),
        ("連接檢查項目清空", K10, js(CONN, lambda o: o["checks"].clear())),
        ("連接檢查少一項", K10, js(CONN, lambda o: o["checks"].pop("lvs_clean"))),
        ("連接檢查的鍵打錯", K10, js(CONN, lambda o: rename(o["checks"], "lvs_clean", "lvs_clear"))),
        ("核心多邊形數被改", K10, js(CONN, lambda o: o.update(core_polygons=[1, 1]))),
        # K11：光學
        ("光學驗證列清空", K11, js(CONN, lambda o: o["optical"]["ec"].clear())),
        ("光學驗證刪一列", K11, js(CONN, lambda o: o["optical"]["ec"].pop())),
        ("光學驗證複製一列", K11, js(CONN, lambda o: o["optical"]["ec"].__setitem__(0, dict(o["optical"]["ec"][1])))),
        ("光學驗證的 EC 打錯", K11, js(CONN, lambda o: o["optical"]["ec"][0].update(ec="x1_inO"))),
        ("光學驗證的 ok 不是真值", K11, js(CONN, lambda o: o["optical"]["ec"][0].update(ok="yes"))),
        ("光學錯誤清單不是空的", K11, js(CONN, lambda o: o["optical"]["errors"].append("x1_in0 接錯"))),
        # K12：故障注入
        ("故障注入結果清空", K12, js(CONN, lambda o: o["faults"].clear())),
        ("缺一個故障案例", K12, js(CONN, lambda o: o["faults"].pop("TiN 斷路"))),
        ("故障案例的鍵打錯", K12, js(CONN, lambda o: rename(o["faults"], "TiN 斷路", "TiN 短路"))),
        ("多一個未知的故障案例", K12, js(CONN, lambda o: o["faults"].update({"未知案例": True}))),
        ("一個故障案例沒抓到", K12, js(CONN, lambda o: o["faults"].update({"TiN 斷路": False}))),
        ("故障結果有重複鍵", K12, text(CONN, lambda t: re.sub(r'"faults":\s*\{', '"faults": {"TiN 斷路": false,', t, count=1))),
        ("頂層的 faults 鍵打錯", K12, js(CONN, lambda o: rename(o, "faults", "fault"))),
        ("DRC 故障注入清空", K12, js(DRC, lambda o: o["fault_injection"].update(caught=[], counts={}))),
        ("DRC 故障注入少一條", K12, js(DRC, lambda o: o["fault_injection"]["caught"].pop())),
        ("審查故障清空", K12, js(REV, lambda o: o["faults"].clear())),
        ("模擬故障少一種", K12, js(SIM, lambda o: o["faults"].pop("phi_low"))),
        ("模擬故障沒抓到", K12, js(SIM, lambda o: o["faults"]["phi_low"].update(caught=False))),
        # K13：佈局審查
        ("佈局審查少一組", K13, js(REV, lambda o: o.update(passed=len(TT_KEYS) - 1))),
        ("佈局審查項目清空", K13, js(REV, lambda o: o["checks"].clear())),
        ("佈局審查的 V 項全部刪除", K13, js(REV, lambda o: o.update(checks=[c for c in o["checks"] if not c["id"].startswith("V")]))),
        ("佈局審查少 V8b", K13, js(REV, lambda o: o.update(checks=[c for c in o["checks"] if c["id"] != "V8b"]))),
        ("佈局審查的 V 項 id 打錯", K13, js(REV, lambda o: o["checks"][0].update(id="V01"))),
        ("佈局審查一項未通過", K13, js(REV, lambda o: o["checks"][0].update(ok=False))),
        ("佈局審查的處置被刪", K13, js(REV, lambda o: next(c for c in o["checks"] if c["id"] == "P1").pop("disposition"))),
        ("佈局審查少一個函數", K13, js(REV, lambda o: o["per_function"].pop("MUX"))),
        # K14：電路模擬
        ("電路模擬 0 等於 0", K14, js(SIM, lambda o: o.update(passed=0, total=0))),
        ("電路模擬少一組", K14, js(SIM, lambda o: o.update(passed=len(TT_KEYS) - 1))),
        ("電路模擬兩邊同時少一組", K14, js(SIM, lambda o: o.update(passed=len(TT_KEYS) - 1, total=len(TT_KEYS) - 1))),
        ("電路模擬函數清空", K14, js(SIM, lambda o: o["functions"].clear())),
        ("電路模擬少一個函數", K14, js(SIM, lambda o: o["functions"].pop("MUX"))),
        ("電路模擬檢查少一項", K14, js(SIM, lambda o: o["checks"].pop("all_pass"))),
        ("電路模擬裕量與交接不同", K14, js(SIM, lambda o: o["functions"]["AND2"].update(margin_handoff=9.0))),
        # K15
        ("指定的 KLayout 不存在", K15, lambda p: None, dict(klayout="不存在的程式", deck="不存在的 deck")),
    ]
    p = fresh()
    base = checks(p)
    shutil.rmtree(p.parent, ignore_errors=True)
    baseline = dict(ok=all(v[0] is not False for v in base.values()), failed=[k for k, v in base.items() if v[0] is False])
    out = {}
    for group, cases in (("基本", basic), ("反向", reverse)):
        for name, key, fn, *kw in cases:
            kw = dict(kw[0]) if kw else {}
            must = kw.pop("must", "")
            p = fresh()
            fn(p)
            r = checks(p, **kw)
            shutil.rmtree(p.parent, ignore_errors=True)
            out[name] = dict(check=key, caught=r[key][0] is False and (key == K1 or r[K1][0] is True) and must in r[key][1], group=group,
                             detail=r[key][1] if r[K1][0] is True or key == K1 else f"K1 未通過：{r[K1][1]}")
    return out, baseline


def main():
    args = sys.argv[1:]
    here = Path(__file__).resolve().parent
    in_tree = not (here / "MANIFEST.json").exists() and (here.parents[2] / "delivery_lut4").exists()
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
    elif in_tree:                                                     # 在課程原始碼樹中：檢查根目錄的交付包，用課程設定的 KLayout 與 deck
        d = here.parents[2] / "delivery_lut4"
        sys.path.insert(0, str(here.parents[1]))
        import paths
        if paths.KLAYOUT_EXE.exists() and paths.DRC_DECK.exists():    # 這台電腦沒有時印「略過」；命令列指定的路徑找不到才算未通過
            klayout = klayout or paths.KLAYOUT_EXE
            deck = deck or paths.DRC_DECK
        if "--self-test" in args:                                     # 只有完整檢查（含自我測試）才寫入課程的結果檔
            out = out or paths.OUT("lut4/s7_delivery", "delivery_check.json")
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
