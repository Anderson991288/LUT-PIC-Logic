"""（v2：輸入為 E+／E− 二相位光，R＝+E）加速版合成：批次向量化的光路計算與批次數值梯度。
光路：n 條波導、相鄰 2×2 MZI（ops[q]＝上方波導編號，0 起算），MZI 模型同 common/mzi.py（T2_closed 乘損耗振幅）。
判讀：
  dual   y = [P_a > P_b] ∧ [P_b > P_c]（order=(a,b,c)）
  single y = [P_a > P_b]（order=(a,b)）
用法：synth(f, Arch(...), nst, seed) → (margin, phases)。"""
import numpy as np
from scipy.optimize import minimize

X4 = np.array([[(x >> b) & 1 for b in range(4)] for x in range(16)], float)
S4 = 1 - 2 * X4                                   # v2：二相位輸入的光場符號（位元 0＝+E、1＝−E）


class Arch:
    def __init__(self, ops, n=5, r_ports=(4,), r_amp=3.0, loss_db=0.9, order=(1, 3, 2), kind="dual"):
        self.ops, self.n, self.order, self.kind = list(ops), n, tuple(order), kind
        self.amp = 10 ** (-loss_db / 20) if loss_db else 1.0
        dp = [k for k in range(n) if k not in r_ports]
        V = np.zeros((16, n), complex)
        if len(dp) == 4: V[:, dp] = S4      # E±：位元 0 → +1、1 → −1；其他尺寸由呼叫端自行設定 V
        for rp in r_ports: V[:, rp] = r_amp
        self.V = V
        self.nph = 2 * len(self.ops)

    @classmethod
    def from_code(cls, code, **kw):
        return cls([int(c) - 1 for c in code], **kw)

    def powers(self, P):
        """P：(B, nph) → 各輸出功率 (B, 16, n)"""
        B = P.shape[0]; n = self.n
        U = np.zeros((B, n, n), complex); U[:, np.arange(n), np.arange(n)] = 1
        for q, m in enumerate(self.ops):
            th, ph = P[:, 2 * q], P[:, 2 * q + 1]
            e = 1j * self.amp * np.exp(0.5j * th); s, c = np.sin(th / 2), np.cos(th / 2); ep = np.exp(1j * ph)
            t11, t12, t21, t22 = (e * ep * s)[:, None], (e * c)[:, None], (e * ep * c)[:, None], (-e * s)[:, None]
            Ui, Uj = U[:, m].copy(), U[:, m + 1]
            U[:, m] = t11 * Ui + t12 * Uj
            U[:, m + 1] = t21 * Ui + t22 * Uj
        E = np.matmul(self.V, U.transpose(0, 2, 1))     # (B,16,n)
        return E.real ** 2 + E.imag ** 2

    def margins(self, P, ins, s=None):
        """(B, 16) 的逐點裕量；s 給定時為平滑版"""
        W = self.powers(P)
        if self.kind == "single":
            a, b = self.order
            return np.where(ins, 1.0, -1.0) * (W[:, :, a] - W[:, :, b])
        a, b, c = self.order
        Da, Db = W[:, :, a] - W[:, :, b], W[:, :, b] - W[:, :, c]
        if s is None:
            return np.where(ins, np.minimum(Da, Db), np.maximum(-Da, -Db))
        return np.where(ins, -np.logaddexp(-s * Da, -s * Db) / s, np.logaddexp(-s * Da, -s * Db) / s)


def _objective(arch, ins, s):
    eye = np.eye(arch.nph) * 1e-6
    def f(p):
        P = np.vstack([p, p + eye])                       # 1 + nph 組一次算完
        m = arch.margins(P, ins, s)
        z = -s * m; zmax = z.max(1, keepdims=True)
        v = (zmax[:, 0] + np.log(np.exp(z - zmax).sum(1)))  # log-sum-exp，數值穩定
        return v[0], (v[1:] - v[0]) / 1e-6
    return f


def synth(f, arch, nst=24, seed=0, s=40.0, stop=None, maxiter=800):
    """回傳 (最佳真實裕量, 相位)。stop：達到此裕量即停止其他起點。"""
    ins = np.array([f >> x & 1 for x in range(16)], bool)
    obj = _objective(arch, ins, s)
    rng = np.random.default_rng(seed); best = (-np.inf, None)
    for _ in range(nst):
        r = minimize(obj, rng.uniform(0, 2 * np.pi, arch.nph), jac=True, method="BFGS", options=dict(maxiter=maxiter))
        m = arch.margins(r.x[None], ins).min()
        if m > best[0]: best = (float(m), r.x)
        if stop is not None and best[0] >= stop: break
    return best


def _multi_objective(arch, ins, s, K):
    nph = arch.nph; eye = np.eye(nph) * 1e-6
    def f(z):
        Pk = z.reshape(K, nph)
        P = np.concatenate([Pk[:, None, :], Pk[:, None, :] + eye[None]], 1).reshape(-1, nph)
        m = arch.margins(P, ins, s)
        zz = -s * m; zm = zz.max(1, keepdims=True)
        v = (zm[:, 0] + np.log(np.exp(zz - zm).sum(1))).reshape(K, nph + 1)
        return v[:, 0].sum(), ((v[:, 1:] - v[:, :1]) / 1e-6).ravel()
    return f


def synth_batch(f, arch, nst=24, seed=0, s=40.0, polish=3, maxiter=2000):
    """K 個起點同時以 L-BFGS 最佳化（可分離目標），再取前 polish 名以個別 BFGS 精修。"""
    ins = np.array([f >> x & 1 for x in range(16)], bool)
    rng = np.random.default_rng(seed)
    z0 = rng.uniform(0, 2 * np.pi, nst * arch.nph)
    r = minimize(_multi_objective(arch, ins, s, nst), z0, jac=True, method="L-BFGS-B", options=dict(maxiter=maxiter, maxcor=30))
    Pk = r.x.reshape(nst, arch.nph)
    mk = arch.margins(Pk, ins).min(1)
    obj = _objective(arch, ins, s); best = (-np.inf, None)
    for k in np.argsort(-mk)[:polish]:
        rr = minimize(obj, Pk[k], jac=True, method="BFGS", options=dict(maxiter=800))
        m = arch.margins(rr.x[None], ins).min()
        cand = (float(m), rr.x) if m >= mk[k] else (float(mk[k]), Pk[k])
        if cand[0] > best[0]: best = cand
    return best


# ---------- numba 版：光路、平滑裕量與數值梯度整段編譯 ----------
import numba as nb


@nb.njit(cache=True, fastmath=False)
def _pow_nb(p, ops, V, amp, n, W):
    """單組相位 → W[16, n]（輸出功率）"""
    U = np.zeros((n, n), np.complex128)
    for i in range(n): U[i, i] = 1.0
    for q in range(ops.shape[0]):
        m = ops[q]; th = p[2 * q]; ph = p[2 * q + 1]
        e = 1j * amp * np.exp(0.5j * th); s = np.sin(th / 2); c = np.cos(th / 2); ep = np.exp(1j * ph)
        t11 = e * ep * s; t12 = e * c; t21 = e * ep * c; t22 = -e * s
        for k in range(n):
            ui = U[m, k]; uj = U[m + 1, k]
            U[m, k] = t11 * ui + t12 * uj
            U[m + 1, k] = t21 * ui + t22 * uj
    for x in range(16):
        for j in range(n):
            acc = 0j
            for k in range(n): acc += U[j, k] * V[x, k]
            W[x, j] = acc.real * acc.real + acc.imag * acc.imag


@nb.njit(cache=True)
def _lse_nb(p, ops, V, amp, n, ins, a, b, c, kind, s, W):
    _pow_nb(p, ops, V, amp, n, W)
    zmax = -1e300; z = np.empty(16)
    for x in range(16):
        if kind == 0:
            Da = W[x, a] - W[x, b]; Db = W[x, b] - W[x, c]
            u = -s * Da; v = -s * Db
            mx = u if u > v else v
            l = mx + np.log(np.exp(u - mx) + np.exp(v - mx))
            m = -l / s if ins[x] else l / s
        else:
            m = (W[x, a] - W[x, b]) if ins[x] else (W[x, b] - W[x, a])
        z[x] = -s * m
        if z[x] > zmax: zmax = z[x]
    acc = 0.0
    for x in range(16): acc += np.exp(z[x] - zmax)
    return zmax + np.log(acc)


@nb.njit(cache=True)
def _obj_grad_nb(p, ops, V, amp, n, ins, a, b, c, kind, s):
    W = np.empty((16, n)); h = 1e-6
    f0 = _lse_nb(p, ops, V, amp, n, ins, a, b, c, kind, s, W)
    g = np.empty(p.shape[0]); q = p.copy()
    for k in range(p.shape[0]):
        q[k] = p[k] + h
        g[k] = (_lse_nb(q, ops, V, amp, n, ins, a, b, c, kind, s, W) - f0) / h
        q[k] = p[k]
    return f0, g


def synth_nb(f, arch, nst=24, seed=0, s=40.0, stop=None, maxiter=800):
    ins = np.array([f >> x & 1 for x in range(16)], np.bool_)
    ops = np.array(arch.ops, np.int64); V = arch.V.astype(np.complex128)
    kind = 0 if arch.kind == "dual" else 1
    a, b = arch.order[0], arch.order[1]; c = arch.order[2] if kind == 0 else 0
    obj = lambda p: _obj_grad_nb(p, ops, V, arch.amp, arch.n, ins, a, b, c, kind, s)
    rng = np.random.default_rng(seed); best = (-np.inf, None)
    for _ in range(nst):
        r = minimize(obj, rng.uniform(0, 2 * np.pi, arch.nph), jac=True, method="BFGS", options=dict(maxiter=maxiter))
        m = arch.margins(r.x[None], ins).min()
        if m > best[0]: best = (float(m), r.x)
        if stop is not None and best[0] >= stop: break
    return best
