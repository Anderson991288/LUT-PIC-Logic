r"""LUT4 v2 s1（輸入 E+／E−）：交接與介面規格——3142132 的固定光路、功能設定與晶片介面。

用途：
  1. lut4_netlist.json：固定光路 3142132（7 顆 MZI、5 條波導、4 層），R 接第 5 條；判讀 o2、o4、o3（雙差值＋AND）。
  2. phases.json：範例函數的 θ1–θ7、φ1–φ7（每顆 MZI 0.9 dB 損耗下合成，60 個起點取最大裕量），記錄接線表 SHA-256。
  3. truth_tables.csv：每個函數 16 組輸入的 P2、P3、P4、Da、Db、判讀。
  4. spec.json：光學埠（10 EC）、14 個相位通道（H01–H14 → P01–P14）、需求表；格式與 B7 規格相同，供佈局程式直接使用。
  5. tolerance.json：R 振幅容許範圍、輸入相對相位誤差、heater 功率、TIA 增益失配容許量。
輸入：synth4.py（合成）、M2 s1 的 P_π 假設（13 mW）。
輸出：out/ 下的上述五個檔。
執行：.\lab design\lut4v2\s1_handoff\handoff.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # design/lut4
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
import synth4 as S                                                   # noqa: E402

STEP = "lut4v2/s1_handoff"
CODE = "3142132"
LOSS_DB = 0.9
R_AMP = 3.0
ORDER = (1, 3, 2)          # o2 > o4 > o3
P_PI_MW = 13.0
LAYERS = [0, 0, 1, 1, 2, 2, 3]          # 3142132：每層 2、2、2、1 顆
NST = 60
R_SCAN = np.round(np.arange(2.0, 4.0001, 0.01), 3)
SIG_IN = [0.02, 0.05, 0.1, 0.2]
SIG_PH = [0.02, 0.05, 0.1]
TRIALS = 500


def tt(fn):
    """fn(x1,x2,x3,x4) → 真值表整數（第 x 位元；x＝x1＋2x2＋4x3＋8x4）。"""
    return sum(int(bool(fn(x & 1, x >> 1 & 1, x >> 2 & 1, x >> 3 & 1))) << x for x in range(16))


FUNCS = {
    "AND2": ("x1·x2", ["x1", "x2"], tt(lambda a, b, c, d: a & b)),
    "OR2": ("x1＋x2", ["x1", "x2"], tt(lambda a, b, c, d: a | b)),
    "XOR2": ("x1 ⊕ x2", ["x1", "x2"], tt(lambda a, b, c, d: a ^ b)),
    "NAND2": ("NOT(x1·x2)", ["x1", "x2"], tt(lambda a, b, c, d: 1 - (a & b))),
    "AND4": ("x1·x2·x3·x4", ["x1", "x2", "x3", "x4"], tt(lambda a, b, c, d: a & b & c & d)),
    "XOR4": ("x1 ⊕ x2 ⊕ x3 ⊕ x4", ["x1", "x2", "x3", "x4"], tt(lambda a, b, c, d: a ^ b ^ c ^ d)),
    "MUX": ("x3 ? x2 : x1", ["x1", "x2", "x3"], tt(lambda a, b, c, d: b if c else a)),
}


def netlist():
    sig = ["x1", "x2", "x3", "x4", "R"]
    role = {1: "上界（判讀）", 3: "中間（判讀）", 2: "下界（判讀）"}
    ops = [int(c) - 1 for c in CODE]
    return dict(
        name="Model-7a", version="1.0", n_waveguides=5, topology=CODE,
        inputs=[dict(index=k + 1, signal=sig[k], layout_port=f"in{k}",
                     amplitude="+1／−1（√P_u；位元 0＝+E、1＝−E）" if k < 4 else f"+{R_AMP:g}（√P_u，固定，與位元 0 同相）") for k in range(5)],
        outputs=[dict(index=k + 1, name=f"o{k + 1}", layout_port=f"out{k}", role=role.get(k, "監看")) for k in range(5)],
        mzis=[dict(name=f"MZI-{k}", waveguides=[r + 1, r + 2], layer=l + 1, theta=f"θ{k}", phi=f"φ{k}")
              for k, (r, l) in enumerate(zip(ops, LAYERS), 1)],
        order="光由左到右；U＝T̂7·T̂6·…·T̂1（同一層的兩顆可交換）",
        mzi_convention=dict(
            matrix="T(θ, φ)＝a·H·diag(e^{iθ}, 1)·H·diag(e^{iφ}, 1)，H＝[[1, i], [i, 1]]/√2，a＝10^(−L/20)",
            ports="每顆 MZI 的第 1 列／行＝上方波導（編號較小），第 2 列／行＝下方波導",
            phases="θ：兩顆 MMI 之間、上臂；φ：第一顆 MMI 之前、上臂；單位 rad"),
        readout=dict(ports=["o2", "o4", "o3"],
                     rule="Da＝P(o2) − P(o4)，Db＝P(o4) − P(o3)；y＝[Da＞0] AND [Db＞0]；兩個比較器門檻都是 0"),
        model=f"每顆 MZI {LOSS_DB:g} dB 插入損耗、相干輸入、單一波長",
    )


def arch(r_amp=R_AMP):
    return S.Arch.from_code(CODE, r_amp=r_amp, loss_db=LOSS_DB, order=ORDER)


def powers(A, p, V=None):
    W = A.powers(p[None])[0] if V is None else _pw(A, p, V)
    return W


def _pw(A, p, V):
    A2 = S.Arch.from_code(CODE, r_amp=R_AMP, loss_db=LOSS_DB, order=ORDER)
    A2.V = V
    return A2.powers(p[None])[0]


def decide(W, g=(1.0, 1.0, 1.0)):
    P2, P3, P4 = W[:, 1] * g[0], W[:, 2] * g[1], W[:, 3] * g[2]
    return (P2 > P4) & (P4 > P3)


def main():
    net = netlist()
    nb = (json.dumps(net, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    paths.OUT(STEP, "lut4_netlist.json").write_bytes(nb)
    sha = hashlib.sha256(nb).hexdigest()

    A = arch()
    funcs, rows = {}, []
    for name, (expr, uses, f) in FUNCS.items():
        m, p = S.synth_nb(f, A, NST, 7)
        ins = np.array([f >> x & 1 for x in range(16)], bool)
        W = A.powers(p[None])[0]
        y = decide(W)
        th, ph = [float(v % (2 * np.pi)) for v in p[0::2]], [float(v % (2 * np.pi)) for v in p[1::2]]
        funcs[name] = dict(expr=expr, uses=uses, truth_hex=f"0x{f:04X}", theta=th, phi=ph, margin=round(float(m), 6),
                           verified=f"{int((y == ins).sum())}/16")
        for x in range(16):
            P2, P3, P4 = W[x, 1], W[x, 2], W[x, 3]
            rows.append([name, x & 1, x >> 1 & 1, x >> 2 & 1, x >> 3 & 1, int(ins[x]),
                         round(P2, 6), round(P3, 6), round(P4, 6), round(P2 - P4, 6), round(P4 - P3, 6), int(y[x])])
        print(name, f"0x{f:04X}", round(m, 4), funcs[name]["verified"], flush=True)
    ph = dict(netlist="lut4_netlist.json", netlist_sha256=sha, unit="rad", R=R_AMP, loss_db_per_mzi=LOSS_DB,
              phase_order="θ_k、φ_k 依 MZI-1…MZI-7", functions=funcs)
    paths.OUT(STEP, "phases.json").write_text(json.dumps(ph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(paths.OUT(STEP, "truth_tables.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["function", "x1", "x2", "x3", "x4", "target", "P2", "P3", "P4", "Da", "Db", "bit"])
        w.writerows(rows)

    # ---------- 容許範圍 ----------
    X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)
    def V_of(R, in_phase=None):
        V = np.zeros((16, 5), complex); V[:, :4] = 1 - 2 * X; V[:, 4] = R          # v2：E±（位元 0＝+E、1＝−E），R＝+E
        if in_phase is not None: V = V * np.exp(1j * in_phase)[None, :]
        return V
    R_ok = {}
    for name, fdat in funcs.items():
        p = np.ravel(np.column_stack([fdat["theta"], fdat["phi"]]))
        ins = np.array([int(fdat["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
        good = [float(R) for R in R_SCAN if (decide(_pw(A, p, V_of(R))) == ins).all()]
        # 取包含 3 的連續區間
        lo = hi = R_AMP
        while round(lo - 0.01, 3) in good: lo = round(lo - 0.01, 3)
        while round(hi + 0.01, 3) in good: hi = round(hi + 0.01, 3)
        R_ok[name] = [lo, hi]
    R_all = [max(v[0] for v in R_ok.values()), min(v[1] for v in R_ok.values())]

    rng_seed = 700
    in_pass, ph_pass = {}, {}
    for s in SIG_IN:
        in_pass[str(s)] = {}
        for name, fdat in funcs.items():
            p = np.ravel(np.column_stack([fdat["theta"], fdat["phi"]]))
            ins = np.array([int(fdat["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
            rng = np.random.default_rng(rng_seed)
            ok = sum((decide(_pw(A, p, V_of(R_AMP, rng.normal(0, s, 5)))) == ins).all() for _ in range(TRIALS))
            in_pass[str(s)][name] = ok / TRIALS
    for s in SIG_PH:
        ph_pass[str(s)] = {}
        for name, fdat in funcs.items():
            p = np.ravel(np.column_stack([fdat["theta"], fdat["phi"]]))
            ins = np.array([int(fdat["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
            rng = np.random.default_rng(rng_seed + 1)
            ok = sum((decide(A.powers((p + rng.normal(0, s, 14))[None])[0]) == ins).all() for _ in range(TRIALS))
            ph_pass[str(s)][name] = ok / TRIALS
    sig_in_ok = max([s for s in SIG_IN if all(v == 1.0 for v in in_pass[str(s)].values())], default=0.0)
    sig_ph_ok = max([s for s in SIG_PH if all(v == 1.0 for v in ph_pass[str(s)].values())], default=0.0)
    gain = {}
    for name, fdat in funcs.items():
        p = np.ravel(np.column_stack([fdat["theta"], fdat["phi"]]))
        ins = np.array([int(fdat["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
        W = A.powers(p[None])[0]
        tol = {}
        for i, ch in enumerate(("o2", "o3", "o4")):
            lim = []
            for sg in (1, -1):
                g = 0.0
                while g < 0.6:
                    gg = [1.0, 1.0, 1.0]; gg[i] = 1 + sg * (g + 0.001)
                    if not (decide(W, gg) == ins).all(): break
                    g += 0.001
                lim.append(round(g, 3))
            tol[ch] = min(lim)
        gain[name] = tol
    power = {}
    for name, fdat in funcs.items():
        pw = [(v % (2 * np.pi)) / np.pi * P_PI_MW for v in fdat["theta"] + fdat["phi"]]
        power[name] = dict(total_mW=round(float(sum(pw)), 1), max_single_mW=round(float(max(pw)), 1))
    worst = round(14 * 2 * P_PI_MW, 0)
    tol = dict(R_nominal=R_AMP, R_scan=[2.0, 4.0, 0.01], R_range_per_function=R_ok, R_range_all=R_all,
               R_power_range_pct=[round((R_all[0] / R_AMP) ** 2 * 100 - 100, 1), round((R_all[1] / R_AMP) ** 2 * 100 - 100, 1)],
               input_phase_pass=in_pass, input_phase_sigma_ok=sig_in_ok, heater_phase_pass=ph_pass, heater_phase_sigma_ok=sig_ph_ok,
               trials=TRIALS, P_pi_mW=P_PI_MW, heater_power=power, worst_mW=worst, gain_tolerance=gain,
               phase_step_mW_per_0p05rad=round(0.05 / np.pi * P_PI_MW, 3))
    paths.OUT(STEP, "tolerance.json").write_text(json.dumps(tol, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 規格（格式同 B7 規格，佈局程式直接讀） ----------
    notes_out = {0: "監看（總功率核對、校正）", 1: "判讀：上界 P(o2)", 2: "判讀：下界 P(o3)", 3: "判讀：中間 P(o4)", 4: "監看（總功率核對、校正）"}
    optical = ([dict(port=f"in{k}", signal=s, direction="輸入", coupler="EC", edge="西緣（左）",
                     note="資料光 E+／E−（位元 0＝+E、1＝−E）" if k < 4 else f"參考光，振幅 {R_AMP:g}（功率 {R_AMP ** 2:g} P_u），與位元 0 同相（+E）")
                for k, s in enumerate(["x1", "x2", "x3", "x4", "R"])]
               + [dict(port=f"out{k}", signal=f"o{k + 1}", direction="輸出", coupler="EC", edge="東緣（右）", note=notes_out[k])
                  for k in range(5)])
    channels = []
    for k, m in enumerate(net["mzis"], 1):
        for kind, sym in (("theta", "θ"), ("phi", "φ")):
            n = len(channels) + 1
            channels.append(dict(channel=f"MZI{k}_{kind}", mzi=m["name"], phase=f"{sym}{k}", heater=f"H{n:02d}",
                                 pad=f"P{n:02d}", phase_index=k - 1, kind=kind))
    fl = "、".join(funcs)
    req = [
        dict(id="O1", item="光學輸入", value="5 路（x1–x4、R），單模、TE、1550 nm，全部來自同一顆雷射（相干）；x1–x4 為二相位 E+／E−（相位 0／π），R 不調變", verify="模擬；量測"),
        dict(id="O2", item="參考光 R", value=f"振幅 {R_AMP:g}，與位元 0 同相（+E）；功率為一路資料光的 {R_AMP ** 2:g} 倍；範例函數都判對的範圍 R＝{R_all[0]:g}–{R_all[1]:g}", verify="本步計算"),
        dict(id="O3", item="輸入之間的相對相位", value=f"5 路輸入在晶片入口的相位須固定且已知；誤差標準差 ≤ {sig_in_ok:g} rad（{TRIALS} 次模擬全對）", verify="本步計算"),
        dict(id="O4", item="光學輸出", value="5 路全部引出：o2、o4、o3 判讀；o1、o5 監看", verify="佈局"),
        dict(id="O5", item="光學耦合", value="10 個 EC，輸入在西緣、輸出在東緣，各用一組光纖陣列（250 µm）", verify="晶片整合"),
        dict(id="E1", item="相位控制通道", value="14 個（每顆 MZI 的 θ、φ 各一），每個通道一個 heater、一個訊號 PAD", verify="連接檢查"),
        dict(id="E2", item="回流", value="heater 地端在核心內就近連成共用地網，GND PAD 的數量與分組由晶片繞線決定（M2 s5），片外共地", verify="連接檢查"),
        dict(id="E3", item="相位範圍與精度", value=f"每個相位 0–2π 可調；誤差標準差 ≤ {sig_ph_ok:g} rad", verify="本步計算"),
        dict(id="E4", item="heater 功率", value=f"P_π≈{P_PI_MW:g} mW；最壞情況 14 個都接近 2π：約 {worst:g} mW", verify="本步計算；量測校正"),
        dict(id="R1", item="判讀", value="3 組 PD＋TIA（o2、o4、o3）；比較器 A：P(o2)＞P(o4)，比較器 B：P(o4)＞P(o3)；兩者 AND；門檻都是 0", verify="模擬、量測"),
        dict(id="R2", item="TIA 增益匹配", value="三路增益差須小於各函數容許量中的最小值（見 tolerance.json）；以出廠修整達成", verify="本步計算"),
        dict(id="F1", item="功能", value=f"範例函數 {fl}；每個 16 組全對（換函數只改 14 個相位）", verify="模擬"),
        dict(id="K1", item="校正", value="容許範圍是單項評估；晶片完成後依量測（MMI 損耗與分光、heater 的 P_π）重新求 14 個相位", verify="量測"),
    ]
    spec = dict(name="LUT4 單顆 PIC（Model-7a）", version="1.0",
                source=dict(netlist="lut4_netlist.json", netlist_sha256=sha, phases="phases.json", truth_table="truth_tables.csv"),
                operation="靜態驗證：每組輸入穩定後讀取",
                optical_ports=optical, phase_channels=channels, ground=dict(pads="相鄰兩個 heater 共用", shared=True),
                requirements=req, checks=dict(netlist_sha=sha == ph["netlist_sha256"], n_phase=len(channels) == 14))
    paths.OUT(STEP, "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("R 範圍", R_all, R_ok)
    print("輸入相位", in_pass, "→", sig_in_ok)
    print("heater 相位", ph_pass, "→", sig_ph_ok)
    print("增益", gain)
    print("功率", power)


if __name__ == "__main__":
    main()
