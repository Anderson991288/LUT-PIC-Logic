r"""LUT4 s2：電路模擬——3142132 換成 PDK 的 MMI 模型、用 IPKISS 電路模擬（Caphe）求散射矩陣，雙差值判讀還對嗎？

用途：
  1. PDK 電路：CORNERSTONE 2×2 MMI＋理想相位區組成 7 顆 MZI，依 lut4_netlist.json 接成 3142132，
     求 10 埠散射矩陣，取出 5×5 的 U，與接線表＋相位的矩陣乘法（無損耗）比較。
  2. 含損耗：每顆 MMI 0.45 dB（每顆 MZI 0.9 dB，與相位設定檔的模型相同），用自建 MMI 模型在 IPKISS 中求 U，
     與含損耗的矩陣乘法比較，並以 U 重算 7 個函數 × 16 組的雙差值判讀與裕量。
  3. 故障注入：只把 MMI 輸出端上下接反、把 φ 接到 MZI 下方輸入；U 的比對與真值表必須抓到。
  4. 損耗敏感度（不重新求相位）：每顆 MZI 損耗 0.0–1.6 dB，看 112 組是否全對與最小裕量；
     雷射功率整體縮放不影響雙差值判讀；但各路徑經過的 MZI 數不同，損耗改變不是整體縮放，相位應依實際損耗求解。
輸入：LUT4 s1 的 out/lut4_netlist.json、out/phases.json、out/truth_tables.csv；IPKISS 建構函式沿用 M2 s3 的 sim.py。
輸出：out/sim_results.json、out/sim_truth.csv。
執行：.\lab design\lut4\s2_sim\sim.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import importlib.util                                                # noqa: E402
import json                                                          # noqa: E402

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import T, embed                                      # noqa: E402

STEP = "lut4/s2_sim"
HAND = "lut4/s1_handoff"
LOSS_MZI_DB = 0.9
LOSS_SCAN = np.round(np.arange(0.0, 1.6001, 0.1), 2)


def load_builder():
    p = paths.STEP("m2_circuit/s3_sim") / "sim.py"
    spec = importlib.util.spec_from_file_location("b7sim", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b7sim"] = mod                                        # IPKISS 的內部類別要登記在模組上
    spec.loader.exec_module(mod)
    return mod


def chain_l(ops, th, ph, loss_db):
    a = 10 ** (-loss_db / 20)
    U = np.eye(5, dtype=complex)
    for (rail, _), t, p in zip(ops, th, ph):
        U = embed(a * T(t, p), rail, 5) @ U
    return U


def judge(U, R, ins_of):
    """16 組輸入（x1 為最低位元）的雙差值判讀、逐點裕量。"""
    X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)
    V = np.zeros((16, 5), complex); V[:, :4] = X; V[:, 4] = R
    P = np.abs(V @ U.T) ** 2
    Da, Db = P[:, 1] - P[:, 3], P[:, 3] - P[:, 2]
    y = (Da > 0) & (Db > 0)
    m = np.where(ins_of, np.minimum(Da, Db), np.maximum(-Da, -Db))
    return P, Da, Db, y, float(m.min())


def main():
    net = json.loads(paths.OUT(HAND, "lut4_netlist.json").read_text(encoding="utf-8"))
    ph = json.loads(paths.OUT(HAND, "phases.json").read_text(encoding="utf-8"))
    ops = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]
    B = load_builder()
    cornerstone, cs, K = B.build_ipkiss()
    pdk = lambda j: cs.SOI220nm_1550nm_TE_STRIP_2x2_MMI()
    lossy = lambda j: K["NonIdealMMI"](delta=0.0, loss_db=LOSS_MZI_DB / 2)

    per, rows, faults = {}, [], {}
    err_pdk, err_loss = 0.0, 0.0
    refl_max = 0.0
    for n, f in ph["functions"].items():
        ins = np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
        U0, refl, back = B.U_of(K["smatrix"](K["b7"](net, f, pdk)), net)
        e0 = float(np.max(np.abs(U0 - chain_l(ops, f["theta"], f["phi"], 0.0))))
        U1, refl1, _ = B.U_of(K["smatrix"](K["b7"](net, f, lossy)), net)
        e1 = float(np.max(np.abs(U1 - chain_l(ops, f["theta"], f["phi"], LOSS_MZI_DB))))
        P, Da, Db, y, mg = judge(U1, ph["R"], ins)
        err_pdk, err_loss, refl_max = max(err_pdk, e0), max(err_loss, e1), max(refl_max, refl, refl1, back)
        energy = float(np.max(np.abs(np.sum(np.abs(U0) ** 2, axis=0) - 1)))
        per[n] = dict(U_err_pdk=e0, U_err_lossy=e1, energy_err_pdk=energy, passed=int((y == ins).sum()), margin=round(mg, 6),
                      margin_handoff=f["margin"])
        for x in range(16):
            rows.append(dict(function=n, x1=x & 1, x2=x >> 1 & 1, x3=x >> 2 & 1, x4=x >> 3 & 1, target=int(ins[x]),
                             P2=round(P[x, 1], 6), P3=round(P[x, 2], 6), P4=round(P[x, 3], 6),
                             Da=round(Da[x], 6), Db=round(Db[x], 6), bit=int(y[x])))
    f0n, f0 = next(iter(ph["functions"].items()))
    for mode in ("swap_out", "phi_low"):
        tot, emax = 0, 0.0
        for n, f in ph["functions"].items():
            ins = np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
            U, _, _ = B.U_of(K["smatrix"](K["b7"](net, f, lossy, mode)), net)
            emax = max(emax, float(np.max(np.abs(U - chain_l(ops, f["theta"], f["phi"], LOSS_MZI_DB)))))
            tot += int((judge(U, ph["R"], ins)[3] == ins).sum())
        faults[mode] = dict(U_err_max=emax, passed=tot, caught=emax > 1e-6 and tot < 16 * len(per))
    sweep = []
    for L in LOSS_SCAN:
        tot, mmin = 0, 1e9
        for n, f in ph["functions"].items():
            ins = np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
            _, _, _, y, mg = judge(chain_l(ops, f["theta"], f["phi"], float(L)), ph["R"], ins)
            tot += int((y == ins).sum()); mmin = min(mmin, mg)
        sweep.append(dict(loss_db=float(L), passed=tot, margin_min=round(mmin, 6)))
    total = 16 * len(per)
    checks = dict(pdk_U_match=err_pdk < 1e-9, lossy_U_match=err_loss < 1e-9, no_reflection=refl_max < 1e-12,
                  all_pass=sum(v["passed"] for v in per.values()) == total, faults_caught=all(v["caught"] for v in faults.values()))
    out = dict(model=dict(pdk="CORNERSTONE SOI220nm_1550nm_TE_STRIP_2x2_MMI", wavelength_um=B.WL, lossy_mmi_db=LOSS_MZI_DB / 2),
               U_err_pdk=err_pdk, U_err_lossy=err_loss, reflection_max=refl_max, functions=per,
               passed=sum(v["passed"] for v in per.values()), total=total, faults=faults, loss_sweep=sweep, checks=checks)
    paths.OUT(STEP, "sim_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(paths.OUT(STEP, "sim_truth.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"PDK 電路：‖U−U_ref‖max {err_pdk:.1e}；含損耗 {err_loss:.1e}；反射 {refl_max:.1e}；{out['passed']}/{total}")
    for n, v in per.items():
        print(f"  {n}: {v['passed']}/16 裕量 {v['margin']:.4f}（交接 {v['margin_handoff']:.4f}）")
    print("故障注入", faults)
    print("損耗掃描", [(s["loss_db"], s["passed"], s["margin_min"]) for s in sweep])
    print("一致性", checks)
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
