r"""LUT4 s8（由 M3 s6 複製，輸入改為 LUT4 交付包）：商用工具對照：Virtuoso／Calibre——同一份交付 GDS，換成業界常用的工具，結果一樣嗎？

用途（在 WSL 的 EDA_Server 以批次指令執行，不開 GUI；結果只寫在本步 out/）：
  1. 由 KLayout 平台 deck 自動產生 Calibre SVRF 規則草案：只移植各層的最小線寬（INTERNAL）與最小間距（EXTERNAL），
     門檻沿用 deck 的值＋feature_margin（−0.001 µm）；其餘規則（格點、重疊、設計區、小面積特徵）不移植，逐條記錄在 not_ported。
     這份草案不是晶圓廠驗證過的 deck，也未證明與 KLayout 版語意等價。
  2. Virtuoso：strmin 把交付的 chip.gds 匯入 OA library；strmout 再以 maxVertices＝200（預設）與 8191 各匯出一次。
  3. Calibre DRC（-hier、-turbo 4）：對交付的 chip.gds、M3 s4 故意加了兩種違規的 chip_fault_drc.gds、兩份 strmout 匯出檔各跑一次。
  4. 來回比對：兩份 strmout 匯出檔再跑 KLayout 平台 deck，並與原 GDS 逐層比較多邊形數與幾何（對稱差面積）、cell 名稱與文字標記。
  5. .raw 小實驗（本機 KLayout）：平台 deck 對 GDS 3 呼叫 .raw 之後，同一層的線寬、間距改成逐塊（不合併）檢查；
     對交付檔與 200 匯出檔各跑「合併／.raw 之後／.clean」三種，找出 200 匯出檔 KLayout 報錯、Calibre 為 0 的原因。
輸入：delivery_lut4/layout/LUT4_chip.gds；LUT4 s6 的 out/chip_fault_drc.gds；design/common/drc 的 KLayout deck；EDA_Server 的 strmin／strmout／calibre。
輸出：out/commercial.json、out/run.sh、out/raw_vs_clean.lydrc、raw_vs_clean_chip.lyrdb、raw_vs_clean_strmout_200.lyrdb、out/strmout_200.gds、out/strmout_8191.gds（及 KLayout 報告 strmout_200_drc.lyrdb、strmout_8191_drc.lyrdb）；
      out/cornerstone_basic_draft_chip.svrf、calibre_chip.log、calibre_chip.summary、calibre_chip.results；
      out/cornerstone_basic_draft_fault.svrf、calibre_fault.log、calibre_fault.summary、calibre_fault.results；
      out/cornerstone_basic_draft_strmout_200.svrf、calibre_strmout_200.log、calibre_strmout_200.summary、calibre_strmout_200.results；
      out/cornerstone_basic_draft_strmout_8191.svrf、calibre_strmout_8191.log、calibre_strmout_8191.summary、calibre_strmout_8191.results；
      out/cds.lib、strmin.log、strmout_200.log、strmout_8191.log、xStrmOut_layerMap.txt（OA library 與 .cadence 暫存資料夾在匯出後刪除）。
執行：.\lab design\lut4\s8_commercial\commercial.py --evidence
        （2026-11-07 重跑：不啟動 EDA_Server。strmin／strmout／Calibre 的紀錄檔與匯出 GDS 是參考專案的既有證據（tools_port/port.py 複製到 out/），
          本機只重跑 KLayout 的部分：兩份匯出檔的平台 deck DRC、與本次交付 GDS 的逐層幾何／cell／文字比對、.raw 小實驗；
          另把本次 chip／fault GDS 與 out/reference_evidence/ 的參考 GDS 去時間戳後逐層比對，本次產生的 SVRF 與參考 SVRF 逐行比對，
          兩者都相同才判定既有 Calibre 證據適用於本次 GDS，否則標「未驗證」。結果分列在 commercial.json 的 status 欄。）
      .\lab design\lut4\s8_commercial\commercial.py --dry（只寫出 run.sh 與 SVRF，不呼叫 EDA_Server）
      .\lab design\lut4\s8_commercial\commercial.py --run-eda（在 EDA_Server 實跑；需使用者授權。沒有這個參數一律不會呼叫 wsl）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402
import re                                                            # noqa: E402
import subprocess                                                    # noqa: E402
from datetime import datetime, timezone                              # noqa: E402

import numpy as np                                                   # noqa: E402
from shapely.geometry import Polygon                                 # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import drc                                               # noqa: E402
from common import gds2png as G                                      # noqa: E402

STEP = "lut4/s8_commercial"
DISTRO = "EDA_Server"
TURBO = 4                                                            # 平行上限（本計畫最多 6）
TOP = "L4_CHIP"


def wsl_path(p):
    p = Path(p).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def deck_rules():
    """從 KLayout deck 讀出各層的 width／space 規則（GDS 層號、門檻、原始說明）。"""
    text = paths.DRC_DECK.read_text(encoding="utf-8", errors="replace")
    layer = {m.group(1): int(m.group(2)) for m in re.finditer(r"^(\w+)\s*=\s*(?:input|polygons)\((\d+),\s*0\)", text, re.M)}
    margin = float(re.search(r"^feature_margin\s*=\s*(-?[\d.]+)\.um", text, re.M).group(1))
    n_total = len(re.findall(r"\.output\(", text))
    outputs = [d.replace("&lt;", "<") for d in re.findall(r"\.output\('([^']*)'\)", text)]
    rules = []
    for m in re.finditer(r"^(\w+)\.(width|space)\(([\d.]+)\.um\+feature_margin.*?\.output\('([^']*)'\)", text, re.M):
        var, kind, v, desc = m.groups()
        if var in layer:
            rules.append(dict(layer=layer[var], kind=kind, value_um=float(v), threshold_um=round(float(v) + margin, 4),
                              klayout=desc.replace("&lt;", "<")))
    ported = {r["klayout"] for r in rules}
    return rules, n_total, margin, [o for o in outputs if o not in ported]


def svrf(rules, gds, top, rundir, tag):
    """SVRF 草案：每條規則一個 rule check；結果寫 ASCII 結果庫與摘要。"""
    lines = ["// 教學用草案：由 KLayout 平台 deck 自動移植，只含各層最小線寬與最小間距；不是晶圓廠驗證過的 deck。",
             f'LAYOUT PATH "{wsl_path(gds)}"', f'LAYOUT PRIMARY "{top}"', "LAYOUT SYSTEM GDSII",
             f'DRC RESULTS DATABASE "{rundir}/calibre_{tag}.results" ASCII',
             f'DRC SUMMARY REPORT "{rundir}/calibre_{tag}.summary"', "DRC MAXIMUM RESULTS ALL", "PRECISION 1000", ""]
    for g in sorted({r["layer"] for r in rules}):
        lines += [f"LAYER MAP {g} DATATYPE 0 {1000 + g}", f"LAYER L{g} {1000 + g}"]
    lines.append("")
    for r in rules:
        op = "INTERNAL" if r["kind"] == "width" else "EXTERNAL"
        name = f"L{r['layer']}_{'W' if r['kind'] == 'width' else 'S'}"
        lines += [f"{name} {{", f"  @ {r['klayout']}（門檻 {r['threshold_um']:g} µm）",
                  f"  {op} L{r['layer']} < {r['threshold_um']:g} ABUT < 90 SINGULAR REGION", "}"]
        r["svrf_name"] = name
    return "\n".join(lines) + "\n"


def read_summary(path):
    """Calibre 摘要：每條 RULECHECK 的結果數。"""
    out = {}
    for m in re.finditer(r"RULECHECK\s+(\S+)\s+\.+\s+TOTAL Result Count\s*=\s*(\d+)", Path(path).read_text(errors="replace")):
        out[m.group(1)] = int(m.group(2))
    return out


def layer_geom(gds):
    structs, dbu = G.parse(str(gds))
    referenced = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in referenced][0]
    polys = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), polys)
    sc = dbu / 1e-6
    by = {}
    for l, xy in polys:
        by.setdefault(l, []).append(Polygon(xy * sc).buffer(0))
    return {l: (len(v), unary_union(v)) for l, v in by.items()}


# 平台 deck 第 116、123 行寫 soi_etch2_light_layer.raw.sized(0.2.um)：KLayout 的 .raw 會把「該層物件本身」改成不合併模式，
# 之後同一個物件的 GDS 3 線寬、間距檢查就改成逐塊檢查（M3 關卡審查 R1）。下面的小實驗重現這件事。
RAW_DRC = """<?xml version="1.0" encoding="utf-8"?>
<klayout-macro><interpreter>dsl</interpreter><dsl-interpreter-name>drc-dsl-xml</dsl-interpreter-name><text>
tiles(20.mm)
deep
threads(2)
source($input)
report("raw vs clean", $report)
a = polygons(3, 0)
a.width(0.349.um, angle_limit(45)).output("merged_width")
a.space(0.199.um, angle_limit(45)).without_area(0).output("merged_space")
b = polygons(3, 0)
b.raw.sized(0.2.um)
b.width(0.349.um, angle_limit(45)).output("after_raw_width")
b.space(0.199.um, angle_limit(45)).without_area(0).output("after_raw_space")
b.clean.width(0.349.um, angle_limit(45)).output("clean_width")
b.clean.space(0.199.um, angle_limit(45)).without_area(0).output("clean_space")
</text></klayout-macro>
"""
RAW_CATS = ("merged_width", "merged_space", "after_raw_width", "after_raw_space", "clean_width", "clean_space")


def raw_experiment(gds, deck, tag):
    """同一份 GDS 的 GDS 3 線寬／間距：合併（預設）、呼叫過 .raw 之後、再 .clean 之後，各幾處。"""
    rep = deck.with_name(f"raw_vs_clean_{tag}.lyrdb")
    subprocess.run([str(paths.KLAYOUT_EXE), "-b", "-r", str(deck), "-rd", f"input={Path(gds).resolve()}", "-rd", f"report={rep}"],
                   check=True, capture_output=True)
    txt = rep.read_text(encoding="utf-8", errors="replace")
    return {c: len(re.findall(rf"<category>'?{c}'?</category>", txt)) for c in RAW_CATS}


def gds_meta(gds):
    """cell 名稱與文字標記（層、內容），用來確認匯出檔沒有遺失 LVS 要用的標記（M3 關卡審查 R13）。"""
    structs, _ = G.parse(str(gds))
    texts = sorted((n, t[0], t[2]) for n, st in structs.items() for t in st.get("texts", []))
    return sorted(structs), texts


EVIDENCE_FILES = ("strmin.log", "strmout_200.log", "strmout_8191.log", "strmout_200.gds", "strmout_8191.gds", "cds.lib", "xStrmOut_layerMap.txt") + tuple(
    f"calibre_{t}.{ext}" for t in ("chip", "fault", "strmout_200", "strmout_8191") for ext in ("log", "summary", "results"))
SHOT_FILES = ("v_chip.png", "v_core.png", "v_mzi.png", "v_fault.png", "rve_chip.png", "rve_fault.png")
REF_DIR = "reference_evidence"                                       # 參考 GDS、參考 SVRF、參考 commercial.json（port.py 複製，位元組不改）


def gds_records(data):
    i = 0
    while i + 4 <= len(data):
        n = int.from_bytes(data[i:i + 2], "big")
        if n == 0:
            break
        yield data[i + 2], data[i + 3], data[i + 4:i + n]
        i += n


def gds_no_time(path):
    """GDS 全部紀錄，只把 BGNLIB、BGNSTR 的時間欄歸零。"""
    return b"".join(bytes([rt_, dt]) + (bytes(len(p)) if rt_ in (0x01, 0x05) else p) for rt_, dt, p in gds_records(Path(path).read_bytes()))


def flat_polys(gds):
    """頂層攤平後各層的多邊形：頂點四捨五入到 dbu 整數、起點與方向正規化後排序（順序、起點不同仍算同一個多邊形）。"""
    structs, dbu = G.parse(str(gds))
    referenced = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in referenced][0]
    polys = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), polys)
    by = {}
    for l, xy in polys:
        pts = [tuple(int(v) for v in p) for p in np.rint(np.asarray(xy, float)).astype(np.int64)]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        k = pts.index(min(pts))
        a = pts[k:] + pts[:k]
        b = [a[0]] + a[:0:-1]
        by.setdefault(l, []).append(tuple(min(a, b)))
    return {l: sorted(v) for l, v in by.items()}


def compare_gds(this, ref):
    """本次 GDS vs 參考 GDS：去時間戳位元組、逐層多邊形（個數、內容雜湊、對稱差面積）、cell、文字標記。"""
    pa, pb = flat_polys(this), flat_polys(ref)
    ga, gb = layer_geom(this), layer_geom(ref)
    layers = {}
    for l in sorted(set(pa) | set(pb)):
        a, b = pa.get(l, []), pb.get(l, [])
        ua, ub = ga.get(l, (0, Polygon()))[1], gb.get(l, (0, Polygon()))[1]
        layers[str(l)] = dict(n_this=len(a), n_ref=len(b), polygons_equal=a == b,
                              polys_sha256=hashlib.sha256(repr(a).encode()).hexdigest(),
                              sym_diff_um2=round(float(ua.symmetric_difference(ub).area), 6))
    ca, ta = gds_meta(this)
    cb, tb = gds_meta(ref)
    same_bytes = gds_no_time(this) == gds_no_time(ref)
    return dict(this_sha256=hashlib.sha256(Path(this).read_bytes()).hexdigest(), ref_sha256=hashlib.sha256(Path(ref).read_bytes()).hexdigest(),
                bytes_equal_except_timestamps=same_bytes, layers=layers, n_cells=[len(ca), len(cb)], cells_equal=ca == cb,
                n_texts=[len(ta), len(tb)], texts_equal=ta == tb,
                identical=same_bytes and ca == cb and ta == tb and all(v["polygons_equal"] and v["sym_diff_um2"] == 0 for v in layers.values()))


def gds_build_utc(path):
    """BGNLIB 的修改時間（IPKISS 寫的是 UTC）。"""
    p = next(p for rt_, _, p in gds_records(Path(path).read_bytes()) if rt_ == 0x01)
    return datetime(*(int.from_bytes(p[i:i + 2], "big") for i in range(0, 12, 2)), tzinfo=timezone.utc)


def svrf_body(path):
    """SVRF 去掉隨路徑變動的四行（LAYOUT PATH、結果庫、摘要），其餘逐行比。"""
    return [s for s in Path(path).read_text(encoding="utf-8").splitlines()
            if not s.startswith(("LAYOUT PATH", "DRC RESULTS DATABASE", "DRC SUMMARY REPORT"))]


def main():
    evidence = "--evidence" in sys.argv[1:]                          # 2026-11-07：不啟動 EDA_Server，讀 out/ 既有證據
    run_eda = "--run-eda" in sys.argv[1:] and not evidence           # 只有明確給 --run-eda 才可能呼叫 wsl
    out = paths.OUT(STEP)
    chip = paths.ROOT / "delivery_lut4" / "layout" / "LUT4_chip.gds"
    fault = paths.OUT("lut4/s6_verify", "chip_fault_drc.gds")
    info = json.loads(paths.OUT("lut4/s5_chip", "chip_info.json").read_text(encoding="utf-8"))
    die = tuple(info["die_um"])
    rules, n_total, margin, not_ported = deck_rules()
    rd = wsl_path(out)
    gds_in = {"chip": (chip, TOP), "fault": (fault, "L4_CHIP_FAULT"),
              "strmout_200": (out / "strmout_200.gds", TOP), "strmout_8191": (out / "strmout_8191.gds", TOP)}
    for tag, (g, top) in gds_in.items():
        (out / f"cornerstone_basic_draft_{tag}.svrf").write_text(svrf(rules, g, top, rd, tag), encoding="utf-8", newline="\n")
    oa = out                                                          # strmin／strmout 直接在本步 out/ 執行（紀錄檔與程式同一層，索引找得到產生者）
    sh = [
        "#!/bin/bash", "set -e", f"cd {rd}", "rm -f strmout_200.gds strmout_8191.gds",   # 先刪舊檔，避免「覆寫」警告
        "printf 'DEFINE L4_OA ./L4_OA\\n' > cds.lib",
        "rm -rf L4_OA",
        f"strmin -library L4_OA -strmFile {wsl_path(chip)} -topCell {TOP} -view layout -logFile strmin.log -dbuPerUU 1000",
        f"strmout -library L4_OA -strmFile {rd}/strmout_200.gds -topCell {TOP} -view layout -logFile strmout_200.log -maxVertices 200",
        f"strmout -library L4_OA -strmFile {rd}/strmout_8191.gds -topCell {TOP} -view layout -logFile strmout_8191.log -maxVertices 8191",
        "rm -rf L4_OA .cadence",                                      # OA library 只是中間產物：匯出後刪除
        f"cd {rd}",
    ] + [f"calibre -drc -hier -turbo {TURBO} cornerstone_basic_draft_{t}.svrf > calibre_{t}.log 2>&1" for t in gds_in] + ["echo DONE"]
    (out / "run.sh").write_text("\n".join(sh) + "\n", encoding="utf-8", newline="\n")
    if "--dry" in sys.argv:
        print((out / "run.sh").read_text(encoding="utf-8"))
        sys.exit(0)
    if not evidence and not run_eda:                                  # 閘門：預設什麼都不呼叫
        sys.exit("未指定 --evidence 或 --run-eda：不呼叫 EDA_Server。本波未獲授權實跑，請用 --evidence 或 --dry。")
    ev = None
    if evidence:                                                      # 只核對既有證據：不啟動 EDA_Server
        missing = [n for n in EVIDENCE_FILES if not (out / n).exists()]
        if missing:
            sys.exit(f"--evidence：out/ 缺少既有證據檔 {missing}（用 tools_port/port.py 從參考專案複製）")
        ev = dict(mode="只核對既有證據：strmin／strmout／Calibre 未在本機執行；紀錄檔與匯出 GDS 來自參考專案的 EDA_Server 執行結果",
                  files={n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in EVIDENCE_FILES},
                  calibre_layout_paths=sorted({m.group(1) for n in gds_in
                                               for m in re.finditer(r"^Layout Path\(s\):\s+(\S+)", (out / f"calibre_{n}.summary").read_text(errors="replace"), re.M)}),
                  calibre_run_times={n: re.search(r"^Execution Date/Time:\s+(.+?)\s*$", (out / f"calibre_{n}.summary").read_text(errors="replace"), re.M).group(1) for n in gds_in},
                  local_rerun=["KLayout 平台 deck DRC（strmout_200、strmout_8191）",
                               "逐層幾何／cell／文字比對（本次交付 chip.gds vs 兩份匯出檔）", ".raw 小實驗（chip、strmout_200）",
                               "本次 chip／fault GDS vs 參考 GDS（去時間戳、逐層多邊形）", "本次 SVRF vs 參考 SVRF（去路徑行）"])
        print(f"--evidence：{ev['mode']}；證據檔 {len(ev['files'])} 個")
    else:
        r = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", f"bash {rd}/run.sh"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(r.stdout[-400:], r.stderr[-400:])
        if "DONE" not in r.stdout:
            sys.exit("EDA_Server 執行未完成，見 out/*.log（strmin／strmout）與 out/calibre_*.log")

    cal = {t: read_summary(out / f"calibre_{t}.summary") for t in gds_in}
    kl = {t: drc.run(gds_in[t][0], design_area=die) for t in ("strmout_200", "strmout_8191")}
    g0 = layer_geom(chip)
    rt_cmp = {}
    for t in ("strmout_200", "strmout_8191"):
        g1 = layer_geom(gds_in[t][0])
        rows = {}
        for l in sorted(set(g0) | set(g1)):
            n0, u0 = g0.get(l, (0, Polygon()))
            n1, u1 = g1.get(l, (0, Polygon()))
            rows[str(l)] = dict(n_orig=n0, n_out=n1, sym_diff_um2=round(float(u0.symmetric_difference(u1).area), 6))
        c0, t0 = gds_meta(chip)
        c1, t1 = gds_meta(gds_in[t][0])
        rt_cmp[t] = dict(layers=rows, n_cells=[len(c0), len(c1)], cells_equal=c0 == c1, n_texts=[len(t0), len(t1)], texts_equal=t0 == t1)
    deck_x = out / "raw_vs_clean.lydrc"
    deck_x.write_text(RAW_DRC, encoding="utf-8")
    raw = {t: raw_experiment(gds_in[t][0], deck_x, t) for t in ("chip", "strmout_200")}
    gm = g0.get(3)                                                      # 合併後的 GDS 3：匯出前後是否同一個形狀
    merged_200 = dict(pieces_merged=[len(getattr(u, 'geoms', [u])) for u in (gm[1], layer_geom(gds_in['strmout_200'][0])[3][1])])
    logs = {n: (oa / n).read_text(errors="replace") for n in ("strmin.log", "strmout_200.log", "strmout_8191.log")}
    warn = {n: dict(errors=len(re.findall(r"\bERROR\b", s)), warnings=len(re.findall(r"\bWARNING\b", s)),
                    xstrm275=len(re.findall(r"XSTRM-275", s))) for n, s in logs.items()}
    res = dict(deck=paths.DRC_DECK.name, deck_outputs=n_total, ported=len(rules), coverage=f"{len(rules)}/{n_total}", feature_margin_um=margin,
               rules=rules, not_ported=not_ported, deck_categories=len(kl["strmout_8191"]["rules"]),
               raw_vs_clean=raw, merged_gds3_200=merged_200, calibre={t: dict(total=sum(v.values()), by_rule=v) for t, v in cal.items()},
               klayout={t: dict(total=v["total"], counts=v["counts"]) for t, v in kl.items()}, roundtrip=rt_cmp, logs=warn,
               chip_sha256=hashlib.sha256(chip.read_bytes()).hexdigest(), turbo=TURBO, evidence=ev)
    fault_hit = {k for k, v in cal["fault"].items() if v}
    res["checks"] = dict(calibre_chip_clean=res["calibre"]["chip"]["total"] == 0, calibre_fault_caught={"L41_W", "L39_S"} <= fault_hit,
                         rules_all_ran=all(len(v) == len(rules) for v in cal.values()),
                         roundtrip_8191_identical=all(v["sym_diff_um2"] < 1e-6 for v in rt_cmp["strmout_8191"]["layers"].values())
                         and rt_cmp["strmout_8191"]["cells_equal"] and rt_cmp["strmout_8191"]["texts_equal"],
                         raw_explains_200=(raw["strmout_200"]["merged_width"] == 0 and raw["strmout_200"]["clean_width"] == 0
                                           and raw["strmout_200"]["after_raw_width"] + raw["strmout_200"]["after_raw_space"]
                                           == kl["strmout_200"]["total"]),
                         klayout_8191_clean=kl["strmout_8191"]["total"] == 0)
    if evidence:
        ref = out / REF_DIR
        need = ["LUT4_chip.gds", "chip_fault_drc.gds", "commercial.json"] + [f"cornerstone_basic_draft_{t}.svrf" for t in gds_in]
        missing = [n for n in need if not (ref / n).exists()]
        if missing:
            sys.exit(f"--evidence：out/{REF_DIR} 缺少 {missing}（用 tools_port/port.py --no-rewrite 從參考專案複製）")
        cmp_gds = {"chip": compare_gds(chip, ref / "LUT4_chip.gds"), "fault": compare_gds(fault, ref / "chip_fault_drc.gds")}
        svrf_same = {t: svrf_body(out / f"cornerstone_basic_draft_{t}.svrf") == svrf_body(ref / f"cornerstone_basic_draft_{t}.svrf") for t in gds_in}
        ref_com = json.loads((ref / "commercial.json").read_text(encoding="utf-8"))
        ref_chain = ref_com["chip_sha256"] == cmp_gds["chip"]["ref_sha256"]    # 參考 commercial.json 記的 GDS 就是被比對的那一份
        rt8191 = res["checks"]["roundtrip_8191_identical"]
        applies = cmp_gds["chip"]["identical"] and cmp_gds["fault"]["identical"] and all(svrf_same.values()) and ref_chain and rt8191
        res["reference_compare"] = dict(gds=cmp_gds, svrf_equal=svrf_same, reference_commercial_chip_sha_matches=ref_chain,
                                        strmout_8191_vs_this_chip_identical=rt8191, evidence_applies=applies)
        # 截圖沒有 GDS 雜湊可追，只能比時間：port.py 以 copy2 複製二進位檔，保留參考專案的修改時間；參考 GDS 的產生時間在 BGNLIB（UTC）
        build = gds_build_utc(ref / "LUT4_chip.gds")
        shots = {n: datetime.fromtimestamp((out / n).stat().st_mtime, tz=timezone.utc) for n in SHOT_FILES}
        shot_note = dict(reference_gds_built_utc=build.isoformat(), shot_mtime_utc={n: v.isoformat() for n, v in shots.items()},
                         all_shots_older_than_reference_gds=all(v < build for v in shots.values()))
        draft_status = "只核對既有證據" if applies else "未驗證"
        s6 = json.loads(paths.OUT("lut4/s6_verify", "drc_result.json").read_text(encoding="utf-8"))
        delivered_drc = s6["total"] if s6["gds_sha256"] == res["chip_sha256"] else None     # s6 必須是對這一份 GDS 跑的
        res["status"] = dict(
            klayout_platform_deck=dict(
                status="本次通過" if res["checks"]["klayout_8191_clean"] and delivered_drc == 0 else "本次未通過",
                scope="本機 KLayout，平台 deck 全部類別",
                delivered_gds=delivered_drc,
                strmout_8191=kl["strmout_8191"]["total"],
                note="strmout_8191.gds 是既有證據檔；KLayout 對它的 DRC 為本次重跑"),
            klayout_strmout_200_raw_markers=dict(
                status="本次通過" if res["checks"]["raw_explains_200"] else "本次未通過",
                total=kl["strmout_200"]["total"], counts=kl["strmout_200"]["counts"],
                raw_experiment=raw["strmout_200"],
                note="maxVertices 200 匯出檔（既有證據）在 .raw 逐塊檢查下的標記；不是交付 GDS 的 DRC 結果，不與其他任何結果合併或相加；status 指「.raw 小實驗本次重現了這個數字」，不表示該匯出檔可用"),
            calibre_basic_svrf_draft=dict(
                status=draft_status, coverage=res["coverage"],
                applicability=("本次 GDS 與參考 GDS 幾何相同，既有證據適用；本次未在 EDA_Server 重跑" if applies
                               else "本次 GDS 或 SVRF 與參考不同，既有證據不適用於本次 GDS"),
                totals={t: v["total"] for t, v in res["calibre"].items()},
                note="教學用草案，只移植線寬、間距；不是晶圓廠驗證過的 deck，也未證明與 KLayout 版語意等價"),
            virtuoso_strmin_strmout=dict(
                status=draft_status,
                applicability=("strmout_8191.gds 與本次 GDS 逐層相同（本機比對）；本次未在 EDA_Server 重跑" if applies else "既有匯出檔不適用於本次 GDS")),
            platform_signoff=dict(status="原範圍待辦", note="平台沒有提供正式 Calibre 簽核 deck；KLayout 平台 deck 與 Calibre 基本草案都不是平台正式簽核"),
            virtuoso_rve_screenshots=dict(
                status="未驗證", files=list(SHOT_FILES), provenance=shot_note,
                note=("截圖沒有對應的 GDS 雜湊" + ("，而且拍攝時間早於參考 GDS 的產生時間，畫面來自更早的一版 GDS" if shot_note["all_shots_older_than_reference_gds"] else "")
                      + "；本次 GDS 與參考 GDS 幾何相同不能延伸到截圖，只當既有畫面")))
        res["checks"]["evidence_applies"] = applies
    if run_eda:                                                       # 本次實跑：留下工具版本、輸入雜湊、輸出雜湊與各項狀態
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        res["run_record"] = dict(
            mode="本次實跑：EDA_Server 批次執行 strmin、strmout（200／8191）、Calibre 四份 GDS",
            origin="2026-11-07 使用者授權對本次 LUT4 GDS 重跑",
            tools=dict(virtuoso="IC231 ISR15（strmin／strmout）", calibre="aok_cal_2026.1_17.11", host="WSL EDA_Server"),
            inputs=dict(chip_sha256=sha(chip), fault_sha256=sha(fault)),
            calibre_run_times={t: re.search(r"^Execution Date/Time:\s+(.+?)\s*$", (out / f"calibre_{t}.summary").read_text(errors="replace"), re.M).group(1) for t in gds_in},
            outputs_sha256={n: sha(out / n) for n in EVIDENCE_FILES})
        good = all(res["checks"].values())
        res["status"] = dict(
            klayout_platform_deck=dict(status="本次通過" if res["checks"]["klayout_8191_clean"] else "本次未通過", strmout_8191=res["klayout"]["strmout_8191"]["total"]),
            klayout_strmout_200_raw_markers=dict(status="本次通過" if res["checks"]["raw_explains_200"] else "本次未通過", total=res["klayout"]["strmout_200"]["total"],
                                                 note="maxVertices 200 匯出檔在 .raw 逐塊檢查下的標記，不是交付 GDS 的 DRC 結果"),
            calibre_basic_svrf_draft=dict(status="本次通過" if good else "本次未通過", coverage=res["coverage"],
                                          totals={t: res["calibre"][t]["total"] for t in gds_in}, note="教學用草案，只移植線寬與間距，不是晶圓廠驗證過的 deck"),
            virtuoso_strmin_strmout=dict(status="本次通過" if res["checks"]["roundtrip_8191_identical"] else "本次未通過"),
            platform_signoff=dict(status="原範圍待辦", note="平台沒有提供正式 Calibre 簽核 deck；KLayout 平台 deck 與 Calibre 草案都不是製程簽核"))
        paths.OUT(STEP, "eda_run_record.json").write_text(json.dumps(res["run_record"], ensure_ascii=False, indent=1), encoding="utf-8")
    paths.OUT(STEP, "commercial.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SVRF 草案：移植 {len(rules)}/{n_total} 個 output 敘述（deck 共 {res['deck_categories']} 個檢查類別）；未移植：{not_ported}")
    for t, v in res["calibre"].items():
        print(f"Calibre {t}：{v['total']} 個結果 {({k: n for k, n in v['by_rule'].items() if n})}")
    for t, v in kl.items():
        print(f"KLayout {t}：違規 {v['total']} {v['counts']}")
    for t, v0 in rt_cmp.items():
        print(f"來回 {t}：" + "、".join(f"GDS {l} {v['n_orig']}→{v['n_out']} 塊、差 {v['sym_diff_um2']:g} µm²" for l, v in v0["layers"].items())
              + f"；cell {v0['n_cells']} 相同 {v0['cells_equal']}、文字 {v0['n_texts']} 相同 {v0['texts_equal']}")
    print(f".raw 小實驗（GDS 3 線寬／間距）：{raw}；合併後 GDS 3 塊數（原檔、200 匯出）{merged_200['pieces_merged']}")
    print(f"匯入匯出紀錄：{warn}")
    print(f"一致性：{res['checks']}")
    if evidence:
        c_ = res["reference_compare"]
        for t, v in c_["gds"].items():
            print(f"{t} vs 參考：去時間戳位元組相同 {v['bytes_equal_except_timestamps']}、逐層相同 {v['identical']}、"
                  f"多邊形 { {l: x['n_this'] for l, x in v['layers'].items()} }、cell {v['n_cells']}、文字 {v['n_texts']}")
        print(f"SVRF 與參考相同：{c_['svrf_equal']}；既有證據適用：{c_['evidence_applies']}")
        for k, v in res["status"].items():
            print(f"狀態 {k}：{v['status']}")
    sys.exit(0 if all(res["checks"].values()) else 1)


if __name__ == "__main__":
    main()
