r"""論文 M1 s1：現有晶片要以 10 Gb/s 運作，時序、功率、相位各差多少（預算表）。

用途：只用前面步驟已有的結果做三項一階預算，不另跑元件模擬：
  1. 時序：由佈局幾何（課程 M3 s1 每欄 MZI 比直通多的長度、課程 M3 s3 的扇入／扇出長度）算每顆 MZI 輸入端與每個輸出的到達時間差（skew），
     與一階取樣窗允許的 skew 比較；並列出片外常見的時間差來源（光纖、RF 線長度差）。
  2. 功率：最差那組輸入（含 MMI 損耗的 B7、重新校正的相位）的判讀電流要大於 Q 倍總雜訊加偏移，反推每根輸入光纖需要的功率；
     雜訊含 TIA 熱雜訊、比較器雜訊與偏移、shot noise、RIN（共同光源），頻寬用等效雜訊頻寬。
  3. 相位：5 路輸入光由片外分光、各走一根光纖進晶片；先求確定性相位偏差的容許值（各路偏 ±δ 的最差組合下 margin 保留 90%，
     含 MMI 損耗的 B7），再求溫度與雷射波長要穩到多少。漂移是固定的偏差，不能直接用課程 M2 s1 的隨機誤差 σ。
  時序另列判讀埠 o2、o4 的所有路徑範圍（兩者最晚的路徑相同，但最早的不同，不能說同時到達）。
  接收端、發射端與光纖的參數是「介面假設」（見 ASSUME），不是本計畫設計的元件；M1 s3、s4 再以完整模型確認。
輸入：design/m3_layout/s1_core/out/layout_info.json、delivery/interfaces/chip_info.json、
      design/m2_circuit/s3_sim/out/sim_results.json（校正後 margin）、design/m2_circuit/s1_spec/out/tolerance.json（輸入相位容許）。
輸出：design/paper/m1_timing/s1_budget/out/budget.json。
執行：.\lab design\paper\m1_timing\s1_budget\budget.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402
from common.synth import deltas                                      # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/paper/m1_timing（共用模型 model.py）
from model import b7, load_phases                                    # noqa: E402

STEP = "paper/m1_timing/s1_budget"
C0 = 299792458.0                                                     # m/s

# 介面假設（數值為常見典型值；接收端與發射端不是本計畫設計的元件）
ASSUME = dict(
    bit_rate_gbps=10.0,
    lambda_um=1.55,
    ng_si=4.28,               # 0.45 µm × 220 nm 條狀矽波導的群折射率（模態模擬典型值）
    dneff_dT_si=1.8e-4,       # 矽波導有效折射率的溫度係數 1/K
    ng_fiber=1.468,           # 單模光纖群折射率
    dn_dT_fiber=1.0e-5,       # 石英 dn/dT 1/K
    alpha_fiber=5.5e-7,       # 石英熱膨脹係數 1/K
    v_coax_c=0.7,             # RF 同軸線的速度（光速的倍數）
    t_tx_ui=0.3,              # 發射端 10–90% 轉態時間（UI 的倍數）；指「光場振幅」的 10–90%（M1 s4 的波形同此定義）
    rx_bw_ghz=7.0,            # 接收端頻寬（0.7 × 位元率）
    setup_ps=10.0, hold_ps=5.0, jitter_ps=8.0,   # 取樣需要的時間：setup＋hold＋時脈抖動
    resp_a_w=0.5,             # 光偵測器響應度
    tia_noise_pa_rthz=20.0,   # TIA 輸入雜訊電流密度
    q=7.0,                    # 判讀要求：訊號 ≥ Q × 雜訊（約 1e-12 錯誤率）
    tia_ohm=1000.0,           # TIA 轉阻（比較器雜訊與偏移換算到輸入電流用）
    comp_noise_mv=0.5,        # 比較器雜訊（rms）
    comp_offset_mv=0.3,       # 比較器殘餘偏移
    rin_db_hz=-140.0,         # 雷射相對強度雜訊（共同光源：各路完全相關）
    pd_mismatch=0.02,         # 兩個偵測器響應度不匹配（共模 RIN 漏進差動訊號）
    # 平衡偵測：兩個偵測器的電流相減後進同一個 TIA（若兩個 TIA 再相減，熱雜訊 ×√2，需求約多 1.5 dB）。
    # 雷射相位雜訊：5 路來自同一顆雷射，路徑差（晶片內 µm 級、光纖 cm 級）遠小於 DFB 雷射的同調長度（約百公尺級），忽略。
    ec_loss_db=2.0,           # 每個 EC 的耦合損耗（待量測，假設值）
)


def load(rel):
    return json.loads((paths.ROOT / rel).read_text(encoding="utf-8"))


def timing(L, C, A):
    """逐欄傳遞每條軌上「各來源的最早／最晚路程」；MZI 的兩個輸出都混有兩個輸入的所有來源。"""
    g = L["geometry"]
    ex, lmzi, lead = g["rail_vs_bypass_extra_um"], g["mzi_length_um"], g["lead_um"]
    ps_per_um = A["ng_si"] / C0 * 1e6                                # s/m → ps/µm（1e12 ps/s × 1e-6 m/µm）
    src = {p["waveguide"]: p["signal"] for p in L["ports"] if p["port"].startswith("in")}
    rail = {r: {s: (C["fan_in_len_um"][f"in{r - 1}"] + lead,) * 2} for r, s in src.items()}
    per_mzi = []
    for col in range(1, g["columns"] + 1):
        new, used = {}, set()
        for p in sorted((p for p in L["placement"] if p["layer"] == col), key=lambda p: p["mzi"]):
            a, b = p["waveguides"]
            used |= {a, b}
            ins = dict(rail[a])
            for k, v in rail[b].items():
                ins[k] = (min(v[0], ins[k][0]), max(v[1], ins[k][1])) if k in ins else v
            lo, hi = min(v[0] for v in ins.values()), max(v[1] for v in ins.values())
            per_mzi.append(dict(mzi=p["mzi"], column=col, rails=[a, b], sources=sorted(ins),
                                dL_um=round(hi - lo, 3), skew_ps=round((hi - lo) * ps_per_um, 4)))
            out = {k: (v[0] + lmzi + ex, v[1] + lmzi + ex) for k, v in ins.items()}
            new[a], new[b] = out, dict(out)
        for r in rail:
            if r not in used:
                new[r] = {k: (v[0] + lmzi, v[1] + lmzi) for k, v in rail[r].items()}
        rail = new
    outs = []
    for r in sorted(rail):
        fo = C["fan_out_len_um"][f"out{r - 1}"] + lead
        lo, hi = min(v[0] for v in rail[r].values()) + fo, max(v[1] for v in rail[r].values()) + fo
        outs.append(dict(output=f"o{r}", path_um=[round(lo, 2), round(hi, 2)],
                         delay_ps=[round(lo * ps_per_um, 3), round(hi * ps_per_um, 3)], skew_ps=round((hi - lo) * ps_per_um, 4)))
    latest = {o["output"]: o["path_um"][1] for o in outs}
    rd = [o for o in outs if o["output"] in ("o2", "o4")]                 # 判讀用的兩個輸出：所有來源、所有路徑
    rd_lo, rd_hi = min(o["path_um"][0] for o in rd), max(o["path_um"][1] for o in rd)
    ui = 1e3 / A["bit_rate_gbps"]
    t_tx = A["t_tx_ui"] * ui
    t_rx = 0.35 / A["rx_bw_ghz"] * 1e3                               # 一階頻寬限制的 10–90% 轉態時間
    t_e = math.hypot(t_tx, t_rx)
    t_req = A["setup_ps"] + A["hold_ps"] + A["jitter_ps"]
    allow = ui - t_e - t_req
    worst = max(per_mzi, key=lambda m: m["skew_ps"])
    off = [dict(item="光纖長度差 1 mm", skew_ps=round(1e-3 * A["ng_fiber"] / C0 * 1e12, 2)),
           dict(item="光纖長度差 1 cm", skew_ps=round(1e-2 * A["ng_fiber"] / C0 * 1e12, 1)),
           dict(item="RF 同軸線長度差 1 cm", skew_ps=round(1e-2 / (A["v_coax_c"] * C0) * 1e12, 1))]
    return dict(ps_per_um=round(ps_per_um, 5), column_extra_um=ex, column_extra_ps=round(ex * ps_per_um, 4),
                per_mzi=per_mzi, outputs=outs, worst_mzi=worst["mzi"], worst_skew_ps=worst["skew_ps"],
                o2_vs_o4_latest_ps=round((latest["o2"] - latest["o4"]) * ps_per_um, 4),
                readout=dict(o2_um=next(o["path_um"] for o in rd if o["output"] == "o2"),
                             o4_um=next(o["path_um"] for o in rd if o["output"] == "o4"),
                             spread_um=round(rd_hi - rd_lo, 2), spread_ps=round((rd_hi - rd_lo) * ps_per_um, 4)),
                outputs_spread_ps=round((max(o["path_um"][1] for o in outs) - min(o["path_um"][0] for o in outs)) * ps_per_um, 3),
                ui_ps=ui, t_tx_ps=t_tx, t_rx_ps=round(t_rx, 2), t_edge_ps=round(t_e, 2), t_req_ps=t_req,
                skew_allow_ps=round(allow, 2), worst_fraction_of_allow=round(worst["skew_ps"] / allow, 4), offchip=off)


def worst_patterns():
    """每個函數：margin 最差的那組輸入（含 MMI 損耗的 B7、重新校正的相位）的 m＝s·ΔP 與兩個偵測器的功率和 P2＋P4（以 P_u 為單位）。"""
    ph = load_phases()
    bits = np.array(list(itertools.product([0, 1], repeat=4)))
    V = np.hstack([bits.astype(complex), np.full((16, 1), R_AMP + 0j)])
    tgt = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
    out = {}
    for fn, f in ph["functions"].items():
        idx = [int(u[1]) - 1 for u in f["uses"]]
        sg = np.array([1 if tgt[fn](b[idx]) else -1 for b in bits])
        P = np.abs(V @ b7(np.array(f["theta"]), np.array(f["phi"])).T) ** 2
        m = sg * (P[:, READ[0]] - P[:, READ[1]])
        k = int(np.argmin(m))
        out[fn] = dict(m=float(m[k]), S=float(P[k, READ[0]] + P[k, READ[1]]), S_max=float(np.max(P[:, READ[0]] + P[:, READ[1]])))
    return out


def noise_terms(pu_pd, m, S, A, enbw):
    """在偵測器端每路 P_u＝pu_pd（W）時，判讀電流與各項雜訊（A）。
    熱雜訊（TIA）、比較器雜訊（換算到 TIA 輸入）、shot（兩個偵測器）、RIN（共同光源：差動項完全相關、共模項經偵測器不匹配漏進來）。"""
    r = A["resp_a_w"]
    sig = r * m * pu_pd                                              # 判讀電流（最差那組）
    th = A["tia_noise_pa_rthz"] * 1e-12 * math.sqrt(enbw)
    comp = A["comp_noise_mv"] * 1e-3 / A["tia_ohm"]
    shot = math.sqrt(2 * 1.602e-19 * r * S * pu_pd * enbw)
    rin = math.sqrt(10 ** (A["rin_db_hz"] / 10) * enbw)
    rin_diff = rin * sig                                             # 與判讀量成正比：提高功率也不會變小
    rin_cm = rin * A["pd_mismatch"] / 2 * r * S * pu_pd
    off = A["comp_offset_mv"] * 1e-3 / A["tia_ohm"]
    return dict(sig=sig, th=th, comp=comp, shot=shot, rin_diff=rin_diff, rin_cm=rin_cm, off=off)


def power(S, C, A):
    """反推 B7 輸入端需要的 P_u：最差那組輸入要滿足 判讀電流 − 偏移 ≥ Q × 總雜訊（各項以平方和合成）。
    雜訊頻寬用等效雜訊頻寬（二階 Butterworth＝1.11 × −3 dB 頻寬），不是直接用 −3 dB 頻寬。"""
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    wp = worst_patterns()
    prop = max(max(e["prop_db"]) for e in C["loss_estimate"] if e["rail"] in (2, 4))  # 判讀軌的傳播損耗（上限，全部算在輸出側）
    eta = 10 ** (-(prop + A["ec_loss_db"]) / 10)

    def ok(pu_pd, w):
        n = noise_terms(pu_pd, w["m"], w["S"], A, enbw)
        tot = math.sqrt(n["th"] ** 2 + n["comp"] ** 2 + n["shot"] ** 2 + n["rin_diff"] ** 2 + n["rin_cm"] ** 2)
        return n["sig"] - n["off"] - A["q"] * tot

    req = {}
    for fn, w in wp.items():
        lo, hi = 1e-7, 1e-1
        for _ in range(200):                                          # 二分法求最小的 P_u（偵測器端）
            mid = math.sqrt(lo * hi)
            lo, hi = (lo, mid) if ok(mid, w) > 0 else (mid, hi)
        req[fn] = hi
    fn = max(req, key=req.get)
    pu_pd = req[fn]
    w = wp[fn]
    n = noise_terms(pu_pd, w["m"], w["S"], A, enbw)
    var = {k: n[k] ** 2 for k in ("th", "comp", "shot", "rin_diff", "rin_cm")}
    tot = math.sqrt(sum(var.values()))
    dbm = lambda x: 10 * math.log10(x * 1e3)                          # noqa: E731
    pu_core = dbm(pu_pd / eta)
    pu_fiber = pu_core + A["ec_loss_db"]
    r_fiber = pu_fiber + 10 * math.log10(9)
    total = pu_fiber + 10 * math.log10(4 + 9)
    # 只有熱雜訊、用 −3 dB 頻寬時（舊算法）的需求，供對照
    th_old = A["tia_noise_pa_rthz"] * 1e-12 * math.sqrt(A["rx_bw_ghz"] * 1e9)
    pu_old = dbm(A["q"] * th_old / A["resp_a_w"] / w["m"] / eta)
    dp_pd = (A["q"] * tot + n["off"]) / A["resp_a_w"]
    steps = [("偵測器需要的 ΔP", dbm(dp_pd)), ("÷ margin → P_u（偵測器端）", dbm(pu_pd)),
             ("＋傳播損耗", dbm(pu_pd) + prop), ("＋輸出 EC → P_u（B7 輸入端）", pu_core),
             ("＋輸入 EC → 每根資料光纖", pu_fiber), ("參考光纖（9 P_u）", r_fiber), ("5 根合計（13 P_u）", total)]
    return dict(margin_min=round(w["m"], 4), margin_function=fn, worst_S=round(w["S"], 3), enbw_ghz=round(enbw / 1e9, 3),
                noise_ua=round(tot * 1e6, 3), offset_ua=round(n["off"] * 1e6, 3),
                noise_share={k: round(v / tot ** 2, 4) for k, v in var.items()}, thermal_share=round((var["th"] + var["comp"]) / tot ** 2, 4),
                pu_core_per_function_dbm={k: round(dbm(v / eta), 2) for k, v in req.items()},
                pu_core_old_dbm=round(pu_old, 2), dp_pd_dbm=round(dbm(dp_pd), 2),
                prop_db=prop, ec_loss_db=A["ec_loss_db"], pu_core_dbm=round(pu_core, 2), pu_fiber_dbm=round(pu_fiber, 2),
                r_fiber_dbm=round(r_fiber, 2), total_dbm=round(total, 2), steps=[[k, round(v, 2)] for k, v in steps])

def phase_ratio(delta):
    """各函數在每路相位偏差 ≤ delta（各路 −δ、0、＋δ 的最差組合）時，margin 剩下的比例（含 MMI 損耗的 B7）。"""
    ph = load_phases()
    bits = np.array(list(itertools.product([0, 1], repeat=4)))
    V = np.hstack([bits.astype(complex), np.full((16, 1), R_AMP + 0j)])
    tgt = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
    out = {}
    for fn, f in ph["functions"].items():
        idx = [int(u[1]) - 1 for u in f["uses"]]
        sg = np.array([1 if tgt[fn](b[idx]) else -1 for b in bits])
        U = b7(np.array(f["theta"]), np.array(f["phi"]))
        m0 = float(np.min(sg * deltas(U, V, READ)))
        cols = idx if len(idx) < 4 else [0, 1, 2, 3]
        worst = np.inf
        for c in itertools.product([-1, 0, 1], repeat=len(cols)):
            dv = np.zeros(4)
            dv[cols] = delta * np.array(c)
            worst = min(worst, float(np.min(sg * deltas(U @ np.diag(np.exp(1j * np.append(dv, 0.0))), V, READ))))
        out[fn] = round(worst / m0, 4)
    return out


def det_tolerance(keep=0.9, step=0.001):
    """確定性相對相位偏差的容許值：每路用到的輸入各偏 −δ、0 或 ＋δ（以 R 為基準，取所有組合中最差），
    margin 仍 ≥ keep × 無偏差時的 margin 的最大 δ。模型：含 MMI 損耗的 B7 與重新校正的相位（model.py）。
    與課程 M2 s1 的 σ（隨機誤差的標準差，看通過率）不同，這裡是固定的偏差，用來當漂移的預算。"""
    ph = load_phases()
    bits = np.array(list(itertools.product([0, 1], repeat=4)))
    V = np.hstack([bits.astype(complex), np.full((16, 1), R_AMP + 0j)])
    tgt = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
    out = {}
    for fn, f in ph["functions"].items():
        idx = [int(u[1]) - 1 for u in f["uses"]]
        sg = np.array([1 if tgt[fn](b[idx]) else -1 for b in bits])
        U = b7(np.array(f["theta"]), np.array(f["phi"]))
        m0 = float(np.min(sg * deltas(U, V, READ)))
        cols = idx if len(idx) < 4 else [0, 1, 2, 3]
        dirs = [np.array(c) for c in itertools.product([-1, 0, 1], repeat=len(cols)) if any(c)]
        d = 0.0
        while d < 1.0:
            d += step
            worst = np.inf
            for v in dirs:
                dv = np.zeros(4)
                dv[cols] = d * v
                worst = min(worst, float(np.min(sg * deltas(U @ np.diag(np.exp(1j * np.append(dv, 0.0))), V, READ))))
            if worst < keep * m0:
                break
        out[fn] = round(d - step, 3)
    return out


def phase(T, Tm, A):
    lam = A["lambda_um"] * 1e-6
    sigma = float(T["input_phase_sigma_ok"])                       # 課程 M2 s1：隨機誤差的標準差
    det = det_tolerance()
    sig = min(det.values())                                          # 確定性偏差的預算（margin 保留 90%）
    k_si = 2 * math.pi / lam * A["dneff_dT_si"]                                       # rad/(m·K)
    k_f = 2 * math.pi / lam * (A["dn_dT_fiber"] + A["ng_fiber"] * A["alpha_fiber"])  # rad/(m·K)，以群折射率近似 n
    dL_chip = Tm["per_mzi"][[m["mzi"] for m in Tm["per_mzi"]].index(Tm["worst_mzi"])]["dL_um"] * 1e-6

    def dlam(n, L):                                                                   # 雷射波長容許（pm）
        return sig / (2 * math.pi * n * L / lam ** 2) * 1e12

    cases = [dict(case=f"晶片內 {Tm['worst_mzi']} 兩條輸入路徑差", medium="矽波導", L_m=dL_chip, kind="長度差，同溫"),
             dict(case="兩根光纖長度差 1 cm", medium="光纖", L_m=1e-2, kind="長度差，同溫"),
             dict(case="兩根 1 m 光纖溫度不同", medium="光纖", L_m=1.0, kind="整段溫差")]
    for c in cases:
        k = k_si if c["medium"] == "矽波導" else k_f
        ng = A["ng_si"] if c["medium"] == "矽波導" else A["ng_fiber"]
        c["rad_per_K"] = round(k * c["L_m"], 5)
        c["dT_allow_K"] = float(f"{sig / (k * c['L_m']):.3g}")
        c["dlambda_allow_pm"] = None if c["kind"] == "整段溫差" else float(f"{dlam(ng, c['L_m']):.3g}")
    ratio = phase_ratio(sig)                                         # 相位誤差用滿 δ_det 時各函數的 margin 比例（給總預算）
    return dict(sigma_random_rad=sigma, det_rad=sig, det_per_function=det, det_function=min(det, key=det.get), det_keep=0.9,
                det_loss_db={k: round(-10 * math.log10(v), 3) for k, v in ratio.items()},
                k_si_rad_mK=round(k_si, 1), k_fiber_rad_mK=round(k_f, 2), cases=cases)


def main():
    A = ASSUME
    L = load("design/m3_layout/s1_core/out/layout_info.json")
    C = load("delivery/interfaces/chip_info.json")
    T = load("design/m2_circuit/s1_spec/out/tolerance.json")
    tm = timing(L, C, A)
    pw = power(None, C, A)
    ph = phase(T, tm, A)
    fiber = ph["cases"][2]
    verdict = [dict(item="時序", need=f"skew ≤ {tm['skew_allow_ps']} ps", have=f"晶片內最差 {tm['worst_skew_ps']} ps", ok=tm["worst_fraction_of_allow"] < 0.1),
               dict(item="功率", need=f"每根資料光纖 ≥ {pw['pu_fiber_dbm']} dBm", have=f"5 根合計 {pw['total_dbm']} dBm（一般雷射＋光放大器可達）", ok=pw["total_dbm"] < 13),
               dict(item="相位", need=f"相對相位偏差 ≤ {ph['det_rad']} rad", have=f"1 m 光纖溫差需 ≤ {fiber['dT_allow_K'] * 1e3:.2g} mK", ok=fiber["dT_allow_K"] > 0.1)]
    res = dict(assume=A, timing=tm, power=pw, phase=ph, verdict=verdict,
               checks=dict(o2_o4_latest_equal=abs(tm["o2_vs_o4_latest_ps"]) < 1e-6, n_mzi=len(tm["per_mzi"]) == 7,
                           timing_ok=verdict[0]["ok"], power_ok=verdict[1]["ok"], phase_is_gap=not verdict[2]["ok"]))
    out = paths.OUT(STEP, "budget.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"時序：每欄 MZI 多 {tm['column_extra_um']} µm＝{tm['column_extra_ps']} ps；最差 {tm['worst_mzi']} {tm['worst_skew_ps']} ps；"
          f"一階允許 {tm['skew_allow_ps']} ps（占 {tm['worst_fraction_of_allow']:.1%}）；o2、o4 所有路徑 {tm['readout']['o2_um']}、{tm['readout']['o4_um']} µm，範圍 {tm['readout']['spread_ps']} ps")
    print(f"相位預算：確定性偏差容許 {ph['det_per_function']} → {ph['det_rad']} rad（{ph['det_function']}）；隨機 σ {ph['sigma_random_rad']} rad")
    print(f"功率：margin {pw['margin_min']}（{pw['margin_function']}）；等效雜訊頻寬 {pw['enbw_ghz']} GHz；雜訊 {pw['noise_ua']} µA（熱＋比較器占 {pw['thermal_share']:.0%}）；"
          f"P_u（B7 輸入）≥ {pw['pu_core_dbm']} dBm（舊算法 {pw['pu_core_old_dbm']}）；"
          f"資料光纖 ≥ {pw['pu_fiber_dbm']}、參考 {pw['r_fiber_dbm']}、合計 {pw['total_dbm']} dBm")
    for c in ph["cases"]:
        print(f"相位：{c['case']}：{c['rad_per_K']} rad/K → 溫度容許 {c['dT_allow_K']} K；波長容許 {c['dlambda_allow_pm']} pm")
    print("檢查：", res["checks"])
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
