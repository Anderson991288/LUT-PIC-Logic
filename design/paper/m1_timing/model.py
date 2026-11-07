r"""論文 M1 的共用模型：含 MMI 實測損耗的 B7，與在此模型下重新校正的相位（M1 s1–s5 一律用這一份）。

用途：課程 M2 s3 指出每顆 2×2 MMI 有約 0.33 dB 的額外損耗，並在此損耗下重新求相位（最小 margin 0.289，XOR2）；
  M1 s1 的功率預算用的就是這個 margin。為了讓 M1 s2–s4 和 M1 s1 一致，這裡提供同一個模型：
  - b7(θ, φ)：每顆 MZI 的兩顆 MMI 各乘上振幅 10^(−L/20)（L＝課程 M2 s3 的實測損耗），其餘與課程 M1 的 B7 相同；
  - load_phases()：在此模型下用課程 M1 s4 的方法（SLSQP、24 個起點、種子 700＋k、maxiter 600）重求的 14 個相位，
    第一次呼叫時計算並寫入 out/phases_lossy.json，之後直接讀檔；margin 與課程 M2 s3 的「重新校正後」相同（自動核對）。
輸入：design/m1_logic/s5_handoff/out/phases.json（函數與用到的輸入）、design/m1_logic/s5_handoff/out/truth_tables.csv、
      design/m2_circuit/s3_sim/out/sim_results.json（MMI 損耗與重新校正後的 margin）。
輸出：design/paper/m1_timing/out/phases_lossy.json。
執行：.\lab design\paper\m1_timing\model.py（只重算相位並核對；其他程式 import 本檔）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import B7_OPS, READ, R_AMP, T, embed                 # noqa: E402
from common.synth import best_margin                                 # noqa: E402

STEP = "paper/m1_timing"
SIM = json.loads(paths.OUT("m2_circuit/s3_sim", "sim_results.json").read_text(encoding="utf-8"))
LOSS_DB = float(SIM["recalibration"]["loss_db"])
STARTS = int(SIM["recalibration"]["starts"])
MAXITER = int(SIM["recalibration"]["maxiter"])
A2 = 10 ** (-2 * LOSS_DB / 20)                                       # 每顆 MZI 兩顆 MMI 的振幅損耗


def b7(theta, phi):
    """含 MMI 損耗的 B7：U＝∏ embed(a² T(θ_k, φ_k))。"""
    U = np.eye(5, dtype=complex)
    for (rail, _), th, ph in zip(B7_OPS, theta, phi):
        U = embed(A2 * T(th, ph), rail, 5) @ U
    return U


def _words_and_targets():
    rows = list(csv.DictReader(open(paths.OUT("m1_logic/s5_handoff", "truth_tables.csv"), encoding="utf-8-sig")))
    return rows


def _solve():
    ph = json.loads(paths.OUT("m1_logic/s5_handoff", "phases.json").read_text(encoding="utf-8"))
    rows = _words_and_targets()
    out = dict(source="課程 M1 s5 的函數定義；課程 M2 s3 的 MMI 損耗與重新校正方法", loss_db=LOSS_DB, R=R_AMP, functions={})
    for fn, f in ph["functions"].items():
        sub = [r for r in rows if r.get("function", r.get("函數")) == fn]
        words = [tuple(int(r[k]) for k in ("x1", "x2", "x3", "x4")) for r in sub]
        tcol = "target" if "target" in sub[0] else [k for k in sub[0] if k not in ("function", "x1", "x2", "x3", "x4")][0]
        signs = np.array([1 if int(r[tcol]) == 1 else -1 for r in sub])
        V = np.array([list(w) + [R_AMP] for w in words], dtype=complex)
        m, z = best_margin(lambda z: b7(z[:7], z[7:]), 14, V, READ, signs, STARTS, maxiter=MAXITER)
        out["functions"][fn] = dict(uses=f["uses"], theta=z[:7].tolist(), phi=z[7:].tolist(), margin=float(m),
                                    margin_course=SIM["recalibration"]["per_function"][fn]["margin_after"])
        print(f"{fn}：margin {m:.4f}（課程 M2 s3 重新校正後 {out['functions'][fn]['margin_course']:.4f}）")
    out["check_matches_course"] = all(abs(v["margin"] - v["margin_course"]) < 1e-3 for v in out["functions"].values())
    paths.OUT(STEP, "phases_lossy.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_phases():
    p = paths.OUT(STEP, "phases_lossy.json")
    if not p.exists():
        return _solve()
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    r = _solve()
    print("與課程一致：", r["check_matches_course"])
