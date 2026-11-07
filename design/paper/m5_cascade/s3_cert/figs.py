r"""論文 M5 s3 的圖：串接的認證窗。

用途：(a) x1x8 的 margin 對取樣相位：對齊、盒內抽樣共同、認證（1 葉、256 葉），橫線為認證窗；
      (b) 四個 8 輸入函數的對齊窗、抽樣共同窗、認證窗（1 葉與切細），x1x8 加上草稿值。
輸入：design/paper/m5_cascade/s3_cert/out/cert_cascade.json、curves.npz。
輸出：figures/paper/m5/s3_cert.png。
執行：.\lab design\paper\m5_cascade\s3_cert\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402

STEP = "paper/m5_cascade/s3_cert"
NAMES = {"x1x8": "x1x8", "AND8": "AND8", "MAJ8": "MAJ8", "SYNC": "同步字"}


def main():
    R = json.loads(paths.OUT(STEP, "cert_cascade.json").read_text(encoding="utf-8"))
    C = np.load(paths.OUT(STEP, "curves.npz"))
    F = R["functions"]
    fine = {fn: str(max(int(k) for k in F[fn]["configs"])) for fn in NAMES}
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    fn = "x1x8"
    ph = C[f"{fn}_phase"]
    for key, lab, col, ls in (("aligned", "對齊（詳細模擬）", "#7f7f7f", "-"), ("box_min", f"盒內 {F[fn]['n_points']} 點共同（詳細模擬）", "#1f77b4", "-"),
                              ("cert_1", "認證下界（1 葉）", "#d62728", "-"), (f"cert_{fine[fn]}", f"認證下界（{fine[fn]} 葉）", "#ff7f0e", "--")):
        a.plot(ph, C[f"{fn}_{key}"], color=col, ls=ls, lw=1.4, label=lab)
    for k, y, col in (("1", -0.08, "#d62728"), (fine[fn], -0.2, "#ff7f0e")):
        c = F[fn]["configs"][k]
        if c["start"] is not None:
            a.plot([c["start"], c["end"]], [y, y], color=col, lw=4, solid_capstyle="butt")
            a.text(c["end"] + 9, y, f"W＝{c['window']:g} ps", va="center", fontsize=9, color=col)
    a.axhline(0, color="k", lw=0.8)
    a.set_xlim(0, 200)
    a.set_ylim(-0.4, max(0.6, float(C[f"{fn}_aligned"].max()) * 1.1))
    a.set_xlabel("取樣相位（ps，自符號起點）")
    a.set_ylabel("margin − 護欄（P_u）")
    a.set_title("(a) x1x8：13.2 ps 盒的認證下界")
    a.legend(fontsize=8.5, loc="upper right")
    x = np.arange(len(NAMES))
    w = 0.2
    series = [("aligned", "對齊", "#7f7f7f"), ("box_min", "盒內抽樣共同", "#1f77b4"), ("cert1", "認證（1 葉）", "#d62728"), ("certf", "認證（切細）", "#ff7f0e")]
    for k, (key, lab, col) in enumerate(series):
        vals = []
        for f in NAMES:
            if key == "cert1":
                vals.append(F[f]["configs"]["1"]["window"])
            elif key == "certf":
                vals.append(F[f]["configs"][fine[f]]["window"])
            else:
                vals.append(F[f][key])
        bars = b.bar(x + (k - 1.5) * w, vals, w, color=col, label=lab)
        for bb, v in zip(bars, vals):
            b.text(bb.get_x() + bb.get_width() / 2, v + 0.8, f"{v:g}", ha="center", fontsize=7.5)
    d = F["x1x8"]["draft"]
    for k, key in ((0, "aligned"), (1, "box_min"), (2, "window")):
        b.plot(x[0] + (k - 1.5) * w, d[key], marker="_", ms=16, mew=2.2, color="k")
    b.plot([], [], marker="_", ls="", ms=12, mew=2.2, color="k", label="草稿表 III（x1x8）")
    b.axhline(R["t_req_ps"], color="k", ls=":", lw=1)
    b.text(-0.55, R["t_req_ps"] + 1, "T_req", fontsize=8.5, ha="left")
    b.set_xticks(x, [NAMES[f] for f in NAMES])
    b.set_ylabel("窗寬（ps）")
    b.set_title("(b) 8 輸入函數的窗寬")
    b.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    fig.tight_layout()
    out = paths.FIG("paper/m5", "s3_cert.png")
    fig.savefig(out, dpi=150)
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
