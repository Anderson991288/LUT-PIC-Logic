r"""M2 s2：設計流程與 PDK——從規格到 GDS 要經過哪些步驟、每個元件用 PDK 的哪個 cell？

用途：
  1. 由 M2 s1 的 spec.json（與它綁定的接線表）算出晶片需要哪些元件、各幾個：
     2×2 MMI、相位區、heater、訊號 PAD、GND PAD、EC、波導與彎道、交叉（B7 只連相鄰波導時為 0）。
  2. 逐項到 CORNERSTONE PDK（SOI220 變體）查對應的 cell：存在與否、GDS 層、外形尺寸、埠名、有無電路模型，
     並把每個 cell 單獨寫成 GDS 跑平台 DRC（M3 s1 發現 PDK 加熱條本身就有違規後補上）。
     沒有對應 cell、cell 缺少需要的模型、或 cell 過不了 DRC 時，寫明自建的理由與在哪一步處理。
     波導寬度取 PDK MMI 埠的寬度（與 MMI 相接處不跳變）。
  3. 從 KLayout DRC deck 讀出後面佈局一定會碰到的規則（波導、heater、PAD 的最小寬度與間距），
     並換算成佈局要用的數字（PAD 最小間距、一列 PAD 的最小長度）。
  4. 列出從規格到交付的流程：每一步的工具、輸入、輸出與驗收，前一步的輸出必須是後一步的輸入。
  5. 把幾個 PDK cell 的實際多邊形存下來，給 figs.py 畫外形圖（不必再載入 PDK）。
輸入：M2 s1 的 out/spec.json；M1 s5 的 out/b7_netlist.json（以 SHA-256 核對）；CORNERSTONE PDK；design/common/drc 的 DRC deck。
輸出：out/components.json（元件清單與決定）、out/flow.json（流程）、out/pdk_cells_geom.json（cell 外形）、
      各 PDK cell 的單獨 GDS 與 DRC 報告：
        out/cell_SOI220nm_1550nm_TE_STRIP_2x2_MMI.gds、cell_SOI220nm_1550nm_TE_STRIP_2x2_MMI_drc.lyrdb
        out/cell_StraightHeaterFilament.gds、cell_StraightHeaterFilament_drc.lyrdb
        out/cell_HeaterPad.gds、cell_HeaterPad_drc.lyrdb
        out/cell_SOI220nm_1550nm_TE_STRIP_GC.gds、cell_SOI220nm_1550nm_TE_STRIP_GC_drc.lyrdb
        out/cell_SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing.gds、cell_SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing_drc.lyrdb
執行：.\lab design\m2_circuit\s2_flow\flow.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402
import re                                                            # noqa: E402

import paths                                                         # noqa: E402
from common import drc                                               # noqa: E402

STEP = "m2_circuit/s2_flow"
SPEC_STEP = "m2_circuit/s1_spec"
HAND = "m1_logic/s5_handoff"
GEOM_CELLS = ["SOI220nm_1550nm_TE_STRIP_2x2_MMI", "StraightHeaterFilament", "HeaterPad", "SOI220nm_1550nm_TE_STRIP_GC"]


def load_pdk():
    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)              # 要在 import cornerstone 之前選定變體
    import cornerstone
    import cornerstone.all as cs
    return cornerstone, cs


def gds_of(cs, layer):
    return list(cs.TECH.GDSII.LAYERTABLE[(layer.process, layer.purpose)])


def probe(cs, name):
    """查一個 PDK cell：存在、GDS 層、尺寸、埠、電路模型。"""
    if not hasattr(cs, name):
        return dict(cell=name, exists=False)
    c = getattr(cs, name)()
    if name.endswith("Template"):                                    # 模板不是 cell，沒有佈局與埠
        return dict(cell=name, exists=True, module=type(c).__module__.split(".")[-1], kind="trace template")
    lv = c.Layout()
    flat = lv.layout.flat_copy()
    layers = sorted({tuple(gds_of(cs, e.layer)) for e in flat if hasattr(e, "layer")})
    si = lv.size_info()
    try:
        c.CircuitModel()
        model = True
    except Exception:
        model = False
    ports = [dict(name=p.name, domain=type(p).__name__, xy=[round(float(v), 3) for v in p.position]) for p in lv.ports]
    gds = paths.OUT(STEP, f"cell_{name}.gds")
    lv.write_gdsii(str(gds))
    d = drc.run(gds)                                                 # 單一 cell：設計區用 deck 預設值
    return dict(cell=name, exists=True, module=type(c).__module__.split(".")[-1], gds_layers=[list(v) for v in layers],
                size_um=[round(float(si.width), 2), round(float(si.height), 2)], ports=ports, circuit_model=model,
                drc_total=d["total"], drc_counts=d["counts"])


def geom(cs, name):
    lv = getattr(cs, name)().Layout()
    polys = []
    for e in lv.layout.flat_copy():
        if hasattr(e, "layer") and hasattr(e, "shape"):
            pts = [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in e.shape.points]
            w = getattr(e, "line_width", None)                       # Path 只存中心線，另記線寬
            polys.append(dict(gds=gds_of(cs, e.layer), xy=pts, path_width=None if w is None else round(float(w), 3)))
    return dict(polygons=polys, ports=[dict(name=p.name, xy=[round(float(v), 3) for v in p.position]) for p in lv.ports])


def drc_rules():
    """從 DRC deck 讀出 width／space 規則（GDS 3 波導、39 heater、41 PAD）。"""
    text = paths.DRC_DECK.read_text(encoding="utf-8", errors="replace")
    alias = dict(soi_etch2_light_layer=3, fil=39, pad=41)
    rules = {}
    for var, g in alias.items():
        for kind in ("width", "space"):
            m = re.search(rf"^{var}\.{kind}\(([\d.]+)\.um", text, re.M)
            if m:
                rules.setdefault(str(g), {})[kind + "_um"] = float(m.group(1))
    return rules


def main():
    spec = json.loads(paths.OUT(SPEC_STEP, "spec.json").read_text(encoding="utf-8"))
    nb = paths.OUT(HAND, "b7_netlist.json").read_bytes()
    net = json.loads(nb)
    sha_ok = hashlib.sha256(nb).hexdigest() == spec["source"]["netlist_sha256"]

    n_mzi = len({c["mzi"] for c in spec["phase_channels"]})
    n_ch = len(spec["phase_channels"])
    n_ec = len(spec["optical_ports"])
    non_adjacent = [m["name"] for m in net["mzis"] if abs(m["waveguides"][1] - m["waveguides"][0]) != 1]

    cornerstone, cs = load_pdk()
    P = {n: probe(cs, n) for n in ["SOI220nm_1550nm_TE_STRIP_2x2_MMI", "StraightHeaterFilament", "HeaterPad",
                                   "SOI220nm_1550nm_TE_STRIP_GC", "SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing",
                                   "StripWaveguideTemplate"]}
    ec_like = sorted(n for n in dir(cs) if re.search(r"(?:^|_)Edge|EdgeCoupler|_EC$|SSC|SpotSize", n))
    mmi_ports = getattr(cs, "SOI220nm_1550nm_TE_STRIP_2x2_MMI")().Layout().ports
    wg = dict(width_um=float(mmi_ports["in1"].trace_template.core_width),          # 與 MMI 埠相同
              tech_wire_width_um=float(cs.TECH.WG.WIRE_WIDTH),
              template_default_um=float(cs.StripWaveguideTemplate().Layout().core_width),
              bend_radius_um=float(cs.TECH.WG.BEND_RADIUS))
    rules = drc_rules()

    comps = [
        dict(id="C1", function="2×2 分光／合光（50:50）", quantity=2 * n_mzi, where="每顆 MZI 前後各一", pdk=P["SOI220nm_1550nm_TE_STRIP_2x2_MMI"],
             decision="PDK cell", reason="晶圓廠提供佈局與電路模型；埠序 in2／out2 在上方（M0 s1 已用座標確認）", step="M2 s3、M3 s1"),
        dict(id="C2", function="相位區（光學）", quantity=n_ch, where="每顆 MZI 的 θ（臂）與 φ（輸入端）", pdk=None,
             decision="自建（模型）", reason="PDK 沒有「加熱後的波導相位」電路模型；模擬時用一段理想相位 e^{iφ}，佈局上就是一段直波導",
             step="M2 s3"),
        dict(id="C3", function="heater（TiN 加熱條）", quantity=n_ch, where="蓋在每個相位區的波導上方", pdk=P["StraightHeaterFilament"],
             decision="PDK cell" if P["StraightHeaterFilament"]["drc_total"] == 0 else "自建（幾何）",
             reason=("PDK 的加熱條含兩端 PAD 層接點；它只有電氣埠，沒有光學相位模型（相位由 C2 處理）"
                     if P["StraightHeaterFilament"]["drc_total"] == 0 else
                     f"PDK 有加熱條 cell，但它單獨跑平台 DRC 就有 {P['StraightHeaterFilament']['drc_total']} 處違規："
                     "兩端 GDS 41 接點是直徑 2 µm 的圓（畫成多邊形），被判為小於最小寬度 2 µm。改依平台設計規範自畫："
                     "TiN 條（寬 0.9 µm）＋兩端 TiN 落墊＋Ti/AL 接點；尺寸沿用 PDK 加熱條。它只有電氣作用，相位由 C2 處理"),
             step="M3 s1"),
        dict(id="C4", function="訊號 PAD", quantity=n_ch, where="晶片上下緣", pdk=P["HeaterPad"],
             decision="PDK cell", reason="PDK 提供 80×100 µm 的 PAD 層方塊，給探針或打線使用", step="M3 s3"),
        dict(id="C5", function="GND PAD", quantity=1, where="晶片上下緣（數量在 M3 s3 依繞線決定，至少 1 個）", pdk=P["HeaterPad"],
             decision="PDK cell", reason="與訊號 PAD 相同的 cell", step="M3 s3"),
        dict(id="C6", function="繞線（heater→PAD）", quantity=n_ch,
             where=f"{n_ch} 條訊號線（heater 一端到各自的訊號 PAD），另一端全部並接到 GND 匯流線（條數在 M3 s3 決定）", pdk=None,
             decision="自建（幾何）", reason="PDK 沒有走線 cell；用 PAD 層（GDS 41，Ti/AL 直接壓在 TiN 上）畫多邊形，寬度與間距依 DRC 規則",
             step="M3 s3"),
        dict(id="C7", function="波導與彎道", quantity=None, where="MZI 之間、核心到 EC", pdk=P["StripWaveguideTemplate"],
             decision="PDK 模板", reason=f"用 PDK 的條形波導模板由 IPKISS 產生直線與彎道；寬度取 MMI 埠的 {wg['width_um']:g} µm"
                                       f"（模板預設 {wg['template_default_um']:g} µm、技術檔 {wg['tech_wire_width_um']:g} µm，"
                                       "三者不同，取與 MMI 相接時不跳變的寬度）", step="M3 s1、M3 s3"),
        dict(id="C8", function="光學 I/O：EC", quantity=n_ec, where="西緣 5 個輸入、東緣 5 個輸出", pdk=None,
             decision="自建（幾何）", reason="PDK 沒有 EC cell（查無 edge／EC 類名稱）；M2 s1 選 EC 是為了 10 個埠分兩緣各用一組光纖陣列。"
                                         "自建的尖端波導未經晶圓廠驗證，列為風險", step="M3 s3"),
        dict(id="C9", function="光學 I/O 備選：GC", quantity=0, where="不使用", pdk=P["SOI220nm_1550nm_TE_STRIP_GC"],
             decision="不使用（記錄備選）", reason="PDK 有驗證過的 GC 與模型；若 EC 風險太高，可改成 10 個 GC（光纖要斜入射，埠需排成一列）",
             step="—"),
        dict(id="C10", function="波導交叉", quantity=len(non_adjacent), where="不需要", pdk=P["SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing"],
             decision="不需要", reason="B7 的 7 顆 MZI 都只連相鄰兩條波導，平面上不會交叉", step="—"),
    ]
    for c in comps:
        if c["decision"].startswith("PDK"):
            assert c["pdk"] and c["pdk"]["exists"], c["id"]
        if c["decision"].startswith("PDK"):
            c["ok"] = bool(c["pdk"]["exists"] and c["reason"])
        elif c["decision"].startswith("自建"):
            c["ok"] = bool(c["reason"] and c["step"] != "—")              # 自建要有理由，也要指定在哪一步做
        else:
            c["ok"] = bool(c["reason"])

    flow = [
        dict(step="M2 s1", name="介面規格", tool="Python", input=["b7_netlist.json", "phases.json", "truth_tables.csv"],
             output=["spec.json", "tolerance.json"], check="接線表 SHA-256 一致；14 個通道都有 PAD"),
        dict(step="M2 s2", name="設計流程與 PDK", tool="Python＋PDK 查詢", input=["spec.json"],
             output=["components.json", "flow.json"], check="每個元件有 PDK cell 或自建理由"),
        dict(step="M2 s3", name="電路模擬", tool="IPKISS 電路模型（C1＋C2）", input=["spec.json", "phases.json", "components.json"],
             output=["sim_results.json"], check="換成 PDK 模型後 80 組仍全對"),
        dict(step="M3 s1", name="B7 核心佈局", tool="IPKISS 佈局（C1、C3、C7）", input=["spec.json", "components.json"],
             output=["b7_core.gds", "layout_info.json"], check="7 顆 MZI、14 個 MMI、14 個相位區；埠位與 spec 一致"),
        dict(step="M3 s2", name="佈局審查", tool="KLayout 讀回 GDS", input=["b7_core.gds", "layout_info.json"],
             output=["review_checks.json"], check="審查項全部通過或有處置"),
        dict(step="M3 s3", name="晶片整合", tool="IPKISS 佈局（C4–C6、C8）", input=["b7_core.gds", "spec.json"],
             output=["chip.gds", "chip_info.json"], check="左右 EC、上下 PAD；14 訊號＋GND"),
        dict(step="M3 s4", name="DRC 與連接檢查", tool="KLayout DRC deck＋Python", input=["chip.gds", "chip_info.json"],
             output=["drc_result.json", "connectivity.json"], check="DRC 0；每個 heater 接到對的 PAD"),
        dict(step="M3 s5", name="交付", tool="Python", input=["chip.gds", "spec.json", "drc_result.json", "connectivity.json"],
             output=["delivery/"], check="交付檢查程式全部通過"),
    ]
    ht = [q for q in geom(cs, "StraightHeaterFilament")["polygons"] if q["gds"][0] == 39 and q["path_width"]]
    assert len(ht) == 1, "預期加熱條本體是一條 GDS 39 的 Path"
    ht_l = max(x for x, _ in ht[0]["xy"]) - min(x for x, _ in ht[0]["xy"])
    ht_w = ht[0]["path_width"]
    # 依序檢查：每一步的輸入必須是「更前面」的步驟已經產生的檔案（M2 審查 R6）；只核對本清單宣告的檔名
    produced, dangling = {"b7_netlist.json", "phases.json", "truth_tables.csv"}, []
    for s in flow:
        dangling += [f"{s['step']}：{f}" for f in s["input"] if f not in produced]
        produced |= set(s["output"])

    checks = dict(netlist_sha=sha_ok, every_component_justified=all(c["ok"] for c in comps),
                  pdk_cells_exist=all(c["pdk"]["exists"] for c in comps if c["decision"].startswith("PDK")),
                  pdk_cells_drc_clean=all(c["pdk"].get("drc_total", 0) == 0 for c in comps if c["decision"] == "PDK cell"),
                  flow_inputs_produced=not dangling, no_crossing_needed=not non_adjacent)
    summary = dict(n_components=len(comps), n_pdk=sum(c["decision"].startswith("PDK") for c in comps),
                   n_custom=sum(c["decision"].startswith("自建") for c in comps),
                   n_unused=sum(c["decision"].startswith(("不使用", "不需要")) for c in comps),
                   heater_width_um=ht_w, heater_length_um=ht_l,
                   pad_size_um=P["HeaterPad"]["size_um"], mmi_size_um=P["SOI220nm_1550nm_TE_STRIP_2x2_MMI"]["size_um"])
    # 給佈局的數字：PAD 沿晶片緣排成一列時的最小長度（上緣 8 個、下緣 7 個；寬度 80 µm 沿著晶片緣）
    pw, ps = P["HeaterPad"]["size_um"][0], rules["41"]["space_um"]
    n_pad = n_ch + 1
    top, bottom = (n_pad + 1) // 2, n_pad // 2
    summary.update(pad_pitch_min_um=pw + ps, pad_row_top=top, pad_row_bottom=bottom,
                   pad_row_min_um=top * pw + (top - 1) * ps, heater_gap_min_um=rules["39"]["space_um"])
    out = dict(pdk=dict(name="CORNERSTONE", variant="SOI220", version=str(cornerstone.__version__)), waveguide=wg,
               drc_rules=rules, ec_like_cells=ec_like, components=comps, summary=summary, checks=checks)
    paths.OUT(STEP, "components.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.OUT(STEP, "flow.json").write_text(json.dumps(dict(flow=flow, dangling_inputs=dangling), ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    paths.OUT(STEP, "pdk_cells_geom.json").write_text(json.dumps({n: geom(cs, n) for n in GEOM_CELLS}), encoding="utf-8")

    for c in comps:
        cell = c["pdk"]["cell"] if c["pdk"] else "—"
        print(f"{c['id']:>3} {c['function']:<16} ×{c['quantity'] if c['quantity'] is not None else '…':<3} {c['decision']:<10} {cell}")
    print(f"DRC 規則：{rules}")
    print(f"PDK 中名稱像 EC 的 cell：{ec_like or '無'}")
    print(f"一致性：{checks}")
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'components.json'))}、flow.json、pdk_cells_geom.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
