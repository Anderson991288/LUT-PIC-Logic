r"""論文 M3 s3：依論文草稿的設定做詳細模擬——AND4、MAJ4、XOR2 在對齊時與 13.2 ps 延遲盒抽樣點上的共同取樣窗；重現草稿表 III 的「詳細模擬」兩欄。

用途：
  1. 草稿設定（D0）：M3 s2 的 0.9 dB／MZI 相位；輸入延遲模型（每路輸入在 macro 內的路徑合併成一個延遲 δ_i，macro 內差動延遲不計）；
     升餘弦邊緣全寬 31.25 ps；情境集＝Euler 序列（16 個狀態的 de Bruijn B(16,2) 再補第 1 個符號，257 個符號走過全部 256 種有序轉移）＋768 個隨機符號（循環）；
     二階 Butterworth 7 GHz 類比接收端，以一階保持（FOH）精確離散；時變護欄 Γ(t)＝|V_off|＋q·√(σ_c²＋σ_RIN²(t))，
     σ_c 含 TIA 熱雜訊與比較器雜訊（不含 shot），σ_RIN²(t)＝RIN·B_n·[|h|² ∗ (|D|＋ε P_sum)²](t) ／ ∫|h|²（共同光源的 RIN 經接收端濾波）；
     偵測器端每路 P_u＝−7 dBm。安全節點：所有符號 b_s·V(t)−Γ(t) ≥ 0；窗寬 W＝最長連續安全節點的終點減起點。
  2. 延遲盒：以對齊為中心、每路 ±6.6 ps（跨距 13.2 ps）；抽樣點依草稿所附計算程式的組成：16 個角落、中心、16 個均勻隨機點
     （種子 BOX_SEED，本計畫自訂）、8 個軸上端點，共 41 點。三種量：
     (a) 共同窗（草稿計算程式與表 III 的算法）：41 條 margin 曲線逐點取最小，再找最長的安全區間——一個取樣時刻要服務盒內所有延遲，
         包含所有輸入同向平移的點（例如全部 +6.6 ps）；
     (b) 扣中點的共同窗（草稿 III-E 原文：共同延遲由取樣時刻吸收）：每個抽樣點先減去 (max δ_i＋min δ_i)/2，只留下輸入之間的 skew；
     (c) 各自取樣：每個延遲各自找最長窗，再取最小——延遲固定、每個實例各自訓練取樣時刻時的窗寬。
  3. 逐項替換（另一版研究稿的建議：一次只改一項，才知道差異來自哪裡）：在 D0 上分別換成我們論文 M1 的
     邊緣（10–90% 30 ps）、固定護欄（時變護欄的最大值）、B(16,3) 序列、0.33 dB／MMI 的相位與模型（只有 AND4、XOR2）、
     1 ps 格點、加入 shot 雜訊，各自記錄對齊與盒內最小的窗寬。
  4. 記憶長度：接收端脈衝響應的尾端能量降到總能量 10^-4 所需的時間（以 UI 計），說明 Euler 序列（只保證相鄰轉移）與 B(16,3)（所有 3 符號歷史）的差別。
輸入：design/paper/m3_align/s2_synth/out/synth.json、design/paper/m1_timing/out/phases_lossy.json（變體用）、
      design/paper/m1_timing/s1_budget/out/budget.json（雜訊參數）、design/paper/m3_align/draft.py。
輸出：design/paper/m3_align/s3_detail/out/detail.json。
執行：.\lab design\paper\m3_align\s3_detail\detail.py（6 個 worker 約 1 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_timing"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import platform                                                      # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy import signal                                             # noqa: E402

import draft as D                                                    # noqa: E402
import paths                                                         # noqa: E402
from common.mzi import B7_OPS, READ, R_AMP, T, embed                 # noqa: E402

STEP = "paper/m3_align/s3_detail"
FUNCS = ("AND4", "MAJ4", "XOR2")
TGT = {"AND4": lambda b: b.all(), "MAJ4": lambda b: b.sum() >= 3, "XOR2": lambda b: b[0] != b[1]}
HALF_BOX = 6.6                                                       # ps：跨距 13.2 ps 的盒
N_RANDOM, SEED, BOX_SEED = 768, 3300, 935
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
BITS = np.array(list(itertools.product([0, 1], repeat=4)))
TABLE3 = D.TABLE3
VARIANTS = {                                                         # 名稱：(說明, 改了什麼)
    "D0": ("草稿設定", {}),
    "edge": ("邊緣改為 10–90% 30 ps（論文 M1）", dict(edge_full=30.0 / 0.5903)),
    "const_guard": ("固定護欄（時變護欄的最大值）", dict(const_guard=True)),
    "seq3": ("情境改為 B(16,3) 序列（論文 M1）", dict(seq="b163")),
    "m1_phase": ("0.33 dB／MMI 的相位與模型（論文 M1）", dict(m1_phase=True)),
    "dt1": ("時間格點 1 ps", dict(dt=1.0)),
    "shot": ("加入 shot 雜訊", dict(shot=True)),
}


def debruijn(k, n):
    a = [0] * k * n
    seq = []

    def db(t, p):
        if t > n:
            if n % p == 0:
                seq.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    return seq


def sequence(kind):
    if kind == "b163":
        return np.array(debruijn(16, 3))
    db = debruijn(16, 2)
    euler = np.array(db + db[:1])                                    # 線性走法要補回第 1 個符號才含 (最後, 第 1) 這個轉移
    assert len(set(zip(euler[:-1], euler[1:]))) == 256
    rng = np.random.default_rng(SEED)
    return np.concatenate([euler, rng.integers(0, 16, N_RANDOM)])


def b7(theta, phi, amps):
    """amps：每顆 MZI 的場振幅（草稿：每顆 MZI 10^(−0.9/20)；論文 M1：兩顆 MMI 各 10^(−0.33/20)）。"""
    U = np.eye(5, dtype=complex)
    for (rail, _), th, ph in zip(B7_OPS, theta, phi):
        U = embed(amps * T(th, ph), rail, 5) @ U
    return U


class Sim:
    def __init__(self, seq, edge_full, dt, A, pu_w, shot):
        S = D.SETTINGS
        self.seq, self.dt, self.ui = seq, dt, 1e3 / S["bit_rate_gbps"]
        self.n_ui = int(round(self.ui / dt))
        self.N = len(seq) * self.n_ui
        self.t = np.arange(self.N) * dt
        self.edge = edge_full
        b, a = signal.butter(2, 2 * np.pi * S["rx_bw_ghz"] * 1e9, analog=True)
        num, den, _ = signal.cont2discrete((b, a), dt * 1e-12, method="foh")
        self.num, self.den = np.ravel(num), np.ravel(den)
        imp = np.zeros(int(round(2000 / dt)))
        imp[0] = 1.0
        h = signal.lfilter(self.num, self.den, imp)
        self.h2 = np.zeros(self.N)
        self.h2[:len(h)] = h ** 2 / np.sum(h ** 2)
        self.H2 = np.fft.rfft(self.h2)
        self.mem_ui = float(np.argmax(np.cumsum(h[::-1] ** 2)[::-1] / np.sum(h ** 2) < 1e-4) * dt / self.ui)
        enbw = S["rx_bw_ghz"] * 1e9 * (math.pi / 4) / math.sin(math.pi / 4)
        unit = A["resp_a_w"] * pu_w
        th = A["tia_noise_pa_rthz"] * 1e-12 * math.sqrt(enbw) / unit
        comp = A["comp_noise_mv"] * 1e-3 / A["tia_ohm"] / unit
        self.sc2 = th ** 2 + comp ** 2
        self.off = A["comp_offset_mv"] * 1e-3 / A["tia_ohm"] / unit
        self.c2 = 10 ** (A["rin_db_hz"] / 10) * enbw
        self.shot2 = 2 * 1.602e-19 * A["resp_a_w"] * pu_w * enbw / unit ** 2 if shot else 0.0   # 乘上 P_sum（P_u）
        self.q, self.eps = A["q"], A["pd_mismatch"]
        self.cache = {}

    def envelope(self, j, tau):
        key = (j, round(tau, 6))
        if key not in self.cache:
            bits = BITS[self.seq][:, j].astype(float)
            n = len(bits)
            prev = np.roll(bits, 1)
            tt = (self.t - tau) % (n * self.ui)
            k = np.floor(tt / self.ui).astype(int)
            w = np.clip((tt - k * self.ui) / self.edge, 0, 1)
            self.cache[key] = prev[k] + (bits[k] - prev[k]) * (1 - np.cos(np.pi * w)) / 2
        return self.cache[key]

    def window(self, U, b_sym, taus, const_guard=False):
        x = np.zeros((self.N, 5), complex)
        for j in range(4):
            x[:, j] = self.envelope(j, taus[j])
        x[:, 4] = R_AMP
        y = x @ U.T
        p2, p4 = np.abs(y[:, READ[0]]) ** 2, np.abs(y[:, READ[1]]) ** 2
        d, s = p2 - p4, p2 + p4
        v = signal.lfilter(self.num, self.den, np.concatenate([d, d]))[self.N:]       # 週期穩態
        rin = np.fft.irfft(np.fft.rfft((np.abs(d) + self.eps * s) ** 2) * self.H2, self.N)
        shot = self.shot2 * np.fft.irfft(np.fft.rfft(s) * self.H2, self.N) if self.shot2 else 0.0   # 強度隨時間變的白雜訊經濾波
        g = self.off + self.q * np.sqrt(self.sc2 + self.c2 * np.maximum(rin, 0) + shot)
        if const_guard:
            g = np.full(self.N, g.max())
        idx = (np.arange(len(self.seq))[:, None] * self.n_ui + np.arange(2 * self.n_ui)[None, :]) % self.N
        margin = np.min(b_sym[self.seq][:, None] * v[idx] - g[idx], axis=0)    # 取樣相位 0–2 UI
        return longest(margin, self.dt), margin


def longest(margin, dt):
    """最長連續安全節點（margin ≥ 0）的終點減起點（ps）。"""
    best, run = 0, 0
    for o in margin >= 0:
        run = run + 1 if o else 0
        best = max(best, run)
    return max(best - 1, 0) * dt


def box_points():
    """草稿的抽樣組成：角落 16、中心 1、均勻隨機 16、軸上端點 8。"""
    rng = np.random.default_rng(BOX_SEED)
    pts = [np.array(v) * HALF_BOX for v in itertools.product((-1, 1), repeat=4)] + [np.zeros(4)]
    pts += list(rng.uniform(-HALF_BOX, HALF_BOX, (16, 4)))
    for i in range(4):
        z = np.zeros(4)
        z[i] = HALF_BOX
        pts += [z, -z]
    return pts


def job(arg):
    fn, var, box = arg
    opt = VARIANTS[var][1]
    S = D.SETTINGS
    A = json.loads(paths.OUT("paper/m1_timing/s1_budget", "budget.json").read_text(encoding="utf-8"))["assume"]
    pu_w = 10 ** (S["pu_dbm"] / 10) * 1e-3
    if opt.get("m1_phase"):
        m1 = json.loads(paths.OUT("paper/m1_timing", "phases_lossy.json").read_text(encoding="utf-8"))
        ph = m1["functions"][fn]
        amps = 10 ** (-2 * m1["loss_db"] / 20)                       # 每顆 MZI 兩顆 MMI
    else:
        ph = json.loads(paths.OUT("paper/m3_align/s2_synth", "synth.json").read_text(encoding="utf-8"))["functions"][fn]["lossy"]
        amps = 10 ** (-S["mzi_loss_db"] / 20)
    U = b7(np.array(ph["theta"]), np.array(ph["phi"]), amps)
    seq = sequence(opt.get("seq", "euler"))
    sim = Sim(seq, opt.get("edge_full", S["edge_full_ps"]), opt.get("dt", 0.5), A, pu_w, opt.get("shot", False))
    b_sym = np.array([1.0 if TGT[fn](b) else -1.0 for b in BITS])
    static = (np.abs(np.hstack([BITS.astype(complex), np.full((16, 1), R_AMP)]) @ U.T) ** 2)
    m_static = float(np.min(b_sym * (static[:, READ[0]] - static[:, READ[1]])))
    pts = [np.zeros(4)] if not box else box_points()
    t0 = time.time()
    ws, env, envc = [], None, None
    for p in pts:
        w, m = sim.window(U, b_sym, p, opt.get("const_guard", False))
        ws.append(w)
        env = m if env is None else np.minimum(env, m)
        if box:
            _, mc = sim.window(U, b_sym, p - (p.max() + p.min()) / 2, opt.get("const_guard", False))   # 扣掉共同平移
            envc = mc if envc is None else np.minimum(envc, mc)
    k = int(np.argmin(ws))
    return dict(fn=fn, var=var, box=box, w=longest(env, sim.dt), w_center=longest(envc, sim.dt) if box else None,
                w_each=float(min(ws)), worst_delay=pts[k].tolist(), n_points=len(pts),
                m_static=round(m_static, 4), n_symbols=len(seq), mem_ui=round(sim.mem_ui, 2), time_s=round(time.time() - t0, 1))


def main():
    t0 = time.time()
    jobs = [(fn, var, box) for var in VARIANTS for fn in FUNCS for box in (False, True)
            if not (var == "m1_phase" and fn == "MAJ4")]
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(job, jobs))
    out = {}
    for r in res:
        out.setdefault(r["var"], {}).setdefault(r["fn"], {})["box_min" if r["box"] else "aligned"] = r["w"]
        o = out[r["var"]][r["fn"]]
        if r["box"]:
            o["box_each_min"] = r["w_each"]
            o["box_center"] = r["w_center"]
            o["worst_delay"] = r["worst_delay"]
            o["n_points"] = r["n_points"]
        o["m_static"], o["n_symbols"], o["mem_ui"] = r["m_static"], r["n_symbols"], r["mem_ui"]
        o["time_s"] = round(o.get("time_s", 0) + r["time_s"], 1)
    d0 = out["D0"]
    delta = {v: {fn: dict(aligned=round(out[v][fn]["aligned"] - d0[fn]["aligned"], 2), box_min=round(out[v][fn]["box_min"] - d0[fn]["box_min"], 2))
                 for fn in out[v]} for v in out if v != "D0"}
    cmp_ = {fn: dict(aligned=d0[fn]["aligned"], draft_aligned=TABLE3[fn]["aligned"], box_min=d0[fn]["box_min"], box_center=d0[fn]["box_center"], box_each_min=d0[fn]["box_each_min"], draft_box_min=TABLE3[fn]["box_min"],
                     draft_cert=TABLE3[fn]["cert"], d_aligned=round(d0[fn]["aligned"] - TABLE3[fn]["aligned"], 2),
                     d_box=round(d0[fn]["box_min"] - TABLE3[fn]["box_min"], 2)) for fn in FUNCS}
    t_req = D.SETTINGS["t_req_ps"]
    checks = dict(
        aligned_within_3ps=all(abs(v["d_aligned"]) <= 3.0 for v in cmp_.values()),
        box_within_3ps=all(abs(v["d_box"]) <= 3.0 for v in cmp_.values()),
        box_above_cert=all(v["box_min"] >= v["draft_cert"] for v in cmp_.values()),
        all_above_treq=all(v["box_min"] >= t_req for v in cmp_.values()),
        order_same=sorted(FUNCS, key=lambda f: d0[f]["aligned"]) == sorted(FUNCS, key=lambda f: TABLE3[f]["aligned"]),
    )
    res = dict(variants={k: v[0] for k, v in VARIANTS.items()}, half_box_ps=HALF_BOX, t_req_ps=t_req, n_random=N_RANDOM, seed=SEED,
               results=out, delta=delta, compare=cmp_, wall_s=round(time.time() - t0, 1), workers=WORKERS, cpu=platform.processor(), checks=checks)
    path = paths.OUT(STEP, "detail.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for fn, v in cmp_.items():
        print(f"{fn}：對齊 {v['aligned']:g} ps（草稿 {v['draft_aligned']:g}）｜盒內共同窗 {v['box_min']:g} ps（草稿 {v['draft_box_min']:g}；認證 {v['draft_cert']:g}）｜扣中點 {v['box_center']:g}｜各自取樣最小 {v['box_each_min']:g}"
              f"｜最差延遲 {d0[fn]['worst_delay']}｜靜態 margin {d0[fn]['m_static']}")
    for var, dv in delta.items():
        print(f"{VARIANTS[var][0]}：" + "；".join(f"{fn} 對齊 {x['aligned']:+g}、盒 {x['box_min']:+g}" for fn, x in dv.items()))
    print(f"接收端記憶：{d0['AND4']['mem_ui']} UI（能量剩 1e-4）｜時間 {res['wall_s']} s（{WORKERS} 個 worker）")
    print("檢查：", checks)
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
