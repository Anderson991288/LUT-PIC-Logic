r"""論文 M3 s1：參數對齊與護欄差異——草稿的設定和我們目前的設定差在哪？XOR2 的雜訊護欄為何看起來差約 2 倍？

用途：
  1. 參數對照：草稿表 II、II-A（draft.py）逐項對照論文 M1 的設定（budget.json、window.json、model.py），標「相同／不同」與後續處理的步驟。
  2. 護欄：在同一個參考面（偵測器端每路 P_u＝−7 dBm，草稿的定義）用 M1 s1 的雜訊模型算各函數的護欄
     Γ＝|V_off|＋qσ（以 P_u 為單位），和草稿表 I 比較。另算「草稿式」護欄（不含 shot；RIN 以 c(|D|＋εP_sum) 線性計入），
     分別取 margin 最差那組輸入與輸出功率最大那組輸入。
  3. 參考面：M1 s1 的 XOR2 需求 −6.74 dBm 是「B7 輸入端」，比偵測器端多了輸出側的傳播損耗與 EC 損耗；
     換回偵測器端後，該功率下的護欄剛好等於 margin。
  4. margin：我們（每顆 MMI 0.33 dB）與草稿表 I（無損、每顆 MZI 0.9 dB）並列；以草稿損耗重新合成留給 M3 s2。
輸入：design/paper/m1_timing/s1_budget/out/budget.json、s4_window/out/window.json、design/paper/m1_timing/out/phases_lossy.json、
      design/paper/m3_align/draft.py。
輸出：design/paper/m3_align/s1_params/out/align.json。
執行：.\lab design\paper\m3_align\s1_params\align.py（約 2 秒）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_timing"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_timing" / "s1_budget"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import budget as B                                                   # noqa: E402
import draft as D                                                    # noqa: E402
import model as M                                                    # noqa: E402
import paths                                                         # noqa: E402

STEP = "paper/m3_align/s1_params"
TGT = {"AND2": np.all, "OR2": np.any, "XOR2": lambda b: np.sum(b) % 2 == 1, "AND4": np.all, "OR4": np.any}
TOL_GUARD = 0.02                                                     # 同參考面時護欄可接受的差（P_u）


def dbm(w):
    return 10 * math.log10(w * 1e3)


def patterns(f):
    """各輸入組合的帶號判讀量 m＝s·(P2−P4) 與兩個判讀埠的功率和（P_u）。"""
    bits = np.array(list(itertools.product([0, 1], repeat=4)))
    V = np.hstack([bits.astype(complex), np.full((16, 1), M.R_AMP + 0j)])
    idx = [int(u[1]) - 1 for u in f["uses"]]
    return bits, V, idx


def guards(fn, f, A, enbw, pu_w):
    bits, V, idx = patterns(f)
    sg = np.array([1 if TGT[fn](b[idx]) else -1 for b in bits])
    P = np.abs(V @ M.b7(np.array(f["theta"]), np.array(f["phi"])).T) ** 2
    d = P[:, M.READ[0]] - P[:, M.READ[1]]
    m = sg * d
    s = P[:, M.READ[0]] + P[:, M.READ[1]]
    k_w, k_s = int(np.argmin(m)), int(np.argmax(s))
    r = A["resp_a_w"]
    unit = r * pu_w                                                  # 1 P_u 對應的偵測電流

    def ours(k):
        n = B.noise_terms(pu_w, float(m[k]), float(s[k]), A, enbw)
        tot = math.sqrt(sum(n[x] ** 2 for x in ("th", "comp", "shot", "rin_diff", "rin_cm")))
        return (n["off"] + A["q"] * tot) / unit, {x: round(n[x] / unit, 4) for x in ("th", "comp", "shot", "rin_diff", "rin_cm", "off")}

    c = math.sqrt(10 ** (A["rin_db_hz"] / 10) * enbw)

    def draft_style(k):
        n = B.noise_terms(pu_w, float(m[k]), float(s[k]), A, enbw)
        rin = c * (abs(float(d[k])) + A["pd_mismatch"] * float(s[k]))           # 已是 P_u 單位
        sig = math.sqrt((n["th"] / unit) ** 2 + (n["comp"] / unit) ** 2 + rin ** 2)
        return n["off"] / unit + A["q"] * sig

    g_w, parts = ours(k_w)
    return dict(m=round(float(m[k_w]), 4), S_worst=round(float(s[k_w]), 3), S_max=round(float(s[k_s]), 3),
                guard_ours=round(g_w, 4), guard_ours_smax=round(ours(k_s)[0], 4), parts=parts,
                guard_draft_style=round(draft_style(k_w), 4), guard_draft_style_smax=round(draft_style(k_s), 4))


def guard_curve(f, fn, A, enbw, pdbm):
    out = []
    for p in pdbm:
        out.append(guards(fn, f, A, enbw, 10 ** (p / 10) * 1e-3)["guard_ours"])
    return out


def main():
    bud = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))
    win = json.loads(paths.OUT("paper/m1_timing/s4_window", "window.json").read_text(encoding="utf-8"))
    ph = M.load_phases()
    A = bud["assume"]
    S = D.SETTINGS
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    pu7 = 10 ** (S["pu_dbm"] / 10) * 1e-3

    # 1. 參數對照
    t_tx = win["t_tx_ps"]
    full_ours = t_tx / 0.5903
    rc1090_draft = S["edge_full_ps"] * 0.5903
    same = lambda a, b: "相同" if abs(a - b) < 1e-9 else "不同"           # noqa: E731
    rows = [
        ("接收端（響應度、TIA 雜訊、Z_T、頻寬、RIN、PD 失配、比較器雜訊與偏移、q）",
         "0.5 A/W、20 pA/√Hz、1 kΩ、7 GHz 二階 Butterworth、−140 dB/Hz、2%、0.5 mV、0.3 mV、7",
         f"{A['resp_a_w']} A/W、{A['tia_noise_pa_rthz']:g} pA/√Hz、{A['tia_ohm']/1e3:g} kΩ、{A['rx_bw_ghz']:g} GHz 二階 Butterworth、"
         f"{A['rin_db_hz']:g} dB/Hz、{A['pd_mismatch']:.0%}、{A['comp_noise_mv']} mV、{A['comp_offset_mv']} mV、{A['q']:g}",
         "相同" if all(abs(A[k] - S[k]) < 1e-9 for k in ("resp_a_w", "tia_noise_pa_rthz", "tia_ohm", "rx_bw_ghz", "rin_db_hz",
                                                          "pd_mismatch", "comp_noise_mv", "comp_offset_mv", "q")) else "不同", "—"),
        ("取樣需求 T_req（setup、hold、抖動）", "10＋5＋8＝23 ps",
         f"{A['setup_ps']:g}＋{A['hold_ps']:g}＋{A['jitter_ps']:g}＝{win['t_req_ps']:g} ps", same(win["t_req_ps"], S["t_req_ps"]), "—"),
        ("雜訊項", "熱、比較器、RIN（含 PD 失配）；未列 shot", "熱、比較器、shot、RIN（差動與共模）", "不同（多 shot）", "本步量化"),
        ("參考光", f"場振幅 {S['r_amp']:g}（9 P_u）", f"場振幅 {M.R_AMP:g}", same(M.R_AMP, S["r_amp"]), "—"),
        ("P_u 的參考面", "macro 輸入端＝偵測器端（輸出側無損耗），−7 dBm 固定",
         f"B7 輸入端，由預算反推；輸出側另有傳播 {bud['power']['prop_db']} dB＋EC {bud['power']['ec_loss_db']:g} dB", "不同", "本步；之後用草稿的定義"),
        ("元件損耗", "每顆 MZI 0.9 dB（模型值）", f"每顆 MMI {M.LOSS_DB} dB（每顆 MZI 約 {2 * M.LOSS_DB:.2f} dB）", "不同", "M3 s2 以 0.9 dB 重新合成"),
        ("輸入邊緣", f"升餘弦全寬 {S['edge_full_ps']} ps（10–90% {rc1090_draft:.1f} ps）",
         f"升餘弦 10–90% {t_tx:g} ps（全寬 {full_ours:.1f} ps）", "不同", "M3 s3 改用草稿值"),
        ("群折射率", f"{S['ng']}", f"{A['ng_si']}", "不同（差 0.2%）", "M3 s3"),
        ("佈局", f"每欄 {D.LAYOUT['column_um']:g} µm（{D.LAYOUT['column_ps']} ps）；macro 內 skew {D.LAYOUT['skew_macro_ps']} ps",
         f"課程的緊湊佈局；晶片內路徑差 {win['chip_spread_ps']:.3f} ps", "不同", "M3 s3 用草稿的 macro 內 skew"),
        ("情境集", S["scenario_4in"], f"B(16,3) de Bruijn 序列（{win['n_symbols']} 個符號，含全部有序轉移）", "不同（我們的較多）", "M3 s3 改用草稿的"),
        ("延遲掃描", S["delay_scan"], "skew 角落（各路 0 或 skew）", "不同", "M3 s3"),
        ("時間格點", "1 ps 與 0.5 ps", f"{win['dt_ps']} ps", "部分相同", "M3 s3"),
        ("合成", S["synth"], f"SLSQP（把最差 margin 寫成限制式後最大化），{M.STARTS} 個起點", "不同", "M3 s2"),
    ]
    params = [dict(item=a, draft=b, ours=c, status=d, handled=e) for a, b, c, d, e in rows]

    # 2. 同參考面的護欄
    g = {fn: guards(fn, f, A, enbw, pu7) for fn, f in ph["functions"].items()}
    cmp_ = {fn: dict(ours=g[fn]["guard_ours"], draft_style=g[fn]["guard_draft_style"], draft_style_smax=g[fn]["guard_draft_style_smax"],
                     draft=D.TABLE1[fn]["guard"]) for fn in g if fn in D.TABLE1}

    # 3. 參考面：XOR2 的需求換到偵測器端
    p = bud["power"]
    loss_out = p["prop_db"] + p["ec_loss_db"]
    plane = {}
    for fn, core in p["pu_core_per_function_dbm"].items():
        pd = core - loss_out
        gp = guards(fn, ph["functions"][fn], A, enbw, 10 ** (pd / 10) * 1e-3)
        plane[fn] = dict(b7_input_dbm=core, pd_dbm=round(pd, 2), guard_at_pd_need=gp["guard_ours"], margin=gp["m"],
                         guard_at_m7=g[fn]["guard_ours"], ratio=round(gp["guard_ours"] / g[fn]["guard_ours"], 3))
    grid = [round(x, 2) for x in np.arange(-14.0, -1.99, 0.25)]
    curve = {fn: guard_curve(ph["functions"][fn], fn, A, enbw, grid) for fn in ("XOR2", "AND4")}

    # 4. margin
    marg = {fn: dict(ours=g[fn]["m"], draft_lossless=D.TABLE1[fn]["lossless"] if fn in D.TABLE1 else None,
                     draft_lossy=D.TABLE1[fn]["lossy"] if fn in D.TABLE1 else None) for fn in g}

    x = plane["XOR2"]
    checks = dict(
        receiver_same=params[0]["status"] == "相同",
        guard_same_plane_close=all(abs(v["ours"] - v["draft"]) <= TOL_GUARD for v in cmp_.values()),
        self_consistent_xor2=abs(x["guard_at_pd_need"] - x["margin"]) < 0.005,
        xor2_guard_smallest=min(cmp_, key=lambda k: cmp_[k]["ours"]) == "XOR2",
    )
    res = dict(draft_pu_dbm=S["pu_dbm"], enbw_ghz=round(enbw / 1e9, 3), params=params, n_diff=sum(1 for r in params if r["status"] != "相同"),
               guards=g, guard_compare=cmp_, tol_guard=TOL_GUARD, plane=plane, loss_out_db=round(loss_out, 2),
               curve_dbm=grid, curve=curve, margins=marg,
               edge=dict(ours_1090_ps=t_tx, ours_full_ps=round(full_ours, 1), draft_full_ps=S["edge_full_ps"], draft_1090_ps=round(rc1090_draft, 1)),
               checks=checks)
    out = paths.OUT(STEP, "align.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in params:
        print(f"{r['item']}｜草稿：{r['draft']}｜我們：{r['ours']}｜{r['status']}｜處理：{r['handled']}")
    print(f"同參考面（偵測器端 {S['pu_dbm']:g} dBm）的護欄（P_u）：")
    for fn, v in cmp_.items():
        print(f"  {fn}：我們 {v['ours']:.3f}｜草稿式 {v['draft_style']:.3f}（最大輸出功率 {v['draft_style_smax']:.3f}）｜草稿表 I {v['draft']:.2f}")
    print(f"XOR2：B7 輸入端 {x['b7_input_dbm']} dBm − 輸出側 {loss_out:.2f} dB ＝ 偵測器端 {x['pd_dbm']} dBm；"
          f"該處護欄 {x['guard_at_pd_need']:.3f}＝margin {x['margin']:.3f}；−7 dBm 時 {x['guard_at_m7']:.3f}（{x['ratio']:.2f} 倍）")
    print("檢查：", checks)
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
