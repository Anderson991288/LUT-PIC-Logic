r"""論文 M2 s3（審查 R6）：靜態篩選是否漏掉窗內最差的組合？

用途：s3、s4、s5 與 M1 s5 的聯合驗收，都先用靜態 margin 從「每路相位殘差 −δ_det／0／＋δ_det × 7 個 heater 擺動 ±ε」
的組合中篩出最差 N_SCREEN＝2 組，再跑時域。轉態干涉與 skew 可能改變排序，所以這裡在校正後條件（消光比規格、skew 20 ps
最差角落）下多跑幾組，比較「篩 2 組」與「多算的最差」：
  - XOR2：不含擺動時全部 3²＝9 組；含擺動時靜態最差的前 TOP["XOR2"] 組（共 9×128 組中）。
  - AND4：含擺動時靜態最差的前 TOP["AND4"] 組（共 81×128 組中）。
以 6 個 worker 平行（每組一個工作，BLAS 單執行緒）。
輸入：同 power.py（M1 的相位、預算、介面、追蹤結果；時域模型 s4_window/window.py）。
輸出：design/paper/m2_evidence/s3_power/out/screen_check.json。
執行：.\lab design\paper\m2_evidence\s3_power\screen_check.py（6 個 worker 約 3 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
M1 = Path(__file__).resolve().parents[2] / "m1_timing"
sys.path.insert(0, str(M1))
sys.path.insert(0, str(M1 / "s4_window"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import window as W                                                   # noqa: E402
from common.mzi import READ                                          # noqa: E402
from common.synth import deltas                                      # noqa: E402
from model import b7, load_phases                                    # noqa: E402

STEP = "paper/m2_evidence/s3_power"
BASE = "paper/m1_timing"
SKEW = 20
N_SCREEN = 2
TOP = {"XOR2": 64, "AND4": 16}
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
_CTX = None


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def context():
    global _CTX
    if _CTX is not None:
        return _CTX
    ph = load_phases()
    s1, s2, s3 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json")
    t = s1["timing"]
    a0 = 10 ** (-s2["er_required_db"] / 20)
    fns = {}
    for fn in TOP:
        f = ph["functions"][fn]
        s = W.signs(fn, f)
        cols = W.used(f)
        best = None
        for psi in W.PSIS:
            xr, mr = W.resolve(np.concatenate([f["theta"], f["phi"]]), W.vecs(a0, psi), s)
            if best is None or mr < best[1]:
                best = (xr, mr, psi)
        corners = []
        for c in itertools.product([0, 1], repeat=len(cols)):
            z = np.zeros(4)
            z[cols] = c
            corners.append(z * SKEW)
        fns[fn] = dict(s=s, cols=cols, th=best[0][:7], pp=best[0][7:], psi=best[2], v=W.vecs(a0, best[2]), corners=corners)
    _CTX = dict(t=t, a0=a0, det=s3["det_rad"], eps=s3["dither_rad"], fns=fns, geo=W.geometry(t["ps_per_um"]),
                sim=W.Sim(t["ui_ps"], t["t_tx_ps"], s1["assume"]["rx_bw_ghz"], W.debruijn(16, 3)))
    return _CTX


def static_m(F, pp, dp):
    D = np.diag(np.exp(1j * np.append(dp, 0.0)))
    return float(np.min(F["s"] * deltas(b7(F["th"], pp) @ D, F["v"], READ)))


def ranked(fn, with_dither):
    C = context()
    F = C["fns"][fn]
    dits = [np.array(d) for d in itertools.product([-1, 1], repeat=7)] if with_dither else [np.zeros(7)]
    cand = []
    for c in itertools.product([-1, 0, 1], repeat=len(F["cols"])):
        dp = np.zeros(4)
        dp[F["cols"]] = C["det"] * np.array(c)
        for d in dits:
            cand.append((static_m(F, F["pp"] + C["eps"] * d, dp), dp, d))
    cand.sort(key=lambda r: r[0])
    return cand


def win(job):
    """一組（相位殘差、擺動）在所有 skew 角落的最差窗內 margin。"""
    rt.setup(plot=False)
    fn, dp, d = job
    C = context()
    F = C["fns"][fn]
    pp = F["pp"] + C["eps"] * np.array(d)
    return min(C["sim"].best_window(C["sim"].run(F["th"], pp, C["geo"], F["s"], taus, C["a0"], F["psi"], dphi=np.array(dp)), C["t"]["t_req_ps"])[0]
               for taus in F["corners"])


def main():
    t0 = time.perf_counter()
    sets = {"XOR2_no_dither_all": ranked("XOR2", False), "XOR2_dither_top": ranked("XOR2", True)[:TOP["XOR2"]],
            "AND4_dither_top": ranked("AND4", True)[:TOP["AND4"]]}
    jobs, idx = [], []
    for key, cand in sets.items():
        fn = key.split("_")[0]
        for k, (ms, dp, d) in enumerate(cand):
            jobs.append((fn, dp.tolist(), d.tolist()))
            idx.append((key, k, ms))
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        mws = list(ex.map(win, jobs))
    out = {}
    for key in sets:
        rows = [(k, ms, mw) for (kk, k, ms), mw in zip(idx, mws) if kk == key]
        mw_all = [r[2] for r in rows]
        worst = int(np.argmin(mw_all))
        m2 = min(mw_all[:N_SCREEN])
        out[key] = dict(n_checked=len(rows), m_win_screen2=round(m2, 5), m_win_worst=round(min(mw_all), 5), worst_static_rank=worst + 1,
                        error_pct=round(100 * (m2 - min(mw_all)) / m2, 2),
                        rows=[dict(rank=k + 1, m_static=round(ms, 5), m_win=round(mw, 5)) for k, ms, mw in rows])
        print(f"{key}：檢查 {len(rows)} 組；篩 2 組 {m2:.5f}、多算的最差 {min(mw_all):.5f}（靜態排序第 {worst + 1}），差 {out[key]['error_pct']}%", flush=True)
    res = dict(n_screen=N_SCREEN, top=TOP, skew_ps=SKEW, sets=out, workers=WORKERS, wall_s=round(time.perf_counter() - t0, 1),
               checks=dict(screen2_within_1pct=all(v["error_pct"] <= 1.0 for v in out.values())))
    paths.OUT(STEP, "screen_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("檢查：", res["checks"], f"；{res['wall_s']} s")


if __name__ == "__main__":
    main()
