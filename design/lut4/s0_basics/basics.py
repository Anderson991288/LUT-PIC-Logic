r"""LUT4 s0：重算 M1 s2 ①② 的兩張表——單顆 MZI、二顆 MZI＋R 在固定門檻下能實現哪些二輸入邏輯。

條件（與 M1 s2 ①② 的文字相同）：理想無損；x1、x2 以光場振幅 0／1 送入；固定讀取上埠、門檻 T＝0.35、高功率判 1、不反轉比較器。
  A. 單顆 MZI：P＝|[T(θ, φ)·(x1, x2)]上|²。
  B. 二顆 MZI＋R：第一顆混合 x1、x2，其上輸出與 R＝3（振幅）進入第二顆，讀第二顆的上輸出。
  方法：相位在 [0, 2π) 均勻隨機取樣（A 40 萬組、B 200 萬組，種子 11），每組算 4 個輸入的判讀，記下出現過的真值表，
       並保留每個真值表離門檻最遠的一組（最小 |P−T|）作為代表。
輸入：common/mzi.py。
輸出：out/basics.json。
執行：.\lab design\lut4\s0_basics\basics.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "lut4/s0_basics"
TH = 0.35
INS = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], float)              # 00／01／10／11


def Tm(th, ph):
    """T(θ, φ) 的四個元素（向量化）：與 common/mzi.T_closed 相同。"""
    e = np.exp(1j * th / 2)
    return (1j * np.exp(1j * ph) * e * np.sin(th / 2), 1j * e * np.cos(th / 2),
            1j * np.exp(1j * ph) * e * np.cos(th / 2), -1j * e * np.sin(th / 2))


def collect(P):
    """P：(N, 4) → {真值表字串: 最大最小裕量}。"""
    bits = P > TH
    marg = np.abs(P - TH).min(1)
    code = (bits * np.array([8, 4, 2, 1])).sum(1)
    out = {}
    for c in np.unique(code):
        out[format(int(c), "04b")] = round(float(marg[code == c].max()), 4)
    return out


def main():
    from common.mzi import T_closed
    rng = np.random.default_rng(11)
    # A
    th, ph = rng.uniform(0, 2 * np.pi, (2, 400_000))
    t11, t12, _, _ = Tm(th, ph)
    assert np.allclose(np.array(Tm(1.1, 0.7)).reshape(2, 2), T_closed(1.1, 0.7))
    E = t11[:, None] * INS[None, :, 0] + t12[:, None] * INS[None, :, 1]
    A = collect(np.abs(E) ** 2)
    # B
    th1, ph1, th2, ph2 = rng.uniform(0, 2 * np.pi, (4, 2_000_000))
    a11, a12, _, _ = Tm(th1, ph1)
    b11, b12, _, _ = Tm(th2, ph2)
    up = a11[:, None] * INS[None, :, 0] + a12[:, None] * INS[None, :, 1]
    E2 = b11[:, None] * up + b12[:, None] * 3.0
    B = collect(np.abs(E2) ** 2)
    res = dict(threshold=TH, single=dict(count=len(A), tables=A), two_mzi_R=dict(count=len(B), tables=B))
    paths.OUT(STEP, "basics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("單顆", len(A), sorted(A)); print("二顆＋R", len(B), sorted(B))


if __name__ == "__main__":
    main()
