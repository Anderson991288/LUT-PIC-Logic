r"""M1 s3：B7 的矩陣運算——14 個相位如何決定「每個輸出是各輸入的加權和」，以及判讀量為什麼是二次式。

用途：
  1. 把每顆 MZI 的 2×2 矩陣放進 5×5（其餘波導直通），依接線相乘得 U；輸出光場 y＝U v，v＝[x1, x2, x3, x4, R]。
  2. 路徑相加：u_ij（輸入 j → 輸出 i）＝所有從 j 到 i 的路徑上 2×2 係數的乘積之和。
     列舉全部路徑，驗證與矩陣乘法的 U 完全一致；並以 x4 → o2（1 條）、x4 → o4（2 條）示範。
  3. 手算例（全部 θ＝π/2、φ＝0、R＝3）：輸入 1000、1100 的 y2、y4、P2、P4、ΔP，以及逐層各波導功率（總功率守恆）。
  4. 判讀量的二次式：ΔP＝a_0 + Σ b_j x_j + Σ_{j<k} c_jk x_j x_k（x_j∈{0,1}，x_j²＝x_j 併入一次項）；
     a_0 只來自 R²，b_j 來自 R 與 x_j 的干涉（加上 x_j² 項），c_jk 來自兩路資料的干涉。
     以 M1 s2 找到的 AND2、OR2、XOR2 相位為例，分解四組輸入的 ΔP。
輸入：common/mzi.py；M1 s2 的 out/capability.json（AND2 的 B7 相位）。
輸出：out/algebra.json（U、路徑、手算表、逐層功率、二次式係數與核對）。
執行：.\lab design\m1_logic\s3_matrix\b7_algebra.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import B7_OPS, R_AMP, READ, T, b7_matrix, embed      # noqa: E402

STEP = "m1_logic/s3_matrix"
DEMO_TH = [np.pi / 2] * 7
DEMO_PH = [0.0] * 7


def cplx(z):
    return [round(float(np.real(z)), 6) + 0.0, round(float(np.imag(z)), 6) + 0.0]   # ＋0.0 把 −0.0 變成 0.0


def enumerate_paths(theta, phi, j):
    """從輸入 j 出發的所有路徑：[(終點波導, 係數, [(MZI 編號, 輸出 local p, 輸入 local q), …])]。local：1＝上、2＝下。"""
    paths_ = [(j, 1.0 + 0j, [])]
    for k, ((rail, _), th, ph) in enumerate(zip(B7_OPS, theta, phi), 1):
        t = T(th, ph)
        nxt = []
        for r, w, st in paths_:
            if r in (rail, rail + 1):
                b = r - rail
                for a in (0, 1):
                    nxt.append((rail + a, w * t[a, b], st + [(k, a + 1, b + 1)]))
            else:
                nxt.append((r, w, st))
        paths_ = nxt
    return paths_


def layer_powers(theta, phi, v):
    """各層之後（含輸入端）五條波導的功率。"""
    y = np.array(v, dtype=complex)
    out = [np.abs(y) ** 2]
    for lay in range(4):
        for (rail, l_), th, ph in zip(B7_OPS, theta, phi):
            if l_ == lay:
                y = embed(T(th, ph), rail, 5) @ y
        out.append(np.abs(y) ** 2)
    return out


def quad_coeffs(U):
    """ΔP＝v^T Re(M) v，M＝conj(u2)u2^T − conj(u4)u4^T；回傳 a0、b_j（含 x_j² 項）、c_jk（j<k）。"""
    u2, u4 = U[READ[0]], U[READ[1]]
    M = np.real(np.outer(u2.conj(), u2) - np.outer(u4.conj(), u4))
    a0 = M[4, 4] * R_AMP ** 2
    b = [2 * M[j, 4] * R_AMP + M[j, j] for j in range(4)]
    c = {f"{j + 1}{k + 1}": 2 * M[j, k] for j in range(4) for k in range(j + 1, 4)}
    return float(a0), [float(x) for x in b], {k: float(v) for k, v in c.items()}


def dP_direct(U, bits):
    y = U @ np.array(list(bits) + [R_AMP], dtype=complex)
    P = np.abs(y) ** 2
    return float(P[READ[0]] - P[READ[1]])


def dP_poly(a0, b, c, bits):
    return a0 + sum(b[j] * bits[j] for j in range(4)) + sum(c[f"{j + 1}{k + 1}"] * bits[j] * bits[k]
                                                           for j in range(4) for k in range(j + 1, 4))


def main():
    U = b7_matrix(DEMO_TH, DEMO_PH)
    unitary_err = float(np.max(np.abs(U.conj().T @ U - np.eye(5))))

    # 路徑相加 == 矩陣乘法（全部 25 個元素）
    U_path = np.zeros((5, 5), dtype=complex)
    n_paths = np.zeros((5, 5), dtype=int)
    for j in range(5):
        for r, w, _ in enumerate_paths(DEMO_TH, DEMO_PH, j):
            U_path[r, j] += w
            n_paths[r, j] += 1
    path_err = float(np.max(np.abs(U_path - U)))
    demo = {}
    for i, j, key in ((1, 3, "u24"), (3, 3, "u44")):
        ps = [p for p in enumerate_paths(DEMO_TH, DEMO_PH, j) if p[0] == i]
        demo[key] = dict(total=cplx(U[i, j]), paths=[dict(weight=cplx(w), steps=st,
                                                         factors=[cplx(T(DEMO_TH[k - 1], DEMO_PH[k - 1])[a - 1, b - 1])
                                                                  for k, a, b in st]) for _, w, st in ps])

    # 手算例
    hand = []
    for bits in ((1, 0, 0, 0), (1, 1, 0, 0)):
        v = list(bits) + [R_AMP]
        y = U @ np.array(v, dtype=complex)
        terms2 = [cplx(U[1, j] * v[j]) for j in range(5)]
        terms4 = [cplx(U[3, j] * v[j]) for j in range(5)]
        P = np.abs(y) ** 2
        lp = layer_powers(DEMO_TH, DEMO_PH, v)
        hand.append(dict(bits="".join(map(str, bits)), v=v, terms_y2=terms2, terms_y4=terms4,
                         y2=cplx(y[1]), y4=cplx(y[3]), P2=round(float(P[1]), 6), P4=round(float(P[3]), 6),
                         dP=round(float(P[1] - P[3]), 6), P_all=[round(float(p), 6) for p in P],
                         P_total=round(float(P.sum()), 6), P_in=float(np.sum(np.square(v))),
                         layers=[[round(float(p), 6) for p in row] for row in lp],
                         layer_totals=[round(float(row.sum()), 6) for row in lp]))
    # 獨立手算（M1 審查 R5）：不呼叫 T()，直接用示範相位下每顆 MZI 的字面係數 T＝(−1＋i)/2·[[1, 1], [1, −1]]，
    # 逐層更新五條波導的光場；與矩陣乘法的 y2、y4 比較。
    T_lit = 0.5 * (-1 + 1j) * np.array([[1, 1], [1, -1]])
    hand_err = 0.0
    for h in hand:
        f = np.array(h["v"], dtype=complex)
        for rail, _ in B7_OPS:
            f[rail:rail + 2] = T_lit @ f[rail:rail + 2]
        hand_err = max(hand_err, abs(f[1] - complex(*h["y2"])), abs(f[3] - complex(*h["y4"])))
    lit_vs_T = float(np.max(np.abs(T_lit - T(np.pi / 2, 0))))

    # 二次式：示範相位與 M1 s2 的 AND2 相位
    cap = json.loads(paths.OUT("m1_logic/s2_b7", "capability.json").read_text(encoding="utf-8"))
    cases = [("demo", U)]
    for name, tt in (("AND2", "0001"), ("OR2", "0111"), ("XOR2", "0110")):
        ph = cap["b7_2in"]["funcs"][tt]["phases"]
        cases.append((name, b7_matrix(ph[:7], ph[7:])))
    quad = {}
    for name, Uq in cases:
        a0, b, c = quad_coeffs(Uq)
        err = max(abs(dP_direct(Uq, bits) - dP_poly(a0, b, c, bits)) for bits in itertools.product((0, 1), repeat=4))
        rows = []
        for x1, x2 in ((0, 0), (0, 1), (1, 0), (1, 1)):
            bits = (x1, x2, 0, 0)
            rows.append(dict(bits=f"{x1}{x2}", const=round(a0, 6), linear=round(b[0] * x1 + b[1] * x2, 6),
                             quad=round(c["12"] * x1 * x2, 6), dP=round(dP_direct(Uq, bits), 6)))
        quad[name] = dict(a0=round(a0, 6), b=[round(x, 6) for x in b], c={k: round(v, 6) for k, v in c.items()},
                          poly_err=err, rows_2in=rows)

    res = dict(step="M1 s3", demo_phases="全部 θ＝π/2、φ＝0", R=R_AMP, U=[[cplx(z) for z in row] for row in U],
               unitary_err=unitary_err, path_err=path_err, n_paths=n_paths.tolist(),
               total_paths=int(n_paths.sum()), demo_paths=demo, hand=hand, hand_err=float(hand_err),
               T_literal="(−1＋i)/2·[[1, 1], [1, −1]]", T_literal_vs_T=lit_vs_T, quad=quad)
    out = paths.OUT(STEP, "algebra.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"U 為么正：誤差 {unitary_err:.1e}；路徑相加 vs 矩陣：誤差 {path_err:.1e}（共 {res['total_paths']} 條路徑）")
    for key, d in demo.items():
        print(f"{key}＝{d['total']}，{len(d['paths'])} 條路徑：" + "、".join(str(p['weight']) for p in d["paths"]))
    for h in hand:
        print(f"{h['bits']}：y2＝{h['y2']}、y4＝{h['y4']}；P2＝{h['P2']}、P4＝{h['P4']}、ΔP＝{h['dP']}；"
              f"總功率 {h['P_total']}（輸入 {h['P_in']}）；各層總功率 {h['layer_totals']}")
    for name, q in quad.items():
        print(f"{name}：a0＝{q['a0']}，b＝{q['b']}，c12＝{q['c']['12']}；二次式核對誤差 {q['poly_err']:.1e}")
        for r in q["rows_2in"]:
            print(f"   {r['bits']}：常數 {r['const']:+.3f}  一次 {r['linear']:+.3f}  二次 {r['quad']:+.3f}  → ΔP {r['dP']:+.3f}")
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
