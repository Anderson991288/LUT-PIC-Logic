r"""M2 s3：電路模擬——把 B7 換成 PDK 的 MMI 模型、用 IPKISS 電路模擬求散射矩陣，真值表還對嗎？MMI 不理想時呢？

用途：
  1. PDK MMI 本身：取出 CORNERSTONE 2×2 MMI 在 1.55 µm 的散射矩陣，依「in2／out2 在上方」對應成 2×2 矩陣，與理想 H 比較。
  2. 整顆 B7：依元件清單（M2 s2）用 PDK MMI＋自建理想相位區（e^{iφ}）組成 7 顆 MZI，再依接線表接成 B7，
     由 IPKISS 電路模擬（Caphe）求 10 埠散射矩陣 S；取出 5×5 的 U（輸入 in0–in4 → 輸出 out0–out4），
     與 M1 的矩陣乘法 U_ref 比較；檢查反射為 0、能量守恆；用 U 重算 80 組真值表與 margin。
  3. 故障注入（接線常見錯誤）：
       a. 每顆 MMI 的輸入、輸出都把上下接反——MMI 上下對稱，預期 U 不變（不是錯誤）；
       b. 只把 MMI 輸出端接反；c. 把 φ 接到 MZI 的下方輸入。b、c 必須被 U 的比對抓到。
  4. MMI 不理想（PDK 模型沒有包含的情況）：自建一個有分光偏差 δ 與額外損耗的 MMI 模型，
     先用 IPKISS 與 NumPy 各算一次確認一致，再用 NumPy 掃描：
       a. 每顆 MMI 額外損耗 0–1.5 dB（同一值）；
       b. 每顆 MMI 同一個分光偏差 δ（直通功率比例 0.5＋δ），δ＝−0.15～0.15；
       c. 每顆 MMI 各自隨機 δ～N(0, σ²)，σ＝0.01、0.02、0.05，加上實測損耗 0.33 dB，各 500 次（種子 700＋k）。
     相位維持 M1 的設定（不重新校正），看 80 組是否全對、margin 剩多少。
  5. 重新校正：在損耗 0.33 dB 的模型下，以 M1 s4 的方法與設定（SLSQP，24 個起點，種子 700＋k，maxiter 600）重找 14 個相位，看 margin 能否補回。
輸入：M1 s5 的 out/b7_netlist.json、out/phases.json、out/truth_tables.csv；M2 s1 的 out/spec.json；M2 s2 的 out/components.json。
輸出：out/sim_results.json（摘要與檢查）、out/sim_truth.csv（PDK 模型 80 組的 P2、P4、ΔP）、out/mmi_sweep.json（第 4 項）。
執行：.\lab design\m2_circuit\s3_sim\sim.py
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
from common.optics import H                                          # noqa: E402
from common.synth import best_margin                                 # noqa: E402

STEP = "m2_circuit/s3_sim"
HAND = "m1_logic/s5_handoff"
WL = 1.55                                   # µm
LOSS_MEAS_DB = 0.33                         # 每顆 2×2 MMI 的實測額外損耗（同平台 0.30–0.36 dB 的中間值）
LOSS_SCAN = np.round(np.arange(0.0, 1.5001, 0.01), 2)
DELTA_SCAN = np.round(np.arange(-0.15, 0.15001, 0.0025), 4)
SIG_D = [0.01, 0.02, 0.05]
TRIALS = 500
RECAL_STARTS = 24                           # 與 M1 s4 相同：24 個起點、maxiter 600（M2 審查 R4）
RECAL_MAXITER = 600
OPS = None                                  # 由接線表推出的 MZI 位置，main() 設定
WORDS = [format(k, "04b") for k in range(16)]


# ---------- 讀交接檔 ----------
def load():
    nb = paths.OUT(HAND, "b7_netlist.json").read_bytes()
    net = json.loads(nb)
    ph = json.loads(paths.OUT(HAND, "phases.json").read_text(encoding="utf-8"))
    spec = json.loads(paths.OUT("m2_circuit/s1_spec", "spec.json").read_text(encoding="utf-8"))
    comp = json.loads(paths.OUT("m2_circuit/s2_flow", "components.json").read_text(encoding="utf-8"))
    with open(paths.OUT(HAND, "truth_tables.csv"), encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    tgt, dP_m1 = {}, {}
    for r in rows:
        w = r["x1"] + r["x2"] + r["x3"] + r["x4"]
        tgt.setdefault(r["function"], {})[w] = int(r["target"])
        dP_m1.setdefault(r["function"], {})[w] = float(r["dP"])
    sha = hashlib.sha256(nb).hexdigest()
    ok = dict(netlist_sha=sha == ph["netlist_sha256"] == spec["source"]["netlist_sha256"])
    return net, ph, comp, tgt, dP_m1, ok


def truth(U, R, tgt_f):
    """16 組的 P2、P4、ΔP、判讀是否正確，以及 margin＝min s·ΔP。"""
    V = np.array([[int(c) for c in w] + [R] for w in WORDS], dtype=complex)
    P = np.abs(V @ U.T) ** 2
    d = P[:, READ[0]] - P[:, READ[1]]
    s = np.array([1 if tgt_f[w] else -1 for w in WORDS])
    return P, d, int(np.sum(s * d > 0)), float(np.min(s * d))


# ---------- IPKISS 電路 ----------
def build_ipkiss():
    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)              # 要在 import cornerstone 之前選定變體
    import cornerstone
    import cornerstone.all as cs
    import ipkiss3.all as i3

    class PhaseModel(i3.CompactModel):
        """理想相位區：光通過時乘上 e^{iφ}，無損耗、無反射。"""
        parameters = ["phase"]
        terms = [i3.OpticalTerm(name="in"), i3.OpticalTerm(name="out")]

        def calculate_smatrix(parameters, env, S):
            S["out", "in"] = S["in", "out"] = np.exp(1j * parameters.phase)

    class IdealPhase(i3.PCell):
        phase = i3.NumberProperty(default=0.0)

        class Netlist(i3.NetlistView):
            def _generate_terms(self, terms):
                terms += i3.OpticalTerm(name="in")
                terms += i3.OpticalTerm(name="out")
                return terms

        class CircuitModel(i3.CircuitModelView):
            def _generate_model(self):
                return PhaseModel(phase=self.cell.phase)

    class MMIModel(i3.CompactModel):
        """不理想的 2×2 MMI：直通功率比例 0.5＋δ、交叉 0.5−δ，額外損耗 loss_db；埠名與 PDK 相同（in2／out2 在上方）。"""
        parameters = ["delta", "loss_db"]
        terms = [i3.OpticalTerm(name=n) for n in ("in1", "in2", "out1", "out2")]

        def calculate_smatrix(parameters, env, S):
            a = 10 ** (-parameters.loss_db / 20)
            t = a * np.sqrt(0.5 + parameters.delta) + 0j           # 逐項寫出：這個函式由 numba 編譯，不能迭代混合型別的 tuple
            k = 1j * a * np.sqrt(0.5 - parameters.delta)
            S["out2", "in2"] = S["in2", "out2"] = t
            S["out1", "in1"] = S["in1", "out1"] = t
            S["out2", "in1"] = S["in1", "out2"] = k
            S["out1", "in2"] = S["in2", "out1"] = k

    class NonIdealMMI(i3.PCell):
        delta = i3.NumberProperty(default=0.0)
        loss_db = i3.NumberProperty(default=0.0)

        class Netlist(i3.NetlistView):
            def _generate_terms(self, terms):
                for n in ("in1", "in2", "out1", "out2"):
                    terms += i3.OpticalTerm(name=n)
                return terms

        class CircuitModel(i3.CircuitModelView):
            def _generate_model(self):
                return MMIModel(delta=self.cell.delta, loss_db=self.cell.loss_db)

    def mzi(theta, phi, mmi1, mmi2, mode="ok"):
        """T＝H·diag(e^{iθ},1)·H·diag(e^{iφ},1)：φ 在上方輸入、θ 在上臂。上方＝in2／out2。
        mode：ok 正確；swap_all MMI 輸入輸出都上下接反；swap_out 只有輸出接反；phi_low φ 接到下方輸入。"""
        up_i, lo_i = ("in1", "in2") if mode == "swap_all" else ("in2", "in1")
        up_o, lo_o = ("out1", "out2") if mode in ("swap_all", "swap_out") else ("out2", "out1")
        t_name, b_name = ("b_in", "t_in") if mode == "phi_low" else ("t_in", "b_in")
        return i3.ConnectComponents(
            child_cells=dict(mmi1=mmi1, mmi2=mmi2, th=IdealPhase(phase=float(theta)), ph=IdealPhase(phase=float(phi))),
            links=[("ph:out", f"mmi1:{up_i}"), (f"mmi1:{up_o}", "th:in"), ("th:out", f"mmi2:{up_i}"),
                   (f"mmi1:{lo_o}", f"mmi2:{lo_i}")],
            external_port_names={"ph:in": t_name, f"mmi1:{lo_i}": b_name, f"mmi2:{up_o}": "t_out", f"mmi2:{lo_o}": "b_out"})

    def b7(net, f, mmi_factory, mode="ok"):
        """依接線表的 MZI 順序，追蹤每條波導目前的來源埠，把 7 顆 MZI 接起來。"""
        n = net["n_waveguides"]
        ins = {i["index"]: i["layout_port"] for i in net["inputs"]}
        outs = {o["index"]: o["layout_port"] for o in net["outputs"]}
        src = {k: ("ext", ins[k]) for k in range(1, n + 1)}
        children, links, ext = {}, [], {}
        for j, m in enumerate(net["mzis"]):
            a, b = m["waveguides"]
            name = f"M{j + 1}"
            children[name] = mzi(f["theta"][j], f["phi"][j], mmi_factory(2 * j), mmi_factory(2 * j + 1), mode)
            for wg, port in ((a, "t_in"), (b, "b_in")):
                kind, p = src[wg]
                if kind == "ext":
                    ext[f"{name}:{port}"] = p
                else:
                    links.append((p, f"{name}:{port}"))
            src[a], src[b] = ("int", f"{name}:t_out"), ("int", f"{name}:b_out")
        for k in range(1, n + 1):
            kind, p = src[k]
            assert kind == "int", f"波導 {k} 沒有經過任何 MZI"
            ext[p] = outs[k]
        return i3.ConnectComponents(child_cells=children, links=links, external_port_names=ext)

    def smatrix(cell, wl=WL):
        return cell.CircuitModel().get_smatrix(wavelengths=np.array([wl]))

    return cornerstone, cs, dict(b7=b7, smatrix=smatrix, NonIdealMMI=NonIdealMMI)


def U_of(S, net):
    ins = [i["layout_port"] for i in net["inputs"]]
    outs = [o["layout_port"] for o in net["outputs"]]
    U = np.array([[S[o, i][0] for i in ins] for o in outs])
    refl = max(abs(S[p, p][0]) for p in ins + outs)
    back = max(abs(S[i, j][0]) for i in ins for j in ins if i != j)      # 輸入埠之間不應互通
    return U, float(refl), float(back)


# ---------- NumPy：不理想 MMI ----------
def Hn(delta, loss_db):
    a = 10 ** (-loss_db / 20)
    return a * np.array([[np.sqrt(0.5 + delta), 1j * np.sqrt(0.5 - delta)], [1j * np.sqrt(0.5 - delta), np.sqrt(0.5 + delta)]])


def chain_ni(theta, phi, deltas, loss_db, n=5):
    U = np.eye(n, dtype=complex)
    for j, ((rail, _), th, ph) in enumerate(zip(OPS, theta, phi)):
        t = Hn(deltas[2 * j + 1], loss_db) @ np.diag([np.exp(1j * th), 1]) @ Hn(deltas[2 * j], loss_db) @ np.diag([np.exp(1j * ph), 1])
        m = np.eye(n, dtype=complex)
        m[rail:rail + 2, rail:rail + 2] = t
        U = m @ U
    return U


def eval_all(ph, tgt, deltas, loss_db):
    res = {}
    for n, f in ph["functions"].items():
        _, _, ok, mg = truth(chain_ni(f["theta"], f["phi"], deltas, loss_db), ph["R"], tgt[n])
        res[n] = (ok, mg)
    return sum(v[0] for v in res.values()), min(v[1] for v in res.values()), res


def contiguous(ok, x, x0):
    i0 = int(np.argmin(np.abs(x - x0)))
    lo = hi = i0
    while lo > 0 and ok[lo - 1]:
        lo -= 1
    while hi < len(x) - 1 and ok[hi + 1]:
        hi += 1
    return [float(x[lo]), float(x[hi])] if ok[i0] else None


def main():
    net, ph, comp, tgt, dP_m1, checks = load()
    global OPS
    OPS = [(m["waveguides"][0] - 1, m["layer"] - 1) for m in net["mzis"]]   # U_ref 只依交接檔的接線表
    mmi_cell = next(c["pdk"]["cell"] for c in comp["components"] if c["id"] == "C1")
    cornerstone, cs, K = build_ipkiss()
    pdk_mmi = lambda j: getattr(cs, mmi_cell)()                                           # noqa: E731

    # 1. PDK MMI 本身（上方＝in2／out2）
    mmi_err = {}
    for wl in (1.50, 1.55, 1.60):
        S = K["smatrix"](pdk_mmi(0), wl)
        Hp = np.array([[S[o, i][0] for i in ("in2", "in1")] for o in ("out2", "out1")])
        mmi_err[f"{wl:.2f}"] = float(np.max(np.abs(Hp - H)))

    # 2. 整顆 B7（PDK MMI＋理想相位）
    per, rows, U_err_max = {}, [], 0.0
    for n, f in ph["functions"].items():
        S = K["smatrix"](K["b7"](net, f, pdk_mmi))
        U, refl, back = U_of(S, net)
        U_ref = chain(OPS, f["theta"], f["phi"], 5)
        err = float(np.max(np.abs(U - U_ref)))
        U_err_max = max(U_err_max, err)
        P, d, ok, mg = truth(U, ph["R"], tgt[n])
        V = np.array([[int(c) for c in w] + [ph["R"]] for w in WORDS])
        energy = float(np.max(np.abs(P.sum(1) - (np.abs(V) ** 2).sum(1))))
        d_vs_m1 = float(max(abs(d[k] - dP_m1[n][w]) for k, w in enumerate(WORDS)))
        per[n] = dict(passed=ok, total=16, margin=round(mg, 6), U_err=err, reflection=refl, input_crosstalk=back,
                      energy_err=energy, dP_vs_M1_csv=d_vs_m1)
        for k, w in enumerate(WORDS):
            rows.append(dict(function=n, x1=w[0], x2=w[1], x3=w[2], x4=w[3], target=tgt[n][w], P2=round(P[k, READ[0]], 6),
                             P4=round(P[k, READ[1]], 6), dP=round(d[k], 6), bit=int(d[k] > 0)))
        print(f"{n}: {ok}/16，margin {mg:.4f}，‖U−U_ref‖max {err:.1e}，反射 {refl:.1e}")

    # 3. 故障注入
    faults = {}
    for mode in ("swap_all", "swap_out", "phi_low"):
        r = {}
        for n, f in ph["functions"].items():
            U, _, _ = U_of(K["smatrix"](K["b7"](net, f, pdk_mmi, mode)), net)
            _, _, ok, _ = truth(U, ph["R"], tgt[n])
            r[n] = dict(passed=ok, U_err=float(np.max(np.abs(U - chain(OPS, f["theta"], f["phi"], 5)))))
        faults[mode] = dict(passed=sum(v["passed"] for v in r.values()), U_err_max=max(v["U_err"] for v in r.values()),
                            per_function=r)

    # 4. 不理想 MMI：先核對 IPKISS 自建模型與 NumPy 一致
    rng = np.random.default_rng(700)
    dd = rng.normal(0, 0.03, 14)
    f0 = ph["functions"]["AND4"]
    U_ip, _, _ = U_of(K["smatrix"](K["b7"](net, f0, lambda j: K["NonIdealMMI"](delta=float(dd[j]), loss_db=LOSS_MEAS_DB))), net)
    ni_check = float(np.max(np.abs(U_ip - chain_ni(f0["theta"], f0["phi"], dd, LOSS_MEAS_DB))))

    zero = np.zeros(14)
    loss_ok, loss_margin, loss_mf = [], [], {n: [] for n in ph["functions"]}
    for L in LOSS_SCAN:
        p, mg, res = eval_all(ph, tgt, zero, L)
        loss_ok.append(p == 80)
        loss_margin.append(round(mg, 6))
        for n in loss_mf:
            loss_mf[n].append(round(res[n][1], 6))
    p_meas, mg_meas, res_meas = eval_all(ph, tgt, zero, LOSS_MEAS_DB)
    p0, mg0, _ = eval_all(ph, tgt, zero, 0.0)

    d_ok, d_margin, d_func, d_mf = [], [], {n: [] for n in ph["functions"]}, {n: [] for n in ph["functions"]}
    for dl in DELTA_SCAN:
        p, mg, res = eval_all(ph, tgt, np.full(14, dl), LOSS_MEAS_DB)
        d_ok.append(p == 80)
        d_margin.append(round(mg, 6))
        for n in d_func:
            d_func[n].append(res[n][0] == 16)
            d_mf[n].append(round(res[n][1], 6))
    rand = {}
    for s in SIG_D:
        okc, worst = 0, []
        for k in range(TRIALS):
            dl = np.clip(np.random.default_rng(700 + k).normal(0, s, 14), -0.49, 0.49)
            p, mg, _ = eval_all(ph, tgt, dl, LOSS_MEAS_DB)
            okc += p == 80
            worst.append(mg)
        rand[str(s)] = dict(pass_rate=okc / TRIALS, margin_p05=float(np.percentile(worst, 5)), margin_min=float(np.min(worst)))

    # 5. 重新校正（損耗 0.33 dB）
    recal = {}
    V = np.array([[int(c) for c in w] + [ph["R"]] for w in WORDS], dtype=complex)
    for n, f in ph["functions"].items():
        signs = np.array([1 if tgt[n][w] else -1 for w in WORDS])
        mk = lambda z: chain_ni(z[:7], z[7:], zero, LOSS_MEAS_DB)                       # noqa: E731
        m, z = best_margin(mk, 14, V, READ, signs, RECAL_STARTS, maxiter=RECAL_MAXITER)
        recal[n] = dict(margin_before=res_meas[n][1], margin_after=float(m), margin_ideal=per[n]["margin"])
        print(f"重新校正 {n}：margin {res_meas[n][1]:.4f} → {m:.4f}（理想 {per[n]['margin']:.4f}）")

    sweep = dict(loss_meas_db=LOSS_MEAS_DB, loss_scan=LOSS_SCAN.tolist(), loss_all_ok=loss_ok, loss_margin=loss_margin, loss_margin_per_function=loss_mf,
                 loss_range_ok=contiguous(np.array(loss_ok), LOSS_SCAN, 0.0),
                 delta_scan=DELTA_SCAN.tolist(), delta_all_ok=d_ok, delta_margin=d_margin, delta_margin_per_function=d_mf,
                 delta_range_ok=contiguous(np.array(d_ok), DELTA_SCAN, 0.0),
                 delta_range_per_function={n: contiguous(np.array(v), DELTA_SCAN, 0.0) for n, v in d_func.items()},
                 random=rand, trials=TRIALS, ipkiss_vs_numpy_nonideal=ni_check)
    paths.OUT(STEP, "mmi_sweep.json").write_text(json.dumps(sweep, ensure_ascii=False), encoding="utf-8")

    checks.update(ops_from_netlist_match_common=OPS == list(B7_OPS), pdk_mmi_is_H=max(mmi_err.values()) < 1e-12, all_80=sum(v["passed"] for v in per.values()) == 80,
                  U_err_lt_1e12=U_err_max < 1e-12, no_reflection=max(v["reflection"] for v in per.values()) < 1e-12,
                  energy=max(v["energy_err"] for v in per.values()) < 1e-9,
                  symmetric_swap_harmless=faults["swap_all"]["U_err_max"] < 1e-12,
                  faults_caught=all(faults[m]["U_err_max"] > 1e-3 for m in ("swap_out", "phi_low")),
                  nonideal_model_match=ni_check < 1e-12)
    out = dict(pdk=dict(name="CORNERSTONE", version=str(cornerstone.__version__), mmi_cell=mmi_cell),
               engine="IPKISS 電路模型（Caphe）", wavelength_um=WL,
               model_scope="PDK MMI 模型＋自建理想相位區；元件之間為理想連接（無傳播損耗、無 EC、無熱模型）",
               pdk_mmi_vs_H=mmi_err, functions=per, passed=sum(v["passed"] for v in per.values()), total=80,
               U_err_max=U_err_max, margin_min=min(v["margin"] for v in per.values()),
               faults=faults, recalibration=dict(loss_db=LOSS_MEAS_DB, starts=RECAL_STARTS, maxiter=RECAL_MAXITER, per_function=recal),
               nonideal=dict(loss_meas=dict(passed=p_meas, margin=mg_meas, margin_ideal=mg0,
                                            per_function={n: dict(passed=v[0], margin=v[1]) for n, v in res_meas.items()}),
                             loss_range_ok=sweep["loss_range_ok"], delta_range_ok=sweep["delta_range_ok"],
                             delta_range_per_function=sweep["delta_range_per_function"], random=rand),
               checks=checks)
    paths.OUT(STEP, "sim_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(paths.OUT(STEP, "sim_truth.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"PDK MMI 與 H 的最大差：{mmi_err}")
    print(f"PDK 模型：{out['passed']}/80，‖U−U_ref‖max {U_err_max:.1e}，最小 margin {out['margin_min']:.4f}")
    for m, v in faults.items():
        print(f"故障注入 {m}：{v['passed']}/80，‖U−U_ref‖max {v['U_err_max']:.2e}")
    print(f"不理想 MMI：IPKISS 與 NumPy 差 {ni_check:.1e}；損耗 {LOSS_MEAS_DB} dB 時 {p_meas}/80、margin {mg_meas:.4f}（理想 {mg0:.4f}）")
    print(f"全對的損耗範圍 {sweep['loss_range_ok']} dB；分光偏差 δ 範圍 {sweep['delta_range_ok']}；各函數 {sweep['delta_range_per_function']}")
    for s, r in rand.items():
        print(f"隨機 δ σ＝{s}：{r['pass_rate']:.1%} 全對，margin 5% 分位 {r['margin_p05']:.3f}")
    print(f"一致性：{checks}")
    print(f"寫出 {rt.rel(paths.OUT(STEP, 'sim_results.json'))}、sim_truth.csv、mmi_sweep.json")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
