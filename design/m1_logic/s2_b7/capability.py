r"""M1 s2：從單顆 MZI 到 B7——每一種結構能做幾種二輸入邏輯？為什麼 B7 是 7 顆、4 層？

用途：沿用 M1 s1 的判讀規則（兩個固定讀取埠比大小，ΔP＞0 判 1、ΔP＜0 判 0，ΔP＝0 為邊界），
  對三種結構求「每個二輸入函數能否實現」以及最大的判讀 margin：
  A. 單顆 MZI，只有 x1、x2：任何設定下 00 都沒有光（ΔP＝0），16 種都做不到；用最佳化確認。
  B. 兩顆 MZI＋參考光 R（3 條波導）：MZI-a 混合 x1、x2，MZI-b 混合 MZI-a 的下輸出與 R；
     對每一組讀取埠（有序的兩個輸出）求 16 種函數各自的最大 margin；另對固定讀 o2-o3 時 XOR 的 margin 掃描 R。
  C. B7（5 條波導、7 顆 MZI、讀 o2、o4），x3＝x4＝0：16 種函數各自的最大 margin。
  另以結構可達性說明 4 層的理由：只取 B7 的前 k 層時，有幾路輸入（含 R）的光能同時到達 o2 與 o4。
  margin m＝min_i s_i·ΔP_i（s_i＝+1 代表該組輸入應判 1，−1 應判 0）；m ≥ 0.01 P_u 才算「可實現」。
  最佳化：SLSQP 求 max m s.t. s_i·ΔP_i ≥ m；每個函數多起點（種子 700＋k），取最好的。
輸入：common/mzi.py、common/synth.py（最佳化）。
輸出：out/capability.json（各結構、各函數的 margin 與相位；可達性）。
執行：.\lab design\m1_logic\s2_b7\capability.py
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
from common.mzi import B7_OPS, R_AMP, READ, T, chain                 # noqa: E402
from common.synth import best_margin                                 # noqa: E402

STEP = "m1_logic/s2_b7"
INPUTS = [(0, 0), (0, 1), (1, 0), (1, 1)]
M_OK = 0.01                                     # 可實現的 margin 下限（P_u）
NAMES = {"0000": "固定 0", "0001": "AND", "0010": "x1·¬x2", "0011": "x1", "0100": "¬x1·x2", "0101": "x2",
         "0110": "XOR", "0111": "OR", "1000": "NOR", "1001": "XNOR", "1010": "¬x2", "1011": "x1＋¬x2",
         "1100": "¬x1", "1101": "¬x1＋x2", "1110": "NAND", "1111": "固定 1"}
TWO_OPS = [(0, 0), (1, 1)]                      # MZI-a：波導 1–2；MZI-b：波導 2–3
R_SWEEP = [3, 2, 1, 0.75, 0.5, 0.3]             # 兩顆 MZI 讀 o2-o3 時，XOR 的 margin 對 R 掃描


def truth_tables():
    return ["".join(b) for b in itertools.product("01", repeat=4)]   # 依 00、01、10、11 的輸出排列


def survey(make_u, n_par, vec_of, read, starts):
    vecs = np.array([vec_of(x1, x2) for x1, x2 in INPUTS], dtype=complex)
    out = {}
    for tt in truth_tables():
        signs = np.array([1.0 if c == "1" else -1.0 for c in tt])
        m, par = best_margin(make_u, n_par, vecs, read, signs, starts)
        out[tt] = dict(name=NAMES[tt], margin=round(m, 6), ok=m >= M_OK, phases=[round(float(v), 6) for v in par])
    return out


def reach(ops, n, layers):
    """只用前 `layers` 層時，每路輸入的光可能到達哪些輸出（結構上，不看相位）。"""
    res = {}
    for j in range(n):
        s = {j}
        for rail, lay in ops:
            if lay < layers and (rail in s or rail + 1 in s):
                s |= {rail, rail + 1}
        res[j] = sorted(s)
    return res


def main():
    t0 = time.time()
    # 驗證 T 與解析式一致、為么正
    rng = np.random.default_rng(1)
    err_T = max(float(np.max(np.abs(T(a, b) - __import__("common.mzi", fromlist=["T_closed"]).T_closed(a, b))))
                for a, b in rng.uniform(0, 2 * np.pi, (20, 2)))
    thetas = np.linspace(0, 2 * np.pi, 9)
    split = [dict(theta=round(float(t), 4), bar=round(float(abs(T(t, 0)[0, 0]) ** 2), 6),
                  cross=round(float(abs(T(t, 0)[1, 0]) ** 2), 6)) for t in thetas]

    # A. 單顆 MZI（x1、x2；讀 out1 對 out2）
    single = survey(lambda p: T(p[0], p[1]), 2, lambda a, b: [a, b], (0, 1), starts=12)

    # B. 兩顆 MZI＋R：所有有序讀取埠
    two = {}
    for rd in itertools.permutations(range(3), 2):
        res = survey(lambda p: chain(TWO_OPS, p[:2], p[2:], 3), 4, lambda a, b: [a, b, R_AMP], rd, starts=16)
        two[f"o{rd[0] + 1}-o{rd[1] + 1}"] = dict(count=sum(v["ok"] for v in res.values()), funcs=res)
    best_pair = max(two, key=lambda k: (two[k]["count"], sum(v["margin"] for v in two[k]["funcs"].values())))

    # B2. 兩顆 MZI＋R、固定讀 o2-o3：XOR 的 margin 隨 R 的變化（M1 審查 R1：做不到只限於 R 大時）
    xor_signs = np.array([-1.0, 1, 1, -1])
    xor_vs_R = {}
    for R in R_SWEEP:
        vecs = np.array([[a, b, R] for a, b in INPUTS], dtype=complex)
        m, _ = best_margin(lambda p: chain(TWO_OPS, p[:2], p[2:], 3), 4, vecs, (1, 2), xor_signs, starts=16)
        xor_vs_R[f"{R:g}"] = round(m, 6)
    # 每個函數是否「至少有一組讀取埠」做得到（允許每個函數換讀取埠）
    any_pair = sum(any(two[k]["funcs"][tt]["ok"] for k in two) for tt in truth_tables())

    # C. B7，x3＝x4＝0，讀 o2、o4
    b7 = survey(lambda p: chain(B7_OPS, p[:7], p[7:], 5), 14, lambda a, b: [a, b, 0, 0, R_AMP], READ, starts=12)

    # 可達性：前 k 層
    reach_tab = []
    for k in range(1, 5):
        r = reach(B7_OPS, 5, k)
        both = [j for j in range(5) if READ[0] in r[j] and READ[1] in r[j]]
        reach_tab.append(dict(layers=k, n_mzi=sum(1 for _, lay in B7_OPS if lay < k), reach=r,
                              both_readouts=[["x1", "x2", "x3", "x4", "R"][j] for j in both], n_both=len(both)))

    res = dict(step="M1 s2", R=R_AMP, m_ok=M_OK, T_closed_err=err_T, split=split,
               single=dict(count=sum(v["ok"] for v in single.values()),
                           max_margin=max(v["margin"] for v in single.values()), funcs=single),
               two_mzi=dict(ops=TWO_OPS, best_pair=best_pair, best_count=two[best_pair]["count"],
                            xor_vs_R_o2o3=xor_vs_R, count_any_pair=any_pair,
                            counts={k: v["count"] for k, v in two.items()}, pairs=two),
               b7_2in=dict(count=sum(v["ok"] for v in b7.values()), min_margin=min(v["margin"] for v in b7.values()),
                           funcs=b7),
               reach=reach_tab, b7_ops=B7_OPS, elapsed_s=round(time.time() - t0, 1))
    out = paths.OUT(STEP, "capability.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"T 與解析式誤差 {err_T:.1e}")
    print(f"A 單顆 MZI：{res['single']['count']}/16，最大 margin {res['single']['max_margin']:.2e}")
    print("B 兩顆 MZI＋R：" + "、".join(f"{k} {v}/16" for k, v in res["two_mzi"]["counts"].items()) + f"；最佳 {best_pair}")
    print(f"C B7（x3＝x4＝0）：{res['b7_2in']['count']}/16，最小 margin {res['b7_2in']['min_margin']:.3f}")
    for r in reach_tab:
        print(f"  前 {r['layers']} 層（{r['n_mzi']} 顆）：同時到達 o2、o4 的輸入 {r['both_readouts']}")
    print(f"寫出 {rt.rel(out)}（{res['elapsed_s']} s）")


if __name__ == "__main__":
    main()
