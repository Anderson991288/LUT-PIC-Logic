r"""M3 s1：IPKISS 佈局：B7 核心——電路連接怎麼變成實體幾何？

用途：依接線表（7 顆 MZI 的位置）與元件清單（PDK 的 2×2 MMI、加熱條），用 IPKISS 畫出 B7 核心的 GDS：
  1. 一顆 MZI cell：上下兩軌間距 PITCH；φ 相位區在上軌輸入段、θ 相位區在上臂；兩顆 MMI 前後以 cosine S 彎接到軌上；
     上下兩臂幾何對稱（等長）。heater 依元件清單自建（PDK 加熱條的接點過不了平台 DRC，見 M2 s2）：
     TiN 條 0.9×100 µm 蓋在相位區的波導上；兩端各以 TiN 短條往上（遠離下臂）引到 10×10 µm 的 TiN 落墊，
     再蓋 11×12 µm 的 Ti/AL 接點（PAD 層直接壓在 TiN 上，無 via）；金屬不蓋在波導上。
  2. B7：4 欄（層），每欄長度＝一顆 MZI；第 l 層、上方波導 p 的 MZI 放在 (l·L_MZI, −p·PITCH)；
     該欄沒有 MZI 的軌用直波導通過；兩端各加一段引線，埠 in0–in4（西）、out0–out4（東）。
  3. 波導寬度取 PDK MMI 埠的寬度（避免接點寬度跳變）；所有點四捨五入到 1 nm。
  4. GDS 100 文字標出 MZI、heater 編號（H01–H14，依規格）與光學埠；GDS 99 外框只畫在另一個 DRC 用的副本
     （核心會被整顆晶片引用，晶片只能有一個 GDS 99）。
  5. 讀回 GDS 核對（不使用畫圖時的變數，只看 GDS 裡的實際位置）：
       MMI、heater 的個數；由 MMI 位置推回每顆 MZI 的（層, 上方波導），與接線表比對；
       由加熱條位置推回（MZI, θ／φ），與規格的 heater 編號比對；光學埠由 GDS 的文字標記取位置，名稱、邊緣與上下順序與規格比對。
  6. 幾何檢查：波導端點與 MMI 埠的接點誤差、上下臂長度差、S 彎最小曲率半徑（≥ 10 µm）、每欄 MZI 軌與直通軌的長度差；
     KLayout DRC（設計區量 GDS 99 外框；正式設計區在 M3 s4 給定）。
  7. 故障注入：把預期改錯（MZI-3 換層、H01／H02 對調）或把 GDS 的 in0／in1 標記對調，讀回比對必須抓到。
輸入：M1 s5 的 out/b7_netlist.json；M2 s1 的 out/spec.json；M2 s2 的 out/components.json；CORNERSTONE PDK。
輸出：out/b7_core.gds（交給後續步驟）、out/b7_core_framed.gds（加外框，只給本步 DRC）、out/b7_core_framed_drc.lyrdb、
      out/layout_info.json（埠位表、MZI 位置、heater 位置、落墊座標與編號、檢查結果）。
執行：.\lab design\m3_layout\s1_core\layout.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common import drc                                               # noqa: E402
from common import gds2png as G                                      # noqa: E402

STEP = "m3_layout/s1_core"
PITCH = 30.0            # 軌距（µm）：heater 落點與間距、熱串擾與 M3 s3 繞線空間的折衷
SB = 40.0               # S 彎水平長度（µm）
STUB = 0.5              # S 彎兩端的水平短段（避免接縫處的楔形縫）
MARGIN = 10.0           # 加熱條兩端到相位區邊緣的距離（µm）
LEAD = 50.0             # 核心兩端引線長度（µm）
FRAME = 20.0            # GDS 99 外框到最外側圖形的距離（µm）
R_MIN = 10.0            # 條形波導最小彎曲半徑（µm，平台截面規範）
NPTS = 61               # 每個 S 彎的取樣點數
STUB_W = 3.0            # heater 端點 TiN 引出短條寬（µm）：比加熱條寬，電阻與發熱集中在加熱條
LAND_OFF = 16.0         # 落墊中心離軌道的距離（µm，往上）：落墊下緣到加熱條上緣 ≥ 10 µm，否則同一塊 TiN 的凹口違反間距規則
LAND_TIN = 10.0         # TiN 落墊邊長（µm）
LAND_AL = (11.0, 12.0)  # Ti/AL 接點（寬, 高）（µm）


def r3(pts):
    return [(round(float(x), 3), round(float(y), 3)) for x, y in pts]


def sbend(x0, y0, y1):
    """cosine S 彎：x0 → x0＋SB，y0 → y1；兩端各有 STUB 的水平段。"""
    t = np.linspace(0, 1, NPTS)
    L = SB - 2 * STUB
    pts = [(x0, y0)] + [(x0 + STUB + L * u, y0 + (y1 - y0) * (1 - np.cos(np.pi * u)) / 2) for u in t] + [(x0 + SB, y1)]
    return pts


def sbend_rmin(dy):
    """cosine S 彎的最小曲率半徑＝2L²／(π²|Δy|)。"""
    L = SB - 2 * STUB
    return 2 * L ** 2 / (np.pi ** 2 * abs(dy))


def plen(pts):
    p = np.array(pts)
    return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))


def join(*parts):
    out = list(parts[0])
    for p in parts[1:]:
        out += list(p[1:]) if np.allclose(out[-1], p[0]) else list(p)
    return out


def build(cs, i3, net, spec, h_len, h_w):
    mmi = cs.SOI220nm_1550nm_TE_STRIP_2x2_MMI()
    ml = mmi.Layout()
    mp = {p.name: (float(p.position.x), float(p.position.y)) for p in ml.ports}
    width = float(ml.ports["in1"].trace_template.core_width)
    assert mp["in2"][1] > mp["in1"][1] and mp["out2"][1] > mp["out1"][1], "PDK 上方埠應為 in2／out2"
    LPH = round(h_len + 2 * MARGIN, 3)                                # 相位區長度

    def rect(layer, x0, y0, x1, y1):
        return i3.Rectangle(layer=layer, center=((x0 + x1) / 2, (y0 + y1) / 2), box_size=(abs(x1 - x0), abs(y1 - y0)))

    HT, PAD = cs.TECH.PPLAYER.HT, cs.TECH.PPLAYER.PAD
    h_el = [rect(HT, 0, -h_w / 2, h_len, h_w / 2)]                    # 加熱條本體（原點＝本體起點、軌道中心）
    for xe in (0.0, h_len):
        h_el += [rect(HT, xe - STUB_W / 2, -h_w / 2, xe + STUB_W / 2, LAND_OFF),
                 rect(HT, xe - LAND_TIN / 2, LAND_OFF - LAND_TIN / 2, xe + LAND_TIN / 2, LAND_OFF + LAND_TIN / 2),
                 rect(PAD, xe - LAND_AL[0] / 2, LAND_OFF - LAND_AL[1] / 2, xe + LAND_AL[0] / 2, LAND_OFF + LAND_AL[1] / 2)]
    heater = i3.LayoutCell(name="B7_HEATER")
    heater.Layout(elements=h_el)

    tpl = cs.StripWaveguideTemplate()
    tpl.Layout(core_width=width)

    def wg(pts):
        w = i3.Waveguide(trace_template=tpl)
        w.Layout(shape=r3(pts))
        return w

    # ---------- 單顆 MZI（區域座標：上軌 y＝0、下軌 y＝−PITCH）----------
    top, bot, mid = 0.0, -PITCH, -PITCH / 2
    mmi_len = mp["out2"][0] - mp["in2"][0]
    xa = LPH + SB                                                     # MMI1 輸入
    xb = xa + mmi_len                                                 # MMI1 輸出
    xc = xb + 2 * SB + LPH                                            # MMI2 輸入
    xd = xc + mmi_len                                                 # MMI2 輸出
    L_MZI = round(xd + SB, 3)
    paths_ = dict(
        in_top=join([(0, top), (LPH, top)], sbend(LPH, top, mid + mp["in2"][1])),
        in_bot=join([(0, bot), (LPH, bot)], sbend(LPH, bot, mid + mp["in1"][1])),
        arm_top=join(sbend(xb, mid + mp["out2"][1], top), [(xb + SB, top), (xb + SB + LPH, top)],
                     sbend(xb + SB + LPH, top, mid + mp["in2"][1])),
        arm_bot=join(sbend(xb, mid + mp["out1"][1], bot), [(xb + SB, bot), (xb + SB + LPH, bot)],
                     sbend(xb + SB + LPH, bot, mid + mp["in1"][1])),
        out_top=sbend(xd, mid + mp["out2"][1], top),
        out_bot=sbend(xd, mid + mp["out1"][1], bot),
    )
    mmi_org = [(xa - mp["in2"][0], mid), (xc - mp["in2"][0], mid)]
    # 接點誤差：每段波導的端點對到 MMI 埠
    want = dict(in_top=(None, ("in2", 0)), in_bot=(None, ("in1", 0)), arm_top=(("out2", 0), ("in2", 1)),
                arm_bot=(("out1", 0), ("in1", 1)), out_top=(("out2", 1), None), out_bot=(("out1", 1), None))
    join_err = 0.0
    for k, (a, b) in want.items():
        pts = r3(paths_[k])
        for end, w in ((pts[0], a), (pts[-1], b)):
            if w:
                (pn, m) = w
                target = (mmi_org[m][0] + mp[pn][0], mmi_org[m][1] + mp[pn][1])
                join_err = max(join_err, float(np.hypot(end[0] - target[0], end[1] - target[1])))
    h_phi = (MARGIN, top)                                             # heater cell 原點＝本體起點
    h_theta = (xb + SB + MARGIN, top)
    elems = [i3.SRef(reference=mmi, position=o, name=f"MMI{k + 1}") for k, o in enumerate(mmi_org)]
    elems += [i3.SRef(reference=wg(p), name=n) for n, p in paths_.items()]
    elems += [i3.SRef(reference=heater, position=h_phi, name="H_phi"), i3.SRef(reference=heater, position=h_theta, name="H_theta")]
    mzi = i3.LayoutCell(name="B7_MZI")
    mzi.Layout(elements=elems)

    # ---------- B7 ----------
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    n_wg, n_lay = net["n_waveguides"], 1 + max(l for _, l in ops)
    end = n_lay * L_MZI
    y = [-k * PITCH for k in range(n_wg)]
    chan = {(c["mzi"], c["kind"]): c for c in spec["phase_channels"]}
    lbl = i3.PPLayer(cs.TECH.PROCESS.NONE, cs.TECH.PURPOSE.LBL)
    outline = i3.PPLayer(cs.TECH.PROCESS.NONE, cs.TECH.PURPOSE.CELL)
    elems, placement, heaters, labels = [], [], [], []
    for (p, l), m in zip(ops, net["mzis"]):
        org = (l * L_MZI, y[p])
        elems.append(i3.SRef(reference=mzi, position=org, name=m["name"].replace("-", "")))
        placement.append(dict(mzi=m["name"], layer=l + 1, waveguides=[p + 1, p + 2], origin_um=list(org)))
        labels.append((m["name"], (org[0] + xa + mmi_len / 2, org[1] + mid)))
        for kind, hpos in (("phi", h_phi), ("theta", h_theta)):
            c = chan[(m["name"], kind)]
            x0 = org[0] + hpos[0]
            heaters.append(dict(heater=c["heater"], pad=c["pad"], mzi=m["name"], kind=kind, phase=c["phase"],
                                origin_um=[round(x0, 3), round(org[1] + hpos[1], 3)],
                                body_um=[round(x0, 3), round(x0 + h_len, 3)], y_um=org[1],
                                landings_um=[[round(x0, 3), round(org[1] + LAND_OFF, 3)],
                                             [round(x0 + h_len, 3), round(org[1] + LAND_OFF, 3)]]))
            labels.append((c["heater"], (x0 + h_len / 2, org[1] + 4)))
    bypass = []
    for l in range(n_lay):
        busy = {r for p, ll in ops if ll == l for r in (p, p + 1)}
        for r in range(n_wg):
            if r not in busy:
                elems.append(i3.SRef(reference=wg([(l * L_MZI, y[r]), ((l + 1) * L_MZI, y[r])])))
                bypass.append(dict(layer=l + 1, waveguide=r + 1))
    for r in range(n_wg):
        elems.append(i3.SRef(reference=wg([(-LEAD, y[r]), (0, y[r])])))
        elems.append(i3.SRef(reference=wg([(end, y[r]), (end + LEAD, y[r])])))
    ins = {i["index"]: i for i in net["inputs"]}
    outs = {o["index"]: o for o in net["outputs"]}
    ports, port_tab = [], []
    for r in range(n_wg):
        for side, x, ang, rec in (("in", -LEAD, 180.0, ins[r + 1]), ("out", end + LEAD, 0.0, outs[r + 1])):
            name = rec["layout_port"]
            ports.append(i3.OpticalPort(name=name, position=(x, y[r]), angle=ang, trace_template=tpl))
            port_tab.append(dict(port=name, signal=rec.get("signal") or rec.get("name"), waveguide=r + 1,
                                 xy_um=[x, y[r]], angle=ang))
            labels.append((name, (x + (8 if side == "in" else -8), y[r] + 3)))
    y_top = LAND_OFF + LAND_AL[1] / 2 + FRAME                         # 上方要包住最上軌 heater 的落墊
    box = [(-LEAD - FRAME, y_top), (end + LEAD + FRAME, y_top), (end + LEAD + FRAME, y[-1] - FRAME), (-LEAD - FRAME, y[-1] - FRAME)]
    frame = i3.Boundary(layer=outline, shape=box)                     # 外框只放在 DRC 用的副本，不放進核心（M3 s4 發現晶片裡會有兩個 GDS 99）
    elems += [i3.Label(layer=lbl, text=t, coordinate=c, height=2.0) for t, c in labels]
    core = i3.LayoutCell(name="B7_CORE")
    core.Layout(elements=elems, ports=ports)

    geo = dict(pitch_um=PITCH, sbend_um=SB, phase_section_um=LPH, heater_margin_um=MARGIN, lead_um=LEAD,
               waveguide_width_um=width, mmi_length_um=mmi_len, mzi_length_um=L_MZI, columns=n_lay,
               core_size_um=[round(end + 2 * LEAD, 3), round((n_wg - 1) * PITCH, 3)],
               outline_um=[round(end + 2 * LEAD + 2 * FRAME, 3), round(y_top - (y[-1] - FRAME), 3)],
               heater_length_um=h_len, heater_width_um=h_w, stub_width_um=STUB_W, landing_offset_um=LAND_OFF,
               landing_tin_um=LAND_TIN, landing_al_um=list(LAND_AL),
               join_err_um=join_err, arm_len_um=[plen(paths_["arm_top"]), plen(paths_["arm_bot"])],
               sbend_dy_um=[abs(mid + mp["in2"][1] - top), abs(mid + mp["in1"][1] - bot)],
               sbend_rmin_um=min(sbend_rmin(mid + mp["in2"][1] - top), sbend_rmin(mid + mp["in1"][1] - bot)),
               rail_vs_bypass_extra_um=round(plen(paths_["in_top"]) + plen(paths_["arm_top"]) + plen(paths_["out_top"])
                                             + 2 * mmi_len - L_MZI, 4))
    names = dict(mmi=mmi.name, heater="B7_HEATER", mzi="B7_MZI", core="B7_CORE")
    framed = i3.LayoutCell(name="B7_CORE_FRAMED")
    framed.Layout(elements=[i3.SRef(reference=core), frame])
    return core, framed, geo, placement, heaters, port_tab, bypass, names


def walk(structs, name, M, T, hits, targets):
    """沿階層累積座標轉換，記下目標 cell 的實際原點。"""
    for s in structs[name]["srefs"]:
        M2, T2 = G.affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        o = M @ T2 + T
        if s["sname"] in targets:
            hits.setdefault(s["sname"], []).append(o)
        if s["sname"] in structs:
            walk(structs, s["sname"], M @ M2, o, hits, targets)


def readback(gds, names, geo, net, spec, heaters, swap=None):
    """只用 GDS 中的實際位置推回接線與 heater 對應，和接線表、規格比對。
    光學埠的位置取自 GDS 的文字標記（M3 審查 R9：原本用畫圖時的埠位表）；swap＝(名稱 a, 名稱 b) 時把兩個標記對調（故障注入）。"""
    structs, dbu = G.parse(str(gds))
    sc = dbu / 1e-6
    sw = dict([swap, swap[::-1]]) if swap else {}
    port_tab = []
    for layer, xy, s in structs[names["core"]]["texts"]:
        s = sw.get(s, s)
        if layer == 100 and s.rstrip("0123456789") in ("in", "out"):
            x, y = xy * sc
            port_tab.append(dict(port=s, xy_um=[float(x - 8 if s.startswith("in") else x + 8), float(y - 3)]))   # 標記在埠內側 8 µm、上方 3 µm
    hits = {}
    walk(structs, names["core"], np.eye(2), np.zeros(2), hits, {names["mmi"], names["heater"]})
    mmis = [o * sc for o in hits.get(names["mmi"], [])]
    hts = [o * sc for o in hits.get(names["heater"], [])]
    L, P = geo["mzi_length_um"], geo["pitch_um"]
    groups = {}
    for o in mmis:
        col = int(np.floor(o[0] / L + 1e-9))
        p = int(round(-o[1] / P - 0.5))
        groups.setdefault((p, col), []).append(o[0])
    found = sorted(groups)
    expect = sorted((m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"])
    name_of = {(m["waveguides"][0] - 1, m["layer"] - 1): m["name"] for m in net["mzis"]}
    # heater：落在哪一欄、哪一軌、在 MMI1 之前（φ）或兩顆 MMI 之間（θ）
    chan = {(c["mzi"], c["kind"]): c["heater"] for c in spec["phase_channels"]}
    inferred = {}
    for o in hts:
        col = int(np.floor(o[0] / L + 1e-9))
        r = int(round(-o[1] / P))
        key = (r, col)
        if key not in name_of:
            inferred[tuple(np.round(o, 3))] = None
            continue
        m1, m2 = sorted(groups[key])
        kind = "phi" if o[0] < m1 else ("theta" if o[0] < m2 else None)
        inferred[tuple(np.round(o, 3))] = chan.get((name_of[key], kind))
    heater_match = all(inferred.get(tuple(np.round(h["origin_um"], 3))) == h["heater"] for h in heaters)
    # 光學埠：名稱、邊緣、上下順序與規格一致
    sp = {p["port"]: p for p in spec["optical_ports"]}
    xs = [p["xy_um"][0] for p in port_tab]
    ok_ports = all(p["port"] in sp and (p["xy_um"][0] == min(xs)) == (sp[p["port"]]["direction"] == "輸入") for p in port_tab)
    for d in ("輸入", "輸出"):
        seq = [p["port"] for p in sorted(port_tab, key=lambda q: -q["xy_um"][1])
               if (p["xy_um"][0] == min(xs)) == (d == "輸入")]
        ok_ports &= seq == [p["port"] for p in spec["optical_ports"] if p["direction"] == d]
    return dict(n_mmi=len(mmis), n_heater=len(hts), mzi_found=[list(k) for k in found], mzi_match=found == expect,
                every_mzi_two_mmi=all(len(v) == 2 for v in groups.values()), heater_match=heater_match,
                heater_unmapped=sum(v is None for v in inferred.values()), ports_match=bool(ok_ports))


def main():
    hand = "m1_logic/s5_handoff"
    nb = paths.OUT(hand, "b7_netlist.json").read_bytes()
    net = json.loads(nb)
    spec = json.loads(paths.OUT("m2_circuit/s1_spec", "spec.json").read_text(encoding="utf-8"))
    comp = json.loads(paths.OUT("m2_circuit/s2_flow", "components.json").read_text(encoding="utf-8"))
    C = {c["id"]: c for c in comp["components"]}
    assert C["C1"]["decision"].startswith("PDK") and C["C1"]["pdk"]["cell"] == "SOI220nm_1550nm_TE_STRIP_2x2_MMI", "與元件清單不一致"
    assert C["C3"]["decision"].startswith("自建"), "元件清單的 heater 應為自建"
    h_len, h_w = comp["summary"]["heater_length_um"], comp["summary"]["heater_width_um"]

    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)              # 要在 import cornerstone 之前選定變體
    import cornerstone.all as cs
    import ipkiss3.all as i3

    core, framed, geo, placement, heaters, port_tab, bypass, names = build(cs, i3, net, spec, h_len, h_w)
    gds = paths.OUT(STEP, "b7_core.gds")
    core.get_default_view(i3.LayoutView).write_gdsii(str(gds))     # core.Layout() 不帶參數會建立新的空白視圖
    gds_f = paths.OUT(STEP, "b7_core_framed.gds")                     # 加 GDS 99 外框的副本，只給本步 DRC 用
    framed.get_default_view(i3.LayoutView).write_gdsii(str(gds_f))
    rb = readback(gds, names, geo, net, spec, heaters)
    d = drc.run(gds_f)
    # 故障注入：同一份 GDS，把「預期」改錯，讀回比對必須抓到
    net_bad = json.loads(nb)
    net_bad["mzis"][2]["layer"] = 3                                   # MZI-3 記成第 3 層
    spec_bad = json.loads(json.dumps(spec))
    a, b = spec_bad["phase_channels"][0], spec_bad["phase_channels"][1]
    a["heater"], b["heater"] = b["heater"], a["heater"]               # H01、H02 對調
    faults = dict(mzi_moved=not readback(gds, names, geo, net_bad, spec, heaters)["mzi_match"],
                  heater_swapped=not readback(gds, names, geo, net, spec_bad, heaters)["heater_match"],
                  port_swapped=not readback(gds, names, geo, net, spec, heaters, swap=("in0", "in1"))["ports_match"])   # GDS 標記對調

    checks = dict(netlist_sha=hashlib.sha256(nb).hexdigest() == spec["source"]["netlist_sha256"],
                  n_mzi=len(placement) == 7, n_mmi=rb["n_mmi"] == 14, n_heater=rb["n_heater"] == 14,
                  mzi_match_netlist=rb["mzi_match"] and rb["every_mzi_two_mmi"], heater_match_spec=rb["heater_match"],
                  ports_match_spec=rb["ports_match"], join_err_lt_1nm=geo["join_err_um"] < 1e-3,
                  arms_equal=abs(geo["arm_len_um"][0] - geo["arm_len_um"][1]) < 1e-6,
                  sbend_rmin_ok=geo["sbend_rmin_um"] >= R_MIN, drc_clean=d["total"] == 0 and not d["outside"],
                  faults_caught=all(faults.values()))
    info = dict(scope="B7 核心（不含 EC、PAD、繞線）", geometry=geo, cells=names, ports=port_tab, placement=placement,
                heaters=heaters, bypass=bypass, readback=rb, faults=faults,
                drc=dict(total=d["total"], counts=d["counts"], n_rules=len(d["rules"]), design_area_um=d["design_area_um"],
                         design_area_source=d["design_area_source"], outside=d["outside"]),
                checks=checks)
    paths.OUT(STEP, "layout_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    g = geo
    print(f"MZI 長 {g['mzi_length_um']:g} µm（相位區 {g['phase_section_um']:g}、S 彎 {g['sbend_um']:g}、MMI {g['mmi_length_um']:g}）；"
          f"核心 {g['core_size_um'][0]:g}×{g['core_size_um'][1]:g} µm；波導寬 {g['waveguide_width_um']:g} µm")
    print(f"S 彎最小曲率半徑 {g['sbend_rmin_um']:.1f} µm；上下臂長 {g['arm_len_um'][0]:.4f}／{g['arm_len_um'][1]:.4f} µm；"
          f"接點誤差 {g['join_err_um']:.1e} µm；MZI 軌比直通軌多 {g['rail_vs_bypass_extra_um']:g} µm")
    print(f"讀回 GDS：MMI {rb['n_mmi']}、加熱條 {rb['n_heater']}、MZI 位置 {rb['mzi_found']}")
    print(f"DRC：{len(d['rules'])} 條規則，違規 {d['total']} {d['counts']}；設計區 {d['design_area_um']}（{d['design_area_source']}）")
    print(f"故障注入（都應為 True）：{faults}")
    print(f"一致性：{checks}")
    print(f"寫出 {rt.rel(gds)}、layout_info.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
