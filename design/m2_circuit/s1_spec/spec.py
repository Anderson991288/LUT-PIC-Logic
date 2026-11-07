r"""M2 s1：PIC 功能與介面規格——晶片和外部設備的邊界在哪？14 個相位怎麼接到 PAD？外部設備要多準？

用途：只讀 M1 的三個交接檔（接線表、相位設定檔、真值表），產生晶片的介面規格 spec.json，並算出介面需要的容許範圍：
  1. 光學介面：5 個輸入、5 個輸出都接到晶片邊緣的 EC；o2、o4 判讀，o1、o3、o5 作為監看埠（總功率核對、校正用）。
  2. 電氣介面：14 個相位各對應一個 heater 與一個訊號 PAD，回流共用 GND PAD。
  3. 參考光容許範圍：相位固定（M1 s5 的相位設定檔），只改 R 的振幅（2.0–4.0，步長 0.005），找出五個函數 80 組都判對的 R 範圍。
  4. 輸入相對相位容許誤差：5 路輸入（x1–x4、R）各加常態分佈的相位誤差（標準差 σ），各 500 次（種子 700＋k），
     看五個函數真值表全對的比例；R 與資料光要來自同一顆雷射，路徑長度差會變成這種相位誤差。
  5. heater 功率預算：相位 φ 需要的功率 P＝(φ mod 2π)/π·P_π（P_π＝13 mW，同平台 TiN heater 的實測值）；
     各函數的總功率，以及校正後最壞情況（每個 heater 都可能需要接近 2π）的上限。
  6. 一致性檢查：接線表的 SHA-256 與相位檔記錄的相同；14 個相位都有通道；埠名與接線表一致。
輸入：M1 s5 的 out/b7_netlist.json、out/phases.json、out/truth_tables.csv。
輸出：out/spec.json（介面規格與需求表）、out/tolerance.json（第 3–5 項的計算結果）。
執行：.\lab design\m2_circuit\s1_spec\spec.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import B7_OPS, READ, chain                           # noqa: E402

STEP = "m2_circuit/s1_spec"
HAND = "m1_logic/s5_handoff"
P_PI_MW = 13.0                       # TiN heater 的 P_π（同平台實測，見報告引用）
R_SCAN = np.round(np.arange(2.0, 4.0001, 0.005), 3)
SIG_IN = [0.02, 0.05, 0.1, 0.2]      # 輸入相對相位誤差標準差（rad）
TRIALS = 500


def load():
    nb = paths.OUT(HAND, "b7_netlist.json").read_bytes()
    net = json.loads(nb)
    ph = json.loads(paths.OUT(HAND, "phases.json").read_text(encoding="utf-8"))
    with open(paths.OUT(HAND, "truth_tables.csv"), encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return net, ph, rows, hashlib.sha256(nb).hexdigest()


def target_of(rows):
    t = {}
    for r in rows:
        t.setdefault(r["function"], {})[r["x1"] + r["x2"] + r["x3"] + r["x4"]] = int(r["target"])
    return t


def dP_all(U, R, in_phase=None):
    """16 組輸入的 ΔP；in_phase：5 路輸入的額外相位（rad）。"""
    words = [format(k, "04b") for k in range(16)]
    V = np.array([[int(c) for c in w] + [R] for w in words], dtype=complex)
    if in_phase is not None:
        V = V * np.exp(1j * np.asarray(in_phase))
    P = np.abs(V @ U.T) ** 2
    return words, P[:, READ[0]] - P[:, READ[1]]


def main():
    net, ph, rows, sha = load()
    tgt = target_of(rows)
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    checks = dict(netlist_sha=sha == ph["netlist_sha256"], ops_match=ops == list(B7_OPS),
                  n_phase=all(len(f["theta"]) == 7 and len(f["phi"]) == 7 for f in ph["functions"].values()))
    U = {n: chain(ops, f["theta"], f["phi"], 5) for n, f in ph["functions"].items()}

    # 3. R 的容許範圍（相位固定）
    ok_R = []
    for R in R_SCAN:
        good = True
        for n in U:
            words, d = dP_all(U[n], R)
            good &= all((x > 0) == bool(tgt[n][w]) and x != 0 for w, x in zip(words, d))
        ok_R.append(bool(good))
    ok_R = np.array(ok_R)
    R0 = ph["R"]
    i0 = int(np.argmin(np.abs(R_SCAN - R0)))
    lo = hi = i0
    while lo > 0 and ok_R[lo - 1]:
        lo -= 1
    while hi < len(R_SCAN) - 1 and ok_R[hi + 1]:
        hi += 1
    R_range = [float(R_SCAN[lo]), float(R_SCAN[hi])]
    per_func_R = {}
    for n in U:
        good = []
        for R in R_SCAN:
            words, d = dP_all(U[n], R)
            good.append(all((x > 0) == bool(tgt[n][w]) and x != 0 for w, x in zip(words, d)))
        g = np.array(good)
        a = b = i0
        while a > 0 and g[a - 1]:
            a -= 1
        while b < len(g) - 1 and g[b + 1]:
            b += 1
        per_func_R[n] = [float(R_SCAN[a]), float(R_SCAN[b])]

    # 4. 輸入相對相位誤差
    in_phase = {}
    for s in SIG_IN:
        res = {}
        for n in U:
            okc = 0
            for k in range(TRIALS):
                e = np.random.default_rng(700 + k).normal(0, s, 5)
                words, d = dP_all(U[n], R0, e)
                okc += all((x > 0) == bool(tgt[n][w]) and x != 0 for w, x in zip(words, d))   # 與 R 掃描相同：ΔP＝0 算失敗
            res[n] = okc / TRIALS
        in_phase[str(s)] = res

    sig_ok = max((s for s in SIG_IN if all(v == 1.0 for v in in_phase[str(s)].values())), default=0.0)

    # 5. heater 功率預算
    power = {}
    for n, f in ph["functions"].items():
        w = np.mod(np.array(list(f["theta"]) + list(f["phi"])), 2 * np.pi)
        w[np.isclose(w, 2 * np.pi, atol=1e-6)] = 0.0                   # 2π−1e-13 這類值等於 0 相位，不需要功率（M2 審查 R1）
        p = w / np.pi * P_PI_MW
        power[n] = dict(total_mW=round(float(sum(p)), 1), max_single_mW=round(float(max(p)), 1))
    worst = 14 * 2 * P_PI_MW

    tol = dict(R_nominal=R0, R_scan=[float(R_SCAN[0]), float(R_SCAN[-1]), 0.005], R_range_all=R_range,
               R_range_per_function=per_func_R, R_power_range_pct=[round(100 * ((R_range[0] / R0) ** 2 - 1), 1),
                                                                    round(100 * ((R_range[1] / R0) ** 2 - 1), 1)],
               input_phase_pass=in_phase, input_phase_sigma_ok=sig_ok, trials=TRIALS, P_pi_mW=P_PI_MW, heater_power=power,
               worst_case_total_mW=worst, phase_step_mW_per_0p05rad=round(0.05 / np.pi * P_PI_MW, 3))
    paths.OUT(STEP, "tolerance.json").write_text(json.dumps(tol, ensure_ascii=False, indent=2), encoding="utf-8")

    # 規格
    sides = {"in": "西緣（左）", "out": "東緣（右）"}
    optical = ([dict(port=i["layout_port"], signal=i["signal"], direction="輸入", coupler="EC", edge=sides["in"],
                     note="資料光 0／1" if i["signal"] != "R" else f"參考光，振幅 {R0:g}（功率 {R0 ** 2:g} P_u）")
                for i in net["inputs"]]
               + [dict(port=o["layout_port"], signal=o["name"], direction="輸出", coupler="EC", edge=sides["out"],
                       note="判讀" if o["role"] == "判讀" else "監看（總功率核對、校正）") for o in net["outputs"]])
    channels = []
    for k, m in enumerate(net["mzis"], 1):
        for kind, sym in (("theta", "θ"), ("phi", "φ")):
            channels.append(dict(channel=f"MZI{k}_{kind}", mzi=m["name"], phase=f"{sym}{k}", heater=f"H{len(channels) + 1:02d}",
                                 pad=f"P{len(channels) + 1:02d}", phase_index=k - 1, kind=kind))
    req = [
        dict(id="O1", item="光學輸入", value="5 路（x1–x4、R），單模、TE、1550 nm，全部來自同一顆雷射（相干）", verify="M2 s3 模擬；量測"),
        dict(id="O2", item="參考光 R", value=f"振幅 {R0:g}（功率為一路資料「1」的 {R0 ** 2:g} 倍）；五個函數都判對的範圍 R＝{R_range[0]:g}–{R_range[1]:g}", verify="本步計算"),
        dict(id="O3", item="輸入之間的相對相位", value=f"5 路輸入在晶片入口的相位須固定且已知；誤差標準差 ≤ {sig_ok:g} rad"
             f"（試過的 σ 中 {TRIALS} 次模擬全對的最大值；95% 信心下失敗率 < 0.6%）", verify="本步計算"),
        dict(id="O4", item="光學輸出", value="5 路全部引出：o2、o4 判讀；o1、o3、o5 監看", verify="M3 佈局"),
        dict(id="O5", item="光學耦合", value="10 個 EC，輸入在西緣、輸出在東緣，各用一組光纖陣列", verify="M3 s3"),
        dict(id="E1", item="相位控制通道", value="14 個（每顆 MZI 的 θ、φ 各一），每個通道一個 heater、一個訊號 PAD", verify="M3 s4 連接檢查"),
        dict(id="E2", item="回流", value="所有 heater 的地端都接到 GND PAD；GND PAD 數量在 M3 s3 依繞線決定（至少 1 個）；"
             "分成數個時在片外共地（M3 審查 R19）", verify="M3 s4 連接檢查"),
        dict(id="E3", item="相位範圍與精度", value=f"每個相位 0–2π 可調；誤差標準差 ≤ 0.05 rad（約 {tol['phase_step_mW_per_0p05rad']:g} mW 的 heater 功率）", verify="M1 s4 相位誤差模擬"),
        dict(id="E4", item="heater 功率", value=f"P_π≈{P_PI_MW:g} mW；最壞情況全部 14 個需近 2π：約 {worst:g} mW", verify="本步計算；量測校正"),
        dict(id="R1", item="判讀", value="ΔP＝P(o2) − P(o4)；ΔP＞0 判 1、ΔP＜0 判 0；兩個偵測器極性不可接反", verify="M2 s3、量測"),
        dict(id="F1", item="功能", value="AND2、OR2、XOR2、AND4、OR4；每個 16 組、共 80 組全對", verify="M2 s3 模擬"),
        dict(id="K1", item="校正", value="O2、O3 與 E3 的容許範圍是單項評估（MMI 理想、其他誤差為 0）；晶片完成後要依量測"
             "（MMI 損耗與分光、heater 的 P_π）重新求 14 個相位，M1 的相位只當起點，並在校正後的相位下重算容許範圍",
             verify="M3 s5 交付文件；量測（M2 審查 R2）"),
    ]
    spec = dict(name="B7 單顆 PIC", version="1.0", source=dict(netlist="b7_netlist.json", netlist_sha256=sha,
                                                                 phases="phases.json", truth_table="truth_tables.csv"),
                operation="靜態驗證：每組輸入穩定後讀取；高速資料的時序不在本課程範圍",
                optical_ports=optical, phase_channels=channels, ground=dict(pads="≥1，數量在 M3 s3 決定", shared=True),
                requirements=req, checks=checks)
    paths.OUT(STEP, "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"一致性：{checks}")
    print(f"R 範圍（五個函數都對）：{R_range}（功率 {tol['R_power_range_pct']} %）；各函數：{per_func_R}")
    for s, r in in_phase.items():
        print(f"輸入相位 σ＝{s} rad：" + "、".join(f"{n} {v:.1%}" for n, v in r.items()))
    print("heater 總功率（mW）：" + "、".join(f"{n} {v['total_mW']}" for n, v in power.items()) + f"；最壞情況 {worst:g}")
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'spec.json'))}、tolerance.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
