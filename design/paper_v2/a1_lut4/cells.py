r"""論文 v2 附錄 A：LUT4 第一級的 14 個 2 輸入光學單元，時序窗是否都通過？

用途：
  LUT4＝四個只接 x1、x2 的 2 輸入光學單元（x3、x4 兩個輸入埠不亮）＋電側以 x3、x4 四選一。
  16 種 2 輸入子函數扣掉常數 0、1，剩 14 個單元；本程式逐一：
  1. 合成：0.9 dB／MZI，以 M3 s2 的 soft-min（同一退火、L-BFGS-B）找 14 個相位，16 個隨機起點取最佳。
     不亮的輸入以 B7 傳遞矩陣第 3、4 欄設為零表示（輸入光場為零）。
  2. 動態窗：沿用 M5 s4 的第 1 層（M3 s3 詳細模擬、類比接收端、時變護欄、Euler 情境序列），算對齊窗與 13.2 ps 盒內 41 點的共同窗。
  3. 認證：沿用 M5 s4 的第 2 層（M5 s3 的盒證明）；不亮的輸入被判為弱耦合，葉盒只切 x1、x2。
  通過條件：盒內共同窗與認證窗都 ≥ T_req（23 ps）。
  回歸檢查：以 M5 s4 中 AND2 所屬類別的代表（輸入全亮）重跑第 1、2 層，結果要與 screen.json 相同。
  另記錄：情境序列投影到 (x1, x2) 後，涵蓋多少種長度 3 的資料歷史（共 64 種）。
輸入：design/paper/m5_cascade/s4_screen/screen.py（合成與動態函數）、其 out/screen.json（回歸值）。
輸出：design/paper_v2/a1_lut4/out/cells.json。
執行：.\lab design\paper_v2\a1_lut4\cells.py（6 個 worker，約數分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))                       # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper" / "m5_cascade" / "s4_screen"))
import screen as S                                                                # noqa: E402  （會一併設定 BLAS 單執行緒與路徑）

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402
from concurrent.futures import ProcessPoolExecutor                                # noqa: E402

import numpy as np                                                                # noqa: E402
from scipy.optimize import minimize                                               # noqa: E402

import paths                                                                      # noqa: E402
from common import runtime as rt                                                  # noqa: E402
from common.mzi import READ, R_AMP                                                # noqa: E402

SY, CC, LF, DT, CT = S.SY, S.CC, S.LF, S.DT, S.CT
LOSS = SY.D.SETTINGS["mzi_loss_db"]
STARTS, SEED0 = 16, 9000
WORKERS = 6
DARK = (2, 3)                                                                     # x3、x4 不亮
NAMES = {(0, 0, 0, 1): "AND", (1, 1, 1, 0): "NAND", (0, 1, 1, 1): "OR", (1, 0, 0, 0): "NOR",
         (0, 1, 1, 0): "XOR", (1, 0, 0, 1): "XNOR", (0, 0, 1, 1): "x1", (1, 1, 0, 0): "NOT x1",
         (0, 1, 0, 1): "x2", (1, 0, 1, 0): "NOT x2", (0, 0, 1, 0): "x1 AND NOT x2", (0, 1, 0, 0): "NOT x1 AND x2",
         (1, 0, 1, 1): "x1 OR NOT x2", (1, 1, 0, 1): "NOT x1 OR x2"}                # 依 (x1x2＝00, 01, 10, 11) 的輸出
COMMON6 = ("AND", "OR", "XOR", "XNOR", "x1", "x2")                                # 附錄 A 常用邏輯用到的子函數


def tt4(g):
    """2 輸入函數 g（00、01、10、11 的輸出）→ 4 輸入真值表整數（第 w 位元＝g(x1, x2)，x1 為最高位，與 M3 s2 相同）。"""
    return sum(g[2 * b[0] + b[1]] << w for w, b in enumerate(SY.BITS))


def unit(z, amp, dark=True):
    U = SY.b7(np.asarray(z), amp)
    if dark:
        U = U.copy()
        U[:, list(DARK)] = 0
    return U


def signed(z, amp, s):
    P = np.abs(SY.V @ unit(z, amp).T) ** 2
    return s * (P[:, READ[0]] - P[:, READ[1]]), P[:, READ[0]] + P[:, READ[1]]


def synth_job(arg):
    tt, k = arg
    amp = 10 ** (-LOSS / 20)
    s = S.signs(tt)
    z = np.random.default_rng(SEED0 + k).uniform(0, 2 * np.pi, 14)
    for beta in SY.BETAS:
        def f(x):
            m, _ = signed(x, amp, s)
            return -(-np.log(np.sum(np.exp(-beta * (m - m.min())))) / beta + m.min())
        z = minimize(f, z, method="L-BFGS-B", options=dict(maxiter=500)).x
    m, _ = signed(z, amp, s)
    return tt, k, float(m.min()), (z % (2 * np.pi)).tolist()


def dyn_job(arg):
    """M5 s4 第 1、2 層，改成直接收傳遞矩陣 U（不亮的欄已設為零）。"""
    key, tt, U = arg
    t0 = time.time()
    b_sym = S.signs(tt)
    sim = S.sim4()
    sim.cache.clear()
    aligned = sim.window(U, b_sym, np.zeros(4))[0]
    mins = np.full(2 * sim.n_ui, np.inf)
    for p in DT.box_points():
        mins = np.minimum(mins, sim.window(U, b_sym, p)[1])
    box = DT.longest(mins, sim.dt)
    M, c = U[list(READ), :4], U[list(READ), 4] * R_AMP
    rx = LF.Rx(sim)
    coef = CC.coeffs(M, c)
    _, weak = LF.weak_inputs(*coef[0][1:])
    gsym = CC.guard_box(sim, coef)[rx.idx]
    e = CC.errors(sim, coef)
    cert = {}
    for bins in (1, 2):
        if bins == 2 and (cert[1] >= S.T_REQ or box < S.T_REQ):
            break
        node = np.full(2 * sim.n_ui, np.inf)
        for _, cc, rr in CC.leaves(weak, bins):
            b = CC.bound(sim, rx, coef, DT.BITS, b_sym, cc, rr, weak)
            node = np.minimum(node, (b["L"] - gsym).min(0))
        cert[bins] = CT.window(node - 2 * e, sim.dt)[0]
    sim.cache.clear()
    return key, dict(aligned=aligned, box=box, cert1=cert[1], cert_fine=cert.get(2), strong=[int(i) + 1 for i in np.nonzero(~weak)[0]],
                     time_s=round(time.time() - t0, 1))


def history_cover():
    """情境序列投影到 (x1, x2) 後的長度 3 歷史數（循環序列）。"""
    seq = np.asarray(S.sim4().seq)
    sym = 2 * SY.BITS[seq, 0] + SY.BITS[seq, 1]
    n = len(sym)
    return len({(sym[i], sym[(i + 1) % n], sym[(i + 2) % n]) for i in range(n)})


def main():
    t0 = time.time()
    cells = [(name, tt4(g)) for g, name in NAMES.items()]
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(synth_job, [(tt, k) for _, tt in cells for k in range(STARTS)], chunksize=4))
    t_syn = time.time() - t0
    amp = 10 ** (-LOSS / 20)
    rows = {}
    for name, tt in cells:
        rs = sorted([r for r in res if r[0] == tt], key=lambda r: -r[2])
        rows[name] = dict(tt=tt, margin=rs[0][2], hits=int(sum(r[2] >= rs[0][2] - S.NEAR for r in rs)), z=rs[0][3])

    ref = json.loads(paths.OUT("paper/m5_cascade/s4_screen", "screen.json").read_text(encoding="utf-8"))
    c5 = ref["classes"][5]
    jobs = [(name, rows[name]["tt"], unit(rows[name]["z"], amp)) for name, _ in cells]
    jobs.append(("regression AND2 class", c5["tt"], unit(c5["best_z"], amp, dark=False)))
    with ProcessPoolExecutor(WORKERS) as ex:
        dyn = dict(ex.map(dyn_job, jobs))
    reg = dyn.pop("regression AND2 class")
    for name in rows:
        d = dyn[name]
        rows[name].update(d, pass_box=d["box"] >= S.T_REQ,
                          pass_cert=max(d["cert1"], d["cert_fine"] or -np.inf) >= S.T_REQ)

    cert_w = {n: max(r["cert1"], r["cert_fine"] or -np.inf) for n, r in rows.items()}
    out = dict(
        t_req_ps=S.T_REQ, loss_db=LOSS, starts=STARTS, dark_inputs=[i + 1 for i in DARK],
        cells=rows,
        summary=dict(n=len(rows), pass_box=sum(r["pass_box"] for r in rows.values()), pass_cert=sum(r["pass_cert"] for r in rows.values()),
                     min_margin=min(r["margin"] for r in rows.values()), min_box=min(r["box"] for r in rows.values()),
                     min_cert=min(cert_w.values()), argmin_cert=min(cert_w, key=cert_w.get),
                     common6_min_box=min(rows[n]["box"] for n in COMMON6), common6_min_cert=min(cert_w[n] for n in COMMON6),
                     lut4_window_ps=min(cert_w.values())),
        history3=dict(covered=history_cover(), total=64),
        regression=dict(box=reg["box"], cert1=reg["cert1"], ref_box=c5["dyn"]["box"], ref_cert1=c5["dyn"]["cert1"]),
        checks=dict(regression=reg["box"] == c5["dyn"]["box"] and reg["cert1"] == c5["dyn"]["cert1"],
                    dark_weak=all(r["strong"] and set(r["strong"]) <= {1, 2} for r in rows.values()),
                    all_margin_pos=all(r["margin"] > 0 for r in rows.values())),
        time_s=dict(synth=round(t_syn, 1), total=round(time.time() - t0, 1)), workers=WORKERS)
    path = paths.OUT("paper_v2/a1_lut4", "cells.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, r in rows.items():
        print(f"{n:16s} margin {r['margin']:.3f}  對齊 {r['aligned']:5.1f}  盒 {r['box']:5.1f}  認證 {r['cert1']:5.1f}/{r['cert_fine']}  輸入 {r['strong']}")
    print("summary", out["summary"], "\nhistory3", out["history3"], "\nregression", out["regression"], "\nchecks", out["checks"], out["time_s"])
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
