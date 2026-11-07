r"""論文 M3 s2：依論文草稿式 2 合成——共用零門檻下，讓最差 margin 最大的 14 個相位；重現草稿表 I。

用途：
  1. 目標：草稿表 I 的 9 個函數（AND4、OR4、MAJ4、TH2、AND3、AND2、AND2′、SOP2、XOR2），全部以 4 個輸入的 16 組字定義
     （沒用到的輸入為任意值），判讀 m＝min_x s_f(x)·(P_o2 − P_o4)，參考光 R＝3。
  2. 方法（草稿 II-B）：內層最小值以退火的 log-sum-exp soft-min 取代，β 依 BETAS 逐段加大，每段用 L-BFGS-B 接續；
     16 個隨機起點（種子 SEED0＋k），最後以實際相位重算最差 margin。
  3. 兩種損耗：無損，與每顆 MZI 0.9 dB（場振幅乘 10^(−0.9/20)，草稿的模型值）。
  4. 交叉核對：同一模型再用課程的 SLSQP（把最差 margin 寫成限制式，24 個起點）求一次，取兩者較大者為「最佳已知」，
     並記錄兩種方法的差（M2 審查 R2 的教訓：合成要交叉核對）。
  5. 護欄：偵測器端每路 −7 dBm（草稿的 P_u），在 margin 最差那組輸入計算（論文 M3 s1 的雜訊模型；另算不含 shot 的草稿式）。
  驗收：margin 與草稿表 I 相差 ≤ TOL（0.02 P_u），或列出差異原因。
輸入：design/paper/m3_align/draft.py、design/paper/m1_timing/s1_budget/out/budget.json（雜訊參數）。
輸出：design/paper/m3_align/s2_synth/out/synth.json。
執行：.\lab design\paper\m3_align\s2_synth\synth.py（6 個 worker 約 3 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_timing" / "s1_budget"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import platform                                                      # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import budget as B                                                   # noqa: E402
import draft as D                                                    # noqa: E402
import paths                                                         # noqa: E402
from common.mzi import B7_OPS, READ, R_AMP, T, embed                 # noqa: E402
from common.synth import best_margin                                 # noqa: E402

STEP = "paper/m3_align/s2_synth"
STARTS, SEED0 = 16, 2000
BETAS = (4.0, 16.0, 64.0, 256.0, 1024.0)                             # soft-min 的退火（β 越大越接近真正的最小值）
SLSQP_STARTS = 24
TOL = 0.02
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
BITS = np.array(list(itertools.product([0, 1], repeat=4)))
FUNCS = {
    "AND4": lambda b: b.all(),
    "OR4": lambda b: b.any(),
    "MAJ4": lambda b: b.sum() >= 3,
    "TH2": lambda b: b.sum() >= 2,
    "AND3": lambda b: b[:3].all(),
    "AND2": lambda b: b[0] and b[1],
    "AND2'": lambda b: b[0] and b[3],
    "SOP2": lambda b: (b[0] and b[1]) or (b[2] and b[3]),
    "XOR2": lambda b: b[0] != b[1],
}


def b7(z, amp):
    U = np.eye(5, dtype=complex)
    for (rail, _), th, ph in zip(B7_OPS, z[:7], z[7:]):
        U = embed(amp * T(th, ph), rail, 5) @ U
    return U


V = np.hstack([BITS.astype(complex), np.full((16, 1), R_AMP + 0j)])


def signed(z, amp, s):
    P = np.abs(V @ b7(z, amp).T) ** 2
    return s * (P[:, READ[0]] - P[:, READ[1]]), P[:, READ[0]] + P[:, READ[1]]


def softmin_run(job):
    fn, loss_db, k = job
    amp = 10 ** (-loss_db / 20)
    s = np.array([1.0 if FUNCS[fn](b) else -1.0 for b in BITS])
    z = np.random.default_rng(SEED0 + k).uniform(0, 2 * np.pi, 14)
    for beta in BETAS:
        def f(x):
            m, _ = signed(x, amp, s)
            return -(-np.log(np.sum(np.exp(-beta * (m - m.min())))) / beta + m.min())
        z = minimize(f, z, method="L-BFGS-B", options=dict(maxiter=500)).x
    m, _ = signed(z, amp, s)
    return fn, loss_db, k, float(m.min()), (z % (2 * np.pi)).tolist()


def slsqp_run(job):
    fn, loss_db = job
    amp = 10 ** (-loss_db / 20)
    s = np.array([1.0 if FUNCS[fn](b) else -1.0 for b in BITS])
    m, z = best_margin(lambda x: b7(x, amp), 14, V, READ, s, SLSQP_STARTS, maxiter=600)
    return fn, loss_db, float(m), z.tolist()


def guard(m, S, A, enbw, pu_w):
    n = B.noise_terms(pu_w, m, S, A, enbw)
    unit = A["resp_a_w"] * pu_w
    full = (n["off"] + A["q"] * math.sqrt(sum(n[x] ** 2 for x in ("th", "comp", "shot", "rin_diff", "rin_cm")))) / unit
    c = math.sqrt(10 ** (A["rin_db_hz"] / 10) * enbw)
    rin = c * (abs(m) + A["pd_mismatch"] * S)
    nos = n["off"] / unit + A["q"] * math.sqrt((n["th"] / unit) ** 2 + (n["comp"] / unit) ** 2 + rin ** 2)
    return round(full, 4), round(nos, 4)


def main():
    t0 = time.time()
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    enbw = A["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
    pu_w = 10 ** (D.SETTINGS["pu_dbm"] / 10) * 1e-3
    losses = (0.0, D.SETTINGS["mzi_loss_db"])
    jobs = [(fn, L, k) for fn in FUNCS for L in losses for k in range(STARTS)]
    with ProcessPoolExecutor(WORKERS) as ex:
        soft = list(ex.map(softmin_run, jobs, chunksize=4))
        t1 = time.time()
        sq = list(ex.map(slsqp_run, [(fn, L) for fn in FUNCS for L in losses]))
    t2 = time.time()
    out = {}
    for fn in FUNCS:
        r = dict(defn=D.TABLE1[fn]["defn"], draft=dict(lossless=D.TABLE1[fn]["lossless"], lossy=D.TABLE1[fn]["lossy"], guard=D.TABLE1[fn]["guard"]))
        for L, key in zip(losses, ("lossless", "lossy")):
            runs = sorted([x for x in soft if x[0] == fn and x[1] == L], key=lambda x: -x[3])
            ms = [x[3] for x in runs]
            q = [x for x in sq if x[0] == fn and x[1] == L][0]
            best_soft, best_sq = runs[0][3], q[2]
            z = runs[0][4] if best_soft >= best_sq else q[3]
            m_best = max(best_soft, best_sq)
            amp = 10 ** (-L / 20)
            s = np.array([1.0 if FUNCS[fn](b) else -1.0 for b in BITS])
            mv, Sv = signed(np.array(z), amp, s)
            k = int(np.argmin(mv))
            g_full, g_nos = guard(float(mv[k]), float(Sv[k]), A, enbw, pu_w)
            r[key] = dict(softmin=round(best_soft, 4), slsqp=round(best_sq, 4), best=round(m_best, 4),
                          method="soft-min" if best_soft >= best_sq else "SLSQP",
                          soft_spread=[round(min(ms), 4), round(float(np.median(ms)), 4), round(max(ms), 4)],
                          soft_hits=int(sum(1 for v in ms if v >= m_best - 0.005)),
                          diff_draft=round(m_best - r["draft"][key], 4), S_worst=round(float(Sv[k]), 3),
                          guard=g_full, guard_no_shot=g_nos, theta=z[:7], phi=z[7:])
        r["loss_ratio"] = round(r["lossy"]["best"] / r["lossless"]["best"], 3)
        r["draft_loss_ratio"] = round(r["draft"]["lossy"] / r["draft"]["lossless"], 3)
        out[fn] = r
    checks = dict(
        lossless_match=all(abs(v["lossless"]["diff_draft"]) <= TOL for v in out.values()),
        lossy_match=all(abs(v["lossy"]["diff_draft"]) <= TOL for v in out.values()),
        guard_match=all(abs(v["lossy"]["guard"] - v["draft"]["guard"]) <= TOL for v in out.values()),
        methods_agree=all(abs(v[k]["softmin"] - v[k]["slsqp"]) <= 0.005 for v in out.values() for k in ("lossless", "lossy")),
    )
    res = dict(starts=STARTS, seed0=SEED0, betas=BETAS, slsqp_starts=SLSQP_STARTS, tol=TOL, pu_dbm=D.SETTINGS["pu_dbm"],
               mzi_loss_db=D.SETTINGS["mzi_loss_db"], functions=out,
               n_lossless_match=sum(1 for v in out.values() if abs(v["lossless"]["diff_draft"]) <= TOL),
               n_lossy_match=sum(1 for v in out.values() if abs(v["lossy"]["diff_draft"]) <= TOL),
               time_s=dict(softmin=round(t1 - t0, 1), slsqp=round(t2 - t1, 1)), workers=WORKERS, cpu=platform.processor(), checks=checks)
    path = paths.OUT(STEP, "synth.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, v in out.items():
        a, b = v["lossless"], v["lossy"]
        print(f"{fn:6s} 無損 {a['best']:.3f}（草稿 {v['draft']['lossless']:.2f}，soft-min {a['softmin']:.3f}／SLSQP {a['slsqp']:.3f}）｜"
              f"0.9 dB {b['best']:.3f}（草稿 {v['draft']['lossy']:.2f}，soft-min {b['softmin']:.3f}／SLSQP {b['slsqp']:.3f}）｜"
              f"護欄 {b['guard']:.3f}（不含 shot {b['guard_no_shot']:.3f}；草稿 {v['draft']['guard']:.2f}）")
    print(f"時間：soft-min {res['time_s']['softmin']} s、SLSQP {res['time_s']['slsqp']} s（{WORKERS} 個 worker）")
    print("檢查：", checks)
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
