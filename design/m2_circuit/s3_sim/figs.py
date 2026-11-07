r"""M2 s3：圖——PDK 模型與 M1 的比對、故障注入、MMI 不理想時的 margin 與重新校正。

用途：所有數字從 sim_results.json、sim_truth.csv、mmi_sweep.json 讀出；M1 的 ΔP 讀 M1 s5 的 truth_tables.csv。
輸入：out/sim_results.json、out/sim_truth.csv、out/mmi_sweep.json；M1 s5 的 out/truth_tables.csv。
輸出：figures/m2/s3_verify.png（圖 M2-7）、figures/m2/s3_nonideal.png（圖 M2-8）。
執行：.\lab design\m2_circuit\s3_sim\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import csv                                                           # noqa: E402
import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
from matplotlib.ticker import FuncFormatter                         # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import BLUE, GREEN, ORANGE, GREY, PURPLE, RED       # noqa: E402

STEP = "m2_circuit/s3_sim"
RES = json.loads(paths.OUT(STEP, "sim_results.json").read_text(encoding="utf-8"))
SW = json.loads(paths.OUT(STEP, "mmi_sweep.json").read_text(encoding="utf-8"))
FCOL = dict(AND2=BLUE, OR2=GREEN, XOR2=PURPLE, AND4=ORANGE, OR4=GREY)


def read_csv(path):
    with open(path, encoding="utf-8-sig") as fh:
        return {(r["function"], r["x1"] + r["x2"] + r["x3"] + r["x4"]): r for r in csv.DictReader(fh)}


def fig_verify(path):
    m1 = read_csv(paths.OUT("m1_logic/s5_handoff", "truth_tables.csv"))
    sim = read_csv(paths.OUT(STEP, "sim_truth.csv"))
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw=dict(width_ratios=[1, 1.15]))
    for key, r in sim.items():
        x, y = float(m1[key]["dP"]), float(r["dP"])
        a.plot(x, y, "o", ms=5, color=RED if r["target"] == "1" else BLUE, alpha=0.8)
    lim = max(abs(float(r["dP"])) for r in sim.values()) * 1.1
    a.plot([-lim, lim], [-lim, lim], color=GREY, lw=0.8, ls="--")
    a.axhline(0, color=GREY, lw=0.6)
    a.axvline(0, color=GREY, lw=0.6)
    a.set_xlabel("M1 矩陣乘法的 ΔP（P$_u$）")
    a.set_ylabel("IPKISS 電路模擬（PDK MMI）的 ΔP（P$_u$）")
    a.set_title(f"80 組 ΔP：兩種算法落在同一條對角線上（{RES['passed']}/80 判對）", fontsize=10.5)
    a.plot([], [], "o", color=RED, label="目標 1（ΔP 應 > 0）")
    a.plot([], [], "o", color=BLUE, label="目標 0（ΔP 應 < 0）")
    a.legend(fontsize=9, loc="upper left")
    a.grid(alpha=0.3)

    names = list(RES["functions"])
    vals = [RES["functions"][n]["U_err"] for n in names]
    labels = names + ["MMI 上下\n全部接反", "只有輸出\n接反", "φ 接到\n下方輸入"]
    F = RES["faults"]
    vals += [F["swap_all"]["U_err_max"], F["swap_out"]["U_err_max"], F["phi_low"]["U_err_max"]]
    cols = [GREEN] * len(names) + [GREEN, RED, RED]
    b.bar(range(len(vals)), np.maximum(vals, 1e-17), color=cols)
    b.set_yscale("log")
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"1e{np.log10(v):.0f}"))   # 預設刻度用 \mathdefault，中文字型缺負號
    b.axhline(1e-12, color=GREY, ls="--", lw=1)
    b.text(-0.4, 2.5e-12, "驗收門檻 1e-12", ha="left", fontsize=8.5, color=GREY)
    passed = [RES["functions"][n]["passed"] for n in names] + [F[m]["passed"] for m in ("swap_all", "swap_out", "phi_low")]
    tot = [16] * len(names) + [80, 80, 80]
    for k, (v, p, t) in enumerate(zip(vals, passed, tot)):
        b.text(k, max(v, 1e-17) * 3, f"{p}/{t}", ha="center", fontsize=8.5)
    b.axvline(len(names) - 0.5, color=GREY, lw=0.8)
    b.set_xticks(range(len(vals)), labels, fontsize=8.5)
    b.set_ylim(1e-17, 50)
    b.set_ylabel("‖U - U$_{ref}$‖ 最大元素差")
    b.set_title("左：五個函數（正確接線）；右：三種接線錯誤（故障注入）", fontsize=10.5)
    b.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_nonideal(path):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(14, 4.4), gridspec_kw=dict(width_ratios=[1.1, 1.1, 1]))
    L = np.array(SW["loss_scan"])
    for n, m in SW["loss_margin_per_function"].items():
        a.plot(L, m, color=FCOL[n], label=n, lw=1.5)
    a.axhline(0, color="black", lw=0.8)
    a.axvspan(0.30, 0.36, color=RED, alpha=0.15)
    a.text(0.33, a.get_ylim()[1] * 0.92 if a.get_ylim()[1] > 0 else 1, "實測\n0.30–0.36", ha="center", fontsize=8, color=RED, va="top")
    hi = SW["loss_range_ok"][1]
    a.axvline(hi, color=RED, ls="--", lw=1)
    a.text(hi + 0.03, -0.55, f"超過 {hi:g} dB 判錯", fontsize=8.5, color=RED)
    a.set_xlabel("每顆 MMI 的額外損耗（dB）")
    a.set_ylabel("margin（P$_u$）")
    a.set_title("(a) MMI 損耗：相位不重調", fontsize=10.5)
    a.legend(fontsize=8.5, ncol=2)
    a.grid(alpha=0.3)

    D = np.array(SW["delta_scan"])
    for n, m in SW["delta_margin_per_function"].items():
        b.plot(D * 100, m, color=FCOL[n], label=n, lw=1.5)
    b.axhline(0, color="black", lw=0.8)
    lo, hi = SW["delta_range_ok"]
    b.axvspan(lo * 100, hi * 100, color=BLUE, alpha=0.1)
    b.text(0, b.get_ylim()[0] * 0.9 if b.get_ylim()[0] < 0 else -0.3, f"全對：δ＝{lo * 100:+.2f}～{hi * 100:+.2f} %",
           ha="center", fontsize=8.5, color=BLUE)
    b.set_xlabel("分光偏差 δ（直通功率比例 50%＋δ；%）")
    b.set_title(f"(b) 每顆 MMI 同一偏差（含 {SW['loss_meas_db']:g} dB 損耗）", fontsize=10.5)
    b.grid(alpha=0.3)

    R = RES["recalibration"]["per_function"]
    names = list(R)
    x = np.arange(len(names))
    w = 0.27
    c.bar(x - w, [R[n]["margin_ideal"] for n in names], w, color=GREY, label="理想 MMI")
    c.bar(x, [R[n]["margin_before"] for n in names], w, color=RED, label=f"{SW['loss_meas_db']:g} dB、沿用 M1 相位")
    c.bar(x + w, [R[n]["margin_after"] for n in names], w, color=GREEN, label=f"{SW['loss_meas_db']:g} dB、重新校正")
    c.set_xticks(x, names)
    c.set_ylabel("margin（P$_u$）")
    c.set_title(f"(c) 重新校正相位（{RES['recalibration']['starts']} 個起點）", fontsize=10.5)
    c.legend(fontsize=8.2)
    c.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_verify(paths.FIG("m2", "s3_verify.png"))
    fig_nonideal(paths.FIG("m2", "s3_nonideal.png"))
    print("寫出 figures/m2/s3_verify.png、s3_nonideal.png")


if __name__ == "__main__":
    main()
