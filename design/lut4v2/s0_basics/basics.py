r"""LUT4 s0（M1 s2 ①②）：E+／E− 輸入下，單顆 MZI、二顆 MZI＋R 以一組差動對判讀能實現哪些二輸入邏輯。

條件：理想無損；x1、x2 以二相位光送入（位元 0 → 光場 +1、1 → −1，記為 s1、s2）；R 不調變、與位元 0 同相。
  判讀與本課程相同：同一顆 MZI 的兩個輸出各接一顆 PD，D＝P(上)−P(下)，D＞0 判 1（比較器門檻 0）。
  A. 單顆 MZI：輸入 (s1, s2)，讀這一顆的兩個輸出。
  B. 二顆 MZI＋R：第一顆混合 s1、s2，上輸出 u 與 R 進入第二顆，讀第二顆的兩個輸出；R＝1 與 R＝3 各算一次。
  方法：相位在 [0, 2π) 均勻隨機取樣（A 40 萬組、B 各 100 萬組，種子 11），每組算 4 個輸入（00／01／10／11）的 D，
       記下出現過的真值表；每個真值表保留裕量（4 列中最小的 |D|，單位 Pᵤ）最大的一組相位與其 4 個 D 值。
  另外對單顆 MZI 掃 θ（φ＝0），存 4 個輸入的 D(θ) 供畫圖。
  對照（強度編碼 OOK：位元 0／1 → 光場 0／1）：同樣的單顆、二顆＋R（R＝1、3）與差動對判讀；
  另算「只讀上埠、固定門檻」的單顆（OOK 取 T＝0.35，E± 取 T＝1，各為該編碼下的中間值）。
  裕量小於 0.001 Pᵤ 的真值表視為做不到（例如 OOK 的 00 輸入在差動對下 D 恆為 0）。
輸入：common/mzi.py（只用來核對矩陣元素）。
輸出：out/basics.json。
執行：.\lab design\lut4v2\s0_basics\basics.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "lut4v2/s0_basics"
BITS = ["00", "01", "10", "11"]                                      # x1x2
S = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]], float)            # 對應的 (s1, s2)
X = (1 - S) / 2                                                     # 強度編碼的光場（對照）
EPS = 1e-3
R_LIST = (1.0, 3.0)


def Tm(th, ph):
    """T(θ, φ) 的四個元素（向量化）：與 common/mzi.T_closed 相同。"""
    e = np.exp(1j * th / 2)
    return (1j * np.exp(1j * ph) * e * np.sin(th / 2), 1j * e * np.cos(th / 2),
            1j * np.exp(1j * ph) * e * np.cos(th / 2), -1j * e * np.sin(th / 2))


def collect(D, phases):
    """D：(N, 4)；phases：(N, k) → {真值表: dict(margin, phases, D)}，真值表依 00／01／10／11 的順序寫成 4 位元。"""
    code = ((D > 0) * np.array([8, 4, 2, 1])).sum(1)
    marg = np.abs(D).min(1)
    out = {}
    for c in np.unique(code):
        idx = np.flatnonzero(code == c)
        k = idx[np.argmax(marg[idx])]
        if marg[k] < EPS:
            continue                                                  # 落在門檻上，不算做得到
        out[format(int(c), "04b")] = dict(margin=round(float(marg[k]), 3), phases=[round(float(v), 4) for v in phases[k]],
                                           D=[round(float(v), 3) for v in D[k]])
    return out


def main():
    from common.mzi import T_closed
    assert np.allclose(np.array(Tm(1.1, 0.7)).reshape(2, 2), T_closed(1.1, 0.7))
    rng = np.random.default_rng(11)
    # A：單顆
    th, ph = rng.uniform(0, 2 * np.pi, (2, 400_000))
    t11, t12, t21, t22 = Tm(th, ph)
    up = t11[:, None] * S[None, :, 0] + t12[:, None] * S[None, :, 1]
    dn = t21[:, None] * S[None, :, 0] + t22[:, None] * S[None, :, 1]
    A = collect(np.abs(up) ** 2 - np.abs(dn) ** 2, np.stack([th, ph], 1))
    # 單顆的 D(θ)，φ＝0：畫圖用
    tg = np.linspace(0, 2 * np.pi, 361)
    a, b, c, d = Tm(tg, np.zeros_like(tg))
    sweep = {BITS[i]: [round(float(v), 4) for v in np.abs(a * S[i, 0] + b * S[i, 1]) ** 2 - np.abs(c * S[i, 0] + d * S[i, 1]) ** 2]
             for i in range(4)}
    # B：二顆＋R
    B = {}
    for R in R_LIST:
        th1, ph1, th2, ph2 = rng.uniform(0, 2 * np.pi, (4, 1_000_000))
        a11, a12, _, _ = Tm(th1, ph1)
        b11, b12, b21, b22 = Tm(th2, ph2)
        u = a11[:, None] * S[None, :, 0] + a12[:, None] * S[None, :, 1]
        D = np.abs(b11[:, None] * u + b12[:, None] * R) ** 2 - np.abs(b21[:, None] * u + b22[:, None] * R) ** 2
        B[f"{R:g}"] = collect(D, np.stack([th1, ph1, th2, ph2], 1))
    # 對照：強度編碼（OOK）＋差動對；單顆只讀上埠＋固定門檻（OOK 與 E± 各一）
    def single(V, th, ph):
        a, b, c, d = Tm(th, ph)
        return a[:, None] * V[None, :, 0] + b[:, None] * V[None, :, 1], c[:, None] * V[None, :, 0] + d[:, None] * V[None, :, 1]
    th, ph = rng.uniform(0, 2 * np.pi, (2, 400_000))
    up, dn = single(X, th, ph)
    ook = dict(single=collect(np.abs(up) ** 2 - np.abs(dn) ** 2, np.stack([th, ph], 1)),
               single_port=collect(np.abs(up) ** 2 - 0.35, np.stack([th, ph], 1)))
    up_e, _ = single(S, th, ph)
    epm_port = collect(np.abs(up_e) ** 2 - 1.0, np.stack([th, ph], 1))
    for R in R_LIST:
        th1, ph1, th2, ph2 = rng.uniform(0, 2 * np.pi, (4, 1_000_000))
        a11, a12, _, _ = Tm(th1, ph1)
        b11, b12, b21, b22 = Tm(th2, ph2)
        u = a11[:, None] * X[None, :, 0] + a12[:, None] * X[None, :, 1]
        D = np.abs(b11[:, None] * u + b12[:, None] * R) ** 2 - np.abs(b21[:, None] * u + b22[:, None] * R) ** 2
        ook[f"two_R{R:g}"] = collect(D, np.stack([th1, ph1, th2, ph2], 1))
    compare = dict(epm=dict(single=sorted(A), single_port=sorted(epm_port), **{f"two_R{k}": sorted(v) for k, v in B.items()}),
                   ook={k: sorted(v) for k, v in ook.items()}, port_threshold=dict(epm=1.0, ook=0.35))
    res = dict(encoding="位元 0 → +1、1 → −1；R 與位元 0 同相", readout="D＝P(上)−P(下)，D＞0 判 1", bits=BITS,
               single=dict(count=len(A), tables=A, sweep_theta=[round(float(v), 4) for v in tg], sweep_D=sweep),
               two_mzi_R={k: dict(count=len(v), tables=v) for k, v in B.items()}, compare=compare,
               ook={k: dict(count=len(v), tables={c: dict(margin=d["margin"]) for c, d in v.items()}) for k, v in ook.items()})
    paths.OUT(STEP, "basics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("單顆", len(A), sorted(A))
    for k, v in B.items():
        print(f"二顆＋R＝{k}", len(v), sorted(v))
    for enc, d in compare.items():
        print(enc, d)


if __name__ == "__main__":
    main()
