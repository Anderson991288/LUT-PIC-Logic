r"""LUT4 v2 s9（輸入 E+／E−）：系統層級分析——晶片走線損耗、TIA 三路同時偏差、波長與溫度、二相位誤差、光功率預算。

相位固定為交接值（LUT4 s1，每顆 MZI 0.9 dB 模型），每項只改一個因素，看 7 個範例函數的 16 組判讀與裕量：
  1. 晶片走線：輸入側 5 路等長，只造成共同縮放；輸出側 o1–o5 的扇出長度不同（LUT4 s5 的 chip_info），
     依傳播損耗 3、4 dB/cm 換成三個讀取埠的相對增益。同時列出統一模型（每顆 MMI 0.45 dB）的各軌損耗。
  2. TIA 增益：三路各自 N(1, σ²)，σ＝1、2、3、5、8%，各 2,000 次（種子 900），全對比例；另以三次類 0x0069（synth4 重新合成，60 個起點）做單路與三路比較。
  3. 波長與溫度：每顆 MZI 的軌比直通多 ΔL（LUT4 s4 由 GDS 量得），波長偏 Δλ 或溫度偏 ΔT 時，
     每顆 MZI 的兩個輸出多一個共同相位 δ（Δλ：2π·n_g·ΔL·Δλ/λ²；ΔT：2π·(dn/dT)·ΔL·ΔT/λ），找全對的範圍。
  4. 二相位誤差（v2）：位元 1 的光場為 −E·e^(iδ)。2026-11-07 起掃描正負兩方向、四路相同與四路各自的誤差，
     範例函數之外也算全部 65,536 張相位庫（s0_coverage 的 merged_phases.npz）。四路各自的誤差用 16 個正負組合加隨機組合。
     同時以較大樣本重算輸入相對相位誤差 σ（5 路各加常態誤差），供 S1 引用。相位都固定，每次只改這一項。
  5. 光功率預算（假設值，報告中列出）：PD 響應度 1 A/W；TIA 輸入雜訊電流密度 20 pA/√Hz；EC 每端 2 dB；
     判讀需要裕量 ≥ 7 倍差值雜訊（兩路相減，雜訊 √2 倍）；頻寬 1 MHz（靜態讀取）與 10 GHz。只算 TIA 雜訊（shot、RIN 未計）。
輸入：LUT4 s0 的 out/merged_phases.npz；LUT4 s1 的 out/phases.json、out/lut4_netlist.json；LUT4 s4 的 out/review_checks.json；LUT4 s5 的 out/chip_info.json。
輸出：out/system.json。
執行：.\lab design\lut4v2\s9_system\system.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import T, embed                                      # noqa: E402
from common.optics import H                                          # noqa: E402

STEP = "lut4v2/s9_system"
LAM, NG, DNDT = 1.55, 4.2, 1.8e-4
SIG_TIA = [0.01, 0.02, 0.03, 0.05, 0.08]
TRIALS = 2000
DLAM = np.round(np.arange(0, 2.0001, 0.01), 3)        # nm
DTEMP = np.round(np.arange(0, 40.0001, 0.1), 2)       # K
DPHI = [-30, -20, -15, -10, -5, -2, 2, 5, 10, 15, 20, 30]   # 位元 1 的相位誤差（度），正負兩方向
DPHI_STEP, DPHI_SCAN = 0.25, 60.0                   # 容許範圍的掃描間距與上限（度）
BOX_RANDOM = 256                                    # 四路各自的誤差：正負組合之外再抽的隨機組合數
SEED_PHASE = 904
SIG_INPUT = [0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05]    # 輸入相對相位誤差的標準差（rad）
TRIALS_INPUT, DRAWS_INPUT = 20000, 100              # 每個 σ：七個範例函數、全部相位庫的抽樣次數
CORNERS = np.array([[1 if c >> j & 1 else -1 for j in range(4)] for c in range(16)], float)
PD_R, I_N, EC_DB, K_SNR = 1.0, 20e-12, 2.0, 7.0
BW = {"1 MHz": 1e6, "10 GHz": 10e9}
MMI_DB = 0.45


LAYOUT_SRC = {}                                                      # 佈局輸入（s4、s5 的 out/）實際讀自哪裡


def _layout_json(step, name):
    """優先讀該步驟的 out/；佈局步驟尚未重跑時退回本資料夾 reference/ 的既有證據（system.json 會記錄來源）。"""
    p = paths.STEP(step) / "out" / name
    if p.exists():
        LAYOUT_SRC[name] = f"{step}/out（本次產物）"
        return json.loads(p.read_text(encoding="utf-8"))
    r = Path(__file__).resolve().parent / "reference" / name
    LAYOUT_SRC[name] = f"reference evidence（{step} 尚未重跑，讀 s9_system/reference/{name}）"
    return json.loads(r.read_text(encoding="utf-8"))


def load():
    ph = json.loads(paths.OUT("lut4v2/s1_handoff", "phases.json").read_text(encoding="utf-8"))
    net = json.loads(paths.OUT("lut4v2/s1_handoff", "lut4_netlist.json").read_text(encoding="utf-8"))
    rev = _layout_json("lut4v2/s4_review", "review_checks.json")
    chip = _layout_json("lut4v2/s5_chip", "chip_info.json")
    return ph, net, rev, chip


def U_of(ops, f, loss_db, delta=0.0):
    a = 10 ** (-loss_db / 20)
    U = np.eye(5, dtype=complex)
    for (r, _), th, p in zip(ops, f["theta"], f["phi"]):
        U = embed(a * np.exp(1j * delta) * T(th, p), r, 5) @ U
    return U


X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)


def V_of(dphi=0.0, R=3.0):
    """16 組輸入的光場（5×16）。dphi：四路共同的 π 誤差，或四路各自的誤差（長度 4），rad。"""
    V = np.zeros((16, 5), complex)
    V[:, :4] = np.where(X > 0, -np.exp(1j * np.asarray(dphi, float)), 1.0)
    V[:, 4] = R
    return V.T


def judge(U, ins, g=(1.0, 1.0, 1.0), dphi=0.0, R=3.0):
    """v2：位元 0＝+E、1＝−E·e^(iδ)（δ＝相位調變的 π 誤差，rad）；R＝+E。"""
    P = np.abs(V_of(dphi, R).T @ U.T) ** 2
    P2, P3, P4 = P[:, 1] * g[0], P[:, 2] * g[1], P[:, 3] * g[2]
    Da, Db = P2 - P4, P4 - P3
    y = (Da > 0) & (Db > 0)
    m = np.where(ins, np.minimum(Da, Db), np.maximum(-Da, -Db))
    return bool((y == ins).all()), float(m.min())


def bank_U(ops, phases, loss_db):
    """相位庫（N×14，欄序 θ1、φ1…）→ 每張真值表的 5×5 U；算法與 U_of 相同，一次算全部。"""
    n, a = len(phases), 10 ** (-loss_db / 20)

    def D(p):
        d = np.zeros((n, 2, 2), complex)
        d[:, 0, 0], d[:, 1, 1] = np.exp(1j * p), 1.0
        return d
    U = np.broadcast_to(np.eye(5, dtype=complex), (n, 5, 5)).copy()
    for k, (r, _) in enumerate(ops):
        U[:, r:r + 2] = a * (H @ D(phases[:, 2 * k]) @ H @ D(phases[:, 2 * k + 1])) @ U[:, r:r + 2]
    return U


def fails(U, ins, V):
    """判錯與否（布林）。U 可為一張（5×5，V 為多組抽樣）或全部相位庫（N×5×5，V 為一組光場）。"""
    P = np.abs(U @ V) ** 2
    Da, Db = P[:, 1] - P[:, 3], P[:, 3] - P[:, 2]
    return (np.where(ins, np.minimum(Da, Db), -np.minimum(Da, Db)) <= 0).any(1)


def common_range(ok):
    """四路誤差相同：由 0 往負、正方向掃描，回傳仍全對的範圍（度）。"""
    out = []
    for sign in (-1, 1):
        lim = 0.0
        for e in np.arange(DPHI_STEP, DPHI_SCAN + DPHI_STEP / 2, DPHI_STEP):
            if not ok(np.deg2rad(sign * e)):
                break
            lim = float(e)
        out.append(sign * lim + 0.0)
    return out


def box_limit(ok, rng):
    """四路誤差各自在 ±ε 內：找 16 個正負組合全對的最大 ε，再用隨機組合確認，有錯就縮小一格。"""
    lim = 0.0
    for e in np.arange(DPHI_STEP, DPHI_SCAN + DPHI_STEP / 2, DPHI_STEP):
        if not all(ok(np.deg2rad(e) * c) for c in CORNERS):
            break
        lim = float(e)
    while lim > 0 and not all(ok(np.deg2rad(d)) for d in rng.uniform(-lim, lim, (BOX_RANDOM, 4))):
        lim -= DPHI_STEP
    return lim


def phase_spec(ops, F, ins_of):
    """二相位誤差與輸入相對相位誤差：七個範例函數與全部相位庫。回傳 dphi_spec、input_phase。"""
    rng = np.random.default_rng(SEED_PHASE)
    U0 = {n: U_of(ops, f, 0.9) for n, f in F.items()}
    per = {}
    for n in F:
        ok = lambda d, n=n: judge(U0[n], ins_of[n], dphi=d)[0]
        per[n] = dict(common_deg=common_range(ok), independent_deg=box_limit(ok, rng))
    lib = np.load(paths.OUT("lut4v2/s0_coverage", "merged_phases.npz"))
    masks, PL = lib["masks"], lib["phases"]
    assert np.array_equal(np.sort(masks), np.arange(1 << 16)) and PL.shape == (1 << 16, 14) and np.isfinite(PL).all()
    assert abs(float(lib["R"]) - 3.0) < 1e-12 and abs(float(lib["loss_db"]) - 0.9) < 1e-12
    UL = bank_U(ops, PL, 0.9)
    f0 = F["XOR4"]
    p0 = np.array([x for tp in zip(f0["theta"], f0["phi"]) for x in tp])[None]
    assert np.allclose(bank_U(ops, p0, 0.9)[0], U0["XOR4"]), "bank_U 與 U_of 不一致"
    insL = (masks[:, None] >> np.arange(16)) & 1 == 1
    assert not fails(UL, insL, V_of()).any(), "相位庫標稱值就有判錯"
    okL = lambda d: not fails(UL, insL, V_of(d)).any()
    fail_ind = {}
    for e in (2, 5, 10):
        bad = np.zeros(len(masks), bool)
        for c in CORNERS:
            bad |= fails(UL, insL, V_of(np.deg2rad(e) * c))
        fail_ind[str(e)] = int(bad.sum())
    dphi_spec = dict(
        model="位元 1 的光場為 −E·e^(iδ)，相位固定，其他條件標稱；只判對錯，未計其他誤差同時發生",
        step_deg=DPHI_STEP, scan_max_deg=DPHI_SCAN, independent_method=f"16 個正負組合加 {BOX_RANDOM} 個隨機組合（種子 {SEED_PHASE}）",
        examples=dict(common_deg=[max(v["common_deg"][0] for v in per.values()), min(v["common_deg"][1] for v in per.values())],
                      independent_deg=min(v["independent_deg"] for v in per.values()), per_function=per),
        library=dict(n_tables=len(masks), common_deg=common_range(okL), independent_deg=box_limit(okL, rng),
                     fail_common={str(e): int(fails(UL, insL, V_of(np.deg2rad(e))).sum()) for e in DPHI}, fail_independent=fail_ind))
    V0, ex, lb = V_of(), {}, {}
    for s in SIG_INPUT:
        E = np.exp(1j * rng.normal(0, s, (TRIALS_INPUT, 5)))[:, :, None] * V0[None]
        ex[str(s)] = {n: round(1 - float(fails(U0[n], ins_of[n], E).mean()), 5) for n in F}
        bad = np.zeros(len(masks), int)
        for e in rng.normal(0, s, (DRAWS_INPUT, 5)):
            bad += fails(UL, insL, V0 * np.exp(1j * e)[:, None])
        lb[str(s)] = dict(tables_all_pass=int((bad == 0).sum()), worst_table_pass=round(1 - int(bad.max()) / DRAWS_INPUT, 3),
                          mean_pass=round(1 - float(bad.mean()) / DRAWS_INPUT, 6))
    input_phase = dict(model="5 路各加 N(0, σ²) 相位誤差，相位固定", seed=SEED_PHASE, trials_examples=TRIALS_INPUT, draws_library=DRAWS_INPUT,
                       examples=ex, library=lb,
                       examples_sigma_ok=max([s for s in SIG_INPUT if all(v == 1.0 for v in ex[str(s)].values())], default=0.0),
                       library_sigma_ok=max([s for s in SIG_INPUT if lb[str(s)]["tables_all_pass"] == len(masks)], default=0.0))
    return dphi_spec, input_phase


def main():
    ph, net, rev, chip = load()
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    F = ph["functions"]
    ins_of = {n: np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool) for n, f in F.items()}
    base = {n: judge(U_of(ops, f, 0.9), ins_of[n])[1] for n, f in F.items()}
    res = dict(base_margin=base, layout_inputs=dict(LAYOUT_SRC))

    # 1. 晶片走線
    fo = chip["fan_out_len_um"]                                       # out0..out4
    L = np.array([fo[f"out{k}"] for k in range(5)])
    route = {}
    for a_db in (3.0, 4.0):
        loss = a_db * (L - L.min()) * 1e-4                            # dB，相對最短
        g = 10 ** (-loss / 10)
        gg = (g[1], g[2], g[3])                                       # o2、o3、o4
        r = {n: judge(U_of(ops, f, 0.9), ins_of[n], gg) for n, f in F.items()}
        route[f"{a_db:g} dB/cm"] = dict(rel_loss_db={f"o{k + 1}": round(float(loss[k]), 4) for k in range(5)},
                                       all_pass=all(v[0] for v in r.values()), margin={n: round(v[1], 4) for n, v in r.items()})
    per_rail = rev["mzi_per_rail"]
    rails = []
    for x in chip["loss_estimate"]:
        k = x["rail"] - 1
        rails.append(dict(rail=x["rail"], length_um=x["length_um"], n_mzi=per_rail[k], prop_db=x["prop_db"],
                          mmi_db=round(2 * per_rail[k] * MMI_DB, 2),
                          total_db=[round(x["prop_db"][0] + 2 * per_rail[k] * MMI_DB, 2), round(x["prop_db"][1] + 2 * per_rail[k] * MMI_DB, 2)]))
    res["route"] = route
    res["rails_unified"] = rails

    # 2. TIA 三路同時偏差
    tia = {}
    for s in SIG_TIA:
        rng = np.random.default_rng(900)
        G = rng.normal(1.0, s, (TRIALS, 3))
        tia[str(s)] = {n: round(float(np.mean([judge(U_of(ops, f, 0.9), ins_of[n], tuple(g))[0] for g in G])), 4) for n, f in F.items()}
    res["tia_mc"] = tia
    s_ok = max([s for s in SIG_TIA if all(v >= 0.999 for v in tia[str(s)].values())], default=0.0)
    res["tia_sigma_ok"] = s_ok

    # 2b. 較難的函數：三次類 0x0069（單一門檻做不到）重新合成，看單路容許量與三路同時偏差
    sys.path.insert(0, str(paths.DESIGN / "lut4v2"))
    import synth4 as S4
    hard = {}
    for hx in (0x0069,):
        m, pv = S4.synth_nb(hx, S4.Arch.from_code("3142132", loss_db=0.9, order=(1, 3, 2)), 60, 7)
        fh = dict(theta=list(pv[0::2]), phi=list(pv[1::2]))
        ins = np.array([hx >> x & 1 for x in range(16)], bool)
        Uh = U_of(ops, fh, 0.9)
        single = {}
        for i, ch in enumerate(("o2", "o3", "o4")):
            lim = []
            for sg in (1, -1):
                g = 0.0
                while g < 0.6:
                    gg = [1.0, 1.0, 1.0]; gg[i] = 1 + sg * (g + 0.001)
                    if not judge(Uh, ins, tuple(gg))[0]:
                        break
                    g += 0.001
                lim.append(round(g, 3))
            single[ch] = min(lim)
        mc = {}
        for sgm in SIG_TIA:
            rng = np.random.default_rng(900)
            G = rng.normal(1.0, sgm, (TRIALS, 3))
            mc[str(sgm)] = round(float(np.mean([judge(Uh, ins, tuple(g))[0] for g in G])), 4)
        hard[f"0x{hx:04X}"] = dict(margin=round(float(m), 4), single=single, mc=mc)
    res["tia_hard"] = hard

    # 3. 波長與溫度
    dL = rev["mzi_extra_gds_um"]
    k_lam = 2 * np.pi * NG * dL / LAM ** 2 * 1e-3                      # rad/nm
    k_T = 2 * np.pi * DNDT * dL / LAM                                 # rad/K
    def tol(scan, k):
        out = {}
        for n, f in F.items():
            lim = 0.0
            for d in scan:
                if not (judge(U_of(ops, f, 0.9, k * d), ins_of[n])[0] and judge(U_of(ops, f, 0.9, -k * d), ins_of[n])[0]):
                    break
                lim = float(d)
            out[n] = lim
        return out
    res["k_lambda_rad_per_nm"], res["k_T_rad_per_K"] = round(float(k_lam), 4), round(float(k_T), 5)
    res["dlambda_tol_nm"] = tol(DLAM, k_lam)
    res["dT_tol_K"] = tol(DTEMP, k_T)

    # 4. 二相位誤差（2026-11-07：dphi_max_deg 只看正方向與七個範例，已由 dphi_spec 取代）
    res["dphi"] = {str(e): {n: dict(zip(("pass", "margin"), judge(U_of(ops, f, 0.9), ins_of[n], dphi=np.deg2rad(e)))) for n, f in F.items()} for e in DPHI}
    res["dphi_spec"], res["input_phase"] = phase_spec(ops, F, ins_of)

    # 5. 光功率預算（只算 TIA 雜訊）
    out_loss = EC_DB + max(route["4 dB/cm"]["rel_loss_db"].values()) + 4.0 * L.min() * 1e-4
    in_loss = EC_DB + 4.0 * chip["fan_in_len_um"]["in0"] * 1e-4
    budget = {}
    for lab, B in BW.items():
        sig_I = I_N * np.sqrt(B) * np.sqrt(2)
        row = {}
        for n in ("XOR4", "AND2"):
            m = base[n]
            Pu = K_SNR * sig_I / (PD_R * m * 10 ** (-out_loss / 10))     # W，在 macro 輸入端
            fiber_data = Pu * 10 ** (in_loss / 10)
            row[n] = dict(margin=round(m, 4), Pu_uW=round(Pu * 1e6, 3), per_data_fiber_dBm=round(10 * np.log10(fiber_data * 1e3), 2),
                          R_fiber_dBm=round(10 * np.log10(9 * fiber_data * 1e3), 2),
                          total_mW=round((4 + 9) * fiber_data * 1e3, 4))
        budget[lab] = row
    res["budget"] = dict(assumptions=dict(PD_A_per_W=PD_R, TIA_pA_rtHz=I_N * 1e12, EC_dB_each=EC_DB, k_snr=K_SNR,
                                          in_loss_db=round(in_loss, 2), out_loss_db=round(out_loss, 2), noise="只計 TIA；shot、RIN、比較器偏移未計"),
                         cases=budget)
    paths.OUT(STEP, "system.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("走線", {k: (v["all_pass"], v["margin"]["XOR4"], v["rel_loss_db"]) for k, v in route.items()})
    print("TIA MC", tia, "→ σ", s_ok)
    print("Δλ", res["dlambda_tol_nm"], "ΔT", res["dT_tol_K"], res["k_lambda_rad_per_nm"], res["k_T_rad_per_K"])
    ds, ip = res["dphi_spec"], res["input_phase"]
    print("相位誤差（度）範例", ds["examples"]["common_deg"], ds["examples"]["independent_deg"], "全表", ds["library"]["common_deg"], ds["library"]["independent_deg"], ds["library"]["fail_common"], ds["library"]["fail_independent"])
    print("輸入相位 σ", ip["examples_sigma_ok"], ip["library_sigma_ok"], ip["library"])
    print("預算", json.dumps(res["budget"], ensure_ascii=False))
    print("各軌", rails)


if __name__ == "__main__":
    main()
