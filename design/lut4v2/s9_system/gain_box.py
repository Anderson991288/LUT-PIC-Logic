r"""LUT4 v2 s9（輸入 E+／E−）：增益盒的確定性檢查——三路增益各在 [1−ε, 1+ε] 內時，16 組判讀是否全部正確。

為什麼不用角落：y＝[g2·P2＞g4·P4]∧[g4·P4＞g3·P3]。目標 1 的列要 Da、Db 都為正，兩者對增益是線性函數，最小值在角落，直接用角落極值。
目標 0 的列要 max(−Da, −Db)＞0，這是凸函數，最小值可能落在盒內，只查 8 個角落會漏掉：
(P2, P3, P4)＝(1, 1.01, 1.005)、增益各在 [0.97, 1.03] 時八角落全判 0，(g2, g3, g4)＝(1.03, 0.97, 1) 卻使兩個差值都為正。
方法：
  目標 1：min(Da)＝lo2·P2−hi4·P4、min(Db)＝lo4·P4−hi3·P3，兩者都要為正。
  目標 0：線性規劃 max t，限制 Da≥t、Db≥t、增益在盒內。t*＞0 表示盒內存在 Da＞0 且 Db＞0，該列判錯；盒內最差裕量為 −t*。
  ε：盒是巢狀的，判讀全對對 ε 單調，用二分搜尋（40 次）。另以封閉式核對：
     目標 1：ε＝min(r(P2,P4), r(P4,P3))；目標 0：ε＝max(r(P4,P2), r(P3,P4), r(P3,P2), 0)，r(a,b)＝(a−b)／(a＋b)。
對象：七個範例函數（phases.json）；0x0069 與 XOR4 的標稱解、耐增益誤差解（gain_robust.json 保存的相位）；全表相位庫 merged_phases.npz（封閉式，逐表）。
範圍：相位固定、每顆 MZI 0.9 dB、R＝3、只有三路增益誤差，沒有偏移、雜訊與其他誤差。這是模型下的確定性界，不是量測，也不是良率。
輸入：LUT4 s1 的 out/phases.json；s0_coverage 的 out/merged_phases.npz；out/gain_robust.json。
輸出：out/gain_box.json。
執行：.\lab design\lut4v2\s9_system\gain_box.py
"""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4*
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402
from scipy.optimize import linprog                                   # noqa: E402

import paths                                                         # noqa: E402
import synth4 as S                                                   # noqa: E402

VER = Path(__file__).resolve().parents[1].name
STEP = f"{VER}/s9_system"
CORNERS = np.array(list(itertools.product((-1, 1), repeat=3)), float)
N_BISECT = 40
SIG_MC, N_MC = (0.01, 0.02, 0.03), 2000
COUNTER = dict(P=(1.0, 1.01, 1.005), delta=0.03, gain=(1.03, 0.97, 1.0))   # 外部審查的反例：(P2, P3, P4)


def lp_row(P, lo, hi):
    """目標 0 的列：盒內 min(Da, Db) 的最大值 t* 與對應增益（g2, g3, g4）。P＝(P2, P3, P4)。"""
    P2, P3, P4 = P
    r = linprog([0, 0, 0, -1], A_ub=[[-P2, 0, P4, 1], [0, P3, -P4, 1]], b_ub=[0, 0],
                bounds=[(lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2]), (None, None)], method="highs")
    if r.status != 0:                                                 # 這個 LP 恆可行且有界，其他狀態都是數值失敗，不能當成判讀結果
        raise RuntimeError(f"linprog 失敗：status {r.status}，{r.message}")
    return float(r.x[3]), r.x[:3]


def row_margin(P, target, lo, hi):
    """盒內該列的最差裕量（＞0 表示全盒判對）與最差增益。"""
    P2, P3, P4 = P
    if target:
        da, db = lo[0] * P2 - hi[2] * P4, lo[2] * P4 - hi[1] * P3
        g = (lo[0], lo[1] if da <= db else hi[1], hi[2] if da <= db else lo[2])
        return min(da, db), g
    t, g = lp_row(P, lo, hi)
    return -t, tuple(g)


def check_box(W, ins, lo, hi):
    """W：(16, 3)＝(P2, P3, P4)；回傳全盒是否判對、最差裕量、最差列與增益。"""
    rows = [row_margin(W[x], bool(ins[x]), lo, hi) for x in range(16)]
    x = int(np.argmin([r[0] for r in rows]))
    return dict(ok=rows[x][0] > 0, margin=float(rows[x][0]), row=x, target=int(ins[x]), gain=[float(v) for v in rows[x][1]])


def box(eps):
    return (1 - eps,) * 3, (1 + eps,) * 3


def eps_bisect(W, ins):
    if not check_box(W, ins, *box(0.0))["ok"]:
        return 0.0
    a, b = 0.0, 1.0
    for _ in range(N_BISECT):
        m = (a + b) / 2
        if check_box(W, ins, *box(m))["ok"]:
            a = m
        else:
            b = m
    return a


def r_(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(a + b > 0, (a - b) / (a + b), np.inf)


def eps_closed(P2, P3, P4, ins):
    """(…, 16) → 逐列的 ε。"""
    yes = np.minimum(r_(P2, P4), r_(P4, P3))
    no = np.maximum.reduce([r_(P4, P2), r_(P3, P4), r_(P3, P2), np.zeros_like(P2)])
    return np.where(ins, yes, no)


def box_margins(P2, P3, P4, ins, delta):
    """盒內逐列的最差裕量（封閉式，等於 row_margin；供 gain_robust 當最佳化目標）。
    目標 0：提高 g2、降低 g3 只會讓 min(Da, Db) 變大；g4 取兩差值相等的值，超出盒時夾到盒邊。"""
    lo, hi = 1 - delta, 1 + delta
    yes = np.minimum(lo * P2 - hi * P4, lo * P4 - hi * P3)
    a, c = hi * P2, lo * P3
    v4 = np.clip((a + c) / 2, lo * P4, hi * P4)
    return np.where(ins, yes, -np.minimum(a - v4, v4 - c))


def corners_pass(W, ins, eps):
    """只查 8 個角落（舊做法，只用來比較）。"""
    G = 1 + eps * CORNERS
    Da = W[None, :, 0] * G[:, 0, None] - W[None, :, 2] * G[:, 2, None]
    Db = W[None, :, 2] * G[:, 2, None] - W[None, :, 1] * G[:, 1, None]
    return bool(np.where(ins[None], np.minimum(Da, Db), np.maximum(-Da, -Db)).min() > 0)


def self_test():
    P, d, g = COUNTER["P"], COUNTER["delta"], COUNTER["gain"]
    P2, P3, P4 = P
    G = 1 + d * CORNERS
    Da, Db = G[:, 0] * P2 - G[:, 2] * P4, G[:, 2] * P4 - G[:, 1] * P3
    m_corner = float(np.maximum(-Da, -Db).min())
    lo, hi = (1 - d,) * 3, (1 + d,) * 3
    t, gw = lp_row(P, lo, hi)
    da, db = g[0] * P2 - g[2] * P4, g[2] * P4 - g[1] * P3
    out = dict(counterexample=dict(P2_P3_P4=list(P), delta=d, corner_margin_min=round(m_corner, 6), corners_all_zero=m_corner > 0,
                                   lp_t_star=round(t, 6), lp_gain=[round(float(x), 6) for x in gw], review_gain=list(g),
                                   review_gain_Da_Db=[round(da, 6), round(db, 6)]))
    assert m_corner > 0 and t > 0 and da > 0 and db > 0, out
    # 隨機列：LP、封閉式與細格點三者一致
    rng = np.random.default_rng(1)
    worst_lp, worst_grid, worst_eps = 0.0, 0.0, 0.0
    ax = np.linspace(-1, 1, 21)
    GG = np.array(list(itertools.product(ax, ax, ax)))
    for _ in range(300):
        p = rng.uniform(0.2, 3.0, 3) * (1 + 0.1 * rng.standard_normal(3))
        p = np.abs(p)
        dl = rng.uniform(0.0, 0.2)
        m_lp = row_margin(p, False, (1 - dl,) * 3, (1 + dl,) * 3)[0]
        m_cf = float(box_margins(p[0], p[1], p[2], False, dl))
        worst_lp = max(worst_lp, abs(m_lp - m_cf))
        Gd = 1 + dl * GG
        grid = np.maximum(-(Gd[:, 0] * p[0] - Gd[:, 2] * p[2]), -(Gd[:, 2] * p[2] - Gd[:, 1] * p[1])).min()
        assert grid >= m_lp - 1e-9                                    # 格點只會比真實最差值大
        worst_grid = max(worst_grid, grid - m_lp)
        one = np.array([p])
        for tgt in (True, False):
            ins = np.full(1, tgt)
            ec = float(eps_closed(one[:, 0], one[:, 1], one[:, 2], ins)[0])
            if 1e-6 < ec < 0.9:                                       # ε 兩側各取一點，LP／角落判定要換邊
                assert row_margin(p, tgt, *box(ec * (1 - 1e-6)))[0] > -1e-12
                assert row_margin(p, tgt, *box(ec * (1 + 1e-6)))[0] < 1e-12
                worst_eps = max(worst_eps, abs(row_margin(p, tgt, *box(ec))[0]))
    assert worst_lp < 1e-9
    out["random_rows"] = dict(n=300, lp_vs_closed_form_max=float(worst_lp), grid_minus_lp_max=round(float(worst_grid), 6), margin_at_closed_eps_max=float(worst_eps))
    return out


def powers(A, p):
    W = A.powers(np.asarray(p, float)[None])[0]
    return np.stack([W[:, 1], W[:, 2], W[:, 3]], axis=1)              # P2、P3、P4


def report(A, p, truth, source):
    ins = np.array([truth >> x & 1 for x in range(16)], bool)
    W = powers(A, p)
    e = eps_bisect(W, ins)
    per_row = eps_closed(W[:, 0], W[:, 1], W[:, 2], ins)
    k = int(np.argmin(per_row))
    ec = float(per_row[k])
    w = check_box(W, ins, *box(ec * 1.0001 + 1e-9))                   # 剛超過 ε：盒內的反例
    scan = np.linspace(0, 2 * ec + 0.01, 4001)[1:]                     # 角落判定在 ε 上不一定單調，所以用掃描找第一次失敗
    fail = [s for s in scan if not corners_pass(W, ins, s)]
    return dict(truth_hex=f"0x{truth:04X}", phases=source, margin_nominal=round(float(check_box(W, ins, *box(0.0))["margin"]), 4),
                eps=round(e, 7), eps_pct=round(e * 100, 4), eps_closed_form=round(ec, 7), agree=bool(abs(e - ec) < 1e-7),
                binding=dict(row=k, x=[k >> b & 1 for b in range(4)], target=int(ins[k]), P2_P3_P4=[round(float(v), 5) for v in W[k]]),
                counter_gain_just_outside=dict(row=w["row"], gain=[round(v, 6) for v in w["gain"]]),
                margin_at_3pct_box=round(check_box(W, ins, *box(0.03))["margin"], 4),
                corner_only_first_fail_eps=round(float(fail[0]), 5) if fail else None, corner_scan_step=round(float(scan[1] - scan[0]), 6))


def main():
    st = self_test()
    print("自我測試：", json.dumps(st, ensure_ascii=False))
    A = S.Arch.from_code("3142132", loss_db=0.9, order=(1, 3, 2))
    ph = json.loads(paths.OUT(f"{VER}/s1_handoff", "phases.json").read_text(encoding="utf-8"))
    gr = json.loads(paths.OUT(STEP, "gain_robust.json").read_text(encoding="utf-8"))
    funcs = {}
    for n, f in ph["functions"].items():
        p = [x for t in zip(f["theta"], f["phi"]) for x in t]
        funcs[n] = report(A, p, int(f["truth_hex"], 16), "s1_handoff/out/phases.json")
    funcs["0x0069"] = report(A, gr["0x0069"]["nominal"]["phases"], 0x0069, "gain_robust.json nominal（與 s9 其他 0x0069 分析相同的標稱解）")
    robust = {n: report(A, gr[n]["robust"]["phases"], t, f"gain_robust.json robust（δ＝{gr[n]['robust']['delta']:g} 的盒內最差裕量最佳化）")
              for n, t in (("0x0069", 0x0069), ("XOR4", 0x6996))}
    for n, r in robust.items():                                       # 最佳化目標（封閉式）與 LP 判定要一致
        assert abs(r["margin_at_3pct_box"] - gr[n]["robust"]["box_margin"]) < 2e-4, (n, r["margin_at_3pct_box"], gr[n]["robust"]["box_margin"])
    robust_nominal_xor4 = report(A, gr["XOR4"]["nominal"]["phases"], 0x6996, "gain_robust.json nominal")
    for n, r in {**funcs, **{"robust " + k: v for k, v in robust.items()}}.items():
        print(n, r["eps_pct"], "%", "binding", r["binding"]["row"], "target", r["binding"]["target"], "corner-only", r["corner_only_first_fail_eps"], r["agree"])

    lib = np.load(paths.OUT(f"{VER}/s0_coverage", "merged_phases.npz"))
    masks = lib["masks"].astype(np.int64)
    ins = (masks[:, None] >> np.arange(16)) & 1 == 1
    W = A.powers(lib["phases"])
    per = eps_closed(W[:, :, 1], W[:, :, 2], W[:, :, 3], ins)
    tab = per.min(1)
    i = int(np.argmin(tab))
    x = int(np.argmin(per[i]))
    Wi = powers(A, lib["phases"][i])
    e_lp = eps_bisect(Wi, ins[i])
    mc = {}
    for sg in SIG_MC:                                                 # 全表最緊的那張，以 system.py 相同的抽樣看統計成功率
        G = np.random.default_rng(900).normal(1.0, sg, (N_MC, 3))
        Da = Wi[None, :, 0] * G[:, 0, None] - Wi[None, :, 2] * G[:, 2, None]
        Db = Wi[None, :, 2] * G[:, 2, None] - Wi[None, :, 1] * G[:, 1, None]
        mc[str(sg)] = round(float((((Da > 0) & (Db > 0)) == ins[i][None]).all(1).mean()), 4)
    tgt0, tgt1 = np.where(ins, np.inf, per).min(), np.where(ins, per, np.inf).min()
    library = dict(file="s0_coverage/out/merged_phases.npz", n_tables=int(len(masks)), eps_min=round(float(tab[i]), 7), eps_min_pct=round(float(tab[i]) * 100, 4),
                   mask=f"0x{int(masks[i]):04X}", row=x, target=int(ins[i, x]), eps_lp_bisect=round(e_lp, 7), worst_table_mc=mc,
                   eps_min_target1_pct=round(float(tgt1) * 100, 4), eps_min_target0_pct=round(float(tgt0) * 100, 4),
                   percentiles_pct={str(q): round(float(np.percentile(tab, q)) * 100, 3) for q in (1, 10, 50, 90)},
                   n_below={f"{t:g}%": int((tab < t / 100).sum()) for t in (1, 2, 3, 5)})
    print("全表", library)
    out = dict(scope="相位固定、每顆 MZI 0.9 dB、R＝3、只有三路增益誤差；模型下的確定性界，不是量測或良率",
               definition="ε：三路增益各自落在 [1−ε, 1+ε] 內的任何組合下，16 組判讀全對的上確界",
               method=dict(target1="線性差值的角落極值", target0="線性規劃：盒內是否存在 Da＞0 且 Db＞0", bisect_iterations=N_BISECT),
               self_test=st, functions=funcs, robust=robust, xor4_gain_robust_nominal=robust_nominal_xor4, library=library)
    paths.OUT(STEP, "gain_box.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'gain_box.json'))}")


if __name__ == "__main__":
    main()
