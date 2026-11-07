r"""論文 M5 s4 的圖：全類別的三層篩選與推測指標。

用途：(a) 各層通過的類別數（靜態 → 動態 → 認證）；
      (b) 每一類的 ρ 對盒內抽樣共同窗：顏色表示認證結果，空心為線性不可分（靠二次項）；黑框是校正組（表 I 的 9 個函數），
          灰帶是修正規則的邊界區（1 ≤ ρ < 校正組最小值）。
輸入：design/paper/m5_cascade/s4_screen/out/screen.json。
輸出：figures/paper/m5/s4_screen.png。
執行：.\lab design\paper\m5_cascade\s4_screen\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter            # noqa: E402

import paths                                                         # noqa: E402

STEP = "paper/m5_cascade/s4_screen"


def main():
    R = json.loads(paths.OUT(STEP, "screen.json").read_text(encoding="utf-8"))
    S, T = R["summary"], R["t_req_ps"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw=dict(width_ratios=[1, 1.35]))
    steps = [("全部類別", S["n_classes"]), ("無損 margin > 0", S["lossless"]["pos"]), ("0.9 dB margin > 0", S["lossy"]["pos"]),
             ("0.9 dB ≥ 0.1 P_u", S["lossy"]["ge01"]), ("對齊窗 ≥ 23 ps", S["dynamic"]["aligned_ge"]),
             ("盒內共同窗 ≥ 23 ps", S["dynamic"]["box_ge"]), ("認證（單葉）", S["dynamic"]["cert1_ge"]), ("認證（含切細）", S["dynamic"]["cert_ge"])]
    cols = ["#7f7f7f"] * 4 + ["#1f77b4"] * 2 + ["#d62728", "#ff7f0e"]
    y = np.arange(len(steps))[::-1]
    a.barh(y, [v for _, v in steps], color=cols)
    for yy, (_, v) in zip(y, steps):
        a.text(v + 2, yy, str(v), va="center", fontsize=9)
    a.set_yticks(y, [s for s, _ in steps])
    a.set_xlim(0, 250)
    a.set_xlabel("類別數（共 222 類）")
    a.set_title("(a) 三層篩選：靜態（灰）、動態（藍）、認證（紅、橘）")
    C = [c for c in R["classes"] if "dyn" in c]
    groups = [("認證（單葉）", lambda c: c["dyn"]["cert1"] >= T, "#d62728"),
              ("認證（切細）", lambda c: c["dyn"]["cert1"] < T and c["certified"], "#ff7f0e"),
              ("有窗、未確認", lambda c: c["has_window"] and not c["certified"], "#1f77b4"),
              ("無窗", lambda c: not c["has_window"], "#7f7f7f")]
    for lab, f, col in groups:
        b.scatter([], [], s=22, color=col, label=lab)
        for sep in (True, False):
            pts = [c for c in C if f(c) and c["static"]["separable"] == sep]
            if pts:
                b.scatter([c["static"]["rho"] for c in pts], [c["dyn"]["box"] for c in pts], s=22,
                          facecolors=col if sep else "none", edgecolors=col, lw=1.1)
    for fn, v in R["calibration"].items():
        b.scatter(v["static"]["rho"], v["dyn"]["box"], s=70, facecolors="none", edgecolors="k", lw=1.3)
        if fn == "XOR2":
            b.annotate(fn, (v["static"]["rho"], v["dyn"]["box"]), xytext=(4, 6), textcoords="offset points", fontsize=8)
        elif fn == "AND4":                                             # 校正組的圈在這裡擠成一團，標籤用引線拉到右下空白
            b.annotate(fn, (v["static"]["rho"], v["dyn"]["box"]), xytext=(34, -30), textcoords="offset points", fontsize=8,
                       arrowprops=dict(arrowstyle="-", color="k", lw=0.6, shrinkA=1, shrinkB=4))
    b.axvspan(1.0, R["revised"]["r_hi"], color="#bbbbbb", alpha=0.35, lw=0, label="修正規則的邊界區")
    b.axvline(1.0, color="#555555", lw=0.8)
    b.axhline(T, color="k", ls=":", lw=1)
    b.scatter([], [], s=22, facecolors="none", edgecolors="k", label="空心：線性不可分")
    b.scatter([], [], s=70, facecolors="none", edgecolors="k", lw=1.3, label="大圈：校正組（表 I）")
    top = [c for c in C if c["dyn"]["box"] > 90]
    for c in top:                                                      # 常數類的窗是整個 2 UI，畫在上緣
        b.annotate(f"{c['dyn']['box']:g} ps ↑", (c["static"]["rho"], 88), xytext=(-7, 0), textcoords="offset points", ha="right", va="center",
                   fontsize=7.5, color="#d62728")
        b.scatter(c["static"]["rho"], 88, s=22, marker="^", color="#d62728")
    b.set_ylim(-5, 92)
    b.set_xscale("log")
    ticks = [0.1, 0.2, 0.5, 1, 2, 5, 10]
    b.xaxis.set_major_locator(FixedLocator(ticks))
    b.xaxis.set_minor_locator(FixedLocator([]))
    b.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    b.set_xlabel("ρ（逐字的 s·D ÷ 自己的護欄，取最小）")
    b.set_ylabel("盒內抽樣共同窗（ps）")
    b.set_title("(b) 靜態指標與動態窗")
    b.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    out = paths.FIG("paper/m5", "s4_screen.png")
    fig.savefig(out, dpi=150)
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
