r"""佈局審查：佈局審查——佈局有沒有照電路圖？埠序、直通線、彎道、金屬位置合理嗎？

用途：只讀 核心佈局 寫出的 GDS（多邊形與文字標記），不用畫圖時的變數，獨立重建光路並逐項審查：
  1. 光路抽取：取出所有 GDS 3 波導（MMI cell 內的除外）並聯集成連通塊；MMI 的四個埠由 MMI cell 自己的多邊形
     找出（最左、最右兩端的尖端，上下各一）；晶片光學埠是波導最左、最右的端點，名稱取最近的文字標記。
     每個連通塊必須恰好接兩個節點（MMI 埠或晶片埠）：多了是短路、少了是斷路。
  2. heater 對應：TiN（GDS 39）聯集成連通塊，編號取最近的「H」文字標記；看每塊 TiN 蓋在哪一段波導上。
  3. 由抽出的連接重算 U：MMI 用理想 H（上方埠為索引 0）、蓋有 heater 的波導段乘上該 heater 的相位
     （heater 編號 → 規格的（MZI, θ／φ）→ 相位設定檔的值），從輸入傳到輸出；五個函數都與接線表＋相位算出的 U 比較，並重算真值表。
  4. 其他審查：Ti/AL（GDS 41）不得蓋在波導上；TiN 只在相位區蓋波導；加熱條本體到其他波導（熱串擾，≥ 10 µm）、
     整塊金屬到其他波導（光吸收，≥ 3 µm）、heater 之間的最小距離；
     光學埠間距；S 彎曲率（由 GDS 中心線三點擬圓重算）；各軌經過的 MZI 數與由 GDS 量出的長度差（及其對波長、溫度的敏感度）。
  5. 故障注入（在讀回的資料上改）：刪掉一段波導（斷路）、加一條跨兩軌的波導（短路）、對調兩個 heater 標記，都必須被抓到。
  6. 審查表：每項寫明方法、結果、判定（通過／處置），交接事項寫明交給哪一步。
輸入：LUT4 s3 的 out/l4_core.gds、out/layout_info.json（只用 cell 名稱與幾何參數做說明，位置一律取自 GDS）；
      M1 s5 的 out/lut4_netlist.json、out/phases.json、out/truth_tables.csv；M2 s1 的 out/spec.json。
輸出：out/review_checks.json（審查表與數字）、out/extracted.json（抽出的連通塊、節點、heater 對應）。
執行：.\lab design\m3_layout\s2_review\review.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from shapely.geometry import LineString, Point, Polygon              # noqa: E402
from shapely.ops import unary_union                                  # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402
from common.mzi import T, embed                                      # noqa: E402
from common.optics import H                                          # noqa: E402

STEP = "lut4v2/s4_review"
LOSS_DB = 0.9                                                         # 每顆 MZI 的插入損耗（與相位設定檔一致）
MMI_AMP = 10 ** (-LOSS_DB / 40)


def chain_lossy(ops, theta, phi):
    """接線表＋相位的參考 U：每顆 MZI 乘振幅 10^(−L/20)（與相位設定檔的模型相同）。"""
    U = np.eye(5, dtype=complex)
    for (rail, _), th, ph in zip(ops, theta, phi):
        U = embed(MMI_AMP ** 2 * T(th, ph), rail, 5) @ U
    return U
CORE = "lut4v2/s3_core"
TOL = 0.01              # 節點與波導的接觸容差（µm）
LBL = 100               # 文字標記層


def flatten(structs, name, M, T, polys, mmis, mmi_name, depth=0):
    """攤平；MMI cell 不展開，只記下它的原點與轉換。"""
    st = structs[name]
    for layer, xy in st["boundaries"]:
        polys.append((layer, xy @ M.T + T))
    for s in st["srefs"]:
        M2, T2 = G.affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        if s["sname"] == mmi_name:
            mmis.append((M @ M2, M @ T2 + T))
        else:
            flatten(structs, s["sname"], M @ M2, M @ T2 + T, polys, mmis, mmi_name, depth + 1)


def mmi_ports(structs, mmi_name, sc):
    """MMI cell 的埠：GDS 3 多邊形最左、最右的頂點，依 y 分上下兩個（區域座標，µm）。"""
    own = []
    G.flatten(structs, mmi_name, np.eye(2), np.zeros(2), own)          # MMI cell 內還有子 cell，先攤平
    pts = np.vstack([xy for l, xy in own if l == 3]) * sc
    out = {}
    for side, x in (("L", pts[:, 0].min()), ("R", pts[:, 0].max())):
        ys = pts[np.isclose(pts[:, 0], x, atol=1e-3), 1]
        mid = (ys.min() + ys.max()) / 2
        out[side + "T"] = (x, float(ys[ys > mid].mean()))
        out[side + "B"] = (x, float(ys[ys < mid].mean()))
    return out


def load(gds, names):
    structs, dbu = G.parse(str(gds))
    sc = dbu / 1e-6
    polys, mmis = [], []
    flatten(structs, names["core"], np.eye(2), np.zeros(2), polys, mmis, names["mmi"])
    polys = [(l, xy * sc) for l, xy in polys]
    loc = mmi_ports(structs, names["mmi"], sc)
    mm = []
    for M, T in mmis:
        assert np.allclose(M, np.eye(2)), "MMI 有旋轉或鏡射，需另外處理"
        o = T * sc
        mm.append({k: (o[0] + v[0], o[1] + v[1]) for k, v in loc.items()})
    texts = [(xy * sc, s) for l, xy, s in structs[names["core"]]["texts"] if l == LBL]
    own = []
    G.flatten(structs, names["mmi"], np.eye(2), np.zeros(2), own)
    mmi_poly = [Polygon(xy * sc) for l, xy in own if l == 3]
    return polys, mm, texts, mmi_poly, [M_T[1] * sc for M_T in mmis]


def extract(polys, mm, texts):
    """波導連通塊 → 節點；heater → 波導段。回傳圖與診斷。"""
    wg = unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 3])
    comps = list(wg.geoms) if hasattr(wg, "geoms") else [wg]
    xs = np.array([c.bounds[0] for c in comps] + [c.bounds[2] for c in comps])
    xmin, xmax = xs.min(), xs.max()
    nodes = {}
    for k, m in enumerate(mm):
        for p, xy in m.items():
            nodes[f"M{k}.{p}"] = xy
    # 晶片埠：波導在最左、最右的端點（每塊取中心 y）
    for side, x in (("in", xmin), ("out", xmax)):
        ends = sorted({round((c.intersection(LineString([(x, -1e4), (x, 1e4)])).centroid.y), 3)
                       for c in comps if abs((c.bounds[0] if side == "in" else c.bounds[2]) - x) < 1e-6}, reverse=True)
        for y in ends:
            lab = min(texts, key=lambda t: np.hypot(t[0][0] - x, t[0][1] - y))
            ok = np.hypot(lab[0][0] - x, lab[0][1] - y) < 15 and lab[1].startswith(side)
            nodes[lab[1] if ok else f"{side}?{y}"] = (x, y)
    touch = []
    for c in comps:
        hit = [n for n, xy in nodes.items() if c.distance(Point(xy)) < TOL]
        touch.append(sorted(hit, key=lambda n: nodes[n][0]))
    # heater：TiN 連通塊與它蓋住的波導段
    tin = unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 39])
    tins = list(tin.geoms) if hasattr(tin, "geoms") else [tin]
    heaters = []
    for t in tins:
        c0 = t.centroid
        hs = [tx for tx in texts if tx[1].startswith("H")]
        lab = min(hs, key=lambda tx: np.hypot(tx[0][0] - c0.x, tx[0][1] - c0.y))
        over = [(i, c.intersection(t).area) for i, c in enumerate(comps) if c.intersects(t)]
        heaters.append(dict(label=lab[1], label_dist=float(np.hypot(lab[0][0] - c0.x, lab[0][1] - c0.y)),
                            comps=[i for i, a in over if a > 1e-6], overlap_um2=float(sum(a for _, a in over)), geom=t))
    return comps, nodes, touch, heaters


def centerline(c, step=0.25):
    """沿 x 每 step µm 切一刀，取波導在該處的上下緣中點（只取單一線段的切片）。"""
    x0, _, x1, _ = c.bounds
    pts = []
    for x in np.arange(x0 + 0.5, x1 - 0.5, step):
        seg = c.intersection(LineString([(x, -1e4), (x, 1e4)]))
        if seg.geom_type == "LineString" and not seg.is_empty:
            ys = [q[1] for q in seg.coords]
            pts.append((x, (min(ys) + max(ys)) / 2))
    return np.array(pts)


def min_radius(cl, stride=8):
    """相距 stride 點（約 2 µm）的三點外接圓半徑的最小值；共線（半徑極大）的忽略。"""
    a, b, c = cl[:-2 * stride], cl[stride:-stride], cl[2 * stride:]
    ab, bc, ca = (np.hypot(*(b - a).T), np.hypot(*(c - b).T), np.hypot(*(a - c).T))
    area = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])) / 2
    ok = area > 1e-6
    return float(np.min(ab[ok] * bc[ok] * ca[ok] / (4 * area[ok]))) if ok.any() else 1e9


def propagate(comps, nodes, touch, heaters, phase_of, n=5):
    """由抽出的連接計算 5×5 U：MMI 用理想 H，蓋 heater 的段乘 e^{iφ}。"""
    seg_phase = {}
    for h in heaters:
        for i in h["comps"]:
            seg_phase[i] = seg_phase.get(i, 0.0) + phase_of(h["label"])
    into = {}                                                         # 右端節點 ← (左端節點, 段)
    for i, t in enumerate(touch):
        if len(t) == 2:
            into[t[1]] = (t[0], i)
    memo = {}

    def field(node):
        if node in memo:
            return memo[node]
        if node.startswith("in"):
            v = np.zeros(n, complex)
            v[int(node[2:])] = 1.0
        elif node.startswith("M") and node.split(".")[1][0] == "R":     # MMI 輸出＝H · [上輸入, 下輸入]
            k = node.split(".")[0]
            a = arrive(f"{k}.LT")
            b = arrive(f"{k}.LB")
            row = 0 if node.endswith("T") else 1
            v = MMI_AMP * (H[row, 0] * a + H[row, 1] * b)   # 每顆 MZI 的損耗平均分給兩顆 MMI
        else:
            v = arrive(node)
        memo[node] = v
        return v

    def arrive(node):
        src, i = into[node]
        return field(src) * np.exp(1j * seg_phase.get(i, 0.0))

    return np.array([arrive(f"out{k}") if f"out{k}" in into else np.zeros(n) for k in range(n)])


def truth(U, R, tgt):
    words = [format(k, "04b") for k in range(16)]
    V = np.array([[1 - 2 * int(c) for c in w] + [R] for w in words], complex)   # E±：位元 0＝+1、1＝−1；R＝+R
    P = np.abs(V @ U.T) ** 2
    Da, Db = P[:, 1] - P[:, 3], P[:, 3] - P[:, 2]                    # 雙差值：P(o2)－P(o4)、P(o4)－P(o3)
    y = (Da > 0) & (Db > 0)
    return sum(bool(v) == bool(tgt[w]) for w, v in zip(words, y))


def main():
    info = json.loads(paths.OUT(CORE, "layout_info.json").read_text(encoding="utf-8"))
    names, geo = info["cells"], info["geometry"]
    gds = paths.OUT(CORE, "l4_core.gds")
    hand = "lut4v2/s1_handoff"
    net = json.loads(paths.OUT(hand, "lut4_netlist.json").read_bytes())
    ph = json.loads(paths.OUT(hand, "phases.json").read_text(encoding="utf-8"))
    spec = json.loads(paths.OUT("lut4v2/s1_handoff", "spec.json").read_text(encoding="utf-8"))
    with open(paths.OUT(hand, "truth_tables.csv"), encoding="utf-8-sig") as fh:
        tgt = {}
        for r in csv.DictReader(fh):
            tgt.setdefault(r["function"], {})[r["x1"] + r["x2"] + r["x3"] + r["x4"]] = int(r["target"])
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    by_heater = {c["heater"]: c for c in spec["phase_channels"]}

    polys, mm, texts, mmi_poly, mmi_org = load(gds, names)
    comps, nodes, touch, heaters = extract(polys, mm, texts)

    def run(comps, touch, heaters):
        res = {}
        for fn, f in ph["functions"].items():
            def phase_of(lbl):
                c = by_heater[lbl]
                return f["theta" if c["kind"] == "theta" else "phi"][c["phase_index"]]
            U = propagate(comps, nodes, touch, heaters, phase_of)
            Uref = chain_lossy(ops, f["theta"], f["phi"])
            res[fn] = dict(U_err=float(np.max(np.abs(U - Uref))), passed=int(truth(U, ph["R"], tgt[fn])))
        return res

    rep = run(comps, touch, heaters)
    bad_nodes = [i for i, t in enumerate(touch) if len(t) != 2]

    # ---------- 其他審查 ----------
    wg_all = unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 3]
                         + [Polygon(np.array(p.exterior.coords) + o) for o in mmi_org for p in mmi_poly])
    al = unary_union([Polygon(xy).buffer(0) for l, xy in polys if l == 41])
    al_over_wg = float(al.intersection(wg_all).area)
    tin_over = [h["overlap_um2"] / 0.45 for h in heaters]               # 蓋住波導的長度（µm，除以波導寬）
    d_body, d_other, d_heat = [], [], []
    for k, h in enumerate(heaters):
        own = set(h["comps"])
        body = h["geom"].intersection(unary_union([comps[i] for i in own]).buffer(0.3))   # 加熱條本體：只取緊貼波導的條狀部分（先前審查 R10）
        others = [c for i, c in enumerate(comps) if i not in own]
        d_body.append(min(c.distance(body) for c in others))          # 熱串擾看本體
        d_other.append(min(c.distance(h["geom"]) for c in others))    # 光吸收看整塊 TiN（含落墊）
        d_heat.append(min(g["geom"].distance(h["geom"]) for j, g in enumerate(heaters) if j != k))
    d_al = min(c.distance(al) for c in comps)
    ins = sorted([v for n, v in nodes.items() if n.startswith("in") and "?" not in n], key=lambda v: -v[1])
    pitch = sorted({round(ins[i][1] - ins[i + 1][1], 3) for i in range(len(ins) - 1)})
    per_rail = [sum(1 for p, _ in ops if r in (p, p + 1)) for r in range(5)]
    # S 彎：每個連通塊沿 x 切片取中心線，以相距約 2 µm 的三點擬圓求曲率半徑（先前審查 R8：只用 GDS）
    r_min, arm_excess = 1e9, []
    for i, c in enumerate(comps):
        cl = centerline(c)
        if len(cl) > 20:
            r_min = min(r_min, min_radius(cl))
        if len(touch[i]) == 2 and all(n.startswith("M") for n in touch[i]):   # MZI 的臂：兩端都是 MMI 埠
            arm_excess.append(float(np.sum(np.hypot(*np.diff(cl, axis=0).T))) - (cl[-1][0] - cl[0][0]))
    extra_gds = 2 * float(np.mean(arm_excess))                        # 每經過一顆 MZI：四個 S 彎＝兩個臂的多出長度
    ng, dndt, lam = 4.2, 1.8e-4, 1.55                                 # 群折射率、矽熱光係數（1/K）、波長（µm）：量級估計
    dphi_dlam = 2 * np.pi * ng * extra_gds / lam ** 2 * 1e-3          # rad/nm
    dphi_dT = 2 * np.pi * dndt * extra_gds / lam                      # rad/K
    mzi_count_ok = len(mm) == 14 and len(heaters) == 14

    # ---------- 故障注入 ----------
    # 斷路：刪掉一段 MZI 內部的臂（兩端都是 MMI 埠的連通塊）
    arm = next(i for i, t in enumerate(touch) if len(t) == 2 and all(n.startswith("M") for n in t))
    c_open = [c for i, c in enumerate(comps) if i != arm]
    t_open = [t for i, t in enumerate(touch) if i != arm]
    try:
        r_open = run(c_open, t_open, [dict(h, comps=[c_open.index(comps[i]) for i in h["comps"] if i != arm]) for h in heaters])
        open_caught = any(v["U_err"] > 1e-6 for v in r_open.values())
    except KeyError:
        open_caught = True                                            # 找不到來源節點，傳遞中斷
    # 短路：在 x＝某直通段中間加一條跨兩軌的波導
    x_mid = geo["mzi_length_um"] * 1.5
    bridge = Polygon([(x_mid - 0.2, 1.0), (x_mid + 0.2, 1.0), (x_mid + 0.2, -2 * geo["pitch_um"] - 1), (x_mid - 0.2, -2 * geo["pitch_um"] - 1)])
    c_short, n_short, t_short, _ = extract(polys + [(3, np.array(bridge.exterior.coords))], mm, texts)
    short_caught = any(len(t) != 2 for t in t_short) or len(c_short) != len(comps)
    # heater 標記對調
    h_sw = [dict(h) for h in heaters]
    i1 = next(k for k, h in enumerate(h_sw) if h["label"] == "H01")
    i2 = next(k for k, h in enumerate(h_sw) if h["label"] == "H02")
    h_sw[i1]["label"], h_sw[i2]["label"] = "H02", "H01"
    swap_caught = any(v["U_err"] > 1e-6 for v in run(comps, touch, h_sw).values())

    U_err = max(v["U_err"] for v in rep.values())
    checks = [
        dict(id="V1", item="光路連通", method="GDS 3 聯集成連通塊，每塊接到的 MMI 埠／晶片埠數",
             result=f"{len(comps)} 塊，每塊恰接 2 個節點" if not bad_nodes else f"{len(bad_nodes)} 塊不是 2 個節點",
             ok=not bad_nodes),
        dict(id="V2", item="MMI 與 heater 個數", method="GDS 中的 MMI 參照、TiN 連通塊", result=f"MMI {len(mm)}、heater {len(heaters)}",
             ok=mzi_count_ok),
        dict(id="V3", item="由佈局重算 U", method="抽出的連接＋理想 MMI＋heater 相位，與接線表＋相位算出的 U 比較",
             result=f"最大差 {U_err:.1e}", ok=U_err < 1e-12),
        dict(id="V4", item="由佈局重算真值表", method=f"{len(rep)} 個函數各 16 組（雙差值＋AND）", result=f"{sum(v['passed'] for v in rep.values())}/{16 * len(rep)}",
             ok=sum(v["passed"] for v in rep.values()) == 16 * len(rep)),
        dict(id="V5", item="光學埠", method="波導最左、最右端點與文字標記",
             result=f"輸入 {sum(n.startswith('in') and '?' not in n for n in nodes)}、輸出 {sum(n.startswith('out') and '?' not in n for n in nodes)}；間距 {'、'.join(f'{v:g}' for v in pitch)} µm",
             ok=sum(n.startswith(("in", "out")) and "?" not in n for n in nodes) == 10),
        dict(id="V6", item="Ti/AL 不蓋波導", method="GDS 41 與 GDS 3（含 MMI）交集面積", result=f"{al_over_wg:.3g} µm²", ok=al_over_wg == 0),
        dict(id="V7", item="TiN 只在相位區蓋波導", method="每塊 TiN 蓋住波導的長度",
             result=f"{min(tin_over):.1f}–{max(tin_over):.1f} µm（加熱條本體 100 µm，加上兩端 3 µm 寬引線各一半），每塊只蓋 1 段", ok=all(len(h["comps"]) == 1 for h in heaters)),
        dict(id="V8", item="加熱條本體到其他波導", method="蓋在波導上的 TiN 本體到其他波導段的最小距離（熱串擾；以 TiN 間距 10 µm 為下限）",
             result=f"{min(d_body):.2f} µm", ok=min(d_body) >= 10.0),
        dict(id="V8b", item="金屬到其他波導", method="整塊 TiN（含落墊）與 Ti/AL 到不在它下方的波導的最小距離（光吸收；下限 3 µm）",
             result=f"TiN {min(d_other):.2f} µm、Ti/AL {d_al:.2f} µm", ok=min(d_other) >= 3.0 and d_al >= 3.0),
        dict(id="V9", item="heater 之間", method="TiN 塊之間的最小距離（DRC 只要求 ≥ 10 µm）", result=f"{min(d_heat):.1f} µm",
             ok=min(d_heat) >= 10.0),
        dict(id="V10", item="故障注入", method="斷路、短路、heater 標記對調",
             result=f"斷路 {'抓到' if open_caught else '漏掉'}、短路 {'抓到' if short_caught else '漏掉'}、對調 {'抓到' if swap_caught else '漏掉'}",
             ok=open_caught and short_caught and swap_caught),
        dict(id="V11", item="S 彎曲率", method="由 GDS 的中心線三點擬圓（下限 10 µm）", result=f"最小 {r_min:.1f} µm", ok=r_min >= 10.0),
        dict(id="P1", item="各軌固定相位差", method="由 GDS 量 MZI 臂的中心線長度，推每經過一顆 MZI 比直通軌多走的長度",
             result=f"每顆 MZI 多 {extra_gds:.2f} µm（核心佈局參數算 {geo['rail_vs_bypass_extra_um']:.2f}）；各軌經過的 MZI 數 {per_rail}；"
                    f"約 {dphi_dlam:.2f} rad/nm、{dphi_dT:.4f} rad/K（每顆）",
             ok=None, disposition="不修改佈局：由晶片完成後的相位校正吸收（需求 K1）"),
        dict(id="P2", item="光學埠間距", method="輸入埠相鄰距離", result=f"{'、'.join(f'{v:g}' for v in pitch)} µm",
             ok=None, disposition="光纖陣列的間距較大；晶片整合用扇出波導把埠距拉開到 EC 的間距"),
        dict(id="P3", item="熱串擾", method="加熱條本體到最近的其他波導（上一軌或同一顆 MZI 的下臂，兩者幾乎等距）", result=f"{min(d_body):.1f} µm（未模擬溫度分布）",
             ok=None, disposition="DRC 不管熱串擾；量測校正時一併處理（K1）"),
    ]
    out = dict(gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(), scope="LUT4 核心（核心佈局 的 GDS）；只用 GDS 中的多邊形與文字標記",
               n_components=len(comps), n_nodes=len(nodes), per_function=rep, U_err_max=U_err,
               passed=sum(v["passed"] for v in rep.values()), al_over_wg_um2=al_over_wg,
               tin_over_wg_um=[round(x, 2) for x in tin_over], min_heater_body_to_other_wg_um=float(min(d_body)),
               sbend_rmin_gds_um=round(r_min, 2), mzi_extra_gds_um=round(extra_gds, 3), dphi_dlam_rad_nm=round(dphi_dlam, 3),
               dphi_dT_rad_K=round(dphi_dT, 4),
               min_tin_to_other_wg_um=float(min(d_other)), min_al_to_wg_um=float(d_al),
               min_heater_to_heater_um=float(min(d_heat)), port_pitch_um=pitch, mzi_per_rail=per_rail,
               faults=dict(open=open_caught, short=short_caught, heater_swap=swap_caught),
               checks=checks, all_ok=all(c["ok"] for c in checks if c["ok"] is not None),
               n_pass=sum(c["ok"] is True for c in checks), n_disposition=sum(c["ok"] is None for c in checks))
    paths.OUT(STEP, "review_checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ext = dict(nodes={k: [round(v[0], 3), round(v[1], 3)] for k, v in nodes.items()},
               components=[dict(index=i, nodes=t, bounds=[round(b, 3) for b in c.bounds]) for i, (c, t) in enumerate(zip(comps, touch))],
               heaters=[dict(label=h["label"], components=h["comps"], label_dist_um=round(h["label_dist"], 2),
                             bounds=[round(b, 3) for b in h["geom"].bounds]) for h in heaters])
    paths.OUT(STEP, "extracted.json").write_text(json.dumps(ext, ensure_ascii=False, indent=1), encoding="utf-8")

    for c in checks:
        mark = "通過" if c["ok"] is True else ("未通過" if c["ok"] is False else "處置")
        print(f"{c['id']:>3} {mark}　{c['item']}：{c['result']}" + (f"（{c['disposition']}）" if c["ok"] is None else ""))
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'review_checks.json'))}、extracted.json")
    sys.exit(0 if out["all_ok"] else 1)


if __name__ == "__main__":
    main()
