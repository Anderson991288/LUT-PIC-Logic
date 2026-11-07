r"""M1 s4：AND／OR／XOR 實例——同一顆 B7、同一組接線，只換 14 個相位，就換成不同的邏輯函數。

用途：
  1. 對五個函數求相位：AND2、OR2、XOR2（只看 x1、x2）與 AND4、OR4（看全部四路）。
     每個函數都要求 16 組四位元輸入全部判對；二輸入函數的 x3、x4 可以是任意值（不保證未使用的輸入是暗的）。
     以 common/synth.py 求最大 margin 的 14 個相位（θ1–θ7、φ1–φ7）。
  2. 真值表：每組輸入的目標、P2、P4、ΔP、判讀；檢查全部判對且沒有邊界。
  3. 相位誤差：14 個相位同時加上常態分佈誤差（標準差 σ），各 500 次（種子 700＋k），看真值表仍全對的比例。
  4. 對照：二輸入函數若只要求 x3＝x4＝0 的 4 組判對，重新最佳化的 margin（看「x3、x4 任意」要付出多少代價）。
輸入：common/mzi.py、common/synth.py。
輸出：out/gates.json（各函數相位、margin、真值表、相位誤差通過率、對照 margin）。
執行：.\lab design\m1_logic\s4_gates\gates.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import time                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import R_AMP, READ, b7_matrix                         # noqa: E402
from common.synth import best_margin, deltas                         # noqa: E402

STEP = "m1_logic/s4_gates"
SIGMAS = [0.01, 0.02, 0.05, 0.1]                # 相位誤差標準差（rad）
TRIALS = 500
STARTS = 24
BITS = list(itertools.product((0, 1), repeat=4))   # x1x2x3x4，x1 為最高位
FUNCS = {                                       # 名稱 → (函數使用的輸入數, 真值)
    "AND2": (2, lambda b: b[0] & b[1]),
    "OR2": (2, lambda b: b[0] | b[1]),
    "XOR2": (2, lambda b: b[0] ^ b[1]),
    "AND4": (4, lambda b: int(all(b))),
    "OR4": (4, lambda b: int(any(b))),
}


def make_u(p):
    return b7_matrix(p[:7], p[7:])


def solve(bits, f):
    vecs = np.array([list(b) + [R_AMP] for b in bits], dtype=complex)
    signs = np.array([1.0 if f(b) else -1.0 for b in bits])
    m, par = best_margin(make_u, 14, vecs, READ, signs, STARTS, maxiter=600)
    return m, par, vecs, signs


def main():
    t0 = time.time()
    res = {}
    for name, (n, f) in FUNCS.items():
        m, par, vecs, signs = solve(BITS, f)
        P = np.abs(vecs @ make_u(par).T) ** 2
        dP = P[:, READ[0]] - P[:, READ[1]]
        target = (signs > 0).astype(int)
        dec = (dP > 0).astype(int)
        rows = [dict(bits="".join(map(str, b)), target=int(t), P2=round(float(p[READ[0]]), 6),
                     P4=round(float(p[READ[1]]), 6), dP=round(float(d), 6), bit=int(k))
                for b, t, p, d, k in zip(BITS, target, P, dP, dec)]
        robust = {}
        for s in SIGMAS:
            ok = sum(bool(np.all(signs * deltas(make_u(par + np.random.default_rng(700 + k).normal(0, s, 14)),
                                                vecs, READ) > 0)) for k in range(TRIALS))
            robust[str(s)] = ok / TRIALS
        res[name] = dict(n_inputs=n, theta=[float(v) for v in par[:7]],      # 相位存全精度：真值表由這組相位算出，
                         phi=[float(v) for v in par[7:]], margin=round(m, 6),  # 四捨五入後重播會差約 1e-6（M1 s5 發現）
                         passed=int(np.sum(dec == target)), total=len(BITS),
                         min_abs_dP=round(float(np.min(np.abs(dP))), 6), rows=rows, phase_error_pass=robust,
                         abs_u25=round(float(abs(make_u(par)[READ[0], 4])), 6),      # R 對 o2、o4 的權重：
                         abs_u45=round(float(abs(make_u(par)[READ[1], 4])), 6))     # 解釋相位敏感度（M1 審查 R8）
        print(f"{name}：{res[name]['passed']}/16，margin {m:.3f} P_u；"
              + "、".join(f"σ={s}：{v:.0%}" for s, v in robust.items()))

    only00 = {}
    for name in ("AND2", "OR2", "XOR2"):
        m, *_ = solve([b for b in BITS if b[2] == 0 and b[3] == 0], FUNCS[name][1])
        only00[name] = round(m, 6)
        print(f"{name}（只要求 x3＝x4＝0）：margin {m:.3f}；x3、x4 任意：{res[name]['margin']:.3f}")

    total = sum(v["passed"] for v in res.values())
    out = paths.OUT(STEP, "gates.json")
    out.write_text(json.dumps(dict(step="M1 s4", R=R_AMP, read="o2-o4", sigmas=SIGMAS, trials=TRIALS, funcs=res,
                                   margin_only_x34_zero=only00, passed=total, total=16 * len(res),
                                   elapsed_s=round(time.time() - t0, 1)), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"共 {total}/{16 * len(res)} 組判讀正確；寫出 {rt.rel(out)}（{time.time() - t0:.0f} s）")


if __name__ == "__main__":
    main()
