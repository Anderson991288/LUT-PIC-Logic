r"""M1 s1：光訊號與邏輯——用一顆 MMI 加一個相位，看光怎麼被讀成 AND2，以及為什麼需要參考光。

用途：
  1. 輸入：x1、x2 是光場振幅 0／1；上臂先加相位 φ，再進理想 MMI（common/optics.py 的 H）。
  2. 混合：兩個輸出光場 y上、y下；功率 P上＝|y上|²、P下＝|y下|²。
  3. 讀取：比較兩個功率，ΔP＝P上 − P下；ΔP＞0 判 1、ΔP＜0 判 0、ΔP＝0 是邊界（不算成功判讀）。
  驗證 ΔP＝2·x1·x2·sin φ（只有乘積項），並示範兩種判讀規則在雷射功率下降時的差別：
  固定門檻 T＝1（ΔP＞T 判 1）與比大小（看 ΔP 的正負）。
輸入：無。
輸出：out/and2.json（真值表、公式驗證、波形與兩種判讀的結果）、
      figures/m1/s1_deltaP_phase.png（圖 M1-4）、figures/m1/s1_waveform.png（圖 M1-5）。
執行：.\lab design\m1_logic\s1_signal\and2_readout.py
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
from common.optics import H, phase, power                            # noqa: E402

STEP = "m1_logic/s1_signal"
PHI = np.pi / 2                     # 讓 ΔP＝2·x1·x2 的相位
T_FIXED = 1.0                       # 固定門檻（對照用）
INPUTS = [(0, 0), (0, 1), (1, 0), (1, 1)]
SEQ_X1 = [0, 1, 0, 1, 1, 0, 0, 1]   # 波形：每個位元 1 ns
SEQ_X2 = [0, 0, 1, 1, 1, 0, 1, 1]
SCALE = [1.0] * 4 + [0.4] * 4       # 後 4 個位元雷射功率降到 40%（例如耦合變差）


def mix(x1, x2, phi=PHI, scale=1.0):
    """回傳 (y上, y下, P上, P下, ΔP)；scale 是功率倍數，光場乘 √scale。"""
    v = np.sqrt(scale) * np.array([x1, x2], dtype=complex)
    y = H @ phase(phi) @ v
    p = power(y)
    return y[0], y[1], float(p[0]), float(p[1]), float(p[0] - p[1])


def decide_sign(dp, tol=1e-12):
    return 1 if dp > tol else (0 if dp < -tol else None)          # None＝邊界


def fig_phase(path, phis, curves):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    styles = {"00": ("#8a8f96", "-"), "01": ("#2f6fb5", "--"), "10": ("#c08a2b", ":"), "11": ("#c0392b", "-")}
    for k, dp in curves.items():
        c, ls = styles[k]
        ax.plot(phis / np.pi, dp, color=c, ls=ls, lw=2.2 if k == "11" else 1.8, label=f"x1x2＝{k}")
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(0.5, color="#5f6368", lw=0.8, ls="--")
    ax.text(0.53, -0.7, "φ＝π/2：AND2 的相位", fontsize=9, color="#5f6368")
    ax.set_xlabel("上臂相位 φ（π）")
    ax.set_ylabel("ΔP＝P上 - P下（P$_u$）")              # 含 $…$ 的標籤用 ASCII 減號：mathtext 字型沒有 U+2212
    ax.set_title("ΔP 只有乘積項：00、01、10 在任何相位都正好是 0")
    ax.legend(ncol=4, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False)
    ax.grid(alpha=0.3)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_wave(path, wave):
    n = len(SEQ_X1)
    t = np.arange(n + 1)
    fig, axs = plt.subplots(5, 1, figsize=(9, 6.2), sharex=True,
                            gridspec_kw=dict(height_ratios=[0.8, 0.8, 1.6, 0.8, 0.8]))

    def steps(ax, vals, color, label):
        ax.step(t, list(vals) + [vals[-1]], where="post", color=color, lw=2)
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=10)
        ax.grid(alpha=0.3)

    steps(axs[0], SEQ_X1, "#2f6fb5", "x1")
    steps(axs[1], SEQ_X2, "#2f6fb5", "x2")
    dp = [w["dP"] for w in wave]
    steps(axs[2], dp, "#c0392b", "ΔP（P$_u$）")
    axs[2].axhline(T_FIXED, color="#c08a2b", ls="--", lw=1.2)
    axs[2].text(n - 0.05, T_FIXED + 0.08, "固定門檻 T＝1", ha="right", fontsize=9, color="#c08a2b")
    axs[2].axhline(0, color="black", lw=0.8)
    axs[2].axvspan(4, 8, color="#f4e3c9", alpha=0.5, zorder=0)
    axs[2].text(6, 1.75, "雷射功率降到 40%", ha="center", fontsize=9)
    for ax, key, label in ((axs[3], "dec_T", "門檻判讀"), (axs[4], "dec_sign", "比大小")):
        ax.set_ylim(-0.6, 1.6)
        ax.set_yticks([])
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=10)
        for i, w in enumerate(wave):
            d = w[key]
            ok = d == w["target"]
            txt = "邊界" if d is None else str(d)
            ax.text(i + 0.5, 0.5, txt, ha="center", va="center", fontsize=11,
                    color="#2e7d4f" if ok else "#c0392b", fontweight="bold")
        ax.grid(alpha=0.3)
    axs[4].set_xlabel("時間（ns），每格一個位元；綠色＝與 AND2 相同，紅色＝錯誤或無法判讀")
    axs[4].set_xticks(range(n + 1))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    table = []
    for x1, x2 in INPUTS:
        yu, yd, pu, pd, dp = mix(x1, x2)
        table.append(dict(x1=x1, x2=x2, y_up=[round(yu.real, 6), round(yu.imag, 6)],
                          y_dn=[round(yd.real, 6), round(yd.imag, 6)], P_up=round(pu, 6), P_dn=round(pd, 6),
                          dP=round(dp, 6), target=x1 * x2, dec_sign=decide_sign(dp), dec_T=int(dp > T_FIXED)))

    phis = np.linspace(-1, 1, 721) * np.pi
    curves, err = {}, 0.0
    for x1, x2 in INPUTS:
        dp = np.array([mix(x1, x2, p)[4] for p in phis])
        curves[f"{x1}{x2}"] = dp
        err = max(err, float(np.max(np.abs(dp - 2 * x1 * x2 * np.sin(phis)))))

    wave = []
    for x1, x2, s in zip(SEQ_X1, SEQ_X2, SCALE):
        _, _, pu, pd, dp = mix(x1, x2, scale=s)
        wave.append(dict(x1=x1, x2=x2, scale=s, P_up=round(pu, 6), P_dn=round(pd, 6), dP=round(dp, 6),
                         target=x1 * x2, dec_T=int(dp > T_FIXED), dec_sign=decide_sign(dp)))

    fig_phase(paths.FIG("m1", "s1_deltaP_phase.png"), phis, curves)
    fig_wave(paths.FIG("m1", "s1_waveform.png"), wave)

    res = dict(step="M1 s1", phi_rad=PHI, T_fixed=T_FIXED, table=table,
               formula="dP = 2*x1*x2*sin(phi)", formula_max_err=err,
               dP_00_max_over_phi=float(np.max(np.abs(curves["00"]))),
               sign_rule=dict(correct=sum(r["dec_sign"] == r["target"] for r in table),
                              boundary=sum(r["dec_sign"] is None for r in table)),
               T_rule=dict(correct=sum(r["dec_T"] == r["target"] for r in table)),
               wave=wave, wave_scale_low=SCALE[-1],
               wave_T_errors=sum(w["dec_T"] != w["target"] for w in wave),
               wave_T_errors_low_power=sum(w["dec_T"] != w["target"] for w in wave if w["scale"] < 1),
               wave_sign_boundary=sum(w["dec_sign"] is None for w in wave),
               wave_sign_wrong=sum(w["dec_sign"] is not None and w["dec_sign"] != w["target"] for w in wave))
    out = paths.OUT(STEP, "and2.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print("x1 x2 |  P上   P下    ΔP  | 比大小 門檻T=1 | AND2")
    for r in table:
        s = "邊界" if r["dec_sign"] is None else r["dec_sign"]
        print(f" {r['x1']}  {r['x2']} | {r['P_up']:4.2f}  {r['P_dn']:4.2f}  {r['dP']:5.2f} |  {s!s:4}   {r['dec_T']}     |  {r['target']}")
    print(f"ΔP＝2·x1·x2·sinφ 驗證誤差 {err:.1e}；00 在任何相位的 |ΔP| 最大 {res['dP_00_max_over_phi']:.1e}")
    print(f"波形：門檻判讀錯 {res['wave_T_errors']} 個位元（都在低功率段）；比大小 邊界 {res['wave_sign_boundary']} 個、判錯 {res['wave_sign_wrong']} 個")
    print(f"寫出 {rt.rel(out)}")


if __name__ == "__main__":
    main()
