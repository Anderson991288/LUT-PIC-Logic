r"""PTF2 數學驗證——report/PTF2.html 頁內數字的獨立重算。

用途（全部自行實作，不 import 本專案或其他專案的模組）：
  1. 多線性展開：在布林立方體上 D(x) 可唯一寫成 Σ_S c_S Π_{i∈S} x_i（16 個係數）。對每種光路隨機取 200 組參數，
     解出 c_S，記錄各次數係數的最大值（除以 max|D|）。三次、四次項應只剩浮點誤差（10⁻¹⁵ 等級）：
     (a) 3142132＋R＝3、0.9 dB／MZI 的 Da、Db（本專案的判讀量）；(b) B7 磚牆＋R（頁內表 3 第 1 列）；(c) 兩顆 B7 全光串接；
     (d) 任意複數調變器＋12 埠含損耗網路＋8 偵測器任意加權；(e) 每個輸入扇出 3 個調變器；(f) x1、x2 調變器串在同一路光（三次項應出現）。
     另以 11 個係數（≤ 二次）最小平方擬合 Da、Db，殘差應為數值誤差。
  2. NPN 等價類：輸入置換（24）×輸入反相（16）×輸出反相（2），4 輸入共 222 類；每類代表取類中最小整數。
  3. 門檻次數：對每類代表以 LP 檢查是否存在次數 ≤ d 的多線性多項式使 s(x)·D(x) ≥ 1（d＝0…4）；
     統計各次數的類數與真值表張數（參考：1／2、14／1,880、166／55,692、40／7,960、1／2；PTF2 以下 181 類、57,574 張）。
  4. PTF2 逐張 LP（65,536 張，與類別統計交叉核對）。
  5. Cover 上界：n 輸入時 PTF2 張數 ≤ 2·Σ_{k<N} C(2ⁿ−1, k)，N＝1＋n＋n(n−1)/2（n＝4 時 61,654）。
  6. XOR4 不可能：任何二次式 Σ_x s(x)D(x)＝0（隨機光路數值核對）；B7 對 XOR4 最多判對幾組（LP 逐一去掉列）。
  7. 串聯 π 相位調變做 XNOR4：E＝Π(1−2x_i)，D＝2Re(E·R*)，各次數係數 2、−4、8、−16、32。
  8. 頁面核對：report/PTF2.html 是否含本檔算出的關鍵數字，且無本機路徑或舊專案名稱。
輸入：無（隨機種子 2026）；report/PTF2.html（核對用）。
輸出：out/ptf2.json。
執行：.\lab design\ptf2\ptf2_check.py
"""
import itertools
import json
import re
import sys
import time
from math import comb, log2
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
HTML = HERE.parents[1] / "report" / "PTF2.html"
SEED, NRAND = 2026, 200
K = 4
XS = np.arange(16)
BITS = ((XS[:, None] >> np.arange(K)) & 1)                                   # (16, 4)：x_{b+1}＝第 b 位元
SUBSETS = [S for d in range(5) for S in itertools.combinations(range(K), d)]  # 16 個單項式，依次數排序
MONO = np.array([[all(BITS[x, i] for i in S) for S in SUBSETS] for x in range(16)], float)   # (16, 16) 多線性基底
DEG = np.array([len(S) for S in SUBSETS])
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
B7_OPS = [0, 3, 1, 0, 2, 1, 3]            # 原 B7 磚牆：每顆 MZI 的上方軌（0 起算），o2−o4 判讀
M7A_OPS = [2, 0, 3, 1, 0, 2, 1]           # 3142132


def T(th, ph, amp=1.0):
    return amp * (H @ np.diag([np.exp(1j * th), 1]) @ H @ np.diag([np.exp(1j * ph), 1]))


def chain(ops, p, n=5, amp=1.0):
    U = np.eye(n, dtype=complex)
    for q, m in enumerate(ops):
        E = np.eye(n, dtype=complex); E[m:m + 2, m:m + 2] = T(p[2 * q], p[2 * q + 1], amp); U = E @ U
    return U


def haar(n, rng):
    Z = (rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / np.sqrt(2)
    Q, R = np.linalg.qr(Z)
    return Q * (np.diag(R) / np.abs(np.diag(R)))


def coeffs(D):
    """16 個 D 值 → 16 個多線性係數（依 SUBSETS 次序）。"""
    return np.linalg.solve(MONO, D)


def deg_max(D):
    c = np.abs(coeffs(D)) / max(np.max(np.abs(D)), 1e-300)
    return [float(c[DEG == d].max()) for d in range(1, 5)]


def circuits(rng):
    """每種光路回傳一組隨機參數下 16 個輸入的 D（可能多個判讀量）。"""
    X = BITS.astype(float)
    out = {}
    # (a) 3142132＋R＝3、0.9 dB：Da、Db
    U = chain(M7A_OPS, rng.uniform(0, 2 * np.pi, 14), amp=10 ** (-0.9 / 20))
    V = np.column_stack([X, np.full(16, 3.0)]).astype(complex)
    P = np.abs(V @ U.T) ** 2
    out["3142132+R, 0.9 dB/MZI: Da=P2-P4"] = P[:, 1] - P[:, 3]
    out["3142132+R, 0.9 dB/MZI: Db=P4-P3"] = P[:, 3] - P[:, 2]
    # (b) B7＋R（單級）：o2−o4
    U1 = chain(B7_OPS, rng.uniform(0, 2 * np.pi, 14))
    P = np.abs(V @ U1.T) ** 2
    out["B7+R single stage: P2-P4"] = P[:, 1] - P[:, 3]
    # (c) 兩顆 B7 全光串接
    U2 = chain(B7_OPS, rng.uniform(0, 2 * np.pi, 14)) @ U1
    P = np.abs(V @ U2.T) ** 2
    out["two B7 cascaded: P2-P4"] = P[:, 1] - P[:, 3]
    # (d) 任意複數調變器＋12 埠含損耗網路＋8 偵測器任意加權
    t0 = rng.normal(size=4) + 1j * rng.normal(size=4); t1 = rng.normal(size=4) + 1j * rng.normal(size=4)
    tmod = t0[None, :] + (t1 - t0)[None, :] * X                       # (16, 4)
    v = np.zeros((16, 12), complex); v[:, :4] = tmod; v[:, 4] = 3.0
    W = 0.5 * haar(12, rng)
    P = np.abs(v @ W.T) ** 2
    out["random modulators + 12-port lossy network + 8 weighted detectors"] = P[:, :8] @ rng.normal(size=8)
    # (e) 每個輸入扇出 3 個並聯調變器，13 埠
    t0 = rng.normal(size=12) + 1j * rng.normal(size=12); t1 = rng.normal(size=12) + 1j * rng.normal(size=12)
    Xf = np.repeat(X, 3, axis=1)
    v = np.zeros((16, 13), complex); v[:, :12] = t0 + (t1 - t0) * Xf; v[:, 12] = 3.0
    P = np.abs(v @ haar(13, rng).T) ** 2
    out["fan-out: each input drives 3 modulators (13 ports)"] = P[:, 0] - P[:, 1]
    # (f) x1、x2 調變器串在同一路光（違反條件 1）
    t0 = rng.normal(size=4) + 1j * rng.normal(size=4); t1 = rng.normal(size=4) + 1j * rng.normal(size=4)
    tm = t0 + (t1 - t0) * X
    v = np.zeros((16, 5), complex); v[:, 0] = tm[:, 0] * tm[:, 1]; v[:, 1] = tm[:, 2]; v[:, 2] = tm[:, 3]; v[:, 3] = 3.0
    P = np.abs(v @ haar(5, rng).T) ** 2
    out["serial: x1 and x2 modulators on the same path"] = P[:, 0] - P[:, 1]
    return out


def multilinear_table(rng):
    acc = {}
    for _ in range(NRAND):
        for k, D in circuits(rng).items():
            acc.setdefault(k, []).append(deg_max(D))
    rows = {}
    for k, v in acc.items():
        v = np.array(v).max(0)
        rows[k] = dict(deg1=float(v[0]), deg2=float(v[1]), deg3=float(v[2]), deg4=float(v[3]), cubic_or_higher_is_zero=bool(max(v[2], v[3]) < 1e-12))
    return rows


def quad_fit(rng):
    """Da、Db 用 11 個係數（≤ 二次）最小平方擬合的最大殘差（200 組隨機 3142132 相位）。"""
    A = MONO[:, DEG <= 2]
    worst = 0.0
    for _ in range(NRAND):
        c = circuits(rng)
        for k in ("3142132+R, 0.9 dB/MZI: Da=P2-P4", "3142132+R, 0.9 dB/MZI: Db=P4-P3"):
            D = c[k]; cf = np.linalg.lstsq(A, D, rcond=None)[0]
            worst = max(worst, float(np.max(np.abs(A @ cf - D))) / float(np.max(np.abs(D))))
    return worst


# ---------- NPN 類 ----------
def npn_classes():
    tts = np.arange(65536, dtype=np.int64)
    b = (tts[:, None] >> XS) & 1                                           # (65536, 16)
    best = tts.copy()
    for perm in itertools.permutations(range(K)):
        for neg in range(1 << K):
            bb = BITS[:, list(perm)] ^ ((neg >> np.arange(K)) & 1)
            src = (bb << np.arange(K)).sum(1)                              # 變換後輸入 x 對應的原輸入
            v = (b[:, src] << XS).sum(1)
            best = np.minimum(best, np.minimum(v, 65535 ^ v))
    reps, sizes = np.unique(best, return_counts=True)
    return reps, sizes, best


def threshold_degree(t):
    s = np.where((t >> XS) & 1, 1.0, -1.0)
    for d in range(5):
        A = MONO[:, DEG <= d]
        r = linprog(np.zeros(A.shape[1]), A_ub=-(s[:, None] * A), b_ub=-np.ones(16), bounds=[(None, None)] * A.shape[1], method="highs")
        if r.status == 0:
            return d
    return 5


def is_ptf2(t):
    s = np.where((t >> XS) & 1, 1.0, -1.0)
    A = MONO[:, DEG <= 2]
    r = linprog(np.zeros(A.shape[1]), A_ub=-(s[:, None] * A), b_ub=-np.ones(16), bounds=[(None, None)] * A.shape[1], method="highs")
    return r.status == 0


def cover_bound(n):
    N = 1 + n + n * (n - 1) // 2
    return N, 2 * sum(comb(2 ** n - 1, k) for k in range(N))


def xor4_best_agreement():
    """B7（任何二次門檻）對 XOR4 最多判對幾組：逐一去掉 r 列再做 LP。"""
    s = np.where((0x6996 >> XS) & 1, 1.0, -1.0)
    A = MONO[:, DEG <= 2]
    for r in range(0, 4):
        for drop in itertools.combinations(range(16), r):
            keep = [x for x in range(16) if x not in drop]
            res = linprog(np.zeros(A.shape[1]), A_ub=-(s[keep, None] * A[keep]), b_ub=-np.ones(len(keep)), bounds=[(None, None)] * A.shape[1], method="highs")
            if res.status == 0:
                return 16 - r
    return None


def html_check(nums, deg_rep=None):
    if not HTML.exists():
        return dict(available=False)
    t = HTML.read_text(encoding="utf-8")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", body)
    found = {k: (str(v) in txt or f"{v:,}" in txt) for k, v in nums.items()}
    bad = sorted(set(re.findall(r"[A-Za-z]:\\[^\s\"<]*|Lab0\w*", t)))
    res = dict(available=True, file="report/PTF2.html", numbers_found=found, all_found=all(found.values()),
               forbidden_strings=bad, clean=not bad)
    m = re.search(r"const DEG = (\{.*?\});", t, flags=re.S)             # 頁面互動檢查內嵌的「類代表 → 門檻次數」表
    if m and deg_rep is not None:
        page = {int(k): int(v) for k, v in json.loads(m.group(1)).items()}
        mism = [dict(rep=f"0x{r:04X}", page=page.get(r), ours=d) for r, d in deg_rep.items() if page.get(r) != d]
        res["embedded_degree_table"] = dict(n_page=len(page), n_ours=len(deg_rep), same_reps=set(page) == set(deg_rep),
                                            n_mismatch=len(mism), mismatches=mism[:20], match=not mism and set(page) == set(deg_rep))
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    rng = np.random.default_rng(SEED)
    res = dict(seed=SEED, n_random=NRAND)
    res["multilinear_max_coeff"] = multilinear_table(rng)
    res["quad_fit_max_residual_rel"] = quad_fit(np.random.default_rng(SEED + 1))
    print("多線性係數（相對 max|D|）：")
    for k, v in res["multilinear_max_coeff"].items():
        print(f"  {k}: 1次 {v['deg1']:.3f} 2次 {v['deg2']:.3f} 3次 {v['deg3']:.1e} 4次 {v['deg4']:.1e}")
    print(f"Da、Db 的 11 係數擬合最大相對殘差 {res['quad_fit_max_residual_rel']:.1e}")

    reps, sizes, rep_of = npn_classes()
    res["npn"] = dict(n_classes=int(len(reps)), reference_n_classes=222, sizes_sum=int(sizes.sum()))
    deg_rep = {int(r): threshold_degree(int(r)) for r in reps}
    by_deg = {}
    for r, sz in zip(reps, sizes):
        d = deg_rep[int(r)]; by_deg.setdefault(d, [0, 0]); by_deg[d][0] += 1; by_deg[d][1] += int(sz)
    res["threshold_degree"] = {str(d): dict(classes=v[0], tables=v[1]) for d, v in sorted(by_deg.items())}
    res["threshold_degree"]["reference"] = {"0": [1, 2], "1": [14, 1880], "2": [166, 55692], "3": [40, 7960], "4": [1, 2]}
    ptf2_classes = sum(v[0] for d, v in by_deg.items() if d <= 2); ptf2_tables = sum(v[1] for d, v in by_deg.items() if d <= 2)
    res["ptf2_by_class"] = dict(classes=ptf2_classes, tables=ptf2_tables, reference=dict(classes=181, tables=57574),
                                fraction_pct=round(ptf2_tables / 655.36, 1))
    examples = {"XOR2 0x6666": 0x6666, "MUX 0xCACA": 0xCACA, "AND4 0x8000": 0x8000, "XOR3 class 0x0069": 0x0069, "XOR4 0x6996": 0x6996, "XNOR4 0x9669": 0x9669}
    res["examples_degree"] = {k: deg_rep[int(rep_of[v])] for k, v in examples.items()}
    print("NPN 類", res["npn"], "門檻次數", res["threshold_degree"], "PTF2", res["ptf2_by_class"], res["examples_degree"])

    t1 = time.perf_counter()
    flags = np.array([is_ptf2(t) for t in range(65536)])
    by_class = np.array([deg_rep[int(r)] <= 2 for r in rep_of])
    res["ptf2_direct"] = dict(n_ptf2=int(flags.sum()), n_non_ptf2=int((~flags).sum()), elapsed_s=round(time.perf_counter() - t1, 1),
                              matches_class_count=bool(flags.sum() == ptf2_tables), per_table_agreement_with_class=bool((flags == by_class).all()))
    np.save(OUT / "ptf2_flags.npy", flags)
    print("逐張 LP", res["ptf2_direct"])

    res["cover_bound"] = {str(n): dict(N=cover_bound(n)[0], bound=cover_bound(n)[1], total=2 ** (2 ** n),
                                       log2_bound=round(log2(cover_bound(n)[1]), 1)) for n in range(2, 11)}
    res["cover_bound_n4_reference"] = 61654
    # XOR4：Σ s(x)D(x)＝0（隨機 B7），與最多判對幾組
    rng2 = np.random.default_rng(SEED + 2)
    s = np.where((0x9669 >> XS) & 1, 1.0, -1.0)
    sums = [float(np.sum(s * circuits(rng2)["B7+R single stage: P2-P4"])) for _ in range(50)]
    res["xor4"] = dict(max_abs_sum_sD_random_B7=float(np.max(np.abs(sums))), best_agreement_of_16=xor4_best_agreement(), reference_best_agreement=14)
    # 串聯 π 相位：XNOR4
    E = np.prod(1 - 2 * BITS, axis=1).astype(float)
    D = 2 * E                                                              # 2·Re(E·R*)，R＝1
    c = coeffs(D)
    tt = int(sum(int(D[x] > 0) << x for x in range(16)))
    res["serial_pi_xnor4"] = dict(D_values=sorted(set(D.tolist())), truth_hex=f"0x{tt:04X}", is_xnor4=tt == 0x9669,
                                  coeff_by_degree=[float(c[DEG == d][0]) for d in range(5)], reference=[2, -4, 8, -16, 32])
    nums = dict(classes=222, ptf2_classes=181, ptf2_tables=57574, all_tables=65536, non_ptf2=7962, deg1=1880, deg2=55692, deg3=7960,
                cover4=61654, pct=87.9)
    res["html_check"] = html_check(nums, deg_rep)
    res["elapsed_s"] = round(time.perf_counter() - t0, 1)
    checks = dict(cubic_zero=all(v["cubic_or_higher_is_zero"] for k, v in res["multilinear_max_coeff"].items() if "serial" not in k),
                  serial_cubic_nonzero=res["multilinear_max_coeff"]["serial: x1 and x2 modulators on the same path"]["deg3"] > 1e-3,
                  npn_222=res["npn"]["n_classes"] == 222, ptf2_181=ptf2_classes == 181, ptf2_57574=ptf2_tables == 57574,
                  direct_57574=res["ptf2_direct"]["n_ptf2"] == 57574, cover_61654=res["cover_bound"]["4"]["bound"] == 61654,
                  xor4_14=res["xor4"]["best_agreement_of_16"] == 14, xnor4_serial=res["serial_pi_xnor4"]["is_xnor4"],
                  html_numbers=res["html_check"].get("all_found", False), html_clean=res["html_check"].get("clean", False),
                  html_degree_table=res["html_check"].get("embedded_degree_table", {}).get("match", False))
    res["checks"] = checks; res["all_ok"] = all(checks.values())
    (OUT / "ptf2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Cover n=4", res["cover_bound"]["4"], "XOR4", res["xor4"], "串聯", res["serial_pi_xnor4"]["coeff_by_degree"])
    print("頁面核對", res["html_check"])
    print("checks", checks, "→", "本次通過" if res["all_ok"] else "本次未通過", f"{res['elapsed_s']} s")
    sys.exit(0 if res["all_ok"] else 1)


if __name__ == "__main__":
    main()
