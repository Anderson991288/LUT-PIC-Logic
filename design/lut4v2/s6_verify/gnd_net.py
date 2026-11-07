r"""heater 供電回路的電阻網路：依每段走線的長、寬、厚度建立節點方程式，求多個 heater 同時驅動時的電壓、功率與相位誤差。

用途：取代「單一 heater 的獨立串聯電阻」估算。verify.py 呼叫 analyze()，結果寫入 connectivity.json 的 electrical.gnd_network，
      逐段資料寫入 out/gnd_segments.json。全部是由幾何推算的模型值，不是寄生萃取，也不是量測。
線段來源：走線與地網中心線、線寬取自 chip_info.json（routes[].pts、routes[].bus、wire_width_um、gnd_wire_width_um；有 group 欄位的走線屬於共用地網），
      heater 落墊座標取自 layout_info.json；再以 chip.gds 的 GDS 41 逐段核對（中心線在金屬內、線寬相符、沒有模型以外的金屬）。
節點分析：每個 Ti/AL 網切成線段（頂點、T 字接點、PAD 邊界都是節點；重複線段只算一次），R＝ρ·L／(W·t)。
      heater 是兩個落墊之間的電阻 R_h。訊號 PAD 接理想電壓源，GND PAD 為 0 V。解出 ΔV＝A·V（A 為 14×14 矩陣，與電壓大小無關）。
相位模型：φ＝π·P／P_π、P＝ΔV²／R_h。理想電壓 V_k 使無走線電阻時相位恰為 φ_k，以 v_k＝√φ_k 正規化後 φ'＝(A·v)²。
報告的四種條件：
  single：只驅動一個 heater（其他訊號 PAD 為 0 V），2π 時的相位不足。其值與其他 heater 無關，單路校正可吸收。
  multi：14 個 heater 同時 2π，無校正。A 的非對角元為負或零，所以其他 heater 全開是每個 heater 的最差條件。
  single_cal_residual：先逐路校正（V_k 乘 1／A_kk，使單路驅動時相位正確），再同時驅動。這是單路校正吸收不了的部分。
  joint_cal：以 A⁻¹ 同時求 14 個電壓（跨通道聯合校正）。在本模型內殘差為零，代價是要先得到 A，並列出所需電壓增量。
另以七個範例函數與全表相位庫的實際相位計算相位誤差，並把受影響的相位放回光路模型，看裕量與判讀。
輸入：由 verify.py 傳入 chip_info、layout_info、規格與讀回的 Ti/AL 連通塊；phases.json、s0_coverage/out/merged_phases.npz（只讀）。
輸出：analyze() 回傳的 dict；out/gnd_segments.json。
"""
import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4*
import synth4 as S                                                   # noqa: E402

RHO_AL = 2.8e-8          # Ti/AL 電阻率（Ω·m，沿用 verify.py：以純鋁估，Ti 層忽略）
PAD_WH = (80.0, 100.0)   # PDK HeaterPad（µm，同 chip.py）
TWO_PI = 2 * np.pi
ASSUMPTIONS = [
    "Ti/AL 電阻率 2.8e-8 Ω·m、厚 0.22 µm（片電阻約 0.127 Ω/□），沿用專案現有值；Ti 層、薄膜電阻率上升與溫度係數未計",
    "heater 電阻 R_h 是假設值（平台未公開 TiN 片電阻），取 chip_info 的 0.5、1、2 kΩ，並視為不隨溫度改變",
    "相位與 heater 功率成正比，φ＝π·P／P_π；熱串擾未計",
    "線段以中心線長度計，轉角與 T 字接點未做二維電流修正（每個轉角約高估 0.4 □）；Ti/AL 與 TiN 的接觸電阻未計",
    "PAD 視為等電位，線段算到 PAD 邊界（chip_info 的 length_um 含伸入 PAD 的 20 µm，本模型不計）；PAD 內電流擴散未計",
    "訊號 PAD 為理想電壓源，每個 GND PAD 都接到理想 0 V；探針、打線、驅動器輸出阻抗與片外共地阻抗未計",
]


def _k(p):
    return (round(float(p[0]), 3), round(float(p[1]), 3))


def _pad_box(p):
    (x, y), (w, h) = p["xy_um"], PAD_WH
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def raw_segments(info):
    """{net: [(a, b, 線寬, 類別)]}。"""
    w_sig = info["wire_width_um"]
    w_gnd = info.get("gnd_wire_width_um", w_sig)
    nets = {}
    for r in info["routes"]:
        w = w_gnd if r.get("group") else w_sig
        s = nets.setdefault(r["net"], [])
        for a, b in zip(r["pts"][:-1], r["pts"][1:]):
            s.append((a, b, w, "走線"))
        for ln in r.get("bus", []):
            for a, b in zip(ln[:-1], ln[1:]):
                s.append((a, b, w, "核心地線"))
    return nets


def split_net(segs, pad):
    """切成節點之間的線段：頂點、線段互相交會處與 PAD 邊界都切開；PAD 內的部分併成一個節點，重複線段只留一條。"""
    use = [s for s in segs if np.hypot(s[0][0] - s[1][0], s[0][1] - s[1][1]) > 1e-6]
    lines = [LineString([s[0], s[1]]) for s in use]
    cuts = {_k(p) for a, b, _, _ in use for p in (a, b)}
    edge = pad.exterior
    for i, li in enumerate(lines):
        for g in [edge] + lines[i + 1:]:
            x = li.intersection(g)
            for q in (x.geoms if hasattr(x, "geoms") else [x]):
                if q.geom_type == "Point":
                    cuts.add(_k((q.x, q.y)))
    cuts = sorted(cuts)
    pts = [Point(c) for c in cuts]
    edges = {}
    for (a, b, w, kind), li in zip(use, lines):
        on = sorted((li.project(p), c) for p, c in zip(pts, cuts) if li.distance(p) < 2e-3)
        for (d0, p0), (d1, p1) in zip(on[:-1], on[1:]):
            if d1 - d0 < 2e-3:
                continue
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            if pad.contains(Point(mid)):
                continue
            key = tuple(sorted((p0, p1)))
            if key not in edges or w > edges[key]["w"]:
                edges[key] = dict(a=p0, b=p1, L=d1 - d0, w=w, kind=kind)
    return list(edges.values())


class Network:
    def __init__(self, info, linfo, spec):
        self.t_um = info["al_thickness_um"]
        pads = {p["name"]: p for p in info["pads"]}
        self.pad_of = {c["heater"]: c["pad"] for c in spec["phase_channels"]}
        self.H = sorted(self.pad_of)
        self.edges = []
        node_net = {}
        for net, segs in raw_segments(info).items():
            pb = _pad_box(pads[net])
            for e in split_net(segs, pb):
                e["net"] = net
                e["R"] = RHO_AL * e["L"] * 1e-6 / (e["w"] * 1e-6 * self.t_um * 1e-6)
                e["xy"] = [list(e["a"]), list(e["b"])]
                for end in "ab":
                    if pb.buffer(2e-3).contains(Point(e[end])):
                        e[end] = "PAD:" + net
                    node_net.setdefault(e[end], set()).add(net)
                self.edges.append(e)
        assert all(len(v) == 1 for v in node_net.values()), "同一節點屬於兩個網"
        self.node_net = {k: next(iter(v)) for k, v in node_net.items()}
        self.gnd_of, self.ends = {}, {}
        gnd_names = {p["name"] for p in info["pads"] if p["heater"] is None}
        for h in linfo["heaters"]:
            ends = [_k(p) for p in h["landings_um"]]
            nets = [self.node_net[e] for e in ends]                  # 落墊不在任何網上時這裡會出錯（KeyError），不靜默略過
            sig = [e for e, n in zip(ends, nets) if n == self.pad_of[h["heater"]]]
            gnd = [e for e, n in zip(ends, nets) if n in gnd_names]
            assert len(sig) == 1 and len(gnd) == 1, (h["heater"], nets)
            self.ends[h["heater"]] = (sig[0], gnd[0])
            self.gnd_of[h["heater"]] = self.node_net[gnd[0]]
        self.nodes = sorted((n for n in node_net if not isinstance(n, str)), key=str)
        self.fixed = sorted(n for n in node_net if isinstance(n, str))
        self.ix = {n: i for i, n in enumerate(self.nodes)}
        self.fx = {n: i for i, n in enumerate(self.fixed)}

    def laplacian(self, Rh_ohm=None):
        """(L_uu, L_uf)：Rh_ohm 為 None 時不接 heater（用來求走線本身的電阻）。"""
        n, m = len(self.nodes), len(self.fixed)
        Luu, Luf = np.zeros((n, n)), np.zeros((n, m))

        def stamp(a, b, g):
            for p, q in ((a, b), (b, a)):
                if p in self.ix:
                    i = self.ix[p]
                    Luu[i, i] += g
                    if q in self.ix:
                        Luu[i, self.ix[q]] -= g
                    else:
                        Luf[i, self.fx[q]] -= g
        for e in self.edges:
            stamp(e["a"], e["b"], 1.0 / e["R"])
        if Rh_ohm is not None:
            for h in self.H:
                stamp(*self.ends[h], 1.0 / Rh_ohm)
        return Luu, Luf

    def transfer(self, Rh_ohm):
        """A：訊號 PAD 電壓 → heater 兩端電壓差（14×14），GND PAD 為 0。"""
        Luu, Luf = self.laplacian(Rh_ohm)
        F = np.zeros((len(self.fixed), len(self.H)))
        for j, h in enumerate(self.H):
            F[self.fx["PAD:" + self.pad_of[h]], j] = 1.0
        Vn = np.linalg.solve(Luu, -Luf @ F)
        A = np.zeros((len(self.H), len(self.H)))
        for k, h in enumerate(self.H):
            s, g = self.ends[h]
            A[k] = Vn[self.ix[s]] - Vn[self.ix[g]]
        return A

    def wire_resistance(self):
        """不接 heater 時的走線電阻：訊號線 R_sig；地網的 Z（Z_ii＝自身回路，Z_ij＝j 的電流在 i 的地端造成的電壓）。"""
        Luu, _ = self.laplacian()
        Z = np.linalg.inv(Luu)
        at = lambda a, b: float(Z[self.ix[a], self.ix[b]])
        r_sig = {h: at(self.ends[h][0], self.ends[h][0]) for h in self.H}
        r_gnd = {h: at(self.ends[h][1], self.ends[h][1]) for h in self.H}
        nets = {}
        for h in self.H:
            nets.setdefault(self.gnd_of[h], []).append(h)
        mutual = {n: {a: {b: round(at(self.ends[a][1], self.ends[b][1]), 3) for b in hs} for a in hs} for n, hs in sorted(nets.items())}
        return r_sig, r_gnd, mutual


def gds_check(net, al, al_name, info):
    """中心線、線寬與 chip.gds 的 GDS 41 比對。"""
    poly = {n[0]: g for g, n in zip(al, al_name) if len(n) == 1}
    pads = {p["name"]: _pad_box(p) for p in info["pads"]}
    out_um, width_rows, covered = 0.0, [], {}
    for e in net.edges:
        a, b = e["xy"]
        g = poly[e["net"]]
        li = LineString([a, b])
        out_um += li.difference(g.buffer(1e-3)).length
        covered.setdefault(e["net"], []).append(li.buffer(e["w"] / 2, cap_style=3, join_style=2))
        if e["L"] > e["w"] * 2.5:                                      # 太短的線段中點落在接點附近，量不出線寬
            ux, uy = (b[0] - a[0]) / e["L"], (b[1] - a[1]) / e["L"]
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            cut = LineString([(mx - uy * 4 * e["w"], my + ux * 4 * e["w"]), (mx + uy * 4 * e["w"], my - ux * 4 * e["w"])]).intersection(g)
            parts = [c for c in (cut.geoms if hasattr(cut, "geoms") else [cut]) if c.distance(Point(mx, my)) < 1e-3]
            width_rows.append((e["net"], e["w"], parts[0].length if parts else 0.0, e["L"]))
    dev = [(n, w, m, L) for n, w, m, L in width_rows if abs(m - w) > 0.05]
    extra = {}
    for n, gs in covered.items():
        rest = poly[n].difference(unary_union(gs).buffer(0.01)).difference(pads[n].buffer(0.01))
        big = [p for p in (rest.geoms if hasattr(rest, "geoms") else [rest]) if p.area > 1.0]
        extra[n] = round(sum(p.area for p in big), 2)
    arms = {}
    for n in sorted({e["net"] for e in net.edges}):
        rest = poly[n].difference(pads[n].buffer(0.01))             # 0.01 µm：PAD 座標取到 1 nm 後與 GDS 的差，不算分支
        arms[n] = sum(g.area > 1.0 for g in (rest.geoms if hasattr(rest, "geoms") else [rest]))
    return dict(centerline_outside_metal_um=round(out_um, 4), width_samples=len(width_rows), width_mismatch=len(dev),
                width_mismatch_rows=[dict(net=n, nominal_um=w, gds_um=round(m, 3), length_um=round(L, 1)) for n, w, m, L in dev],
                width_gds_um=sorted({round(m, 2) for _, _, m, _ in width_rows}), metal_outside_model_um2=extra, arms_outside_pad=arms)


def drive(P, hidx):
    """相位（B, 14，依 θ1、φ1…）→ 依 heater 排列的目標相位 [0, 2π)。"""
    v = np.mod(P[:, hidx], TWO_PI)
    return np.where(np.isclose(v, TWO_PI, atol=1e-6), 0.0, v)


def apply_phase(P, hidx, phi):
    Q = P.copy()
    Q[:, hidx] = phi
    return Q


def margins(arch, P, ins):
    W = arch.powers(P)
    Da, Db = W[:, :, 1] - W[:, :, 3], W[:, :, 3] - W[:, :, 2]
    return np.where(ins, np.minimum(Da, Db), np.maximum(-Da, -Db))


def phase_cases(A, phi):
    """phi：(B, 14) 目標相位 → 無校正與單路校正後的實際相位。"""
    v = np.sqrt(phi)
    raw = (v @ A.T) ** 2
    cal = ((v / np.diag(A)) @ A.T) ** 2
    return raw, cal


def analyze(info, linfo, spec, ph, lib_path, al, al_name, seg_path):
    net = Network(info, linfo, spec)
    r_sig, r_gnd, mutual = net.wire_resistance()
    H = net.H
    chk = gds_check(net, al, al_name, info)
    ch = {c["heater"]: c for c in spec["phase_channels"]}
    hidx = np.array([2 * ch[h]["phase_index"] + (ch[h]["kind"] == "phi") for h in H])
    arch = S.Arch.from_code("3142132", loss_db=ph["loss_db_per_mzi"], order=(1, 3, 2))
    assert abs(ph["R"] - 3.0) < 1e-12
    F = ph["functions"]
    Pf = {n: np.array([x for t in zip(f["theta"], f["phi"]) for x in t])[None] for n, f in F.items()}
    insf = {n: np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool)[None] for n, f in F.items()}
    lib = np.load(lib_path)
    PL = lib["phases"]
    insl = (lib["masks"][:, None].astype(np.int64) >> np.arange(16)) & 1 == 1
    base_l = margins(arch, PL, insl).min(1)
    good = base_l > 0                                                 # 相位庫中有解的真值表
    by_R = {}
    for Rk in sorted({d["R_kohm"] for d in info["current_density"]}):
        A = net.transfer(Rk * 1e3)
        d = np.diag(A)
        off = A - np.diag(d)
        full = np.full((1, len(H)), TWO_PI)
        single = TWO_PI * (1 - d ** 2)
        raw, cal = phase_cases(A, full)
        multi, resid = TWO_PI - raw[0], TWO_PI - cal[0]
        vj = np.linalg.solve(A, np.sqrt(full[0]))                     # 聯合校正：同時 2π 所需電壓
        rnd = np.random.default_rng(5).uniform(0, TWO_PI, (4000, len(H)))   # 抽樣確認全開是最差條件
        worst_rnd = float(np.abs(rnd - phase_cases(A, rnd)[1]).max())
        k1, km, kr = int(np.argmax(single)), int(np.argmax(multi)), int(np.argmax(resid))
        funcs = {}
        for n in F:
            phi = drive(Pf[n], hidx)
            r0, c0 = phase_cases(A, phi)
            m0 = margins(arch, Pf[n], insf[n]).min()
            m_raw = margins(arch, apply_phase(Pf[n], hidx, r0), insf[n]).min()
            m_cal = margins(arch, apply_phase(Pf[n], hidx, c0), insf[n]).min()
            funcs[n] = dict(margin_nominal=round(float(m0), 4), err_max_uncal_rad=round(float(np.abs(phi - r0).max()), 4),
                            err_max_single_cal_rad=round(float(np.abs(phi - c0).max()), 4),
                            margin_uncal=round(float(m_raw), 4), margin_single_cal=round(float(m_cal), 4))
        phiL = drive(PL, hidx)
        rL, cL = phase_cases(A, phiL)
        mL_raw = margins(arch, apply_phase(PL, hidx, rL), insl).min(1)
        mL_cal = margins(arch, apply_phase(PL, hidx, cL), insl).min(1)
        libr = dict(n_tables=int(good.sum()), margin_nominal_min=round(float(base_l[good].min()), 4),
                    err_max_uncal_rad=round(float(np.abs(phiL - rL)[good].max()), 4), err_max_single_cal_rad=round(float(np.abs(phiL - cL)[good].max()), 4),
                    margin_uncal_min=round(float(mL_raw[good].min()), 4), margin_single_cal_min=round(float(mL_cal[good].min()), 4),
                    n_fail_uncal=int((mL_raw[good] <= 0).sum()), n_fail_single_cal=int((mL_cal[good] <= 0).sum()),
                    worst_single_cal=f"0x{int(lib['masks'][good][np.argmin(mL_cal[good])]):04X}")
        by_R[f"{Rk:g}"] = dict(
            single=dict(condition="只驅動一個 heater 到 2π，其他訊號 PAD 0 V；與其他 heater 的設定無關，可由單路校正吸收",
                        dphi_2pi_rad={h: round(float(x), 4) for h, x in zip(H, single)}, max_rad=round(float(single[k1]), 4), worst_heater=H[k1]),
            multi=dict(condition="14 個 heater 同時 2π、無校正（同一地網全開是每個 heater 的最差條件）",
                       dphi_2pi_rad={h: round(float(x), 4) for h, x in zip(H, multi)}, max_rad=round(float(multi[km]), 4), worst_heater=H[km]),
            single_cal_residual=dict(condition="先逐路校正（其他 heater 關閉時相位正確），再 14 個同時 2π；單路校正吸收不了的部分",
                                     dphi_2pi_rad={h: round(float(x), 4) for h, x in zip(H, resid)}, max_rad=round(float(resid[kr]), 4), worst_heater=H[kr],
                                     random_phase_max_rad=round(worst_rnd, 4)),
            joint_cal=dict(condition="以 A⁻¹ 同時求 14 個電壓（跨通道聯合校正）；本模型內殘差為零，須先由量測得到 A",
                           residual_rad=round(float(np.abs((A @ vj) ** 2 - TWO_PI).max()), 9),
                           v_increase_vs_ideal_max_pct=round(float((vj / np.sqrt(TWO_PI) - 1).max() * 100), 2)),
            off_diagonal_nonpositive=bool((off <= 1e-12).all()), functions=funcs, library=libr)
    r1 = by_R["1"]
    n_shared = sum(1 for m in mutual.values() for a in m for b in m[a] if a != b and m[a][b] > 1e-6) // 2
    segs = sorted((dict(net=e["net"], kind=e["kind"], xy_um=e["xy"], L_um=round(e["L"], 3), W_um=e["w"], R_ohm=round(e["R"], 4)) for e in net.edges),
                  key=lambda e: (e["net"], e["xy_um"]))
    seg_path.write_text(json.dumps(dict(scope="由幾何推算的模型值", rho_ohm_m=RHO_AL, t_um=net.t_um, segments=segs), ensure_ascii=False, indent=0), encoding="utf-8")
    route_r = {}
    for e in net.edges:
        route_r[e["net"]] = route_r.get(e["net"], 0.0) + e["R"]
    return dict(
        scope="由幾何與假設值推算的模型值，不是寄生萃取，也不是量測",
        assumptions=ASSUMPTIONS, sources=["chip_info.json routes[].pts／bus、wire_width_um、gnd_wire_width_um", "layout_info.json heaters[].landings_um", "chip.gds GDS 41（核對）"],
        sheet_resistance_ohm_sq=round(RHO_AL / (net.t_um * 1e-6), 4), n_segments=len(net.edges), n_nodes=len(net.nodes),
        widths_um=sorted({e["w"] for e in net.edges}), shared_gnd_pairs=n_shared,
        sig_series_ohm={h: round(r_sig[h], 3) for h in H}, gnd_self_ohm={h: round(r_gnd[h], 3) for h in H}, gnd_mutual_ohm=mutual,
        net_total_ohm={k: round(v, 3) for k, v in sorted(route_r.items())},
        gds_check=chk, by_R_heater_kohm=by_R,
        worst=dict(R_h_kohm=1, single_rad=r1["single"]["max_rad"], multi_rad=r1["multi"]["max_rad"], residual_rad=r1["single_cal_residual"]["max_rad"],
                   multi_heater=r1["multi"]["worst_heater"], residual_heater=r1["single_cal_residual"]["worst_heater"]))
