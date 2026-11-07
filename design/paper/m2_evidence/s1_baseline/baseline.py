r"""論文 M2 s1：與固定加總模型比較——只數 MZI 的延遲與損耗，能不能預測 10 Gb/s 下的結果？

用途：可程式光子電路上的數位運算（Liang、Jiang、Chiu，DCPPC，ASP-DAC 2026，第 V-A 節；指標沿用 Matsuo 等人，ISVLSI 2020）
用固定加總的指標評估電路：每顆 MZI 延遲 1 ps，功率衰減依 MZI 的角色固定扣 dB（只做繞線的 0 dB、計算 1 dB、合併 3 dB）。
這個模型適合合成階段的比較，
本步把它當作基準，用在同一顆 B7 的 5 個函數上，與 M1 的時域流程（判讀量是光場的二次式、共同取樣窗、校正後驗收）逐項對照：
  1. 晶片內延遲：固定模型＝判讀路徑上的 MZI 數 × 1 ps；時域流程＝佈局路徑長度換算的到達時間差（M1 s1）。
  2. skew 容許：原研究沒有 skew 的指標；本步替它補一個假設（審查 R3）：不看干涉，判讀在最後一路到達後成立，
     所有函數都是 UI − t_e − T_req（M1 s1 的一階估計）；
     時域流程＝各函數 skew 額外代價達 1 dB 的點（M1 s4），以及 skew 0 時就有的轉態代價。
  3. 功率：固定模型＝最差判讀路徑的累計衰減；時域流程＝由靜態 margin 與雜訊反推的 B7 輸入端需求（M1 s1）。比較兩者的函數排序。
  4. 情境判定：skew 0、15、20 ps，未追蹤的輸入相位漂移 0.3 rad，消光比 20 dB 且不重新求相位。固定模型沒有相位與殘留光的項，
     這兩種情境預測為「不受影響」；時域流程給出 margin 比例或功率代價。
  5. 判定準則（審查 R3，程式與報告相同）：一律換成功率代價（dB）比較。固定模型在通過的情境預測 0 dB；
     時域流程的代價＝skew 情境用 M1 s4 的總功率代價（含 skew 0 的轉態代價，因為固定模型兩者都沒有；另列額外代價），
     相位與消光比情境用 −10 log10(margin 比例)。意見不同＝固定模型「通過」而時域流程代價 ≥ THR_DB 或無窗，
     或固定模型「不通過」而時域流程代價 < THR_DB。另算「固定模型加 3 dB 安全係數」（代價 ≥ 3 dB 才算不同）的敏感度。
  6. 角色判定的敏感度（審查 R14）：ROUTE_TOL 換成 0.02、0.1 rad 時的路徑衰減與排序。
MZI 角色的對應（本步的假設，寫在報告）：θ 距 0、π、2π 不到 0.05 rad 視為只做繞線；其餘若兩個輸入都有光則為合併，否則為計算。
輸入：design/paper/m1_timing/out/phases_lossy.json（model.py）、design/paper/m1_timing/s1_budget/out/budget.json、
      s2_interface/out/interface_v2.json、s4_window/out/window.json、s5_assess/out/joint.json、
      design/m3_layout/s1_core/out/layout_info.json、delivery/interfaces/chip_info.json（經 s4 的 geometry()）。
      原研究參數出處：J.-W. Liang, I. H.-R. Jiang, K.-H. Chiu, ASP-DAC 2026, Sec. V-A（Table II 的評估設定）。
輸出：design/paper/m2_evidence/s1_baseline/out/baseline.json。
執行：.\lab design\paper\m2_evidence\s1_baseline\baseline.py（約 5 秒）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
M1 = Path(__file__).resolve().parents[2] / "m1_timing"
sys.path.insert(0, str(M1))                                          # 共用模型 model.py
sys.path.insert(0, str(M1 / "s4_window"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import window as W                                                   # noqa: E402  s4 的幾何與 signs／used／vecs
from common.mzi import READ, T                                       # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import b7 as b7_matrix, load_phases                       # noqa: E402

STEP = "paper/m2_evidence/s1_baseline"
BASE = "paper/m1_timing"
FIX = dict(delay_ps_per_mzi=1.0, db_route=0.0, db_calc=1.0, db_comb=3.0)   # 固定加總模型的參數（沿用 DCPPC 的評估設定）
ROUTE_TOL = 0.05                                                     # θ 距 0、π、2π 小於此值視為只做繞線（本研究的假設）
ROUTE_TOLS = (0.02, 0.05, 0.1)                                       # 角色判定的敏感度
THR_DB = 1.0                                                         # 判定「意見不同」的功率代價門檻
SAFETY_DB = 3.0                                                      # 敏感度：固定模型加安全係數
DRIFT_RAD = 0.3
ER_FIXED_DB = 20.0
SKEW_CASES = (0, 15, 20)


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def is_route(theta, tol=ROUTE_TOL):
    return min(abs(theta - k * np.pi) for k in range(3)) < tol


def path_metrics(f, cols, tol=ROUTE_TOL):
    """固定加總模型：從每個用到的輸入（與 R）沿有光的分支走到 o2、o4，回傳最差路徑的 (dB, MZI 數) 與各 MZI 角色。"""
    th, ph = np.array(f["theta"]), np.array(f["phi"])
    # 先決定每顆 MZI 的兩個輸入是否有光：逐欄傳遞「是否有光」
    lit = np.zeros(5, bool)
    for j in [int(u[1]) - 1 for u in f["uses"]] + [4]:
        lit[j] = True
    roles = {}
    for col in cols:
        new = lit.copy()
        for k, r in col:
            t = np.abs(T(th[k], ph[k])) ** 2
            a, b = lit[r], lit[r + 1]
            roles[k] = "route" if is_route(th[k], tol) else ("comb" if (a and b) else "calc")
            new[r] = (a and t[0, 0] > 1e-3) or (b and t[0, 1] > 1e-3)
            new[r + 1] = (a and t[1, 0] > 1e-3) or (b and t[1, 1] > 1e-3)
        lit = new
    db_of = {"route": FIX["db_route"], "calc": FIX["db_calc"], "comb": FIX["db_comb"]}
    worst = (0.0, 0)
    starts = [int(u[1]) - 1 for u in f["uses"]] + [4]
    for s in starts:                                                 # 枚舉所有有光的分支（7 顆 MZI，路徑數很少）
        stack = [(s, 0, 0.0, 0)]
        while stack:
            r, c, db, n = stack.pop()
            if c == len(cols):
                if r in READ:
                    worst = max(worst, (db, n))
                continue
            hit = [(k, rr) for k, rr in cols[c] if rr in (r, r - 1)]
            if not hit:
                stack.append((r, c + 1, db, n))
                continue
            k, rr = hit[0]
            t = np.abs(T(th[k], ph[k])) ** 2
            i = r - rr                                               # 從上方（0）或下方（1）進入
            for o in (0, 1):
                if t[o, i] > 1e-3:
                    stack.append((rr + o, c + 1, db + db_of[roles[k]], n + 1))
    return worst, roles


def main():
    ph = load_phases()
    s1, s2, s4, J = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s4_window", "window.json"), \
        load("s5_assess", "joint.json")
    t = s1["timing"]
    geo = W.geometry(t["ps_per_um"])
    cols = geo["cols"]
    allow_fixed = t["skew_allow_ps"]                                 # UI − t_e − T_req：固定模型對所有函數的 skew 容許
    out = {}
    for fn, f in ph["functions"].items():
        (loss_db, n_mzi), roles = path_metrics(f, cols)
        s = W.signs(fn, f)
        th, pp = np.array(f["theta"]), np.array(f["phi"])
        U = b7_matrix(th, pp)
        m0 = float(np.min(s * deltas(U, W.vecs(0.0, 0.0), READ)))
        # 未追蹤的相位漂移：每路 −δ、0、＋δ 的最差組合（靜態）
        cs = W.used(f)
        drift = np.inf
        for c in itertools.product([-1, 0, 1], repeat=len(cs)):
            d = np.zeros(4)
            d[cs] = DRIFT_RAD * np.array(c)
            D = np.diag(np.exp(1j * np.append(d, 0.0)))
            drift = min(drift, float(np.min(s * deltas(U @ D, W.vecs(0.0, 0.0), READ))))
        # 消光比 20 dB、沿用原相位：ψ 取最差
        a0 = 10 ** (-ER_FIXED_DB / 20)
        er = min(float(np.min(s * deltas(U, W.vecs(a0, psi), READ))) for psi in W.PSIS)
        rows = s4["functions"][fn]["ideal"]["rows"]
        sk = {r["skew_ps"]: r["penalty_db"] for r in rows}
        pe = [(r["penalty_db"] if r["penalty_db"] is not None else 99) - rows[0]["penalty_db"] for r in rows]
        allow_1db = rows[-1]["skew_ps"]
        for k in range(1, len(rows)):
            if pe[k] >= 1.0:
                allow_1db = rows[k - 1]["skew_ps"] + (1.0 - pe[k - 1]) / (pe[k] - pe[k - 1]) * (rows[k]["skew_ps"] - rows[k - 1]["skew_ps"])
                break
        out[fn] = dict(
            fixed=dict(path_loss_db=loss_db, path_mzi=n_mzi, delay_ps=n_mzi * FIX["delay_ps_per_mzi"],
                       roles={str(k + 1): v for k, v in sorted(roles.items())}, skew_allow_ps=allow_fixed,
                       skew_penalty_db={str(S): (0.0 if S <= allow_fixed else None) for S in SKEW_CASES},
                       drift_ratio=1.0, er20_ratio=1.0),
            flow=dict(chip_spread_ps=t["readout"]["spread_ps"], skew_allow_1db_ps=round(allow_1db, 1),
                      skew_penalty_db={str(S): sk[S] for S in SKEW_CASES},
                      skew_extra_db={str(S): (None if sk[S] is None else round(sk[S] - sk[0], 3)) for S in SKEW_CASES}, pu_static_dbm=s1["power"]["pu_core_per_function_dbm"][fn],
                      m0=round(m0, 4), drift_ratio=round(drift / m0, 3), er20_ratio=round(er / m0, 3),
                      er_need_fixed_db=s2["er_need_fixed_db"][fn]))
    # 功率排序：固定模型（路徑衰減大者要更多光）與時域流程（靜態需求高者）
    rank_fixed = sorted(out, key=lambda f: -out[f]["fixed"]["path_loss_db"])
    rank_flow = sorted(out, key=lambda f: -out[f]["flow"]["pu_static_dbm"])
    joint = {f: dict(drift_m_win=v["drift"]["m_win"], drift_penalty_db=v["drift"]["penalty_db"],
                     nominal_m_win=v["nominal"]["m_win"]) for f, v in J["functions"].items()}
    # 每個情境換成功率代價後判定（固定模型通過＝預測 0 dB；時域流程無窗或判錯＝代價 None）
    def verdict(fixed_ok, flow_db, thr):
        if fixed_ok:
            if flow_db is None:
                return True, "固定模型通過、時域流程無窗"
            return bool(flow_db >= thr), f"固定模型 0 dB、時域流程 {flow_db:.2f} dB" + (f" ≥ {thr:g} dB" if flow_db >= thr else f" < {thr:g} dB")
        if flow_db is None:
            return False, "兩者都不通過"
        return bool(flow_db < thr), "固定模型不通過、時域流程 " + (f"{flow_db:.2f} dB < {thr:g} dB" if flow_db < thr else f"{flow_db:.2f} dB ≥ {thr:g} dB")
    cases = []
    for fn, r in out.items():
        for S in SKEW_CASES:
            fx, fl = r["fixed"]["skew_penalty_db"][str(S)], r["flow"]["skew_penalty_db"][str(S)]
            cases.append(dict(function=fn, case=f"skew {S} ps", fixed_ok=fx is not None, flow_db=fl,
                              flow_extra_db=r["flow"]["skew_extra_db"][str(S)]))
        for case, key in ((f"未追蹤漂移 {DRIFT_RAD} rad", "drift_ratio"), (f"消光比 {ER_FIXED_DB:g} dB、不重解", "er20_ratio")):
            v = r["flow"][key]
            cases.append(dict(function=fn, case=case, fixed_ok=True, flow_db=None if v <= 0 else round(float(-10 * np.log10(v)), 3), flow_ratio=v))
    for c in cases:
        c["disagree"], c["reason"] = verdict(c["fixed_ok"], c["flow_db"], THR_DB)
        c["disagree_safety"] = verdict(c["fixed_ok"], c["flow_db"], SAFETY_DB)[0]
    disagree = [dict(function=c["function"], case=c["case"], fixed="通過（0 dB）" if c["fixed_ok"] else "不通過",
                     flow="無窗" if c["flow_db"] is None else f"{c['flow_db']:.2f} dB", reason=c["reason"]) for c in cases if c["disagree"]]
    # 角色判定的敏感度
    tol_sens = {}
    for tol in ROUTE_TOLS:
        loss = {fn: path_metrics(f, cols, tol)[0][0] for fn, f in ph["functions"].items()}
        tol_sens[str(tol)] = dict(path_loss_db=loss, rank=sorted(loss, key=lambda k: -loss[k]))
    res = dict(fixed_params=FIX, route_tol_rad=ROUTE_TOL, drift_rad=DRIFT_RAD, er_fixed_db=ER_FIXED_DB, skew_cases=list(SKEW_CASES),
               ui_ps=t["ui_ps"], functions=out, rank_fixed=rank_fixed, rank_flow=rank_flow, joint=joint, disagree=disagree,
               n_disagree=len(disagree), n_cases=len(cases), cases=cases, thr_db=THR_DB, safety_db=SAFETY_DB,
               n_disagree_safety=sum(c["disagree_safety"] for c in cases), route_tol_sensitivity=tol_sens,
               checks=dict(delay_negligible_both=all(r["fixed"]["delay_ps"] < 0.1 * t["ui_ps"] and r["flow"]["chip_spread_ps"] < 0.1 * t["ui_ps"]
                                                     for r in out.values()),
                           ranking_same=rank_fixed[0] == rank_flow[0],
                           ranking_reversed_all_tols=all(v["rank"][0] != rank_flow[0] for v in tol_sens.values())))
    paths.OUT(STEP, "baseline.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for fn, r in out.items():
        fx, fl = r["fixed"], r["flow"]
        print(f"{fn}：固定模型 路徑 {fx['path_mzi']} 顆 MZI、{fx['path_loss_db']:g} dB、延遲 {fx['delay_ps']:g} ps、skew 容許 {fx['skew_allow_ps']} ps"
              f"（角色 {fx['roles']}）｜時域流程 晶片內差 {fl['chip_spread_ps']} ps、1 dB 點 {fl['skew_allow_1db_ps']} ps、"
              f"skew 0／15／20 ps 代價 {fl['skew_penalty_db']}、靜態需求 {fl['pu_static_dbm']} dBm、漂移 {DRIFT_RAD} rad 後 margin {fl['drift_ratio']:.0%}、"
              f"消光比 {ER_FIXED_DB:g} dB 不重解 {fl['er20_ratio']:.0%}")
    print(f"功率排序：固定模型 {rank_fixed}；時域流程 {rank_flow}")
    print(f"意見不同 {len(disagree)}／{res['n_cases']} 個情境：")
    for d in disagree:
        print("  ", d)
    print(f"加 {SAFETY_DB:g} dB 安全係數後意見不同 {res['n_disagree_safety']}／{res['n_cases']}；角色敏感度：", {k: v["rank"] for k, v in tol_sens.items()})
    print("檢查：", res["checks"])


if __name__ == "__main__":
    main()
