r"""LUT4 s9：TIA 增益失配的補強——(A) 量測增益後重新求相位；(B) 合成時挑耐增益誤差的相位解。

對象：三次類 0x0069（單一門檻做不到，標稱相位下三路增益 σ＝3% 時只有約 82% 全對）與 XOR4。
  A. 每次抽三路增益 g～N(1, σ²)（σ＝2、3、5%，各 100 次，種子 910），把 g 放進模型重新合成 14 個相位
     （起點：標稱相位＋3 個隨機起點），看在該組 g 下 16 組是否全對與裕量。
  B. 目標改成增益盒（各路 1±δ，δ＝3%）內最差的裕量最大（log-sum-exp 平滑，24 個起點）。盒內最差裕量用 gain_box.box_margins：
     目標 0 的列最差點可能在盒內，只看 8 個角落不夠（2026-11-07 修正，舊版用 8 個角落）。
     得到的相位以單路容許量與三路蒙地卡羅（σ＝1–8%、2,000 次，種子 900）和標稱解比較；確定性的 ε 由 gain_box.py 計算。
模型：每顆 MZI 0.9 dB、R＝3、雙差值 o2＞o4＞o3（同 synth4）。
輸入：synth4.py。
輸出：out/gain_robust.json（含標稱解與 B 解的相位，供 gain_box.py 重播）。
執行：.\lab design\lut4\s9_system\gain_robust.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4*
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import gain_box as GB                                                # noqa: E402
import paths                                                         # noqa: E402
import synth4 as S                                                   # noqa: E402

STEP = "lut4/s9_system"
A = S.Arch.from_code("3142132", loss_db=0.9, order=(1, 3, 2))
DELTA_B = 0.03
SIG_A = [0.02, 0.03, 0.05]
SIG_MC = [0.01, 0.02, 0.03, 0.05, 0.08]
NA, NMC = 100, 2000


def margins(P, ins, G):
    """P：(B, 14)，G：(K, 3) 增益（o2、o3、o4）→ (B, K, 16) 逐點裕量。"""
    W = A.powers(P)                                                  # (B, 16, 5)
    P2 = W[:, None, :, 1] * G[None, :, 0, None]
    P3 = W[:, None, :, 2] * G[None, :, 1, None]
    P4 = W[:, None, :, 3] * G[None, :, 2, None]
    Da, Db = P2 - P4, P4 - P3
    return np.where(ins, np.minimum(Da, Db), np.maximum(-Da, -Db))


def margins_box(P, ins, delta):
    """P：(B, 14) → (B, 16) 增益盒內逐列的最差裕量。"""
    W = A.powers(P)
    return GB.box_margins(W[:, :, 1], W[:, :, 2], W[:, :, 3], ins, delta)


def solve(ins, G, starts, s=40.0, delta=None):
    """G 給定時看這些增益點；delta 給定時看整個增益盒。"""
    eye = np.eye(14) * 1e-6
    fm = (lambda P: margins_box(P, ins, delta)) if delta is not None else (lambda P: margins(P, ins, G))

    def f(p):
        m = fm(np.vstack([p, p + eye])).reshape(15, -1)
        z = -s * m
        zm = z.max(1, keepdims=True)
        v = zm[:, 0] + np.log(np.exp(z - zm).sum(1))
        return v[0], (v[1:] - v[0]) / 1e-6
    best = (-np.inf, None)
    for p0 in starts:
        r = minimize(f, p0, jac=True, method="BFGS", options=dict(maxiter=600))
        m = float(fm(r.x[None]).min())
        if m > best[0]:
            best = (m, r.x)
    return best


def tol_single(p, ins):
    out = {}
    for i, ch in enumerate(("o2", "o3", "o4")):
        lim = []
        for sg in (1, -1):
            g = 0.0
            while g < 0.6:
                gg = np.ones((1, 3)); gg[0, i] = 1 + sg * (g + 0.001)
                if margins(p[None], ins, gg).min() <= 0:
                    break
                g += 0.001
            lim.append(round(g, 3))
        out[ch] = min(lim)
    return out


def mc(p, ins):
    res = {}
    for sg in SIG_MC:
        G = np.random.default_rng(900).normal(1.0, sg, (NMC, 3))
        res[str(sg)] = round(float((margins(p[None], ins, G)[0].min(1) > 0).mean()), 4)
    return res


def main():
    out = {}
    for name, f in (("0x0069", 0x0069), ("XOR4", 0x6996)):
        ins = np.array([f >> x & 1 for x in range(16)], bool)
        m0, p0 = S.synth_nb(f, A, 60, 7)                               # 標稱解（與 LUT4 s1 相同方法）
        rec = dict(nominal=dict(margin=round(m0, 4), single=tol_single(p0, ins), mc=mc(p0, ins), phases=[float(x) for x in p0]))
        # A：量測增益後重求
        rng = np.random.default_rng(910)
        a_res = {}
        for sg in SIG_A:
            ok, mm, ok_nom = 0, [], 0
            for _ in range(NA):
                g = rng.normal(1.0, sg, (1, 3))
                ok_nom += margins(p0[None], ins, g).min() > 0
                st = [p0] + [rng.uniform(0, 2 * np.pi, 14) for _ in range(3)]
                m, _ = solve(ins, g, st)
                ok += m > 0
                mm.append(m)
            a_res[str(sg)] = dict(nominal_pass=ok_nom / NA, resolved_pass=ok / NA, resolved_margin_min=round(float(min(mm)), 4),
                                  resolved_margin_median=round(float(np.median(mm)), 4))
            print(name, "A σ", sg, a_res[str(sg)], flush=True)
        rec["remeasure"] = a_res
        # B：耐增益誤差的解（δ＝3% 的增益盒）
        rng = np.random.default_rng(920)
        mB, pB = solve(ins, None, [p0] + [rng.uniform(0, 2 * np.pi, 14) for _ in range(23)], delta=DELTA_B)
        rec["robust"] = dict(delta=DELTA_B, box_margin=round(mB, 4), margin=round(float(margins(pB[None], ins, np.ones((1, 3))).min()), 4),
                             single=tol_single(pB, ins), mc=mc(pB, ins), phases=[float(x) for x in pB])
        print(name, "B", {k: v for k, v in rec["robust"].items() if k != "phases"}, flush=True)
        out[name] = rec
    paths.OUT(STEP, "gain_robust.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
