r"""晶片整合：晶片整合：EC 與 PAD——光怎麼進出晶片？heater 怎麼繞線到 PAD？

用途：把 LUT4 s3 的 LUT4 核心（直接匯入它的 GDS，不重畫）放進整顆晶片：
  1. EC：100 nm 薄矽尖端邊緣耦合器（GDS 3／4／5；尖端 0.25 µm＝GDS 5 最小線寬），配 250 µm 間距的光纖陣列；
     輸入 5 個在西緣、輸出 5 個在東緣，以第 3 軌為中心上下對稱。
  2. 扇出：核心埠距 30 µm → EC 間距 250 µm，用 cosine S 彎（長 FAN）。輸入側再加一段補長段（長 COMP，COMP_N 個餘弦凸起，
     一律往上凸），讓 5 個輸入從 EC 到核心等長：輸入之間的長度差會變成隨溫度、波長漂移的相位差（先前審查 R3）。
     輸出側接偵測器只量功率，不需等長。記下所有彎道的最小曲率半徑與各路長度。
  3. 繞線（只有一層金屬 Ti/AL，訊號線與地線不能交叉）：
       - heater 在第 r 軌時（r＝0–4 由上往下），往北要跨 r 條波導、往南要跨 5 − r 條（含自己這一軌），取跨越較少的一側；
       - 直走會碰到其他 heater 的 TiN（或自己的加熱條）時，先在落墊高度橫移到沒有 TiN 的位置（MMI／S 彎區）再直走；
       - 所有走線先垂直到「轉折高度」，再斜線到 PAD 列；PAD 依走線的左右順序排列，所以走線之間不會交叉。
  4. PAD：PDK 的 HeaterPad（80×100 µm），中心距 ≥ 150 µm，一律排在晶片上下緣最外圍（使用者 2026-10-31：探針、打線只碰得到外緣）。
     單層金屬不能讓訊號線跨過地線，所以不用 GND 匯流排：heater 是電阻，哪一端接訊號都可以，
     讓相鄰兩個 heater 的地端排在一起，兩條地線接到同一個 GND PAD（逐一試每個 heater 的方向，取 PAD 數最少者）。
     編號依規格（H01→P01…）；GND PAD 北側 GN1、GN2…，南側 GS1、GS2…（由西往東）。
  5. 估計：每條軌從輸入 EC 到輸出 EC 的波導長度與 MMI 數 → 傳播損耗（平台 strip 波導 3–4 dB/cm）＋MMI 損耗（每顆 0.33 dB）；
     heater 電阻假設對應的 TiN 電阻率；每個 GND PAD 的最大電流。
  6. 檢查：KLayout DRC（設計區＝晶片尺寸）；Ti/AL 不同網之間的最小距離 ≥ 10 µm；Ti/AL 到其他 heater 的 TiN ≥ 10 µm；
     Ti/AL 不蓋 TiN 加熱條本體；每個 Ti/AL 連通塊恰含一個 PAD；Ti/AL 跨越波導的次數；電流密度（mA/µm²）估算。
輸入：LUT4 s3 的 out/l4_core.gds、out/layout_info.json；M2 s1 的 out/spec.json；M1 s5 的 out/phases.json、out/lut4_netlist.json；
      M2 s2 的 out/components.json；M2 s3 的 out/mmi_sweep.json。
輸出：out/chip.gds、out/chip_info.json（PAD、EC、走線、跨越、電流密度、檢查）、out/chip_drc.lyrdb。
執行：.\lab design\m3_layout\s3_chip\chip.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from shapely.geometry import LineString, Polygon, box                # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import drc                                               # noqa: E402
from common import gds2png as G                                      # noqa: E402

STEP = "lut4/s5_chip"
CORE = "lut4/s3_core"
# EC（100 nm 薄矽尖端；尺寸依平台規則與先前的耦合估算）
EC = dict(tip_w=0.25, base_w=1.0, core_end_w=0.35, tip_len=30.0, taper_len=200.0, bilevel_len=30.0, win_half=10.0)
EC_PITCH = 250.0        # 光纖陣列間距（µm，V-groove）
FAN = 400.0             # 扇出 S 彎長度（µm）
COMP, COMP_N = 600.0, 2  # 輸入補長段長度（µm）與凸起個數：最小曲率半徑 ≥ 30 µm、凸起高度 ≤ 200 µm 的最短組合
LOSS_DB_CM = (3.0, 4.0)  # 平台 strip 波導傳播損耗（典型約 3、上限 4 dB/cm）
T_TIN = 0.15            # TiN 厚度（µm，公開 PDK 的製程概述）
STUB = 0.5
NPTS = 161
PAD = (80.0, 100.0)     # PDK HeaterPad
PAD_PITCH = 150.0       # PAD 最小中心距（µm）
W_SIG = 10.0            # 訊號線、地線寬（µm）
GND_DX = 20.0           # 兩條地線接同一個 GND PAD 時，各離 PAD 中心的距離（µm）
SPACE = 10.0            # Ti/AL 最小間距（DRC）
LANE_L, LANE_R = 22.0, 30.0   # 橫移後的垂直走線位置：左端在加熱條起點左方、右端在終點右方（µm）
Y_TURN = 60.0           # 北側轉折高度（µm）；南側為 −(核心下緣＋…)
Y_STAG = 12.0           # 相鄰走線轉折高度的錯開量（µm）
DIE_Y = (-640.0, 560.0)  # 上下緣由 EC 列決定（最外側 EC 在 y≈440、−560）
EDGE = 60.0             # PAD 外緣到晶片邊緣（µm）：假設值（切割道與崩邊的餘量），平台未公布，待確認
PAD_Y_N = DIE_Y[1] - EDGE - PAD[1]   # 北側 PAD 下緣（PAD 外緣離晶片邊 EDGE）
PAD_Y_S = DIE_Y[0] + EDGE + PAD[1]   # 南側 PAD 上緣
T_AL = 0.22             # Ti/AL 厚度（µm，公開 PDK 的製程概述）
R_HEATER_KOHM = (0.5, 1.0, 2.0)   # TiN 片電阻沒有公開值：heater 電阻取三個假設值


def r3(pts):
    return [(round(float(x), 3), round(float(y), 3)) for x, y in pts]


def sbend(x0, y0, x1, y1):
    t = np.linspace(0, 1, NPTS)
    L = (x1 - x0) - 2 * STUB * np.sign(x1 - x0)
    return [(x0, y0)] + [(x0 + STUB * np.sign(x1 - x0) + L * u, y0 + (y1 - y0) * (1 - np.cos(np.pi * u)) / 2) for u in t] + [(x1, y1)]


def bump(x0, y0, L, h, n):
    """補長段：x0 → x0＋L，n 個往上的餘弦凸起，高度 h；兩端各有 STUB 的水平段。"""
    t = np.linspace(0, 1, 4 * NPTS)
    Lb = L - 2 * STUB
    return [(x0, y0)] + [(x0 + STUB + Lb * u, y0 + h * (1 - np.cos(2 * np.pi * n * u)) / 2) for u in t] + [(x0 + L, y0)]


def plen(pts):
    q = np.array(pts)
    return float(np.sum(np.hypot(*np.diff(q, axis=0).T)))


def pav(xs, gaps):
    """在「相鄰間距 ≥ gaps[i]」的限制下，讓位置最接近 xs（保序回歸）。"""
    c = np.concatenate([[0.0], np.cumsum(gaps)])
    z = np.array(xs, float) - c
    blocks = [[v, 1] for v in z]
    out = []
    for v in blocks:
        out.append(v)
        while len(out) > 1 and out[-2][0] / out[-2][1] > out[-1][0] / out[-1][1]:
            a = out.pop()
            out[-1][0] += a[0]
            out[-1][1] += a[1]
    zz = np.concatenate([[b[0] / b[1]] * b[1] for b in out])
    return list(zz + c)


def plan_routes(heaters, geo, side_of, tin_by_heater):
    """每個 heater 的兩個端點：方向、是否橫移、垂直走線的 x。"""
    terms = []
    for h in heaters:
        side = side_of(h)
        (xl, yl), (xr, yr) = h["landings_um"]
        for end, (x, y), lane in (("L", (xl, yl), xl - LANE_L), ("R", (xr, yr), xr + LANE_R)):
            # 直走會不會碰到 TiN：北側看其他 heater，南側連自己的加熱條也會被蓋到
            y_far = Y_TURN if side == "N" else -10_000
            path = box(x - W_SIG / 2 - SPACE, min(y, y_far), x + W_SIG / 2 + SPACE, max(y, y_far))
            others = [g for k, g in tin_by_heater.items() if k != h["heater"]]
            hit = any(path.intersects(g) for g in others) or side == "S"
            terms.append(dict(heater=h["heater"], pad=h["pad"], end=end, side=side, start=(x, y), lane=lane if hit else x, jog=hit))
    return terms


def gnd_runs(ts):
    """依左右順序，把連續的地線兩兩一組（同一個 GND PAD）；回傳 [[t], [t, t], …]。"""
    groups, run = [], []
    for t in ts + [None]:
        if t is not None and t["role"] == "gnd":
            run.append(t)
            continue
        groups += [run[i:i + 2] for i in range(0, len(run), 2)]
        run = []
    return groups


def choose_roles(terms, side):
    """逐一試該側每個 heater 的方向（哪一端接訊號），取 PAD 數最少者；同數時取改動最少（左端＝訊號為預設）。"""
    ts = sorted([t for t in terms if t["side"] == side], key=lambda t: t["lane"])
    hs = sorted({t["heater"] for t in ts})
    best = None
    for code in range(2 ** len(hs)):
        flip = {h: bool(code >> i & 1) for i, h in enumerate(hs)}
        for t in ts:
            t["role"] = "sig" if (t["end"] == "L") != flip[t["heater"]] else "gnd"
        key = (len(hs) + len(gnd_runs(ts)), sum(flip.values()))
        if best is None or key < best[0]:
            best = (key, flip)
    for t in ts:
        t["role"] = "sig" if (t["end"] == "L") != best[1][t["heater"]] else "gnd"
    return ts


def assign_pads(terms, side):
    """依走線左右順序排 PAD（一列，中心距 ≥ PAD_PITCH）：訊號線各接自己的 PAD，相鄰的兩條地線共用一個 GND PAD。
    回傳該側走線（含目標 x）與 PAD 列 [(x, 'sig'|'gnd', [走線…])]。"""
    ts = choose_roles(terms, side)
    gid = {id(t): g for g in gnd_runs(ts) for t in g}
    slots, seen = [], set()
    for t in ts:
        if t["role"] == "sig":
            slots.append(("sig", [t]))
        elif id(gid[id(t)][0]) not in seen:
            seen.add(id(gid[id(t)][0]))
            slots.append(("gnd", gid[id(t)]))
    px = pav([float(np.mean([t["lane"] for t in ws])) for _, ws in slots], [PAD_PITCH] * (len(slots) - 1))
    for x, (kind, ws) in zip(px, slots):
        offs = [0.0] if len(ws) == 1 else [-GND_DX, GND_DX]
        for t, o in zip(ws, offs):
            t["target"] = x + o
    return ts, [(x, kind, ws) for x, (kind, ws) in zip(px, slots)]


# 走線轉角用圓角：斜接（mitre）在小角度轉折處會留下 0.2 µm 的凹口，被 DRC 判為 GDS 41 間距違規
def al_route(t, y_turn, y_pad, y_end):
    pts = [t["start"]]
    if t["jog"]:
        pts.append((t["lane"], t["start"][1]))
    pts += [(t["lane"], y_turn), (t["target"], y_pad), (t["target"], y_end)]
    clean = [pts[0]]
    for p in pts[1:]:
        if np.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-6:
            clean.append(p)
    return clean


def stagger(ts):
    """錯開轉折高度（LUT4 佈局新增）：同一側往左走的走線，越靠左越早轉；往右走的，越靠右越早轉。
    同一高度轉折時，相鄰走線的斜率不同，轉角附近間距會小於 10 µm。"""
    left = sorted([t for t in ts if t["target"] < t["lane"] - 1e-6], key=lambda t: t["lane"])
    right = sorted([t for t in ts if t["target"] > t["lane"] + 1e-6], key=lambda t: -t["lane"])
    out = {id(t): 0.0 for t in ts}
    for grp in (left, right):
        for k, t in enumerate(grp):
            out[id(t)] = k * Y_STAG
    return out


def main():
    info = json.loads(paths.OUT(CORE, "layout_info.json").read_text(encoding="utf-8"))
    spec = json.loads(paths.OUT("lut4/s1_handoff", "spec.json").read_text(encoding="utf-8"))
    ph = json.loads(paths.OUT("lut4/s1_handoff", "phases.json").read_text(encoding="utf-8"))
    comp = json.loads(paths.OUT("m2_circuit/s2_flow", "components.json").read_text(encoding="utf-8"))
    tol = json.loads(paths.OUT("lut4/s1_handoff", "tolerance.json").read_text(encoding="utf-8"))
    C = {c["id"]: c for c in comp["components"]}
    assert C["C4"]["decision"] == "PDK cell" and C["C8"]["decision"].startswith("自建")
    geo = info["geometry"]
    P = geo["pitch_um"]
    n_wg = 5
    core_gds = paths.OUT(CORE, "l4_core.gds")

    # ---------- TiN（讀回核心 GDS，判斷走線會不會碰到）----------
    structs, dbu = G.parse(str(core_gds))
    flat = []
    G.flatten(structs, info["cells"]["core"], np.eye(2), np.zeros(2), flat)
    flat = [(l, xy * dbu / 1e-6) for l, xy in flat]
    tin = unary_union([Polygon(xy).buffer(0) for l, xy in flat if l == 39])
    tin_parts = list(tin.geoms)
    tin_by_heater = {}
    for h in info["heaters"]:
        c = (sum(h["body_um"]) / 2, h["y_um"])
        tin_by_heater[h["heater"]] = next(g for g in tin_parts if g.distance(Polygon([(c[0] - 1, c[1] - 1), (c[0] + 1, c[1] - 1),
                                                                                   (c[0] + 1, c[1] + 1), (c[0] - 1, c[1] + 1)])) == 0)
    wg_core = unary_union([Polygon(xy).buffer(0) for l, xy in flat if l == 3])

    def side_of(h):
        r = int(round(-h["y_um"] / P))
        return "N" if r < n_wg - r else "S"                           # 往北跨 r 條、往南跨 n−r 條（含自己這軌）；相同時取北

    terms = plan_routes(info["heaters"], geo, side_of, tin_by_heater)
    tsN, rowN = assign_pads(terms, "N")
    tsS, rowS = assign_pads(terms, "S")
    y_turn_S = -(n_wg - 1) * P - 20.0

    pads = []
    for row, side in ((rowN, "N"), (rowS, "S")):
        yc = PAD_Y_N + PAD[1] / 2 if side == "N" else PAD_Y_S - PAD[1] / 2
        k = 0
        for x, kind, ws in row:
            if kind == "sig":
                name, heater = ws[0]["pad"], ws[0]["heater"]
            else:
                k += 1
                name, heater = ("GN" if side == "N" else "GS") + str(k), None
            for t in ws:
                t["net"] = name
            pads.append(dict(name=name, net=name, heater=heater, side=side, xy_um=[round(x, 3), yc],
                             heaters=[t["heater"] for t in ws]))
    routes = []
    stag = stagger(tsN)
    for t in tsN:
        routes.append(dict(t, pts=al_route(t, Y_TURN + stag[id(t)], PAD_Y_N - 20, PAD_Y_N + 20)))
    stag = stagger(tsS)
    for t in tsS:
        routes.append(dict(t, pts=al_route(t, y_turn_S - stag[id(t)], PAD_Y_S + 20, PAD_Y_S - 20)))
    al_polys = {}
    for r in routes:
        g = LineString(r["pts"]).buffer(W_SIG / 2, cap_style=2, join_style=1, quad_segs=8)
        r["length_um"] = round(LineString(r["pts"]).length, 2)
        al_polys.setdefault(r["net"], []).append(g)

    # ---------- EC 與扇出 ----------
    ins = sorted([p for p in info["ports"] if p["angle"] == 180.0], key=lambda p: -p["xy_um"][1])
    outs = sorted([p for p in info["ports"] if p["angle"] == 0.0], key=lambda p: -p["xy_um"][1])
    yc = ins[n_wg // 2]["xy_um"][1]
    ec_len = EC["tip_len"] + EC["taper_len"] + EC["bilevel_len"]
    x_in, x_out = ins[0]["xy_um"][0], outs[0]["xy_um"][0]
    XW, XE = x_in - FAN - COMP - ec_len, x_out + FAN + ec_len
    ecs, fans, fan_in, fan_out, bumps = [], [], {}, {}, {}
    s_in = {k: sbend(x_in - FAN, yc + (n_wg // 2 - k) * EC_PITCH, x_in, pi["xy_um"][1]) for k, pi in enumerate(ins)}
    target = max(plen(sb) for sb in s_in.values()) + COMP              # 最長的 S 彎配上平直的補長段
    for k, (pi, po) in enumerate(zip(ins, outs)):
        y_ec = yc + (n_wg // 2 - k) * EC_PITCH
        lo, hi = 0.0, 250.0                                           # 二分法找凸起高度，使總長＝target
        for _ in range(60):
            mid = (lo + hi) / 2
            if plen(bump(x_in - FAN - COMP, y_ec, COMP, mid, COMP_N)) + plen(s_in[k]) < target:
                lo = mid
            else:
                hi = mid
        h = 0.0 if plen(s_in[k]) + COMP >= target - 1e-9 else hi
        path = bump(x_in - FAN - COMP, y_ec, COMP, h, COMP_N)[:-1] + s_in[k]
        fans.append(path)
        fo = sbend(x_out, po["xy_um"][1], x_out + FAN, y_ec)
        fans.append(fo)
        fan_in[pi["port"]], fan_out[po["port"]], bumps[pi["port"]] = round(plen(path), 3), round(plen(fo), 3), round(h, 2)
        ecs.append(dict(port=pi["port"], signal=pi["signal"], side="W", facet_um=[XW, y_ec]))
        ecs.append(dict(port=po["port"], signal=po["signal"], side="E", facet_um=[XE, y_ec]))
    dy = max(abs(f[-1][1] - f[0][1]) for f in fans)
    hmax = max(bumps.values())
    fan_rmin = min(2 * (FAN - 2 * STUB) ** 2 / (np.pi ** 2 * dy),
                   ((COMP - 2 * STUB) / COMP_N) ** 2 / (2 * np.pi ** 2 * hmax) if hmax > 0 else 1e9)

    # ---------- IPKISS ----------
    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)
    import cornerstone.all as cs
    import ipkiss3.all as i3
    T = cs.TECH.PPLAYER
    width = geo["waveguide_width_um"]
    tpl = cs.StripWaveguideTemplate()
    tpl.Layout(core_width=width)

    xb = EC["tip_len"] + EC["taper_len"]
    xe = xb + EC["bilevel_len"]
    t2, b2, ce = EC["tip_w"] / 2, EC["base_w"] / 2, EC["core_end_w"] / 2
    ec_cell = i3.LayoutCell(name="L4_EC")
    ec_cell.Layout(elements=[
        i3.Boundary(layer=T.SLAB, shape=[(0, -t2), (EC["tip_len"], -t2), (xb, -b2), (xe, -width / 2), (xe, width / 2), (xb, b2),
                                         (EC["tip_len"], t2), (0, t2)]),
        i3.Boundary(layer=T.WG, shape=[(xb, -ce), (xe, -width / 2), (xe, width / 2), (xb, ce)]),
        i3.Rectangle(layer=T.WG_HOL, center=(xb / 2, 0.0), box_size=(xb, 2 * EC["win_half"]))])

    def wg(pts):
        w = i3.Waveguide(trace_template=tpl)
        w.Layout(shape=r3(pts))
        return w

    core = i3.GDSCell(filename=str(core_gds), cell_name=info["cells"]["core"])
    pad_cell = cs.HeaterPad()
    lbl = i3.PPLayer(cs.TECH.PROCESS.NONE, cs.TECH.PURPOSE.LBL)
    outline = i3.PPLayer(cs.TECH.PROCESS.NONE, cs.TECH.PURPOSE.CELL)
    el = [i3.SRef(reference=core, position=(0, 0), name="CORE")]
    for e in ecs:
        x, y = e["facet_um"]
        tr = i3.Translation((x, y)) if e["side"] == "W" else i3.Rotation(rotation=180.0) + i3.Translation((x, y))
        el.append(i3.SRef(reference=ec_cell, transformation=tr))
        el.append(i3.Label(layer=lbl, text=f"{e['signal']}_{e['port']}", coordinate=(x + (40 if e["side"] == "W" else -40), y + 15),
                           height=5.0))
    el += [i3.SRef(reference=wg(f)) for f in fans]
    for p in pads:
        el.append(i3.SRef(reference=pad_cell, position=tuple(p["xy_um"]), name=p["name"]))
        el.append(i3.Label(layer=lbl, text=p["name"], coordinate=tuple(p["xy_um"]), height=10.0))
    al_union = {}
    for net, gs in al_polys.items():
        r_close = SPACE / 2 + 1.0                                     # 同一網內小於 10 µm 的縫補起來（兩條地線靠太近時 DRC 會判間距違規）
        u = unary_union(gs).buffer(r_close, join_style=2).buffer(-r_close, join_style=2)
        al_union[net] = u
        for g in (u.geoms if hasattr(u, "geoms") else [u]):
            el.append(i3.Boundary(layer=T.PAD, shape=r3(np.array(g.exterior.coords)[:-1])))
    el.append(i3.Boundary(layer=outline, shape=[(XW, DIE_Y[0]), (XE, DIE_Y[0]), (XE, DIE_Y[1]), (XW, DIE_Y[1])]))
    chip = i3.LayoutCell(name="L4_CHIP")
    chip.Layout(elements=el)
    gds = paths.OUT(STEP, "chip.gds")
    chip.get_default_view(i3.LayoutView).write_gdsii(str(gds))

    # ---------- 檢查 ----------
    die = (round(XE - XW, 3), round(DIE_Y[1] - DIE_Y[0], 3))
    d = drc.run(gds, design_area=die)
    # Ti/AL 到「別的 heater」的 TiN；Ti/AL 不得蓋到任何加熱條本體（落墊以外）
    d_tin, body_hit = 1e9, 0.0
    for r in routes:
        g = LineString(r["pts"]).buffer(W_SIG / 2, cap_style=2, join_style=1, quad_segs=8)
        for k, tg in tin_by_heater.items():
            if k != r["heater"]:
                d_tin = min(d_tin, g.distance(tg))
        h = next(h for h in info["heaters"] if h["heater"] == r["heater"])
        body = box(h["body_um"][0] + 2, h["y_um"] - 0.45, h["body_um"][1] - 2, h["y_um"] + 0.45)
        body_hit += g.intersection(body).area
    pad_boxes = {p["name"]: box(p["xy_um"][0] - PAD[0] / 2, p["xy_um"][1] - PAD[1] / 2, p["xy_um"][0] + PAD[0] / 2, p["xy_um"][1] + PAD[1] / 2)
                 for p in pads}
    al_all = unary_union(list(al_union.values()) + list(pad_boxes.values()))
    comps = list(al_all.geoms) if hasattr(al_all, "geoms") else [al_all]
    pads_per_comp = [sum(c.intersects(b) for b in pad_boxes.values()) for c in comps]
    cross = {}
    for r in routes:
        g = LineString(r["pts"]).buffer(W_SIG / 2, cap_style=2, join_style=1, quad_segs=8)
        inter = g.intersection(wg_core)
        n = len(inter.geoms) if hasattr(inter, "geoms") else (0 if inter.is_empty else 1)
        r["crossings"] = n
        cross[r["heater"] + "_" + r["role"]] = n

    # 電流密度：每個 heater 最壞（任一函數）的功率 → 電流 I＝√(P/R)
    chan = {c["heater"]: c for c in spec["phase_channels"]}
    p_mw = {}
    for fn, f in ph["functions"].items():
        for hname, c in chan.items():
            v = float(np.mod(f[c["kind"]][c["phase_index"]], 2 * np.pi))
            v = 0.0 if np.isclose(v, 2 * np.pi, atol=1e-6) else v
            p_mw.setdefault(fn, {})[hname] = v / np.pi * tol["P_pi_mW"]
    p_max = 2 * tol["P_pi_mW"]
    hl = info["geometry"]
    sq = hl["heater_length_um"] / hl["heater_width_um"]                # 加熱條的方塊數（長／寬）
    dens = []
    for R in R_HEATER_KOHM:
        i_max = np.sqrt(p_max * 1e-3 / (R * 1e3)) * 1e3              # mA
        # 每條地線只帶自己 heater 的電流（線寬與訊號線相同），兩條在 GND PAD 上才會合：PAD 的電流＝兩個 heater 相加
        gp = [p for p in pads if p["heater"] is None]
        i_gp = max(sum(np.sqrt(p_mw[fn][h] * 1e-3 / (R * 1e3)) * 1e3 for h in p["heaters"]) for p in gp for fn in p_mw)
        n_gp = max(len(p["heaters"]) for p in gp)
        dens.append(dict(R_kohm=R, I_heater_max_mA=round(float(i_max), 2), V_heater_max_V=round(float(i_max) * R, 2),
                         J_line_mA_um2=round(float(i_max) / (W_SIG * T_AL), 2),
                         rho_tin_uohm_cm=round(R * 1e3 * T_TIN * 1e-6 / sq * 1e8, 0),
                         I_gnd_pad_mA=round(float(i_gp), 1), I_gnd_pad_worst_mA=round(n_gp * float(i_max), 1)))

    # 傳播損耗估計（每條軌：輸入扇出＋核心＋輸出扇出；核心內每經過一顆 MZI 多走 rail_vs_bypass_extra_um）
    net = json.loads(paths.OUT("lut4/s1_handoff", "lut4_netlist.json").read_text(encoding="utf-8"))
    sweep = json.loads(paths.OUT("m2_circuit/s3_sim", "mmi_sweep.json").read_text(encoding="utf-8"))
    n_mzi = [sum(1 for m in net["mzis"] if r + 1 in m["waveguides"]) for r in range(n_wg)]
    core_len = x_out - x_in
    loss = []
    for r in range(n_wg):
        L = fan_in[ins[r]["port"]] + core_len + n_mzi[r] * hl["rail_vs_bypass_extra_um"] + fan_out[outs[r]["port"]]
        mmi = 2 * n_mzi[r] * sweep["loss_meas_db"]
        loss.append(dict(rail=r + 1, length_um=round(L, 1), n_mmi=2 * n_mzi[r],
                         prop_db=[round(L * 1e-4 * x, 2) for x in LOSS_DB_CM], mmi_db=round(mmi, 2),
                         total_db=[round(L * 1e-4 * x + mmi, 2) for x in LOSS_DB_CM]))
    # PAD 是否在最外圍：讀回寫出的 GDS，PAD 外側（到晶片邊緣之間）除了外框（GDS 99）沒有任何層的圖形（M3 關卡審查 R9）
    st_c, db_c = G.parse(str(gds))
    flat_c = []
    G.flatten(st_c, "L4_CHIP", np.eye(2), np.zeros(2), flat_c)
    al_out = unary_union([Polygon(xy * db_c / 1e-6).buffer(0) for l, xy in flat_c if l != 99])
    # 不同網之間的最小距離：讀回 GDS 的 GDS 41（走線、PAD、核心內的落墊）各連通塊之間（M3 關卡審查 R10）
    al41 = unary_union([Polygon(xy * db_c / 1e-6).buffer(0) for l, xy in flat_c if l == 41])
    al41 = list(al41.geoms) if hasattr(al41, "geoms") else [al41]
    d_net = min(al41[i].distance(al41[j]) for i in range(len(al41)) for j in range(i + 1, len(al41)))
    outer = unary_union([box(XW, PAD_Y_N + PAD[1] + 0.001, XE, DIE_Y[1]), box(XW, DIE_Y[0], XE, PAD_Y_S - PAD[1] - 0.001)])
    ec_edge = min(min(e["facet_um"][1] - DIE_Y[0], DIE_Y[1] - e["facet_um"][1]) for e in ecs)   # EC 中心到上下切割邊的最近距離
    n_flip = sum(1 for r in routes if r["end"] == "L" and r["role"] == "gnd")
    checks = dict(pads_outermost=al_out.intersection(outer).area < 1e-6,
                  gnd_pads_shared=all(len(p["heaters"]) <= 2 for p in pads if p["heater"] is None),
                  drc_clean=d["total"] == 0 and not d["outside"], al_spacing=d_net >= SPACE - 1e-6,
                  al_to_other_tin=d_tin >= SPACE - 1e-6, al_not_on_heater_body=body_hit < 1e-6,
                  one_pad_per_al_net=all(n == 1 for n in pads_per_comp) and len(comps) == len(pads),
                  n_signal_pads=sum(p["heater"] is not None for p in pads) == 14,
                  ec_count=len(ecs) == 10, ec_pitch=all(abs((ecs[2 * k]["facet_um"][1] - ecs[2 * k + 2]["facet_um"][1]) - EC_PITCH) < 1e-6
                                                         for k in range(n_wg - 1)),
                  fan_rmin_ok=fan_rmin >= 10.0, inputs_equal_length=max(fan_in.values()) - min(fan_in.values()) < 0.01,
                  pad_pitch=all(b - a >= PAD_PITCH - 1e-6 for s in ("N", "S") for a, b in
                                zip(sorted(p["xy_um"][0] for p in pads if p["side"] == s)[:-1],
                                    sorted(p["xy_um"][0] for p in pads if p["side"] == s)[1:])),
                  mapping_spec=all(p["name"] == chan[p["heater"]]["pad"] for p in pads if p["heater"]))
    out = dict(die_um=list(die), die_x_um=[XW, XE], die_y_um=list(DIE_Y), ec=ecs, ec_params=EC, ec_pitch_um=EC_PITCH,
               fan_length_um=FAN, comp_length_um=COMP, comp_n=COMP_N, comp_bump_um=bumps, fan_in_len_um=fan_in, fan_out_len_um=fan_out,
               fan_in_spread_um=round(max(fan_in.values()) - min(fan_in.values()), 4),
               fan_out_spread_um=round(max(fan_out.values()) - min(fan_out.values()), 1),
               fan_rmin_um=round(fan_rmin, 1), pads=pads, pad_pitch_min_um=PAD_PITCH,
               pad_edge_um=EDGE, ec_edge_min_um=round(ec_edge, 1), n_pads=len(pads), n_gnd_pads=sum(p["heater"] is None for p in pads),
               n_pads_side={s: sum(p["side"] == s for p in pads) for s in ("N", "S")}, n_heater_flipped=n_flip,
               loss_estimate=loss, loss_db_cm=list(LOSS_DB_CM), mmi_loss_db=sweep["loss_meas_db"],
               heater_squares=round(sq, 1), tin_thickness_um=T_TIN, gnd_pad_dx_um=GND_DX,
               routes=[{k: (v if k != "pts" else [[round(a, 3), round(b, 3)] for a, b in v]) for k, v in r.items()} for r in routes],
               n_crossings=int(sum(cross.values())), crossings=cross, n_jog=sum(r["jog"] for r in routes),
               al_min_net_spacing_um=round(d_net, 2), al_min_to_other_tin_um=round(d_tin, 2), al_components=len(comps),
               wire_width_um=W_SIG, al_thickness_um=T_AL, current_density=dens,
               drc=dict(total=d["total"], counts=d["counts"], n_rules=len(d["rules"]), design_area_um=d["design_area_um"],
                        design_area_source=d["design_area_source"], outside=d["outside"]),
               checks=checks)
    paths.OUT(STEP, "chip_info.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"晶片 {die[0]:g}×{die[1]:g} µm；EC 10 個（間距 {EC_PITCH:g} µm）；扇出 {FAN:g} µm＋輸入補長 {COMP:g} µm、最小曲率半徑 {fan_rmin:.1f} µm")
    print(f"輸入扇出長度 {fan_in}（差 {max(fan_in.values()) - min(fan_in.values()):.4f} µm）；補長凸起 {bumps}；輸出扇出差 {out['fan_out_spread_um']} µm")
    print("損耗估計（不含 EC）：" + "；".join(f"軌 {x['rail']} {x['length_um']:.0f} µm、{x['n_mmi']} MMI → {x['total_db'][0]}–{x['total_db'][1]} dB" for x in loss))
    print(f"PAD {len(pads)} 個（北 {out['n_pads_side']['N']}、南 {out['n_pads_side']['S']}；GND {out['n_gnd_pads']}），"
          f"外緣離晶片邊 {EDGE:g} µm；改成右端接訊號的 heater {n_flip} 個")
    print("北側 PAD：" + "、".join(f"{p['name']}@{p['xy_um'][0]:.0f}" for p in pads if p["side"] == "N"))
    print("南側 PAD：" + "、".join(f"{p['name']}@{p['xy_um'][0]:.0f}" for p in pads if p["side"] == "S"))
    print(f"走線 {len(routes)} 條（橫移 {out['n_jog']}）；跨越波導 {out['n_crossings']} 次；Ti/AL 不同網最小距離 {d_net:.2f} µm；"
          f"到其他 TiN {d_tin:.2f} µm；Ti/AL 連通塊 {len(comps)}")
    for x in dens:
        print(f"假設 heater {x['R_kohm']:g} kΩ：單條最大 {x['I_heater_max_mA']} mA（{x['V_heater_max_V']} V）→ {x['J_line_mA_um2']} mA/µm²；"
              f"GND PAD 最大 {x['I_gnd_pad_mA']} mA（最壞 {x['I_gnd_pad_worst_mA']} mA）")
    print(f"DRC：{len(d['rules'])} 條規則，違規 {d['total']} {d['counts']}；設計區 {d['design_area_um']}（{d['design_area_source']}）；外框外 {d['outside']}")
    print(f"一致性：{checks}")
    print(f"寫出 {rt.rel(gds)}、chip_info.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
