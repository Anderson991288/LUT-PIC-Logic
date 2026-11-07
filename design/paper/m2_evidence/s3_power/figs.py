r"""論文 M2 s3：圖——相位偏差所需的最小 P_u，以及三種情況下取樣窗寬度隨 P_u 的變化。

用途：數字讀 out/power.json。
輸入：out/power.json。
輸出：figures/paper/m2/s3_power.png（圖 M2-2）。
執行：.\lab design\paper\m2_evidence\s3_power\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, GREY, PURPLE, RED               # noqa: E402

STEP = "paper/m2_evidence/s3_power"
P = json.loads(paths.OUT(STEP, "power.json").read_text(encoding="utf-8"))
COL = {"AND4": PURPLE, "XOR2": RED}


def main():
    F = P["functions"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
    # (a) P_u,min(δ)
    ax = axs[0]
    for fn, c in COL.items():
        r = F[fn]
        x = [q["delta_rad"] for q in r["rows"] if q["pu_min_dbm"] is not None]
        y = [q["pu_min_dbm"] for q in r["rows"] if q["pu_min_dbm"] is not None]
        ax.plot(x, y, "o-", color=c, lw=2, label=f"{fn}：窗存在所需")
    bud = F["XOR2"]["budget_pu_dbm"]
    ax.axhline(bud, color="k", ls="--", lw=1.2)
    ax.text(0.005, bud + 0.3, f"系統預算 {bud:.2f} dBm", color="k", fontsize=8.5)
    ax.axvline(P["det_rad"], color=GREY, lw=1)
    ax.text(P["det_rad"] + 0.004, ax.get_ylim()[0] + 0.3, f"δ_det {P['det_rad']}", color=GREY, fontsize=8.5)
    ax.set_xlabel("每路輸入相位偏差 δ（rad，最差組合，不追蹤）")
    ax.set_ylabel("B7 輸入端 P_u（dBm）")
    # 窗內已判錯（m_win ≤ 0）：兩個函數最早出現的 δ 起，加光也無效
    bad = min(q["delta_rad"] for f in F.values() for q in f["rows"] if q["pu_min_dbm"] is None)
    ax.axvspan(bad, max(P["deltas_rad"]) + 0.02, color="#f6dede", zorder=0)
    ax.text(bad + 0.01, -9, "δ ≥ %g rad：\n至少一個函數\n窗內判錯、加光無效" % bad, color=RED, fontsize=8.5)
    ax.set_xlim(-0.01, max(P["deltas_rad"]) + 0.02)
    ax.set_title("(a) 相位偏差要多少光來補", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper left")
    # (b)(c) W(P_u)
    for ax, fn in zip(axs[1:], COL):
        r = F[fn]
        for name, lab, c in (("nominal", "名義（理想消光比、無 skew）", GREEN), ("drift", f"未追蹤漂移 {P['drift_rad']} rad（規格、skew 20 ps）", RED),
                             ("final", "校正後（聯合驗收條件）", BLUE)):
            ax.plot(r["pu_grid_dbm"], r["w_ps"][name], color=c, lw=2, label=lab)
        ax.axhline(P["t_req_ps"], color=GREY, ls="--", lw=1)
        ax.text(r["pu_grid_dbm"][0] + 0.1, P["t_req_ps"] + 1, f"T_req {P['t_req_ps']:g} ps", color=GREY, fontsize=8.5)
        ax.axvline(r["budget_pu_dbm"], color="k", ls="--", lw=1.2)
        ax.text(r["budget_pu_dbm"] + 0.1, max(max(v) for v in r["w_ps"].values()) * 0.97, "系統預算", color="k", fontsize=8.5)
        ax.set_xlabel("B7 輸入端 P_u（dBm）")
        ax.set_ylabel("取樣窗寬度 W（ps）")
        ax.set_title(f"({'b' if fn == 'AND4' else 'c'}) {fn}：窗寬與光功率", fontsize=10.5)
        ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(paths.FIG("paper/m2", "s3_power.png"), dpi=160)
    print("寫出 figures/paper/m2/s3_power.png")


if __name__ == "__main__":
    main()
