r"""M1 s3：圖——沿路徑求 u（x4 → o2、x4 → o4 的兩條路徑）、1100 的逐層功率、ΔP 的常數／一次／二次分解。

用途：把 b7_algebra.py 的結果畫成圖；路徑由 out/algebra.json 的 steps 畫出，B7 接線用 common/draw.py。
輸入：out/algebra.json。
輸出：figures/m1/s3_paths.png（圖 M1-10）、figures/m1/s3_layers.png（圖 M1-11）、figures/m1/s3_quadratic.png（圖 M1-12）。
執行：.\lab design\m1_logic\s3_matrix\figs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()

import json                                                          # noqa: E402

import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.draw import B7_W, B7_XL, B7_YS, BLUE, ORANGE, GREEN, RED, GREY, draw_b7   # noqa: E402
from common.mzi import B7_OPS                                        # noqa: E402

ALG = json.loads(paths.OUT("m1_logic/s3_matrix", "algebra.json").read_text(encoding="utf-8"))


def c2s(z):
    """[實部, 虛部] → '0.25+0.25i'；−0.00 寫成 0.00。"""
    re_, im = (0.0 if abs(v) < 5e-3 else v for v in z)
    return f"{re_:.2f}{im:+.2f}i"


def clear_path_labels(ax, steps):
    """紅色路徑斜穿 MZI 方塊時，把方塊標籤移到斜線沒經過的角落；路徑在方塊內走直線時不經過中央，標籤不動。"""
    for k, a, b in steps:
        if a == b:
            continue
        rail, lay = B7_OPS[k - 1]
        yc = (B7_YS[rail] + B7_YS[rail + 1]) / 2
        lab = next(t for t in ax.texts if t.get_text().startswith(f"MZI-{k}\n"))
        lab.set_position((B7_XL[lay] + 0.73 * B7_W, yc + (0.38 if a > b else -0.38)))      # a＞b：往下走，空的是右上角


def fig_paths(path):
    items = [("x4 → o2：唯一的一條路徑", ALG["demo_paths"]["u24"]["paths"][0], ALG["demo_paths"]["u24"]["total"]),
             ("x4 → o4：路徑 A", ALG["demo_paths"]["u44"]["paths"][0], None),
             ("x4 → o4：路徑 B", ALG["demo_paths"]["u44"]["paths"][1], ALG["demo_paths"]["u44"]["total"])]
    fig, axs = plt.subplots(3, 1, figsize=(10.5, 12))
    for ax, (title, p, total) in zip(axs, items):
        draw_b7(ax, path=p["steps"], fs=9.5)
        clear_path_labels(ax, p["steps"])
        fac = " × ".join(f"T{k}[{a},{b}]" for k, a, b in p["steps"])
        vals = " × ".join(f"({c2s(z)})" for z in p["factors"])
        txt = f"{title}\n{fac}＝{vals}＝{c2s(p['weight'])}"
        if total:
            txt += f"\n{'u24' if '→ o2' in title else 'u44＝路徑 A＋路徑 B'}＝{c2s(total)}"
        ax.set_title(txt, fontsize=10.5, loc="left")
    fig.text(0.5, 0.005, "示範相位：7 顆 MZI 都設 θ＝π/2、φ＝0。Tk[p,q]＝第 k 顆 MZI 從輸入 q 到輸出 p 的係數（1＝上、2＝下）。",
             ha="center", fontsize=9.5, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_layers(path):
    h = next(x for x in ALG["hand"] if x["bits"] == "1100")
    P = np.array(h["layers"]).T                                   # 列＝波導，行＝截面
    fig, ax = plt.subplots(figsize=(9, 4.2))
    im = ax.imshow(P, cmap="Blues", aspect="auto", vmin=0, vmax=max(9.5, P.max()))
    for r in range(5):
        for c in range(5):
            ax.text(c, r, f"{P[r, c]:.3g}", ha="center", va="center", fontsize=10,
                    color="white" if P[r, c] > 5 else "black")
    ax.set_xticks(range(5), ["輸入端", "第 1 層後", "第 2 層後", "第 3 層後", "第 4 層後\n（輸出）"])
    ax.set_yticks(range(5), ["波導 1", "波導 2（o2）", "波導 3", "波導 4（o4）", "波導 5"])
    for c, tot in enumerate(h["layer_totals"]):
        ax.text(c, 5.0, f"總和 {tot:g}", ha="center", va="center", fontsize=9.5, color=GREEN)
    ax.set_ylim(5.4, -0.5)
    ax.set_title("輸入 1100（R＝3）：每一層之後各波導的功率（P$_u$）。光在波導間重新分配，總和始終是 11", fontsize=10.5)
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_quad(path):
    names = ["AND2", "OR2", "XOR2"]
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 4), sharey=True)
    for ax, n in zip(axs, names):
        rows = ALG["quad"][n]["rows_2in"]
        x = np.arange(4)
        for xi, r in zip(x, rows):
            parts = [("常數（R²）", r["const"], ORANGE), ("一次（R·x 與 x²）", r["linear"], BLUE), ("二次（x1·x2）", r["quad"], RED)]
            pos, neg = 0.0, 0.0
            for lab, v, col in parts:
                if v >= 0:
                    ax.bar(xi, v, bottom=pos, color=col, width=0.6, label=lab if xi == 0 else None)
                    pos += v
                else:
                    ax.bar(xi, v, bottom=neg, color=col, width=0.6, label=lab if xi == 0 else None)
                    neg += v
            ax.plot(xi, r["dP"], "kD", ms=7, zorder=5, label="ΔP（合計）" if xi == 0 else None)
            ax.text(xi + 0.33, r["dP"], f"{r['dP']:+.2f}", va="center", fontsize=9)
        ax.axhline(0, color="black", lw=1)
        ax.set_xticks(x, [r["bits"] for r in rows])
        ax.set_xlabel("x1x2（x3＝x4＝0）")
        q = ALG["quad"][n]
        ax.set_title(f"{n}：常數 {q['a0']:.2f}、b1＝{q['b'][0]:.2f}、b2＝{q['b'][1]:.2f}、c12＝{q['c']['12']:.2f}", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel("ΔP 的組成（P$_u$）")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=9.5, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    fig_paths(paths.FIG("m1", "s3_paths.png"))
    fig_layers(paths.FIG("m1", "s3_layers.png"))
    fig_quad(paths.FIG("m1", "s3_quadratic.png"))
    print("寫出 figures/m1/s3_paths.png、s3_layers.png、s3_quadratic.png")


if __name__ == "__main__":
    main()
