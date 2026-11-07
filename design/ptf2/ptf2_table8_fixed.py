r"""PTF2 補充：report/PTF2.html 表 8「固定 o2−o4」與「裕量中位數」欄的重建（下限搜尋，不是證明）。

定義沿用 ptf2_table8.py：v＝(t(x₁,x₂), t(x₃,x₄), R)，R＝1，六種四階編碼；NPN 類與次數沿用 ptf2_check.py。
一個 NPN 類只要有任一成員可實現就計入。只搜尋上限欄（LP）可行的類別與成員。

判讀量 D(x)＝|a†v|²−|b†v|²，門檻固定為 0。兩種 a、b 定義都跑，分開報告（看到結果前就決定）：
  unitary_rows：任務指定。a†、b† 是 3×3 么正光路的兩列；光路用三顆 MZI 的 Reck 三角（6 個相位，涵蓋 U(3) 除去輸出相位）。
  free_ab：頁面方法段的字面定義「a、b ∈ C³」，兩列不必正交等長（等於光路含不等損耗）。
差別：unitary_rows 時 M＝aa†−bb† 無跡。四階相位編碼的 |v_i| 全為 1，D 的對角項和＝tr M＝0，D 沒有常數項（Σₓ D(x)＝0），
      常數類與許多不平衡的真值表都不可能實現。所以另解一次加上 tr M＝0 的 LP：這是 unitary_rows 的嚴格上限，
      也是它的候選成員篩選條件（必要條件，不改定義）；沒有任何成員過關的類不必搜尋，直接判為不可實現。

裕量（寫死，不隨結果調整）：min_x s(x)D(x) / ((|a|²＋|b|²)·max_x‖v(x)‖²)。六種編碼的 max‖v‖² 都是 3。
判定：裕量 > 1e-3。類裕量＝試過成員的最大值；裕量中位數＝可實現類的類裕量中位數。
成員：可行成員先去掉輸出反相重複（交換 a、b 即互換），以固定種子隨機排序，取前 6 個（甲段，頁面欄位的對應值）。
      甲段未實現的類再試其餘成員（乙段，只用來判斷差距來源，分開報告，不併入甲段）：每輪每類 8 個，
      已實現的類退出，每類至多 STAGE_B_CAP 個，每個變體牆鐘至多 STAGE_B_WALL_S 秒，到時停在該輪結束。
最佳化：每成員 25 個隨機起點，平滑 min（logsumexp）L-BFGS，β 逐段加大；以非平滑實際裕量排序，
        前 3 名再用 SLSQP 解 epigraph（最大化 t，s(x)D(x)/N ≥ t）；最後一律以 actual_margin() 從 a、b 重算。
輸入：無。輸出：out/ptf2_table8_fixed.json。
執行：.\lab design\ptf2\ptf2_table8_fixed.py --procs 13
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import get_context
from pathlib import Path

for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_k] = "1"

import numpy as np
from scipy.optimize import least_squares, linprog, minimize
from scipy.special import logsumexp

from ptf2_check import T, haar, is_ptf2, npn_classes, threshold_degree
from ptf2_table8 import BITS, ENC, XS, features, level

OUT = Path(__file__).resolve().parent / "out"
SEED = 2026
N_STARTS = 25
N_MEMBERS = 6
MARGIN_MIN = 1e-3
STAGE_B_CAP = 64
STAGE_B_ROUND = 8
STAGE_B_WALL_S = 600
BETAS = (100.0, 1000.0, 10000.0)
LBFGS_MAXITER = 200
N_POLISH = 3
SLSQP_MAXITER = 200
VARIANTS = ("unitary_rows", "free_ab")
MESH_PORTS = (0, 1, 0)                                   # 每顆 MZI 的上方軌（0 起算），依光路順序
REVISIONS = [                                            # 試跑或第一版跑完後的修改與原因
    dict(when="after 3-class pilot, before the full run",
         change="unitary_rows candidate members filtered by an extra LP with tr M = 0; stage B changed to rounds with a wall limit; mzi() rewritten in closed form",
         reason="pilot showed all 3 phase-encoding classes failing under unitary_rows: tr M = 0 removes the constant term of D, so most LP-feasible members are provably impossible and random picks were wasted. "
                "tr M = 0 is a necessary condition, so this changes which members are tried, not the definition. Threshold, member count, start count and normalization unchanged."),
]
PAGE = {"amplitude a/3": (161, 156, 156, 0, 0.024), "PAM4 binary": (174, 164, 164, 0, 0.020), "PAM4 Gray": (116, 106, 106, 0, 0.017),
        "MZM sin(pi a/6)": (173, 163, 163, 0, 0.018), "phase binary": (195, 195, 166, 29, 0.26), "phase Gray": (89, 89, 89, 0, 0.25)}


EYE3 = np.eye(3, dtype=complex)


def fields(enc):
    t, gray = ENC[enc]
    return np.array([[t(level(int(b[0]), int(b[1]), gray)), t(level(int(b[2]), int(b[3]), gray)), 1.0] for b in BITS], complex)   # (16, 3)


def signs(tt):
    return np.where((tt >> XS) & 1, 1.0, -1.0)


def pnorm(V):
    return float(np.max(np.sum(np.abs(V) ** 2, axis=1)))


# ---------- 光路 ----------
def mzi(th, ph):
    """T(θ,φ) 與兩個偏導（與 ptf2_check.T 同一個定義）。"""
    e, f = np.exp(1j * th), np.exp(1j * ph)
    p, q = 0.5 * (e - 1), 0.5j * (e + 1)                 # H·diag(e^{iθ},1)·H＝[[p, q], [q, −p]]
    dp, dq = 0.5j * e, -0.5 * e
    T0 = np.array([[p * f, q], [q * f, -p]])
    return T0, np.array([[dp * f, dq], [dq * f, -dp]]), np.array([[1j * p * f, 0], [1j * q * f, 0]])


def embed(B, m, one):
    E = EYE3.copy() if one else np.zeros((3, 3), complex)
    E[m:m + 2, m:m + 2] = B
    return E


def mesh(p, grad=False):
    Es, dEs = [], []
    for q, m in enumerate(MESH_PORTS):
        B, dth, dph = mzi(p[2 * q], p[2 * q + 1])
        Es.append(embed(B, m, True)); dEs.append((embed(dth, m, False), embed(dph, m, False)))
    U = Es[2] @ Es[1] @ Es[0]
    if not grad:
        return U
    dU = np.empty((6, 3, 3), complex)
    for j in range(2):
        dU[j] = Es[2] @ Es[1] @ dEs[0][j]
        dU[2 + j] = Es[2] @ dEs[1][j] @ Es[0]
        dU[4 + j] = dEs[2][j] @ Es[1] @ Es[0]
    return U, dU


def rows_ab(variant, x):
    if variant == "unitary_rows":
        U = mesh(x)
        return np.conj(U[0]), np.conj(U[1])
    return x[0:3] + 1j * x[3:6], x[6:9] + 1j * x[9:12]


def actual_margin(a, b, V, s):
    """非平滑實際裕量（只用 a、b 與定義式，不經過最佳化的梯度路徑）。回傳裕量、raw min sD、|a|²＋|b|²。"""
    D = np.abs(V @ np.conj(a)) ** 2 - np.abs(V @ np.conj(b)) ** 2
    raw = float(np.min(s * D)); n = float(np.sum(np.abs(a) ** 2) + np.sum(np.abs(b) ** 2))
    return raw / (n * pnorm(V)), raw, n


def m_and_jac(variant, x, V, s, P):
    """正規化後每組輸入的 s·D/(N·P) 與對參數的 Jacobian (16, n)。"""
    if variant == "unitary_rows":
        U, dU = mesh(x, True)
        E = U[:2] @ V.T                                  # (2, 16)
        dE = dU[:, :2, :] @ V.T                          # (6, 2, 16)
        D = np.abs(E[0]) ** 2 - np.abs(E[1]) ** 2
        dD = 2 * (np.conj(E[0]) * dE[:, 0, :]).real - 2 * (np.conj(E[1]) * dE[:, 1, :]).real
        c = s / (2.0 * P)
        return c * D, (c * dD).T
    a, b = x[0:3] + 1j * x[3:6], x[6:9] + 1j * x[9:12]
    A, B = V @ np.conj(a), V @ np.conj(b)
    D = np.abs(A) ** 2 - np.abs(B) ** 2
    N = float(x @ x)
    GA = np.conj(A)[:, None] * V; GB = np.conj(B)[:, None] * V
    dD = 2 * np.hstack([GA.real, GA.imag, -GB.real, -GB.imag])
    c = s / (N * P)
    return c * D, c[:, None] * dD - np.outer(c * D / N, 2 * x)


def smooth_obj(x, variant, V, s, P, beta):
    m, J = m_and_jac(variant, x, V, s, P)
    z = -beta * m
    lse = logsumexp(z)
    return lse / beta, -(np.exp(z - lse) @ J)            # 最小化 −softmin


def polish(variant, x0, V, s, P):
    m0, _ = m_and_jac(variant, x0, V, s, P)
    z0 = np.append(x0, m0.min()); n = len(x0)

    def cons(z):
        return m_and_jac(variant, z[:n], V, s, P)[0] - z[n]

    def cjac(z):
        return np.hstack([m_and_jac(variant, z[:n], V, s, P)[1], -np.ones((16, 1))])

    g = np.zeros(n + 1); g[n] = -1.0
    r = minimize(lambda z: -z[n], z0, jac=lambda z: g, method="SLSQP", constraints=[dict(type="ineq", fun=cons, jac=cjac)],
                 options=dict(maxiter=SLSQP_MAXITER, ftol=1e-10))
    return r.x[:n]


def init_start(variant, rng):
    if variant == "unitary_rows":
        return rng.uniform(0, 2 * np.pi, 6)
    x = rng.normal(size=12)
    return x / np.linalg.norm(x)


def search_member(task):
    """一個候選成員：N_STARTS 個起點 → 平滑 min → 非平滑複核 → 前 N_POLISH 名 SLSQP。"""
    variant, enc, rep, tt, stage = task
    t0 = time.perf_counter()
    V = fields(enc); s = signs(tt); P = pnorm(V)
    rng = np.random.default_rng([SEED, list(ENC).index(enc), VARIANTS.index(variant), tt])
    cand = []
    for _ in range(N_STARTS):
        x = init_start(variant, rng)
        for beta in BETAS:
            x = minimize(smooth_obj, x, args=(variant, V, s, P, beta), jac=True, method="L-BFGS-B",
                         options=dict(maxiter=LBFGS_MAXITER, ftol=1e-13, gtol=1e-9)).x
            if variant == "free_ab":
                x = x / np.linalg.norm(x)
        cand.append((actual_margin(*rows_ab(variant, x), V, s)[0], x))
    cand.sort(key=lambda c: -c[0])
    starts_smooth = [c[0] for c in cand]
    best_m, best_x = cand[0]
    for _, x in cand[:N_POLISH]:
        y = polish(variant, x, V, s, P)
        if variant == "free_ab":
            y = y / np.linalg.norm(y)
        m = actual_margin(*rows_ab(variant, y), V, s)[0]
        if m > best_m:
            best_m, best_x = m, y
    return dict(variant=variant, enc=enc, rep=rep, tt=tt, stage=stage, margin=float(best_m), x=[float(v) for v in best_x],
                margin_smooth_best=float(starts_smooth[0]), n_starts_over_threshold=int(sum(m > MARGIN_MIN for m in starts_smooth)),
                cpu_s=time.perf_counter() - t0)


# ---------- 上限（LP，同 ptf2_table8.py） ----------
def lp_chunk(arg):
    enc, tts = arg
    F = features(enc)
    ok, ok0 = [], []
    tr = np.array([[1.0, 1, 1, 0, 0, 0, 0, 0, 0]])       # features() 的前三欄是 M_11、M_22、M_33
    for tt in tts:
        s = signs(int(tt))
        kw = dict(A_ub=-(s[:, None] * F), b_ub=-np.ones(16), bounds=[(None, None)] * 9, method="highs")
        ok.append(linprog(np.zeros(9), **kw).status == 0)
        ok0.append(ok[-1] and linprog(np.zeros(9), A_eq=tr, b_eq=[0.0], **kw).status == 0)
    return enc, tts, ok, ok0


def feasible_tables(pool):
    ok = {e: np.zeros(65536, bool) for e in ENC}; ok0 = {e: np.zeros(65536, bool) for e in ENC}
    jobs = [(e, c) for e in ENC for c in np.array_split(np.arange(65536), 32)]
    for e, tts, o, o0 in pool.imap_unordered(lp_chunk, jobs):
        ok[e][tts] = o; ok0[e][tts] = o0
    return ok, ok0


def choose_members(enc, rep, ok, rep_of):
    feas = np.flatnonzero(ok & (rep_of == rep))
    assert all(ok[65535 ^ int(t)] for t in feas)
    uniq = feas[feas < (65535 ^ feas)]
    perm = np.random.default_rng([SEED, list(ENC).index(enc), rep]).permutation(uniq)
    return [int(t) for t in perm[:N_MEMBERS]], [int(t) for t in perm[N_MEMBERS:N_MEMBERS + STAGE_B_CAP]], int(len(uniq))


# ---------- 自我檢查 ----------
def selftest():
    rng = np.random.default_rng(SEED + 7)
    V = fields("phase binary"); s = signs(0x1234); P = pnorm(V)
    res = {}
    for variant, n in (("unitary_rows", 6), ("free_ab", 12)):
        x = rng.normal(size=n)
        _, J = m_and_jac(variant, x, V, s, P)
        Jn = np.empty_like(J); h = 1e-6
        for k in range(n):
            e = np.zeros(n); e[k] = h
            Jn[:, k] = (m_and_jac(variant, x + e, V, s, P)[0] - m_and_jac(variant, x - e, V, s, P)[0]) / (2 * h)
        a, b = rows_ab(variant, x)
        res[variant] = dict(jac_err=float(np.max(np.abs(J - Jn))),
                            m_vs_actual_err=float(abs(m_and_jac(variant, x, V, s, P)[0].min() - actual_margin(a, b, V, s)[0])))
    p = rng.uniform(0, 2 * np.pi, 6)
    U = mesh(p)
    ref = np.eye(3, dtype=complex)
    for q, m in enumerate(MESH_PORTS):
        E = np.eye(3, dtype=complex); E[m:m + 2, m:m + 2] = T(p[2 * q], p[2 * q + 1]); ref = E @ ref
    res["mesh_vs_ptf2_check_T_err"] = float(np.max(np.abs(U - ref)))
    res["mesh_unitary_err"] = float(np.max(np.abs(U.conj().T @ U - np.eye(3))))
    Z = np.diag([1.0, -1.0, 0.0])
    worst = 0.0
    for _ in range(5):                                  # 任意么正的 M＝U†ZU 都能由 6 個相位做出（Reck 涵蓋性）
        W = haar(3, rng); Mt = W.conj().T @ Z @ W

        def resid(q):
            Uq = mesh(q); d = (Uq.conj().T @ Z @ Uq - Mt).ravel()
            return np.concatenate([d.real, d.imag])
        worst = max(worst, min(float(np.max(np.abs(least_squares(resid, rng.uniform(0, 2 * np.pi, 6), xtol=1e-13, ftol=1e-13).fun))) for _ in range(8)))
    res["mesh_reaches_random_M_err"] = worst
    res["ok"] = bool(max(res["unitary_rows"]["jac_err"], res["free_ab"]["jac_err"]) < 1e-6 and res["mesh_vs_ptf2_check_T_err"] < 1e-12 and worst < 1e-8)
    return res


def summarize(enc, class_info, by_class, variant):
    classes, marg_realized = [], []
    n_ptf2 = n_cubic = n_b = n_b_ptf2 = n_b_cubic = 0
    for rep, info in class_info.items():
        if not info["A"]:                                # tr M＝0 的 LP 已證明這類沒有成員可行
            classes.append(dict(rep=f"0x{rep:04X}", degree=info["degree"], n_feasible_members_mod_complement=0, n_tried=0, realized=False, margin=None, proved_infeasible_by_trace0_lp=True))
            continue
        A = [r for r in by_class.get(rep, []) if r["stage"] == "A"]
        Bs = [r for r in by_class.get(rep, []) if r["stage"] == "B"]
        best = max(A, key=lambda r: r["margin"])
        realized = best["margin"] > MARGIN_MIN
        a, b = rows_ab(variant, np.array(best["x"]))
        c = dict(rep=f"0x{rep:04X}", degree=info["degree"], n_feasible_members_mod_complement=info["n_uniq"], n_tried=len(A), realized=bool(realized),
                 margin=best["margin"], best_member=f"0x{best['tt']:04X}", n_starts_over_threshold=best["n_starts_over_threshold"],
                 member_margins={f"0x{r['tt']:04X}": round(r["margin"], 6) for r in A},
                 a=[[float(z.real), float(z.imag)] for z in a], b=[[float(z.real), float(z.imag)] for z in b])
        if variant == "unitary_rows":
            c["mesh_phases_theta_phi"] = [float(v) % (2 * np.pi) for v in best["x"]]
        realized_b = realized
        if Bs:
            bb = max(Bs, key=lambda r: r["margin"])
            c["stage_b"] = dict(n_tried=len(Bs), best_margin=bb["margin"], best_member=f"0x{bb['tt']:04X}")
            realized_b = realized or bb["margin"] > MARGIN_MIN
        if realized:
            marg_realized.append(best["margin"]); n_ptf2 += info["degree"] <= 2; n_cubic += info["degree"] == 3
        if realized_b:
            n_b += 1; n_b_ptf2 += info["degree"] <= 2; n_b_cubic += info["degree"] == 3
        classes.append(c)
    n = len(marg_realized); med = float(np.median(marg_realized)) if n else None
    pg = PAGE[enc]
    all_m = np.array([c["margin"] for c in classes if c["margin"] is not None])
    return dict(upper_bound_classes=len(class_info), n_searched_classes=int(sum(1 for c in classes if c["n_tried"])), n_classes=n, n_ptf2=int(n_ptf2), n_cubic=int(n_cubic), margin_median=med,
                margin_quartiles=[float(q) for q in np.percentile(marg_realized, [25, 75])] if n else None,
                page=dict(upper=pg[0], fixed=pg[1], ptf2=pg[2], cubic=pg[3], margin_median=pg[4]),
                diff_vs_page=dict(fixed=n - pg[1], ptf2=int(n_ptf2) - pg[2], cubic=int(n_cubic) - pg[3], margin_ratio=round(med / pg[4], 3) if n else None),
                n_margin_in_0_to_threshold=int(np.sum((all_m > 0) & (all_m <= MARGIN_MIN))),
                sensitivity_not_adopted=dict(note="若正規化改用單一波導最大光場 max|v_i|²＝1（裕量×3，門檻不變）", n_classes=int(np.sum(all_m * 3 > MARGIN_MIN)),
                                             margin_median=float(np.median(all_m[all_m * 3 > MARGIN_MIN] * 3)) if np.any(all_m * 3 > MARGIN_MIN) else None),
                with_stage_b=dict(n_classes=int(n_b), n_ptf2=int(n_b_ptf2), n_cubic=int(n_b_cubic)),
                cpu_s=round(sum(r["cpu_s"] for v in by_class.values() for r in v), 1), classes=classes)


def verify(rows, variant):
    """從 JSON 內容重算：符號要等於最佳成員的真值表，裕量要吻合；么正變體另查 a、b 正交等長。"""
    worst = 0.0; bad = []; orth = 0.0
    for enc, row in rows.items():
        V = fields(enc)
        for c in row["classes"]:
            if not c["realized"]:
                continue
            tt = int(c["best_member"], 16)
            a = np.array([complex(*z) for z in c["a"]]); b = np.array([complex(*z) for z in c["b"]])
            D = np.abs(V @ np.conj(a)) ** 2 - np.abs(V @ np.conj(b)) ** 2
            if int(sum(int(D[x] > 0) << x for x in range(16))) != tt:
                bad.append((enc, c["rep"]))
            worst = max(worst, abs(actual_margin(a, b, V, signs(tt))[0] - c["margin"]))
            if variant == "unitary_rows":
                orth = max(orth, abs(np.vdot(a, b)), abs(np.vdot(a, a) - 1), abs(np.vdot(b, b) - 1))
    return dict(sign_mismatch=bad, max_margin_err=float(worst), max_orthonormal_err=float(orth))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=13)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--pilot", type=int, default=0, help="每種編碼只跑 N 個類（固定種子抽樣），用來估時間")
    ap.add_argument("--no-stage-b", action="store_true")
    ap.add_argument("--stage-b-wall-s", type=float, default=STAGE_B_WALL_S)
    ap.add_argument("--cache", default=None, help="LP 可行表暫存 .npz（可省略）")
    ap.add_argument("--out", default=str(OUT / "ptf2_table8_fixed.json"))
    args = ap.parse_args()
    t0 = time.perf_counter()
    variants = args.variants.split(",")
    st = selftest()
    print("selftest", st, flush=True)
    if not st["ok"]:
        sys.exit(2)
    reps, sizes, rep_of = npn_classes()
    deg = {int(r): threshold_degree(int(r)) for r in reps}
    assert all(is_ptf2(r) == (d <= 2) for r, d in deg.items())
    with get_context("spawn").Pool(args.procs) as pool:
        if args.cache and Path(args.cache).exists():
            z = np.load(args.cache); ok = {e: z[f"e{i}"] for i, e in enumerate(ENC)}; ok0 = {e: z[f"z{i}"] for i, e in enumerate(ENC)}
        else:
            ok, ok0 = feasible_tables(pool)
            if args.cache:
                np.savez_compressed(args.cache, **{f"e{i}": ok[e] for i, e in enumerate(ENC)}, **{f"z{i}": ok0[e] for i, e in enumerate(ENC)})
        t_lp = time.perf_counter() - t0
        prev = json.loads((OUT / "ptf2_table8.json").read_text(encoding="utf-8"))["rows"]
        check = {}; info = {v: {} for v in VARIANTS}
        for e in ENC:
            cl = [int(r) for r in np.unique(rep_of[ok[e]])]
            cl0 = np.unique(rep_of[ok0[e]])
            check[e] = dict(classes=len(cl), tables=int(ok[e].sum()), same_as_ptf2_table8_json=len(cl) == prev[e]["classes_upper_bound"] and int(ok[e].sum()) == prev[e]["tables_feasible"],
                            trace0_classes=int(len(cl0)), trace0_tables=int(ok0[e].sum()), trace0_ptf2=int(sum(deg[int(r)] <= 2 for r in cl0)), trace0_cubic=int(sum(deg[int(r)] == 3 for r in cl0)))
            if args.pilot:
                cl = sorted(np.random.default_rng([SEED, 99]).permutation(cl)[:args.pilot].tolist())
            for v, mask in (("unitary_rows", ok0[e]), ("free_ab", ok[e])):
                info[v][e] = {}
                for r in cl:
                    A, B, nu = choose_members(e, r, mask, rep_of)
                    info[v][e][r] = dict(degree=deg[r], A=A, B=B, n_uniq=nu)
        print("upper bound check", check, f"LP {t_lp:.0f} s", flush=True)
        assert all(c["same_as_ptf2_table8_json"] for c in check.values())

        def run(tasks, label):
            done = []; t1 = time.perf_counter()
            for i, r in enumerate(pool.imap_unordered(search_member, tasks, chunksize=1)):
                done.append(r)
                if (i + 1) % 200 == 0 or i + 1 == len(tasks):
                    w = time.perf_counter() - t1
                    print(f"{label} {i + 1}/{len(tasks)} wall {w:.0f} s eta {w / (i + 1) * (len(tasks) - i - 1):.0f} s", flush=True)
            return done

        results = {}; timing = {}
        for variant in variants:
            t1 = time.perf_counter()
            tasks = [(variant, e, r, t, "A") for e in ENC for r, c in info[variant][e].items() for t in c["A"]]
            res = run(tasks, f"{variant} A")
            timing[variant] = dict(stage_a_wall_s=round(time.perf_counter() - t1, 1), n_members=len(tasks))
            if not args.no_stage_b:
                best = {}
                for r in res:
                    best[(r["enc"], r["rep"])] = max(best.get((r["enc"], r["rep"]), -9.0), r["margin"])
                t1 = time.perf_counter(); n_b = 0; rounds = 0; stopped = False
                for i in range(0, STAGE_B_CAP, STAGE_B_ROUND):
                    if time.perf_counter() - t1 > args.stage_b_wall_s:
                        stopped = True
                        break
                    tasks = [(variant, e, r, t, "B") for e in ENC for r, c in info[variant][e].items() if best.get((e, r), -9.0) <= MARGIN_MIN for t in c["B"][i:i + STAGE_B_ROUND]]
                    if not tasks:
                        break
                    got = run(tasks, f"{variant} B round {rounds}")
                    res += got; n_b += len(tasks); rounds += 1
                    for r in got:
                        best[(r["enc"], r["rep"])] = max(best[(r["enc"], r["rep"])], r["margin"])
                timing[variant].update(stage_b_wall_s=round(time.perf_counter() - t1, 1), stage_b_n_members=n_b, stage_b_rounds=rounds, stage_b_stopped_by_wall_limit=stopped)
            results[variant] = res
    out = dict(
        method=dict(seed=SEED, R=1.0, n_starts_per_member=N_STARTS, n_members_per_class=N_MEMBERS, margin_threshold=MARGIN_MIN, stage_b_cap=STAGE_B_CAP, stage_b_round=STAGE_B_ROUND, stage_b_wall_s=args.stage_b_wall_s,
                    betas=list(BETAS), lbfgs_maxiter=LBFGS_MAXITER, n_polish=N_POLISH, slsqp_maxiter=SLSQP_MAXITER, procs=args.procs, pilot=args.pilot,
                    margin_definition="min_x s(x)D(x) / ((|a|^2+|b|^2) * max_x ||v(x)||^2); max||v||^2 = 3 for all six encodings",
                    class_margin="max over tried members; median over realized classes; class realized if margin > threshold (stage A only)",
                    members="feasible members of the class, output-complement duplicates removed, fixed-seed random order, first n_members = stage A; stage B = further members in rounds, only for classes still unrealized, up to stage_b_cap per class and stage_b_wall_s per variant, reported separately; unitary_rows candidates must also pass the tr M = 0 LP (necessary condition)",
                    optimizer="logsumexp smooth min, L-BFGS-B over betas, rank by non-smooth margin, top n_polish refined by SLSQP epigraph, final value always from actual_margin(a,b)",
                    variants=dict(unitary_rows="a†, b† are two rows of a 3x3 unitary (task statement); 3-MZI Reck triangle ports (0,1),(1,2),(0,1), T(theta,phi) as in ptf2_check",
                                  free_ab="a, b in C^3 unconstrained (literal page method text)"),
                    fixed_before_results=True),
        revisions=REVISIONS, selftest=st, upper_bound_check=check, timing=timing, variants={})
    for variant in variants:
        rows = {}
        for e in ENC:
            by = {}
            for r in results[variant]:
                if r["enc"] == e:
                    by.setdefault(r["rep"], []).append(r)
            rows[e] = summarize(e, info[variant][e], by, variant)
        out["variants"][variant] = dict(rows=rows, verification=verify(rows, variant))
        for e, r in rows.items():
            print(variant, e, {k: r[k] for k in ("upper_bound_classes", "n_classes", "n_ptf2", "n_cubic", "margin_median", "diff_vs_page", "with_stage_b", "n_margin_in_0_to_threshold")}, flush=True)
        print(variant, "verification", out["variants"][variant]["verification"], flush=True)
    out["elapsed_s"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("elapsed_s", out["elapsed_s"], flush=True)


if __name__ == "__main__":
    main()
