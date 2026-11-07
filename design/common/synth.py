"""共用的相位合成（M1 s2 起）：給定電路與目標真值表，找出讓判讀 margin 最大的相位。

  margin m＝min_i s_i·ΔP_i（s_i＝+1 應判 1、−1 應判 0；ΔP＝P(讀取埠 a) − P(讀取埠 b)）。
  求 max m s.t. s_i·ΔP_i ≥ m（SLSQP），多起點，起點種子 seed0＋k；最後以實際相位重算 m。
輸出：無（被其他程式 import）。
"""
import numpy as np
from scipy.optimize import minimize


def deltas(U, vecs, read):
    """vecs：每列一組輸入光場；回傳每組的 ΔP。"""
    P = np.abs(vecs @ U.T) ** 2
    return P[:, read[0]] - P[:, read[1]]


def best_margin(make_u, n_par, vecs, read, signs, starts, seed0=700, maxiter=400):
    """回傳 (m, 參數)；參數取 mod 2π。"""
    def cons(z):
        return signs * deltas(make_u(z[:-1]), vecs, read) - z[-1]

    best = (-np.inf, None)
    for k in range(starts):
        rng = np.random.default_rng(seed0 + k)
        x0 = rng.uniform(0, 2 * np.pi, n_par)
        z0 = np.append(x0, np.min(signs * deltas(make_u(x0), vecs, read)))
        r = minimize(lambda z: -z[-1], z0, method="SLSQP", constraints=[dict(type="ineq", fun=cons)],
                     options=dict(maxiter=maxiter, ftol=1e-10))
        m = float(np.min(signs * deltas(make_u(r.x[:-1]), vecs, read)))   # 以實際值重算，不信任 z[-1]
        if m > best[0]:
            best = (m, r.x[:-1] % (2 * np.pi))
    return best
