r"""連接檢查：DRC 與連接檢查——能不能製造？每個 heater 真的接到對的 PAD 嗎？光真的接到對的 EC 嗎？

用途：只讀 晶片整合 的 chip.gds（多邊形與文字標記），與規格（原理圖）比對：
  1. DRC：KLayout 平台 deck，設計區＝晶片尺寸（宣告值）；另查 GDS 99 只有一個且等於晶片外框、所有圖形在外框內。
  2. 核心未被改動：晶片中 LUT4 核心的多邊形，與 佈局審查 審查過的 l4_core.gds 逐一相同（雜湊比對）。
  3. 電氣連接（LVS）：Ti/AL（GDS 41）與 TiN（GDS 39）各自聯集成連通塊；Ti/AL 直接壓在 TiN 上（無 via），兩者重疊就是接點。
     每塊 Ti/AL 以其中的 PAD 文字標記命名；每塊 TiN 以最近的「H」標記命名。原理圖：heater Hn 一端接 Pn、另一端接 GND（任一個 GN／GS PAD）；GND 配對（哪兩個 heater 共用一個 GND PAD）另與 PAD 表比對。
     檢查：14 個 heater 各恰有兩個接點、分屬訊號網與地網；訊號網只接到自己的 heater；沒有一塊 Ti/AL 含兩個 PAD（短路）。
     走線電阻與相位誤差由 gnd_net.py 的節點分析求得（依每段長、寬、厚度，含共用地線與多路同時驅動）；結果在 electrical.gnd_network。
  4. 光學連接：GDS 3 與 GDS 5（EC 的薄矽尖端）聯集（MMI cell 不展開，否則全部經 MMI 連成一塊）；每個 EC 端面所在的連通塊恰好含一個核心光學埠，
     且 EC 的標記（訊號_埠名）與核心埠名一致、訊號與規格（spec.json）一致。
  5. 故障注入（必須全部被抓到）：Ti/AL 短路、Ti/AL 斷路、TiN 斷路、原理圖對調、PAD 標記對調、EC 標記對調（在讀回的圖形與標記上修改）；
     以及寫出一份加了「1 µm 寬的 Ti/AL」與「相距 5 µm 的兩塊 TiN」的 GDS，KLayout DRC 必須報出對應規則。
輸入：晶片整合 的 out/chip.gds、out/chip_info.json；LUT4 s3 的 out/l4_core.gds、out/layout_info.json；M2 s1 的 out/spec.json。
輸出：out/drc_result.json、out/connectivity.json、out/gnd_segments.json、out/chip_fault_drc.gds（DRC 故障注入用）與 out/chip_fault_drc_drc.lyrdb。
執行：.\lab design\m3_layout\s4_verify\verify.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import copy                                                          # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from shapely.geometry import Point, Polygon, box                     # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import drc                                               # noqa: E402
from common import gds2png as G                                      # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gnd_net                                                       # noqa: E402

STEP = "lut4/s6_verify"
CHIP = "lut4/s5_chip"
CORE = "lut4/s3_core"
RHO_AL = gnd_net.RHO_AL  # Ti/AL 電阻率（Ω·m，以純鋁估；Ti 層忽略）


def flat_all(structs, name, M, T, polys, texts, skip=()):
    st = structs[name]
    for layer, xy in st["boundaries"]:
        polys.append((layer, xy @ M.T + T))
    for layer, xy, s in st["texts"]:
        texts.append((layer, M @ xy + T, s))
    for s in st["srefs"]:
        if s["sname"] in skip:
            continue
        M2, T2 = G.affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        flat_all(structs, s["sname"], M @ M2, M @ T2 + T, polys, texts, skip)


def load(gds, top, skip=()):
    structs, dbu = G.parse(str(gds))
    sc = dbu / 1e-6
    polys, texts = [], []
    flat_all(structs, top, np.eye(2), np.zeros(2), polys, texts, skip)
    return structs, sc, [(l, xy * sc) for l, xy in polys], [(xy * sc, s) for l, xy, s in texts if l == 100]


def parts(geom):
    return list(geom.geoms) if hasattr(geom, "geoms") else ([] if geom.is_empty else [geom])


def core_hash(structs, sc, top):
    """一個 cell（含子 cell 攤平）的多邊形雜湊：各層頂點取到 1 nm 後排序。"""
    polys, texts = [], []
    flat_all(structs, top, np.eye(2), np.zeros(2), polys, texts)
    keys = sorted(f"{l}:" + ",".join(f"{x:.3f}/{y:.3f}" for x, y in np.round(xy * sc, 3)) for l, xy in polys)
    return hashlib.sha256("|".join(keys).encode()).hexdigest(), len(keys)


def electrical(polys, texts, pad_names):
    al = parts(unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 41]))
    tin = parts(unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 39]))
    al_name = []
    for g in al:
        labs = [s for xy, s in texts if s in pad_names and g.contains(Point(xy))]
        al_name.append(labs)
    hs = [(xy, s) for xy, s in texts if s.startswith("H")]
    heaters = []
    for t in tin:
        c = t.centroid
        xy, lab = min(hs, key=lambda h: np.hypot(h[0][0] - c.x, h[0][1] - c.y))
        contacts = [i for i, g in enumerate(al) if g.intersection(t).area > 1e-6]
        heaters.append(dict(label=lab, contacts=contacts, nets=["+".join(al_name[i]) or f"未命名{i}" for i in contacts]))
    return al, tin, al_name, heaters


def lvs(al_name, heaters, schematic, gnd_names):
    """與原理圖比對；回傳逐 heater 結果與錯誤清單。"""
    errs = []
    shorts = [n for n in al_name if len(n) > 1]
    if shorts:
        errs.append(f"短路：一塊 Ti/AL 含 {shorts}")
    floating = [i for i, n in enumerate(al_name) if not n]
    if floating:
        errs.append(f"有 {len(floating)} 塊 Ti/AL 沒有 PAD")
    rows = []
    seen = {}
    for h in heaters:
        want = schematic.get(h["label"])
        ok = want is not None and len(h["contacts"]) == 2
        if ok:
            sig = [n for n in h["nets"] if n == want]
            gnd = [n for n in h["nets"] if n in gnd_names]
            ok = len(sig) == 1 and len(gnd) == 1
        rows.append(dict(heater=h["label"], contacts=len(h["contacts"]), nets=h["nets"], expect=[want, "GND"], ok=bool(ok)))
        seen[h["label"]] = seen.get(h["label"], 0) + 1
        for n in h["nets"]:
            if n not in gnd_names and n != want:
                errs.append(f"{h['label']} 接到 {n}（原理圖為 {want}）")
    missing = [k for k in schematic if k not in seen]
    if missing or any(v != 1 for v in seen.values()):
        errs.append(f"heater 數目不符：缺 {missing}，重複 {[k for k, v in seen.items() if v != 1]}")
    errs += [f"{r['heater']} 接點 {r['contacts']} 個、網 {r['nets']}" for r in rows if not r["ok"]]
    return rows, errs


def optical(polys, texts, ecs, ports_core, die_x, spec_sig):
    """spec_sig：規格的 {核心埠名: 訊號}；EC 標記的訊號與埠都要和規格一致（先前審查 R13：原本比的是畫圖時的變數）。"""
    wg = parts(unary_union([Polygon(xy).buffer(0) for l, xy in polys if l in (3, 5)]))
    rows, errs = [], []
    ec_labels = [(xy, s) for xy, s in texts if "_" in s and (s.split("_")[1].startswith(("in", "out")))]
    for e in ecs:
        fx, fy = e["facet_um"]
        p = Point(fx + (0.05 if e["side"] == "W" else -0.05), fy)
        comp = [g for g in wg if g.distance(p) < 1e-3]
        lab = min(ec_labels, key=lambda t: np.hypot(t[0][0] - fx, t[0][1] - fy))[1]
        hits = [n for n, xy in ports_core.items() if comp and comp[0].distance(Point(xy)) < 1e-3] if comp else []
        ok = len(comp) == 1 and len(hits) == 1 and lab.split("_")[1] == hits[0] and lab.split("_")[0] == spec_sig.get(hits[0])
        rows.append(dict(ec=lab, side=e["side"], core_port=hits, ok=bool(ok)))
        if not ok:
            errs.append(f"EC {lab}：接到 {hits}")
    return rows, errs


def main():
    info = json.loads(paths.OUT(CHIP, "chip_info.json").read_text(encoding="utf-8"))
    linfo = json.loads(paths.OUT(CORE, "layout_info.json").read_text(encoding="utf-8"))
    spec = json.loads(paths.OUT("lut4/s1_handoff", "spec.json").read_text(encoding="utf-8"))
    gds = paths.OUT(CHIP, "chip.gds")
    die = tuple(info["die_um"])
    XW, XE = info["die_x_um"]
    YB, YT = info["die_y_um"]

    # ---------- 1. DRC ----------
    d = drc.run(gds, design_area=die)
    structs, sc, polys, texts = load(gds, "L4_CHIP")
    g99 = [xy for l, xy in polys if l == 99]
    die_poly = box(XW, YB, XE, YT)
    one_frame = len(g99) == 1 and Polygon(g99[0]).symmetric_difference(die_poly).area < 1e-6
    drc_res = dict(gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(), deck=paths.DRC_DECK.name, n_rules=len(d["rules"]),
                   total=d["total"], counts=d["counts"], design_area_um=d["design_area_um"], design_area_source=d["design_area_source"],
                   outside=d["outside"], n_gds99=len(g99), gds99_is_die=one_frame, rules=d["rules"])

    # ---------- 2. 核心未被改動 ----------
    cs_, csc = G.parse(str(paths.OUT(CORE, "l4_core.gds")))
    # IPKISS 匯入 GDS 時會改 cell 名稱（核心變成 PCELL_n、子 cell 加前綴），所以用內容找：引用了 MZI cell 的那一個
    core_in_chip = next(s["sname"] for s in structs["L4_CHIP"]["srefs"]
                        if any(r["sname"].endswith(linfo["cells"]["mzi"]) for r in structs[s["sname"]]["srefs"]))
    h_chip, n_chip = core_hash(structs, sc, core_in_chip)
    h_core, n_core = core_hash(cs_, csc / 1e-6, linfo["cells"]["core"])
    core_same = h_chip == h_core

    # ---------- 3. 電氣（LVS）----------
    pad_names = {p["name"] for p in info["pads"]}
    gnd_names = {p["name"] for p in info["pads"] if p["heater"] is None}
    schematic = {c["heater"]: c["pad"] for c in spec["phase_channels"]}
    al, tin, al_name, heaters = electrical(polys, texts, pad_names)
    rows, errs = lvs(al_name, heaters, schematic, gnd_names)
    # 舊估算（線寬一律 wire_width_um、每個 heater 獨立串聯、含伸入 PAD 的 20 µm）只留在 superseded 供追溯；2026-11-07 起以節點分析為準
    r_route = {r["net"] + "/" + r["heater"]: round(RHO_AL * r["length_um"] * 1e-6 / (info["wire_width_um"] * 1e-6 * info["al_thickness_um"] * 1e-6), 2)
               for r in info["routes"]}
    r_series = {}
    for r in info["routes"]:
        r_series[r["heater"]] = round(r_series.get(r["heater"], 0.0) + r_route[r["net"] + "/" + r["heater"]], 2)
    gn = gnd_net.analyze(info, linfo, spec, json.loads(paths.OUT(f"{STEP.split('/')[0]}/s1_handoff", "phases.json").read_text(encoding="utf-8")),
                         paths.OUT(f"{STEP.split('/')[0]}/s0_coverage", "merged_phases.npz"), al, al_name, paths.OUT(STEP, "gnd_segments.json"))
    # GND 配對：從佈局抽出的「哪些 heater 接到同一個 GND 網」要和 chip_info 的 PAD 表一致（M3 關卡審查 R19）
    gnd_ext = {}
    for row in rows:
        for n in row["nets"]:
            if n in gnd_names:
                gnd_ext.setdefault(n, set()).add(row["heater"])
    gnd_info = {p["name"]: set(p["heaters"]) for p in info["pads"] if p["heater"] is None}
    gnd_pairing_ok = gnd_ext == gnd_info
    gc = gn["gds_check"]
    gnd_model_ok = (gc["centerline_outside_metal_um"] == 0 and gc["width_mismatch"] == 0 and gc["width_samples"] > 0
                    and {k: set(v) for k, v in gn["gnd_mutual_ohm"].items()} == gnd_ext)

    # ---------- 4. 光學 ----------
    ports_core = {s: (xy[0] - (8 if s.startswith("in") else -8), xy[1] - 3) for xy, s in texts
                  if s[:2] in ("in", "ou") and s.rstrip("0123456789") in ("in", "out")}   # 核心埠標記在埠內側 8 µm、上方 3 µm
    mmi_cells = {n for n in structs if n.endswith(linfo["cells"]["mmi"])}   # MMI 不展開：否則所有波導經 MMI 連成一塊
    _, _, polys_o, _ = load(gds, "L4_CHIP", skip=mmi_cells)
    spec_sig = {o["port"]: o["signal"] for o in spec["optical_ports"]}
    o_rows, o_errs = optical(polys_o, texts, info["ec"], ports_core, (XW, XE), spec_sig)

    # ---------- 5. 故障注入 ----------
    faults = {}
    sig_routes = sorted([r for r in info["routes"] if r["role"] == "sig" and r["side"] == "N"], key=lambda r: r["target"])
    a, b = sig_routes[0], sig_routes[1]
    yb = 200.0
    bridge = box(a["target"], yb - 5, b["target"], yb + 5)
    p_short = polys + [(41, np.array(bridge.exterior.coords))]
    _, _, n1, h1 = electrical(p_short, texts, pad_names)
    faults["Ti/AL 短路"] = bool(lvs(n1, h1, schematic, gnd_names)[1])
    yc_ = 390.0                                                       # PAD 下方的垂直段（LUT4：轉折錯開後 y＝200 處是斜線）
    cut = box(a["target"] - 20, yc_ - 8, a["target"] + 20, yc_ + 8)
    p_open = [(l, np.array(Polygon(xy).buffer(0).difference(cut).exterior.coords)) if l == 41 and Polygon(xy).buffer(0).intersects(cut)
              and not Polygon(xy).buffer(0).difference(cut).is_empty and Polygon(xy).buffer(0).difference(cut).geom_type == "Polygon"
              else (l, xy) for l, xy in polys]
    # 斷路後同一塊可能分成兩塊，改用整體做差集
    al_cut = [Polygon(xy).buffer(0).difference(cut) for l, xy in polys if l == 41]
    p_open = [(l, xy) for l, xy in polys if l != 41] + [(41, np.array(g.exterior.coords)) for x in al_cut for g in parts(x)]
    _, _, n2, h2 = electrical(p_open, texts, pad_names)
    faults["Ti/AL 斷路"] = bool(lvs(n2, h2, schematic, gnd_names)[1])
    h0 = next(h for h in linfo["heaters"] if h["heater"] == "H01")   # 依名稱取 H01（先前審查 R12）
    xm = sum(h0["body_um"]) / 2
    tcut = box(xm - 2, h0["y_um"] - 2, xm + 2, h0["y_um"] + 2)
    tin_cut = [Polygon(xy).buffer(0).difference(tcut) for l, xy in polys if l == 39]
    p_tin = [(l, xy) for l, xy in polys if l != 39] + [(39, np.array(g.exterior.coords)) for x in tin_cut for g in parts(x)]
    _, _, n3, h3 = electrical(p_tin, texts, pad_names)
    faults["TiN 斷路"] = bool(lvs(n3, h3, schematic, gnd_names)[1])
    sch_bad = dict(schematic)
    sch_bad["H01"], sch_bad["H02"] = schematic["H02"], schematic["H01"]
    faults["原理圖對調"] = bool(lvs(al_name, heaters, sch_bad, gnd_names)[1])
    t_bad = [(xy, {"P01": "P02", "P02": "P01"}.get(s, s)) for xy, s in texts]
    _, _, n5, h5 = electrical(polys, t_bad, pad_names)
    faults["PAD 標記對調"] = bool(lvs(n5, h5, schematic, gnd_names)[1])
    e_bad = [(xy, {"x1_in0": "x2_in0", "x2_in1": "x1_in1"}.get(s, s)) for xy, s in texts]
    faults["EC 標記對調"] = bool(optical(polys_o, e_bad, info["ec"], ports_core, (XW, XE), spec_sig)[1])

    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)
    import cornerstone.all as cs
    import ipkiss3.all as i3
    T = cs.TECH.PPLAYER
    chip_ref = i3.GDSCell(filename=str(gds), cell_name="L4_CHIP")
    x0 = XW + 900
    bad = i3.LayoutCell(name="L4_CHIP_FAULT")
    bad.Layout(elements=[i3.SRef(reference=chip_ref),
                         i3.Rectangle(layer=T.PAD, center=(x0, YT - 15), box_size=(40.0, 1.0)),        # 1 µm 寬 Ti/AL（PAD 列外側到晶片邊的空地）
                         i3.Rectangle(layer=T.HT, center=(x0 + 200, YT - 18), box_size=(20.0, 2.0)),   # 兩塊 TiN 相距 5 µm
                         i3.Rectangle(layer=T.HT, center=(x0 + 200, YT - 11), box_size=(20.0, 2.0))])
    fg = paths.OUT(STEP, "chip_fault_drc.gds")
    bad.get_default_view(i3.LayoutView).write_gdsii(str(fg))
    fd = drc.run(fg, design_area=die)
    want_rules = {k for k in fd["counts"] if "GDS41<2" in k or "GDS39<10" in k}
    faults["DRC：Ti/AL 太窄"] = any("GDS41<2" in k for k in fd["counts"])
    faults["DRC：TiN 太近"] = any("GDS39<10" in k for k in fd["counts"])
    drc_res["fault_injection"] = dict(gds=fg.name, counts=fd["counts"], caught=sorted(want_rules))

    checks = dict(drc_clean=d["total"] == 0 and not d["outside"], one_gds99=one_frame, core_unchanged=core_same,
                  n_al_nets=len(al) == len(pad_names), n_heaters=len(tin) == 14, lvs_clean=not errs,
                  every_heater_two_contacts=all(r["contacts"] == 2 for r in rows), optical_clean=not o_errs and len(o_rows) == 10,
                  gnd_pairing=gnd_pairing_ok, gnd_model_matches_gds=gnd_model_ok, faults_caught=all(faults.values()))
    conn = dict(gds_sha256=drc_res["gds_sha256"], core_sha_match=core_same, core_polygons=[n_chip, n_core],
                electrical=dict(al_nets=len(al), tin_regions=len(tin), pads=sorted(pad_names), gnd_pads=sorted(gnd_names),
                                channels=rows, errors=errs, gnd_network=gn,
                                superseded_series_estimate=dict(
                                    note="已被 gnd_network 取代，只供追溯，不可引用：線寬一律用 wire_width_um、共地出線只算給一個 heater、未解共享回流電流",
                                    legacy_route_ohm=r_route, legacy_series_ohm=r_series),
                                gnd_pairing={k: sorted(v) for k, v in sorted(gnd_ext.items())},
                                note="各 GND PAD（GN1…、GS1…）在晶片上互不相連，量測時每個 GND PAD 都要接到驅動器的地"),
                optical=dict(ec=o_rows, errors=o_errs), faults=faults, checks=checks)
    paths.OUT(STEP, "drc_result.json").write_text(json.dumps(drc_res, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.OUT(STEP, "connectivity.json").write_text(json.dumps(conn, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"DRC：{len(d['rules'])} 條規則，違規 {d['total']}；設計區 {d['design_area_um']}（{d['design_area_source']}）；外框外 {d['outside']}；"
          f"GDS 99 {len(g99)} 個（等於晶片外框：{one_frame}）")
    print(f"核心與審查版本相同：{core_same}（多邊形 {n_chip}／{n_core}）")
    print(f"電氣：Ti/AL {len(al)} 網、TiN {len(tin)} 塊；" + "、".join(f"{r['heater']}→{'/'.join(r['nets'])}" for r in rows[:4]) + f" …；錯誤 {len(errs)}")
    w = gn["worst"]
    print(f"回路節點分析（模型值，heater 1 kΩ、2π）：單路最差 {w['single_rad']:.3f} rad；14 路同時最差 {w['multi_rad']:.3f} rad（{w['multi_heater']}）；"
          f"單路校正後殘差最差 {w['residual_rad']:.3f} rad（{w['residual_heater']}）；線段 {gn['n_segments']} 段，GDS 線寬不符 {gc['width_mismatch']}")
    print(f"GND 配對（從佈局抽出）：{ {k: sorted(v) for k, v in sorted(gnd_ext.items())} }，與 PAD 表一致：{gnd_pairing_ok}")
    print(f"光學：{sum(r['ok'] for r in o_rows)}/{len(o_rows)} 個 EC 接到對的核心埠")
    print(f"故障注入：{faults}")
    print(f"一致性：{checks}")
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'drc_result.json'))}、connectivity.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
