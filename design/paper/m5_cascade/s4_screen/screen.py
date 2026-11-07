r"""論文 M5 s4：全類別的時序篩選——靜態可實現的 4 輸入 NPN 類別中，有多少在 10 Gb/s 下真的有取樣窗？只看靜態 margin 能預測嗎？

用途：
  0. 類別：4 輸入的 65536 個布林函數依 NPN 變換（輸入排列、輸入取反、輸出取反）分成 222 類；每類取真值表整數最小者為代表
     （第 w 位元＝f(BITS[w])，BITS 與 M3 s2 相同，x1 為最高位）。
  1. 第 0 層（靜態）：每類代表在無損與 0.9 dB／MZI 下以 M3 s2 的 soft-min（同一退火、L-BFGS-B）合成，8 個起點；
     與最佳差 ≤ 0.005 P_u 的起點少於 2 個時再加 8 個；0.9 dB 另從無損的最佳隨機起點解暖啟動一次（M5 s1 的教訓）。統計 margin > 0、≥ 0.1、≥ 0.20 P_u（草稿的保守護欄）的類別數，
     並以類別大小加權成函數比例，與草稿 II-B（無損 181 類有正 margin、177 類 ≥ 0.1、136 類過護欄；0.9 dB 137 類 ≥ 0.1）比較。
     NPN 等價檢查：每類另抽 2 個成員（排除代表）在 0.9 dB 下重新合成，比較「≥ 0.1 P_u」的判定與 margin 比值。
  2. 預先登記的推測（只用第 0 層的靜態量，在算動態窗之前就固定）：三種指標——
       A：靜態 margin m；B：m／g，g＝該類自己 16 組字的靜態護欄最大值（|V_off|＋q√(σ_c²＋c²(|D|＋εP_sum)²)，與 M3 s3 同一模型，不經濾波）；
       C：B 再加有效輸入數 n_eff（M4 s2 的弱耦合判定，G_i ≥ 10⁻³ max G 者）。
     以草稿表 I 的 9 個代表函數（M3 s2 的相位）為校正組，各自擬合「盒內抽樣共同窗 ≈ a＋b·指標（＋c·n_eff）」，
     預測值 ≥ 23 ps 判「推測有窗」，|預測 − 23| < 5 ps 標「邊界」。另記錄是否線性可分（不可分者靠二次項，例如 XOR）。
  3. 第 1 層（動態）：0.9 dB margin > 0 的每一類，以 M3 s3 的詳細模擬（類比接收端、時變護欄、Euler 情境序列）算對齊窗與
     盒內 41 點的共同窗（13.2 ps 盒）。
  4. 第 2 層（認證）：同一類以 M5 s3 的「輸入係數版」盒證明算情境序列單葉認證窗；單葉 < 23 ps 而抽樣共同窗 ≥ 23 ps 時再切 16 葉。
     認證是充分條件：不通過記為「未確認」，不是失敗。
  5. 修正規則（第一次執行後，看過代表類別的結果才提出）：以 ρ＝min_x s·D(x)／Γ(x)（同一組字自己的護欄；M5 審查 R2）判定——
       ρ < 1 → 無窗（某組字穩態時已在護欄內）；ρ ≥ 校正組的最小值 → 有窗（只內插、不外推）；其間 → 邊界，要實際跑動態。
     同類成員一致性：每類的 2 個 NPN 成員（0.9 dB margin > 0 者）也跑第 1 層，檢查規則在「有窗」「無窗」兩區有沒有判錯；
     成員與代表同類、結果相關，不是獨立的保留資料（M5 審查 R1）。
     另一份審查建議的邊界校正：在邊界區依 ρ 的 10、30、50、70、90 百分位各取 1 類（只用靜態量挑選），加進校正組重新擬合 B、C，預測其餘邊界類別。
  6. 對照參考實作的逐類 margin 在另一支內部核對程式（不匯出），本檔不讀其他計畫的檔案。
  驗收：每類三層結果齊全；預先登記推測與修正規則的混淆表（列出推測錯的類別），修正規則在保留資料上的錯誤數；NPN 成員的判定一致性；表 I 三個函數的窗與 M3 s3、M4 s3 相同（回歸）。
輸入：design/paper/m3_align/s2_synth/synth.py（soft-min 與 B7）、synth.json（表 I 相位）、design/paper/m3_align/s3_detail/detail.py（模擬器）、
      design/paper/m5_cascade/s3_cert/cert_cascade.py（盒證明）、design/paper/m3_align/s3_detail/out/detail.json、design/paper/m4_cert/s3_cert/out/cert.json。
輸出：design/paper/m5_cascade/s4_screen/out/screen.json、static.jsonl（合成快取，可續跑）。
執行：.\lab design\paper\m5_cascade\s4_screen\screen.py（6 個 worker；靜態約 45 分鐘，有快取時約 1.5 分鐘；動態與認證約 10 分鐘）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s2_synth"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m3_align" / "s3_detail"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m4_cert" / "s1_quad"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m4_cert" / "s2_leaf"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m4_cert" / "s3_cert"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s2_meander"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s3_cert"))
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import itertools                                                     # noqa: E402
import json                                                          # noqa: E402
import math                                                          # noqa: E402
import time                                                          # noqa: E402
from concurrent.futures import ProcessPoolExecutor                   # noqa: E402

import numpy as np                                                   # noqa: E402
from scipy.optimize import minimize                                  # noqa: E402

import cert_cascade as CC                                            # noqa: E402
import paths                                                         # noqa: E402
import synth as SY                                                   # noqa: E402
from common.mzi import READ, R_AMP                                   # noqa: E402

LF, DT, QD, CT = CC.LF, CC.DT, CC.QD, CC.CT
STEP = "paper/m5_cascade/s4_screen"
BITS = SY.BITS
LOSSES = (0.0, SY.D.SETTINGS["mzi_loss_db"])
STARTS, EXTRA, SEED0 = 8, 8, 7000
WARM_K = 100                                                         # 快取中暖啟動的編號
NEAR = 0.005
MEMBERS = 2
MEMBER_SEED = 4
T_REQ = CT.T_REQ
BAND = 5.0                                                           # ps：預測值離 23 ps 小於此值標「邊界」
WORKERS = int(__import__("os").environ.get("PAPER_WORKERS", "2"))  # 重現時平行上限 2；結果與 worker 數無關
DRAFT = dict(lossless_pos=181, lossless_01=177, lossless_guard=136, lossless_01_func_pct=85.8, lossless_guard_func_pct=63.7, lossy_01=137)
W8 = 1 << np.arange(16)


# ---------- NPN 類別 ----------
def transforms():
    """輸入變換（排列 × 取反）：idx[t, w]＝變換後字 w 對應的原字。共 4!·2⁴＝384 個。"""
    pw = np.array([8, 4, 2, 1])
    out = []
    for perm in itertools.permutations(range(4)):
        for neg in itertools.product([0, 1], repeat=4):
            out.append(((BITS[:, list(perm)] ^ np.array(neg)) @ pw))
    return np.array(out)


def classes():
    """回傳 (代表整數列表（遞增）, 每個函數的代表, 每類大小)。"""
    F = ((np.arange(65536)[:, None] >> np.arange(16)) & 1).astype(np.int64)
    canon = np.full(65536, 1 << 20, dtype=np.int64)
    for idx in transforms():
        v = F[:, idx] @ W8
        canon = np.minimum(canon, np.minimum(v, v ^ 0xFFFF))
    reps, size = np.unique(canon, return_counts=True)
    return reps.tolist(), canon, size.tolist()


def support(tt):
    """函數實際依賴的輸入數（翻轉該輸入會改變輸出者）。"""
    f = np.array([(tt >> w) & 1 for w in range(16)])
    return int(sum(np.any(f != f[np.arange(16) ^ (8 >> i)]) for i in range(4)))


def signs(tt):
    return np.array([1.0 if (tt >> w) & 1 else -1.0 for w in range(16)])


# ---------- 第 0 層：合成 ----------
def soft_task(task):
    """task：(tt, loss_db, [k…]) 或 (tt, loss_db, [WARM_K], z0)；回傳每個起點的 (k, margin, z)。"""
    tt, loss, ks = task[:3]
    amp = 10 ** (-loss / 20)
    s = signs(tt)
    out = []
    for k in ks:
        z = np.array(task[3]) if k == WARM_K else np.random.default_rng(SEED0 + k).uniform(0, 2 * np.pi, 14)
        for beta in SY.BETAS:
            def f(x):
                m, _ = SY.signed(x, amp, s)
                return -(-np.log(np.sum(np.exp(-beta * (m - m.min())))) / beta + m.min())
            z = minimize(f, z, method="L-BFGS-B", options=dict(maxiter=500)).x
        m, _ = SY.signed(z, amp, s)
        out.append((tt, loss, k, float(m.min()), (z % (2 * np.pi)).tolist()))
    return out


def synthesize(targets, cache_path, warm=()):
    """targets：[(tt, loss)]；快取 static.jsonl。先 STARTS 個起點；不一致者再加 EXTRA 個；
    warm：[(tt, 來源損耗, 目標損耗)]，從來源損耗的最佳隨機起點解再暖啟動一次（M5 s1 的教訓），判斷補算只看隨機起點。"""
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            tt, loss, k, m, z = json.loads(line)
            cache[(tt, loss, k)] = (m, z)

    def run(tasks):
        tasks = [(tt, loss, [k for k in ks if (tt, loss, k) not in cache], *rest) for tt, loss, ks, *rest in tasks]
        tasks = [t for t in tasks if t[2]]
        if not tasks:
            return
        with ProcessPoolExecutor(WORKERS) as ex, cache_path.open("a", encoding="utf-8") as fh:
            for res in ex.map(soft_task, tasks, chunksize=2):
                for tt, loss, k, m, z in res:
                    cache[(tt, loss, k)] = (m, z)
                    fh.write(json.dumps([tt, loss, k, m, z]) + "\n")
                fh.flush()

    run([(tt, loss, list(range(STARTS))) for tt, loss in targets])
    again = []
    for tt, loss in targets:
        ms = [cache[(tt, loss, k)][0] for k in range(STARTS)]
        if sum(m >= max(ms) - NEAR for m in ms) < 2:
            again.append((tt, loss, list(range(STARTS, STARTS + EXTRA))))
    run(again)

    def best_random(tt, loss):
        rs = [(cache[(tt, loss, k)][0], k) for k in range(STARTS + EXTRA) if (tt, loss, k) in cache]
        return cache[(tt, loss, max(rs)[1])][1]
    run([(tt, lt, [WARM_K], best_random(tt, lf)) for tt, lf, lt in warm])
    best = {}
    for tt, loss in targets:
        rs = [(cache[(tt, loss, k)][0], k) for k in list(range(STARTS + EXTRA)) + [WARM_K] if (tt, loss, k) in cache]
        m, k = max(rs)
        best[(tt, loss)] = dict(margin=m, z=cache[(tt, loss, k)][1], n_starts=len(rs), source="warm" if k == WARM_K else "random",
                                hits=sum(r[0] >= m - NEAR for r in rs), extra=(tt, loss) in {(a, b) for a, b, _ in again})
    return best


# ---------- 靜態護欄、有效輸入、可分性 ----------
_SIM = {}


def sim4():
    if "s" not in _SIM:
        _SIM["s"] = CC.make_sim(4)[0]
    return _SIM["s"]


def static_terms(z, tt, loss):
    amp = 10 ** (-loss / 20)
    U = SY.b7(np.array(z), amp)
    s = signs(tt)
    m, ps = SY.signed(np.array(z), amp, s)
    d = s * m
    sim = sim4()
    g = sim.off + sim.q * np.sqrt(sim.sc2 + sim.c2 * (np.abs(d) + sim.eps * ps) ** 2)
    d0, l, Q = QD.coeffs(U)
    G, weak = LF.weak_inputs(l, Q)
    # ratio：預先登記用的 m／g（分子、分母可能來自不同的字）；rho：逐字 s·D／Γ 的最小值（同一組字自己的護欄，M5 審查 R2），rho < 1 ⇔ 某組字穩態時已在護欄內
    return dict(margin=float(m.min()), guard=float(g.max()), ratio=float(m.min() / g.max()), rho=float(np.min(m / g)),
                n_eff=int((~weak).sum()), separable=QD.separable(s), support=support(tt))


# ---------- 第 1、2 層：動態窗與認證 ----------
def dyn_job(arg):
    key, tt, z, loss = arg
    t0 = time.time()
    amp = 10 ** (-loss / 20)
    U = SY.b7(np.array(z), amp)
    b_sym = signs(tt)
    sim = sim4()
    sim.cache.clear()
    aligned = sim.window(U, b_sym, np.zeros(4))[0]
    mins = np.full(2 * sim.n_ui, np.inf)
    for p in DT.box_points():
        mins = np.minimum(mins, sim.window(U, b_sym, p)[1])
    box = DT.longest(mins, sim.dt)
    M, c = U[list(READ), :4], U[list(READ), 4] * R_AMP
    rx = LF.Rx(sim)
    coef = CC.coeffs(M, c)
    _, weak = LF.weak_inputs(*coef[0][1:])
    gsym = CC.guard_box(sim, coef)[rx.idx]
    e = CC.errors(sim, coef)
    cert = {}
    for bins in (1, 2):
        if bins == 2 and (cert[1] >= T_REQ or box < T_REQ):
            break
        node = np.full(2 * sim.n_ui, np.inf)
        for _, cc, rr in CC.leaves(weak, bins):
            b = CC.bound(sim, rx, coef, DT.BITS, b_sym, cc, rr, weak)
            node = np.minimum(node, (b["L"] - gsym).min(0))
        cert[bins] = CT.window(node - 2 * e, sim.dt)[0]
    sim.cache.clear()
    return key, dict(aligned=aligned, box=box, cert1=cert[1], cert_fine=cert.get(2), n_leaves_fine=2 ** int((~weak).sum()) if 2 in cert else None,
                     time_s=round(time.time() - t0, 1))


# ---------- 推測 ----------
def features(st, kind):
    if kind == "A":
        return [1.0, st["margin"]]
    if kind == "B":
        return [1.0, math.log(st["ratio"])]
    return [1.0, math.log(st["ratio"]), st["n_eff"]]


def fit_predict(cal, items):
    """cal：[(靜態量, 實際 box)]；回傳每種指標的係數與對 items 的預測。"""
    out = {}
    for kind in "ABC":
        X = np.array([features(s, kind) for s, _ in cal])
        y = np.array([w for _, w in cal])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        rmse = float(np.sqrt(np.mean((X @ coef - y) ** 2)))
        out[kind] = dict(coef=coef.tolist(), rmse_cal=rmse,
                         pred={k: float(np.array(features(s, kind)) @ coef) for k, s in items.items()})
    return out


def label(p):
    return "邊界" if abs(p - T_REQ) < BAND else ("有窗" if p >= T_REQ else "無窗")


def main():
    t0 = time.time()
    out_dir = paths.OUT(STEP, "x").parent
    reps, canon, size = classes()
    rng = np.random.default_rng(MEMBER_SEED)
    members = {}
    for r in reps:
        pool = np.flatnonzero(canon == r)
        pool = pool[pool != r]
        members[r] = sorted(int(x) for x in rng.choice(pool, min(MEMBERS, len(pool)), replace=False)) if len(pool) else []
    targets = [(r, loss) for r in reps for loss in LOSSES] + [(m, LOSSES[1]) for r in reps for m in members[r]]
    t1 = time.time()
    best = synthesize(targets, out_dir / "static.jsonl", warm=[(r, LOSSES[0], LOSSES[1]) for r in reps])
    t_static = round(time.time() - t1, 1)

    # 表 I 的 9 個函數（校正組）用 M3 s2 的相位
    syn = json.loads(paths.OUT("paper/m3_align/s2_synth", "synth.json").read_text(encoding="utf-8"))["functions"]
    cal_items = {}
    for fn, f in SY.FUNCS.items():
        tt = int(sum(int(bool(f(b))) << w for w, b in enumerate(BITS)))
        z = syn[fn]["lossy"]["theta"] + syn[fn]["lossy"]["phi"]
        cal_items[fn] = (tt, z)
    lossy = LOSSES[1]
    stat = {}
    for r in reps:
        b = best[(r, lossy)]
        stat[r] = static_terms(b["z"], r, lossy) if b["margin"] > 0 else None
    cal_stat = {fn: static_terms(z, tt, lossy) for fn, (tt, z) in cal_items.items()}

    # 第 1、2 層
    mem_all = sorted({m for r in reps for m in members[r]})
    mstat = {m: static_terms(best[(m, lossy)]["z"], m, lossy) if best[(m, lossy)]["margin"] > 0 else None for m in mem_all}
    jobs = [(f"cal:{fn}", tt, z, lossy) for fn, (tt, z) in cal_items.items()] + \
           [(f"cls:{r}", r, best[(r, lossy)]["z"], lossy) for r in reps if stat[r] is not None] + \
           [(f"mem:{m}", m, best[(m, lossy)]["z"], lossy) for m in mem_all if mstat[m] is not None]
    t1 = time.time()
    with ProcessPoolExecutor(WORKERS) as ex:
        dyn = dict(ex.map(dyn_job, jobs))
    t_dyn = round(time.time() - t1, 1)

    # 推測：以校正組擬合，再預測每一類（推測只用靜態量）
    fits = fit_predict([(cal_stat[fn], dyn[f"cal:{fn}"]["box"]) for fn in cal_items],
                       {r: stat[r] for r in reps if stat[r] is not None})

    C = []
    for i, r in enumerate(reps):
        b0, b9 = best[(r, LOSSES[0])], best[(r, lossy)]
        mem = [dict(tt=m, margin=best[(m, lossy)]["margin"], static=mstat[m], dyn=dyn.get(f"mem:{m}")) for m in members[r]]
        row = dict(index=i, tt=r, word="".join(str((r >> w) & 1) for w in range(16)), size=size[i],
                   lossless=round(b0["margin"], 5), lossy=round(b9["margin"], 5), hits=[b0["hits"], b9["hits"]], lossy_source=b9["source"],
                   extra=[b0["extra"], b9["extra"]], members=mem, static=stat[r])
        if stat[r] is not None:
            d = dyn[f"cls:{r}"]
            row.update(dyn=d, has_window=d["box"] >= T_REQ,
                       certified=d["cert1"] >= T_REQ or (d["cert_fine"] is not None and d["cert_fine"] >= T_REQ),
                       pred={k: dict(value=round(fits[k]["pred"][r], 2), label=label(fits[k]["pred"][r])) for k in "ABC"},
                       best_z=b9["z"])
        C.append(row)

    def count(f, weight=False):
        return int(sum((c["size"] if weight else 1) for c in C if f(c)))

    pos0 = lambda c: c["lossless"] > 1e-6        # noqa: E731
    summary = dict(
        n_classes=len(reps), n_functions=int(sum(size)),
        lossless=dict(pos=count(pos0), ge01=count(lambda c: c["lossless"] >= 0.1), ge_guard=count(lambda c: c["lossless"] >= 0.20),
                      ge01_func_pct=round(100 * count(lambda c: c["lossless"] >= 0.1, True) / 65536, 1),
                      ge_guard_func_pct=round(100 * count(lambda c: c["lossless"] >= 0.20, True) / 65536, 1)),
        lossy=dict(pos=count(lambda c: c["lossy"] > 1e-6), ge01=count(lambda c: c["lossy"] >= 0.1), ge_guard=count(lambda c: c["lossy"] >= 0.20),
                   ge_own_guard=count(lambda c: c["static"] is not None and c["static"]["ratio"] >= 1)),
        dynamic=dict(evaluated=count(lambda c: "dyn" in c), aligned_ge=count(lambda c: "dyn" in c and c["dyn"]["aligned"] >= T_REQ),
                     box_ge=count(lambda c: c.get("has_window")), cert1_ge=count(lambda c: "dyn" in c and c["dyn"]["cert1"] >= T_REQ),
                     cert_ge=count(lambda c: c.get("certified")),
                     box_ge_func_pct=round(100 * count(lambda c: c.get("has_window"), True) / 65536, 1),
                     box_ge_support2=count(lambda c: c.get("has_window") and c["static"]["support"] >= 2),
                     cert_ge_support2=count(lambda c: c.get("certified") and c["static"]["support"] >= 2)))
    conf = {}
    for k in "ABC":
        tab = {}
        for c in C:
            if "dyn" not in c:
                continue
            key = f"{c['pred'][k]['label']}→{'有窗' if c['has_window'] else '無窗'}"
            tab[key] = tab.get(key, 0) + 1
        wrong = [c["index"] for c in C if "dyn" in c and c["pred"][k]["label"] != "邊界"
                 and (c["pred"][k]["label"] == "有窗") != c["has_window"]]
        conf[k] = dict(coef=fits[k]["coef"], rmse_cal=fits[k]["rmse_cal"], table=tab, wrong=wrong, n_wrong=len(wrong),
                       n_border=sum(1 for c in C if "dyn" in c and c["pred"][k]["label"] == "邊界"))
    # 修正規則（看過代表類別的結果後提出；同類成員只當一致性檢查）：ρ < 1 → 無窗（某組字穩態時已在自己的護欄內）；
    # ρ ≥ 校正組的最小值 → 有窗（只在校正組的範圍內內插，不外推）；其間 → 邊界（要實際跑動態）。
    r_hi = min(cal_stat[fn]["rho"] for fn in cal_items)

    def rule(st):
        return "無窗" if st["rho"] < 1 else ("有窗" if st["rho"] >= r_hi else "邊界")

    def score(rows):
        tab = {}
        for st, win in rows:
            key = f"{rule(st)}→{'有窗' if win else '無窗'}"
            tab[key] = tab.get(key, 0) + 1
        return tab
    rep_rows = [(c["static"], c["has_window"]) for c in C if "dyn" in c]
    mem_rows_dyn = [(m["static"], m["dyn"]["box"] >= T_REQ) for c in C for m in c["members"] if m["dyn"]]
    border = sorted((c for c in C if "dyn" in c and rule(c["static"]) == "邊界"), key=lambda c: c["static"]["rho"])
    pick = [border[int(round(q * (len(border) - 1)))] for q in (0.1, 0.3, 0.5, 0.7, 0.9)] if len(border) >= 5 else []
    bfit = fit_predict([(cal_stat[fn], dyn[f"cal:{fn}"]["box"]) for fn in cal_items] + [(c["static"], c["dyn"]["box"]) for c in pick],
                       {c["tt"]: c["static"] for c in border if c not in pick})
    btab = {}
    for c in border:
        if c in pick:
            continue
        for k in "BC":
            lab = "有窗" if bfit[k]["pred"][c["tt"]] >= T_REQ else "無窗"
            key = f"{k}:{lab}→{'有窗' if c['has_window'] else '無窗'}"
            btab[key] = btab.get(key, 0) + 1
    revised = dict(r_hi=r_hi, reps=score(rep_rows), members=score(mem_rows_dyn), n_members_dyn=len(mem_rows_dyn),
                   border=dict(n=len(border), picked=[c["index"] for c in pick], picked_ratio=[c["static"]["rho"] for c in pick],
                               coef={k: bfit[k]["coef"] for k in "BC"}, rmse={k: bfit[k]["rmse_cal"] for k in "BC"}, table=btab),
                   border_window_rate=sum(c["has_window"] for c in border) / max(1, len(border)),
                   reps_decided=sum(1 for st, _ in rep_rows if rule(st) != "邊界"), n_reps=len(rep_rows),
                   members_decided=sum(1 for st, _ in mem_rows_dyn if rule(st) != "邊界"),
                   members_border_window_rate=sum(w for st, w in mem_rows_dyn if rule(st) == "邊界") / max(1, sum(rule(st) == "邊界" for st, _ in mem_rows_dyn)))
    mem_rows = [(c["lossy"], m["margin"]) for c in C for m in c["members"]]
    member = dict(n=len(mem_rows), agree_01=sum((a >= 0.1) == (b >= 0.1) for a, b in mem_rows),
                  ratio=[min(b / a for a, b in mem_rows if a > 0.05), max(b / a for a, b in mem_rows if a > 0.05)],
                  disagree=[dict(rep=c["index"], rep_margin=c["lossy"], member=m["margin"]) for c in C for m in c["members"]
                            if (c["lossy"] >= 0.1) != (m["margin"] >= 0.1)])
    det = json.loads(paths.OUT("paper/m3_align/s3_detail", "detail.json").read_text(encoding="utf-8"))["results"]["D0"]
    m4 = json.loads(paths.OUT("paper/m4_cert/s3_cert", "cert.json").read_text(encoding="utf-8"))["functions"]
    reg = {fn: dict(aligned=dyn[f"cal:{fn}"]["aligned"], box=dyn[f"cal:{fn}"]["box"], cert1=dyn[f"cal:{fn}"]["cert1"],
                    m3_aligned=det[fn]["aligned"], m3_box=det[fn]["box_min"], m4_cert1=m4[fn]["scenario"]["configs"]["1"]["window"])
           for fn in ("AND4", "MAJ4", "XOR2")}
    checks = dict(
        n_classes_222=len(reps) == 222, all_functions=sum(size) == 65536,
        regression=all(v["aligned"] == v["m3_aligned"] and v["box"] == v["m3_box"] and v["cert1"] == v["m4_cert1"] for v in reg.values()),
        cert_le_box=all(c["dyn"]["cert1"] <= c["dyn"]["box"] and (c["dyn"]["cert_fine"] is None or c["dyn"]["cert_fine"] <= c["dyn"]["box"])
                        for c in C if "dyn" in c),
        all_layers=all("dyn" in c for c in C if c["lossy"] > 1e-6),
        rule_no_false_members=all(not (rule(st) == "無窗" and w) and not (rule(st) == "有窗" and not w) for st, w in mem_rows_dyn))
    res = dict(t_req_ps=T_REQ, band_ps=BAND, losses=LOSSES, starts=STARTS, extra=EXTRA, members_per_class=MEMBERS, draft=DRAFT,
               summary=summary, calibration={fn: dict(static=cal_stat[fn], dyn=dyn[f"cal:{fn}"]) for fn in cal_items},
               prediction=conf, revised=revised, member_check=member, regression=reg, classes=C, checks=checks,
               time_s=dict(static=t_static, dynamic=t_dyn, total=round(time.time() - t0, 1),
                           dyn_sum=round(sum(d["time_s"] for d in dyn.values()), 1)), workers=WORKERS)
    path = paths.OUT(STEP, "screen.json")
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("類別：", summary["n_classes"], "函數：", summary["n_functions"])
    print("無損：", summary["lossless"], "（草稿 181／177／136；85.8%／63.7%）")
    print("0.9 dB：", summary["lossy"], "（草稿 ≥0.1：137）")
    print("動態：", summary["dynamic"])
    for k, v in conf.items():
        print(f"推測 {k}：係數 {np.round(v['coef'], 3).tolist()}、校正 RMSE {v['rmse_cal']:.1f} ps｜{v['table']}｜錯 {v['n_wrong']}、邊界 {v['n_border']}")
    print("修正規則：", json.dumps(revised, ensure_ascii=False))
    print("NPN 成員：", {k: v for k, v in member.items() if k != "disagree"}, "不一致", len(member["disagree"]))
    print("回歸：", reg)
    print("檢查：", checks, res["time_s"])
    print(f"寫出 {rt.rel(path)}")


if __name__ == "__main__":
    main()
