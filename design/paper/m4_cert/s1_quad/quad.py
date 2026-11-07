r"""論文 M4 s1：二次式判讀——偵測功率差 D 是輸入包絡的精確二次式 D(x)＝d0＋lᵀx＋xᵀQx（草稿式 6）。

用途：
  1. 由 B7 的傳遞矩陣 U（M3 s2 的 0.9 dB／MZI 相位）直接寫出 d0、l、Q：
     輸入向量 v＝[x1..x4, R]（實數包絡），M＝u2ᴴu2 − u4ᴴu4（u2、u4 是讀取埠那一列），D＝vᵀ Re(M) v，
     所以 d0＝R²·Re M55、l＝2R·Re M[:4,5]（參考光與資料的干涉）、Q＝Re M[:4,:4]（資料之間的干涉）。
  2. 三種輸入核對 D 與逐點模擬（先算場再取平方）的差：16 組字、2000 組 [0,1]⁴ 的隨機中間值、
     M3 s3 的時域波形（Euler 序列＋768 個隨機符號，對齊與 41 點延遲盒中的 4 個角落）。
  3. 拆解：(a) 把 Q 拿掉、只留 d0＋lᵀx 時 16 組字的 margin；(b) 函數本身是否線性可分（線性規劃找 w、c 使 b_s(wᵀx_s＋c) ≥ 1）——
     線性可分的函數換一組 d0、l 原則上也能做出來，不可分的（SOP2、XOR2）一定要靠 Q 的交叉項。
輸入：design/paper/m3_align/s2_synth/out/synth.json、design/paper/m3_align/s3_detail/detail.py（與 M3 s3 相同的包絡）、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：design/paper/m4_cert/s1_quad/out/quad.json。
執行：.\lab design\paper\m4_cert\s1_quad\quad.py（約 10 秒）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s3_detail"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s2_synth"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import linprog                                   # noqa: E402

import detail as DT                                                  # noqa: E402
import paths                                                         # noqa: E402
import synth as SY                                                   # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

STEP = "paper/m4_cert/s1_quad"
FUNCS = ("AND4", "OR4", "MAJ4", "TH2", "AND3", "AND2", "AND2'", "SOP2", "XOR2")
TIME_FUNCS = DT.FUNCS                                                # AND4、MAJ4、XOR2
N_RAND, SEED = 2000, 4100
TOL = 1e-9


def unitary(fn):
    ph = json.loads(paths.OUT("paper/m3_align/s2_synth", "synth.json").read_text(encoding="utf-8"))["functions"][fn]["lossy"]
    return DT.b7(np.array(ph["theta"]), np.array(ph["phi"]), 10 ** (-DT.D.SETTINGS["mzi_loss_db"] / 20))


def coeffs(U):
    u2, u4 = U[READ[0]], U[READ[1]]
    M = np.real(np.outer(u2.conj(), u2) - np.outer(u4.conj(), u4))    # D＝vᵀ Re(M) v（v 為實數）
    return R_AMP ** 2 * M[4, 4], 2 * R_AMP * M[:4, 4], M[:4, :4]


def direct(U, X):
    """逐點：先算輸出場，再取平方相減。X 的每列是 4 路包絡。"""
    v = np.hstack([X.astype(complex), np.full((len(X), 1), R_AMP)])
    y = v @ U.T
    return np.abs(y[:, READ[0]]) ** 2 - np.abs(y[:, READ[1]]) ** 2


def quad(d0, l, Q, X):
    return d0 + X @ l + np.einsum("ni,ij,nj->n", X, Q, X)


def separable(b):
    """16 組字在 4 維空間是否能用一個平面分開（線性規劃可行即可分）。"""
    A = -b[:, None] * np.hstack([DT.BITS.astype(float), np.ones((16, 1))])
    r = linprog(np.zeros(5), A_ub=A, b_ub=-np.ones(16), bounds=[(None, None)] * 5, method="highs")
    return bool(r.status == 0)


def main():
    rng = np.random.default_rng(SEED)
    Xr = rng.uniform(0, 1, (N_RAND, 4))
    W = DT.BITS.astype(float)
    out, worst = {}, 0.0
    for fn in FUNCS:
        U = unitary(fn)
        d0, l, Q = coeffs(U)
        e_word = float(np.max(np.abs(direct(U, W) - quad(d0, l, Q, W))))
        e_rand = float(np.max(np.abs(direct(U, Xr) - quad(d0, l, Q, Xr))))
        lin = d0 + W @ l
        qq = np.einsum("ni,ij,nj->n", W, Q, W)
        b = np.array([1.0 if SY.FUNCS[fn](w) else -1.0 for w in DT.BITS])
        o = dict(d0=round(float(d0), 6), l=np.round(l, 6).tolist(), Q=np.round(Q, 6).tolist(),
                 l_norm=round(float(np.linalg.norm(l)), 4), Q_norm=round(float(np.linalg.norm(Q, 2)), 4),
                 err_words=e_word, err_random=e_rand, margin=round(float(np.min(b * (lin + qq))), 4),
                 margin_linear_only=round(float(np.min(b * lin)), 4), linearly_separable=separable(b),
                 words=dict(D=np.round(lin + qq, 4).tolist(), linear=np.round(lin, 4).tolist(), quadratic=np.round(qq, 4).tolist()))
        worst = max(worst, e_word, e_rand)
        out[fn] = o
    # 時域波形：與 M3 s3 相同的模擬器與包絡
    S = DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    sim = DT.Sim(DT.sequence("euler"), S["edge_full_ps"], 0.5, A, 10 ** (S["pu_dbm"] / 10) * 1e-3, False)
    time_err = {}
    corners = [np.zeros(4), np.array([-1, -1, 1, 1]) * DT.HALF_BOX, np.array([-1, 1, -1, 1]) * DT.HALF_BOX,
               np.array([1, -1, -1, 1]) * DT.HALF_BOX, np.ones(4) * DT.HALF_BOX]
    for fn in TIME_FUNCS:
        U = unitary(fn)
        d0, l, Q = coeffs(U)
        e = 0.0
        frac = []
        for p in corners:
            X = np.stack([sim.envelope(j, p[j]) for j in range(4)], axis=1)
            e = max(e, float(np.max(np.abs(direct(U, X) - quad(d0, l, Q, X)))))
            mid = np.any((X > 1e-6) & (X < 1 - 1e-6), axis=1)
            frac.append(float(mid.mean()))
        time_err[fn] = dict(err=e, n_samples=int(len(sim.t) * len(corners)), frac_intermediate=round(float(np.mean(frac)), 3))
        out[fn]["err_time"] = e
        worst = max(worst, e)
    checks = dict(exact_words=all(v["err_words"] < TOL for v in out.values()),
                  exact_random=all(v["err_random"] < TOL for v in out.values()),
                  exact_time=all(v["err"] < TOL for v in time_err.values()),
                  q_symmetric=all(np.allclose(v["Q"], np.array(v["Q"]).T) for v in out.values()),
                  not_separable_are_sop2_xor2=sorted(f for f, v in out.items() if not v["linearly_separable"]) == ["SOP2", "XOR2"],
                  not_separable_need_Q=all(v["margin_linear_only"] < 0 for v in out.values() if not v["linearly_separable"]))
    res = dict(tol=TOL, n_random=N_RAND, seed=SEED, functions=out, time=time_err, max_err=worst,
               frac_intermediate=time_err["AND4"]["frac_intermediate"], checks=checks)
    path = paths.OUT(STEP, "quad.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, v in out.items():
        print(f"{fn}：d0 {v['d0']:+.3f}｜‖l‖ {v['l_norm']:.3f}｜‖Q‖ {v['Q_norm']:.3f}｜margin {v['margin']:.3f}、拿掉 Q {v['margin_linear_only']:+.3f}"
              f"｜線性可分 {v['linearly_separable']}｜誤差 字 {v['err_words']:.1e}、隨機 {v['err_random']:.1e}"
              + (f"、時域 {v['err_time']:.1e}" if "err_time" in v else ""))
    print(f"時域取樣點中至少一路在轉態（0 < x < 1）的比例：{res['frac_intermediate']:.1%}")
    print(f"最大誤差 {worst:.1e} P_u｜檢查：", checks)
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
