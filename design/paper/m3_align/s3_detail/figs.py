r"""論文 M3 s3：圖——(a) 三個函數在對齊與盒內 41 點逐點最小時的 margin 減護欄對取樣相位；(b) 與草稿表 III 的窗寬比較；
(c) 在草稿設定上逐項換成論文 M1 的設定時，盒內共同窗的變化。

用途：(a) 的曲線用 detail.py 的模擬器重算（草稿設定，約 15 秒）；(b)(c) 的數字讀 out/detail.json。
輸入：out/detail.json、design/paper/m3_align/s2_synth/out/synth.json、design/paper/m1_timing/s1_budget/out/budget.json。
輸出：figures/paper/m3/s3_detail.png（圖 M3-3）。
執行：.\lab design\paper\m3_align\s3_detail\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import detail as DT                                                  # noqa: E402
import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, ORANGE, PURPLE, RED       # noqa: E402

STEP = "paper/m3_align/s3_detail"
G = json.loads(paths.OUT(STEP, "detail.json").read_text(encoding="utf-8"))
COL = {"AND4": BLUE, "MAJ4": GREEN, "XOR2": RED}


def curves(fn):
    S = DT.D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    ph = json.loads(paths.OUT("paper/m3_align/s2_synth", "synth.json").read_text(encoding="utf-8"))["functions"][fn]["lossy"]
    U = DT.b7(np.array(ph["theta"]), np.array(ph["phi"]), 10 ** (-S["mzi_loss_db"] / 20))
    sim = DT.Sim(DT.sequence("euler"), S["edge_full_ps"], 0.5, A, 10 ** (S["pu_dbm"] / 10) * 1e-3, False)
    b = np.array([1.0 if DT.TGT[fn](x) else -1.0 for x in DT.BITS])
    _, al = sim.window(U, b, np.zeros(4))
    env = None
    for p in DT.box_points():
        _, m = sim.window(U, b, p)
        env = m if env is None else np.minimum(env, m)
    return np.arange(len(al)) * sim.dt, al, env


def main():
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw=dict(width_ratios=[1.35, 1, 1.05]))
    ax = axs[0]
    for fn in DT.FUNCS:
        t, al, env = curves(fn)
        ax.plot(t, al, color=COL[fn], lw=1.6, label=f"{fn} 對齊")
        ax.plot(t, env, color=COL[fn], lw=1.2, ls="--", label=f"{fn} 盒內 41 點逐點最小")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlim(0, 200)
    ax.set_ylim(-0.4, 1.05)
    ax.set_yticks(np.arange(-0.4, 0.81, 0.2))
    ax.set_xlabel("取樣相位（ps，0–2 UI）")
    ax.set_ylabel("margin − 護欄（P_u）")
    ax.set_title("(a) 所有符號中最差的 b·V(t) − Γ(t)：≥ 0 的最長區間即窗寬", fontsize=10)
    ax.legend(fontsize=7.5, ncol=3, loc="upper center")
    ax = axs[1]
    C = G["compare"]
    x = np.arange(len(C))
    for k, (key, dkey, lab, c) in enumerate((("aligned", "draft_aligned", "對齊", GREY), ("box_min", "draft_box_min", "盒內共同窗", BLUE))):
        ax.bar(x + (k - 0.5) * 0.36, [C[f][key] for f in C], 0.34, color=c, label=f"本步：{lab}")
        ax.plot(x + (k - 0.5) * 0.36, [C[f][dkey] for f in C], "_", color=RED, ms=16, mew=2.5, label="草稿表 III" if k == 0 else None)
    ax.plot(x + 0.18, [C[f]["box_center"] for f in C], "o", mfc="white", color=BLUE, ms=7, label="本步：扣中點")
    ax.plot(x + 0.18, [C[f]["draft_cert"] for f in C], "v", color=ORANGE, ms=8, label="草稿的認證窗（M4）")
    ax.axhline(G["t_req_ps"], color="k", ls="--", lw=1)
    ax.text(2.48, G["t_req_ps"] + 1, f"T_req {G['t_req_ps']:g} ps", fontsize=8, ha="left")
    ax.set_xlim(-0.6, 3.15)
    ax.set_xticks(x, list(C))
    ax.set_ylabel("窗寬（ps）")
    ax.set_ylim(0, 80)
    ax.set_title("(b) 與草稿表 III 的比較（跨距 13.2 ps 的盒）", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax = axs[2]
    vars_ = [v for v in G["delta"]]
    y = np.arange(len(vars_))
    for j, fn in enumerate(DT.FUNCS):
        vals = [G["delta"][v][fn]["box_min"] if fn in G["delta"][v] else np.nan for v in vars_]
        ax.barh(y + (j - 1) * 0.26, vals, 0.25, color=COL[fn], label=fn)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y, [G["variants"][v] for v in vars_], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("盒內共同窗的變化（ps，相對於草稿設定）")
    ax.set_title("(c) 一次只改一項：換成論文 M1 的設定", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m3", "s3_detail.png"), dpi=160)
    print("寫出 figures/paper/m3/s3_detail.png")


if __name__ == "__main__":
    main()
