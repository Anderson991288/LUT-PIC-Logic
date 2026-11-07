r"""LUT4 s0：3142132 的矩陣運算——沿路徑求 U 的元素、逐層光場、雙差值的二次式。

用途：
  1. 路徑展開：七顆 MZI 都設 θ＝π/2、φ＝0（理想、無損耗），列出 x4 → o2、o4、o3 的每一條路徑與沿途係數，
     各路徑相加得 u24、u44、u34，並與整體矩陣 U 比對。
  2. 逐層光場：輸入 1100（x1＝x2＝1）加 R＝3，記錄每層之後五條波導的光場與功率（理想模型總功率守恆）。
  3. 範例函數（XOR4，相位取自 LUT4 s1）：Da、Db 對輸入的常數、一次、二次項係數——說明判讀量最多是二次式。
輸入：LUT4 s1 的 out/lut4_netlist.json、out/phases.json。
輸出：out/algebra.json。
執行：.\lab design\lut4\s0_algebra\algebra.py
"""
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import T, embed                                      # noqa: E402

STEP = "lut4/s0_algebra"
HAND = "lut4/s1_handoff"


def cpx(z):
    return [round(float(np.real(z)), 6), round(float(np.imag(z)), 6)]


def paths_from(ops, Ts, src, dst):
    """列舉 src 波導 → dst 波導的所有路徑；每段記 (MZI 編號, 列, 行)（1 起算，列＝輸出、行＝輸入，上方＝1）。"""
    out = []

    def go(q, rail, seq, w):
        if q == len(ops):
            if rail == dst:
                out.append((seq, w))
            return
        r0 = ops[q][0]
        if rail in (r0, r0 + 1):
            c = rail - r0
            for rr in (0, 1):
                go(q + 1, r0 + rr, seq + [(q + 1, rr + 1, c + 1)], w * Ts[q][rr, c])
        else:
            go(q + 1, rail, seq, w)
    go(0, src, [], 1.0 + 0j)
    return out


def main():
    net = json.loads(paths.OUT(HAND, "lut4_netlist.json").read_text(encoding="utf-8"))
    ph = json.loads(paths.OUT(HAND, "phases.json").read_text(encoding="utf-8"))
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    Ts = [T(np.pi / 2, 0.0) for _ in ops]
    U = np.eye(5, dtype=complex)
    for (r, _), t in zip(ops, Ts):
        U = embed(t, r, 5) @ U
    demo = {}
    for name, dst in (("x4_o2", 1), ("x4_o4", 3), ("x4_o3", 2)):
        ps = paths_from(ops, Ts, 3, dst)
        tot = sum(w for _, w in ps)
        demo[name] = dict(paths=[dict(steps=[f"T{q}[{r},{c}]" for q, r, c in seq], value=cpx(w)) for seq, w in ps],
                          sum=cpx(tot), U=cpx(U[dst, 3]), match=bool(abs(tot - U[dst, 3]) < 1e-12),
                          power=round(float(abs(tot) ** 2), 6))
    t_vals = dict(T11=cpx(Ts[0][0, 0]), T12=cpx(Ts[0][0, 1]), T21=cpx(Ts[0][1, 0]), T22=cpx(Ts[0][1, 1]))

    # 逐層光場：1100＋R
    v = np.array([1, 1, 0, 0, 3], complex)
    layers = [dict(after="輸入", field=[cpx(z) for z in v], power=[round(float(abs(z) ** 2), 6) for z in v])]
    for L in range(4):
        for (r, l), t in zip(ops, Ts):
            if l == L:
                v = embed(t, r, 5) @ v
        layers.append(dict(after=f"第 {L + 1} 層", field=[cpx(z) for z in v], power=[round(float(abs(z) ** 2), 6) for z in v],
                           total=round(float(np.sum(np.abs(v) ** 2)), 6)))

    # XOR4：Da、Db 的多線性展開係數
    f = ph["functions"]["XOR4"]
    a = 10 ** (-ph["loss_db_per_mzi"] / 20)
    Uf = np.eye(5, dtype=complex)
    for (r, _), th, p in zip(ops, f["theta"], f["phi"]):
        Uf = embed(a * T(th, p), r, 5) @ Uf
    X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)
    V = np.zeros((16, 5), complex); V[:, :4] = X; V[:, 4] = ph["R"]
    P = np.abs(V @ Uf.T) ** 2
    Da, Db = P[:, 1] - P[:, 3], P[:, 3] - P[:, 2]
    cols = [np.ones(16)] + [X[:, i] for i in range(4)] + [X[:, i] * X[:, j] for i, j in combinations(range(4), 2)]
    names = ["常數"] + [f"x{i + 1}" for i in range(4)] + [f"x{i + 1}x{j + 1}" for i, j in combinations(range(4), 2)]
    A = np.column_stack(cols)
    ca, ra = np.linalg.lstsq(A, Da, rcond=None)[:2]
    cb, rb = np.linalg.lstsq(A, Db, rcond=None)[:2]
    fit_err = float(max(np.max(np.abs(A @ ca - Da)), np.max(np.abs(A @ cb - Db))))
    quad = dict(terms=names, Da=[round(float(c), 4) for c in ca], Db=[round(float(c), 4) for c in cb], fit_err=fit_err)

    out = dict(setting="七顆 θ＝π/2、φ＝0；理想、無損耗", T=t_vals, demo=demo, layers_1100=layers, quadratic_XOR4=quad)
    paths.OUT(STEP, "algebra.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, d in demo.items():
        print(k, len(d["paths"]), "條路徑", d["sum"], "功率", d["power"], d["match"])
        for p_ in d["paths"]:
            print("   ", " × ".join(p_["steps"]), p_["value"])
    for l in layers:
        print(l["after"], l["power"], l.get("total"))
    print("XOR4 二次式擬合誤差", fit_err)


if __name__ == "__main__":
    main()
