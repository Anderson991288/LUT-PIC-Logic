r"""論文 M4 s4：UI 預算與接收端敏感度——一個 UI 被誰吃掉？接收端頻寬 5–9 GHz、位元率提高時窗還夠嗎（草稿表 VI、IV-F）？

用途：
  1. UI 預算（表 VI）：依序加入各效應，看共同取樣窗少多少（前後兩次分析的差，不是可以任意相加的獨立損失）：
       邊緣與 ISI＝UI − W_0（對齊、無護欄）；雜訊＝W_0 − W_n（對齊、時變護欄）；skew＝W_n − W_s（x3、x4 晚 13.2 ps 這一組延遲）；
     再往下延伸到保證值（只在類比接收端，與 M4 s3 同一模型）：
       盒內其他 skew＝W_s − W_ctr（M3 s3 的 41 點、扣中點）；共同平移＝W_ctr − W_box（41 點共同窗：一個取樣時刻要服務
       所有輸入同向的 ±6.6 ps，M3 s3 R1）；認證的保守量＝W_box − W_cert（M4 s3 單葉、情境序列）；
       剩餘＝W_cert − T_req，每側餘裕＝剩餘／2。
     兩種接收端：數位二階 Butterworth（雙線性，草稿 IV-C–IV-F 與表 VI 用）與類比二階 Butterworth（FOH 精確離散，表 III 與 M4 s3 用）。
  2. 接收端頻寬（IV-F）：10 Gb/s、f_3dB＝5–9 GHz，濾波與雜訊等效頻寬一起改；數位接收端的對齊與 skew 13.2 ps 窗，
     類比接收端同一組延遲的窗（認證窗必須不大於它），以及類比接收端的認證窗（M4 s2 的下界、M4 s3 的認證條件；護欄核心 K_m 也依頻寬重算）：
     單葉與每路切 2 份（XOR2 4 葉、其他 16 葉）兩種。認證是充分條件：單葉不過不代表不行，所以兩種都報（M4 審查 R1）。
  3. 位元率（IV-F）：10–25 Gb/s，f_3dB＝0.7×位元率、升餘弦邊緣全寬＝0.3125 UI、時間格＝UI/200 一起縮放；
     T_req＝23 ps、skew 13.2 ps、延遲盒 ±6.6 ps 是物理時間，固定不變。通過＝skew 窗（或認證窗）≥ T_req。
  所有「保證」都在本模型下（升餘弦邊緣、固定延遲、Q＝7 的機率性雜訊護欄、相位已校準）。
  驗收：與草稿表 VI 的 43／5.5／2／49.5 ps、IV-F 的 28.5–56.5 ps 與最高位元率（AND4、MAJ4 15、XOR2 20 Gb/s）比較。
輸入：design/paper/m3_align/s3_detail（模擬器、detail.json）、design/paper/m4_cert/s2_leaf/leaf.py、design/paper/m4_cert/s3_cert（cert.py、cert.json）、
      design/paper/m1_timing/s1_budget/out/budget.json。
輸出：design/paper/m4_cert/s4_budget/out/budget_ui.json、sens.json。
執行：.\lab design\paper\m4_cert\s4_budget\ui.py（6 個 worker 約 1 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s2_leaf"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s3_cert"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402
from contextlib import contextmanager                                # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy import signal                                             # noqa: E402

import cert as CT                                                    # noqa: E402
import leaf as LF                                                    # noqa: E402
import paths                                                         # noqa: E402

DT = LF.DT
QD = LF.QD
STEP = "paper/m4_cert/s4_budget"
FUNCS = LF.FUNCS
S0 = dict(DT.D.SETTINGS)
T_REQ = S0["t_req_ps"]
SKEW = 13.2
TAU_SKEW = np.array([0.0, 0.0, SKEW, SKEW])                          # x3、x4 晚 13.2 ps（草稿表 VI、IV-F 的那一組）
BWS = (5.0, 6.0, 7.0, 8.0, 9.0)
RATES = (10.0, 12.5, 15.0, 17.5, 20.0, 22.5, 25.0)
BW_FRAC = S0["rx_bw_ghz"] / S0["bit_rate_gbps"]                       # 0.7
EDGE_FRAC = S0["edge_full_ps"] * S0["bit_rate_gbps"] / 1e3           # 0.3125 UI
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
DRAFT = dict(budget=dict(edges_isi=43.0, noise=5.5, skew=2.0, window=49.5, remaining=26.5, slack_side=13.25),
             bw_range=(28.5, 56.5), max_rate={"AND4": 15.0, "MAJ4": 15.0, "XOR2": 20.0})


@contextmanager
def settings(**kw):
    """暫時改 M3 s3 的設定（位元率、頻寬）；模擬器與護欄核心在建立／計算時讀它。"""
    old = {k: DT.D.SETTINGS[k] for k in kw}
    DT.D.SETTINGS.update(kw)
    try:
        yield
    finally:
        DT.D.SETTINGS.update(old)


def make_sim(rate, bw, digital):
    """位元率 rate（Gb/s）、接收端 f_3dB bw（GHz）的模擬器；digital＝True 時換成雙線性數位 Butterworth。"""
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    ui = 1e3 / rate
    with settings(bit_rate_gbps=rate, rx_bw_ghz=bw):
        sim = DT.Sim(DT.sequence("euler"), EDGE_FRAC * ui, ui / 200, A, 10 ** (S0["pu_dbm"] / 10) * 1e-3, False)
    if digital:
        sim.num, sim.den = signal.butter(2, bw / (500.0 / sim.dt))     # 截止頻率對 Nyquist（500/dt GHz）正規化
        imp = np.zeros(int(round(2000 / sim.dt)))
        imp[0] = 1.0
        h = signal.lfilter(sim.num, sim.den, imp)
        sim.h2 = np.zeros(sim.N)
        sim.h2[:len(h)] = h ** 2 / np.sum(h ** 2)
        sim.H2 = np.fft.rfft(sim.h2)
    return sim


def b_of(fn):
    return np.array([1.0 if DT.TGT[fn](b) else -1.0 for b in DT.BITS])


def window(sim, rx, U, b_sym, taus, noise=True):
    """共同取樣窗（與 M3 s3 同一算法）；noise＝False 時不扣護欄。"""
    v, g = LF.actual(sim, rx, U, taus)
    bv = b_sym[sim.seq][:, None] * v[rx.idx]
    m = np.min(bv - (g[rx.idx] if noise else 0.0), axis=0)
    return DT.longest(m, sim.dt)


def certify(sim, U, b_sym, rate, bw, bins=1):
    """類比接收端、情境序列的認證窗（M4 s3 的條件；護欄核心依頻寬計算）；bins＝每路切幾份（1＝單葉）。"""
    with settings(bit_rate_gbps=rate, rx_bw_ghz=bw):
        rx = LF.Rx(sim)
        (_, l, Q), _ = LF.pair(U)
        _, weak = LF.weak_inputs(l, Q)
        gbar, _ = LF.guard_box(sim, U)
        e_in, e_btw, _ = LF.errors(sim, U)
        node, _, _ = CT.lower(sim, rx, U, b_sym, weak, bins, gbar[rx.idx])
    return CT.window(node - e_in - e_btw, sim.dt)[0]


def job(arg):
    fn, kind, x = arg
    t0 = time.time()
    U, b_sym = QD.unitary(fn), b_of(fn)
    if kind == "budget":                                             # x＝digital
        sim = make_sim(S0["bit_rate_gbps"], S0["rx_bw_ghz"], x)
        rx = LF.Rx(sim)
        out = dict(w0=window(sim, rx, U, b_sym, np.zeros(4), noise=False), wn=window(sim, rx, U, b_sym, np.zeros(4)),
                   ws=window(sim, rx, U, b_sym, TAU_SKEW))
    else:
        rate, bw = (S0["bit_rate_gbps"], x) if kind == "bw" else (x, BW_FRAC * x)
        dig = make_sim(rate, bw, True)
        drx = LF.Rx(dig)
        ana = make_sim(rate, bw, False)
        out = dict(rate=rate, bw=bw, ui=1e3 / rate, aligned=window(dig, drx, U, b_sym, np.zeros(4)), skew=window(dig, drx, U, b_sym, TAU_SKEW),
                   skew_analog=window(ana, LF.Rx(ana), U, b_sym, TAU_SKEW), cert=certify(ana, U, b_sym, rate, bw),
                   cert_fine=certify(ana, U, b_sym, rate, bw, 2))
    out["time_s"] = round(time.time() - t0, 1)
    return fn, kind, x, out


def main():
    t0 = time.time()
    jobs = [(fn, "budget", d) for fn in FUNCS for d in (True, False)]
    jobs += [(fn, "bw", b) for fn in FUNCS for b in BWS] + [(fn, "rate", r) for fn in FUNCS for r in RATES]
    with ProcessPoolExecutor(WORKERS) as ex:
        R = list(ex.map(job, jobs))
    det = json.loads(paths.OUT("paper/m3_align/s3_detail", "detail.json").read_text(encoding="utf-8"))["results"]["D0"]
    cj = json.loads(paths.OUT("paper/m4_cert/s3_cert", "cert.json").read_text(encoding="utf-8"))["functions"]
    ui = 1e3 / S0["bit_rate_gbps"]
    budget = {fn: {} for fn in FUNCS}
    sens = {fn: dict(bw=[], rate=[]) for fn in FUNCS}
    for fn, kind, x, o in R:
        if kind == "budget":
            it = dict(edges_isi=ui - o["w0"], noise=o["w0"] - o["wn"], skew=o["wn"] - o["ws"])
            rec = dict(w0=o["w0"], wn=o["wn"], ws=o["ws"], items=it, remaining=o["ws"] - T_REQ, slack_side=(o["ws"] - T_REQ) / 2)
            if not x:                                                # 類比：延伸到盒內最小與認證窗
                wr, wb = det[fn]["box_center"], det[fn]["box_min"]
                wc, wh = cj[fn]["scenario"]["configs"]["1"]["window"], cj[fn]["order4"]["configs"]["1"]["window"]
                rec.update(w_ctr=wr, w_box=wb, w_cert=wc, w_cert_hist=wh, box_rest=o["ws"] - wb, box_skew=o["ws"] - wr,
                           box_common=wr - wb, cert_conservative=wb - wc,
                           remaining_cert=wc - T_REQ, slack_side_cert=(wc - T_REQ) / 2)
            budget[fn]["digital" if x else "analog"] = rec
        else:
            sens[fn][kind].append(o)
    for fn in FUNCS:
        for kind in ("bw", "rate"):
            sens[fn][kind].sort(key=lambda r: r["bw"] if kind == "bw" else r["rate"])
        rr = sens[fn]["rate"]
        sens[fn]["max_rate_detail"] = max([r["rate"] for r in rr if r["skew"] >= T_REQ], default=None)
        sens[fn]["max_rate_cert"] = max([r["rate"] for r in rr if r["cert"] >= T_REQ], default=None)
        sens[fn]["min_bw_cert"] = min([r["bw"] for r in sens[fn]["bw"] if r["cert"] >= T_REQ], default=None)
        sens[fn]["max_rate_cert_fine"] = max([r["rate"] for r in rr if r["cert_fine"] >= T_REQ], default=None)
        sens[fn]["min_bw_cert_fine"] = min([r["bw"] for r in sens[fn]["bw"] if r["cert_fine"] >= T_REQ], default=None)
    a4 = budget["AND4"]["digital"]
    bw_sk = [r["skew"] for r in sens["AND4"]["bw"]]
    # 各項由相鄰兩次分析的差定義，加總必等於 UI（恆等式），所以不列入驗收（M4 審查 R6）
    checks = dict(analog_chain=all(b["analog"]["ws"] >= b["analog"]["w_ctr"] >= b["analog"]["w_box"] >= b["analog"]["w_cert"]
                                   for b in budget.values()),
                  fine_not_worse=all(r["cert_fine"] >= r["cert"] - 0.5 for f in sens.values() for k in ("bw", "rate") for r in f[k]),
                  bw_detail_above_treq=all(r["skew"] >= T_REQ for f in sens.values() for r in f["bw"]),
                  max_rate_matches_draft=all(sens[fn]["max_rate_detail"] == DRAFT["max_rate"][fn] for fn in FUNCS),
                  cert_below_detail=all(max(r["cert"], r["cert_fine"]) <= r["skew_analog"] for f in sens.values() for k in ("bw", "rate") for r in f[k]))
    common = dict(ui_ps=ui, t_req_ps=T_REQ, skew_ps=SKEW, tau_skew_ps=TAU_SKEW.tolist(), bw_frac=BW_FRAC, edge_frac_ui=EDGE_FRAC, draft=DRAFT)
    paths.OUT(STEP, "budget_ui.json").write_text(json.dumps(dict(common, functions=budget, checks=checks, time_s=round(time.time() - t0, 1)),
                                                            ensure_ascii=False, indent=1), encoding="utf-8")
    paths.OUT(STEP, "sens.json").write_text(json.dumps(dict(common, bws_ghz=BWS, rates_gbps=RATES, functions=sens, checks=checks),
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    for fn in FUNCS:
        for k, b in budget[fn].items():
            s = "／".join(f"{v:.1f}" for v in b["items"].values())
            ext = (f"｜盒內其他 skew {b['box_skew']:.1f}、共同平移 {b['box_common']:.1f}、認證保守 {b['cert_conservative']:.1f}、認證窗 {b['w_cert']:.1f}、每側 {b['slack_side_cert']:.2f}"
                   if k == "analog" else "")
            print(f"{fn} {k:7s}：邊緣與 ISI／雜訊／skew＝{s} ps → W_s {b['ws']:.1f}，剩 {b['remaining']:.1f}，每側 {b['slack_side']:.2f}{ext}")
        print(f"   頻寬 5–9 GHz：skew 窗 {[r['skew'] for r in sens[fn]['bw']]}，認證 {[r['cert'] for r in sens[fn]['bw']]}，"
              f"切細 {[r['cert_fine'] for r in sens[fn]['bw']]}")
        print(f"   位元率：skew 窗 {[r['skew'] for r in sens[fn]['rate']]}，認證 {[r['cert'] for r in sens[fn]['rate']]}"
              f"，切細 {[r['cert_fine'] for r in sens[fn]['rate']]}"
              f" → 最高 {sens[fn]['max_rate_detail']}（認證 單葉 {sens[fn]['max_rate_cert']}、切細 {sens[fn]['max_rate_cert_fine']}）Gb/s")
    print(f"草稿表 VI：43／5.5／2 → 49.5；本步數位 AND4：{a4['items']['edges_isi']:.1f}／{a4['items']['noise']:.1f}／{a4['items']['skew']:.1f} → {a4['ws']:.1f}"
          f"｜頻寬 skew 窗 {min(bw_sk)}–{max(bw_sk)}（草稿 28.5–56.5）")
    print("檢查：", checks, f"｜{round(time.time() - t0, 1)} s")
    print("寫出 design/paper/m4_cert/s4_budget/out/budget_ui.json、sens.json")


if __name__ == "__main__":
    main()
