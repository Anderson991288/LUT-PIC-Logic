r"""LUT4 s0：全表獨立重播——把本次第一輪相位與補強相位合併成可重播的相位庫，逐張重算 65,536 張 × 16 列。

用途：cover4.py 與 refine.py 由合成器回報裕量；本程式不 import synth4、不呼叫合成器的判讀函式，只依設計契約重新實作光路與判讀，
      分開報告第一輪（24 起點）與合併後（第一輪＋最差 40 張補強）兩份資料。另做反向測試，確認換編碼、換相位欄序、改接線會被抓到。
契約：T(θ,φ)＝a·H·diag(e^{iθ},1)·H·diag(e^{iφ},1)，a＝10^(−0.9/20)；3142132 依序混合軌 (3,4),(1,2),(4,5),(2,3),(1,2),(3,4),(2,3)；
      D_a＝P2−P4、D_b＝P4−P3，皆＞0 判 1；q＝x1＋2x2＋4x3＋8x4；列裕量＝(2b−1)·min(D_a,D_b)。
輸入：out/coverage_phases.npz、out/refine_phases.npz、reference/coverage_margins.npy。
輸出：out/merged_phases.npz（masks、phases、margins、round）、out/full_replay.json、out/failures_round1.csv（第一輪未過的 mask）。
執行：.\lab design\lut4\s0_coverage\replay_full.py
"""
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ENCODING = "OOK"                # OOK：場包絡 x；EPM：場包絡 1−2x（位元 0＝+E）
TOL = 1e-8                          # 判定通過的數值容差（P_u）
RAILS = [2, 0, 3, 1, 0, 2, 1]       # 3142132 的上方軌（0 起算）
AMP = 10 ** (-0.9 / 20)
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
Q = np.arange(16)
X = np.stack([(Q >> j) & 1 for j in range(4)]).astype(float)        # (4, 16)，x1 為最低位


def vectors(encoding=ENCODING, r=3.0):
    data = X if encoding == "OOK" else 1 - 2 * X
    return np.vstack([data, np.full(16, r)]).astype(complex)        # (5, 16)


def fields(ph, rails=RAILS, encoding=ENCODING, r=3.0):
    """ph：(B, 14)，欄序 θ1, φ1, …, θ7, φ7；回傳 (B, 5, 16) 的輸出場。"""
    B = len(ph)
    f = np.broadcast_to(vectors(encoding, r), (B, 5, 16)).copy()
    for k, i in enumerate(rails):
        ft = np.zeros((B, 2, 2), complex); ft[:, 0, 0] = np.exp(1j * ph[:, 2 * k]); ft[:, 1, 1] = 1
        fp = np.zeros((B, 2, 2), complex); fp[:, 0, 0] = np.exp(1j * ph[:, 2 * k + 1]); fp[:, 1, 1] = 1
        t = AMP * (H @ ft @ H @ fp)                                  # 右側先作用
        f[:, i:i + 2] = np.einsum("bij,bjq->biq", t, f[:, i:i + 2])
    return f


def judge(ph, masks, **kw):
    """回傳每張的裕量、判錯列數、邊界列數（|D| ≤ TOL）。"""
    p = np.abs(fields(ph, **kw)) ** 2
    da, db = p[:, 1] - p[:, 3], p[:, 3] - p[:, 2]
    want = ((masks[:, None] >> Q) & 1).astype(bool)
    row = np.where(want, np.minimum(da, db), -np.minimum(da, db))
    bad = ((da > 0) & (db > 0)) != want
    edge = np.abs(np.minimum(da, db)) <= TOL
    return row.min(1), bad.sum(1), edge.sum(1)


def replay(ph, masks, **kw):
    m, bad, edge = np.empty(len(ph)), np.empty(len(ph), int), np.empty(len(ph), int)
    for j in range(0, len(ph), 2048):
        s = slice(j, j + 2048)
        m[s], bad[s], edge[s] = judge(ph[s], masks[s], **kw)
    return m, bad, edge


def stats(m, bad, edge, masks):
    ok = (m > TOL) & (bad == 0)
    return dict(tables=int(len(m)), rows=int(16 * len(m)), passed_tables=int(ok.sum()), failed_tables=int((~ok).sum()),
                wrong_rows=int(bad.sum()), boundary_rows=int(edge.sum()), missing=int(np.isnan(m).sum()),
                min_margin_pu=float(m.min()), worst_mask=f"0x{int(masks[int(m.argmin())]):04X}", median_margin_pu=float(np.median(m)),
                ge_0p05=int((m >= 0.05).sum()), ge_0p1=int((m >= 0.1).sum()), tolerance_pu=TOL)


def main():
    t0 = time.perf_counter()
    z = np.load(OUT / "coverage_phases.npz")
    order = np.argsort(z["masks"])
    masks, ph1, m1 = z["masks"][order].astype(np.int64), z["phases"][order], z["margins"][order]
    assert (masks == np.arange(65536)).all() and ph1.shape == (65536, 14)
    r = np.load(OUT / "refine_phases.npz")
    ph2, src = ph1.copy(), np.full(65536, 24, np.int32)
    best = {}
    for f, mg, p in zip(r["masks"], r["margins"], r["phases"]):
        if np.isfinite(p).all() and (int(f) not in best or mg > best[int(f)][0]):
            best[int(f)] = (float(mg), p)
    for f, (mg, p) in best.items():
        if mg > m1[f]:
            ph2[f], src[f] = p, 100
    a = replay(ph1, masks)
    b = replay(ph2, masks)
    s1, s2 = stats(*a, masks), stats(*b, masks)
    s1["max_abs_diff_vs_synth"] = float(np.abs(a[0] - m1).max())
    refm = np.load(HERE / "reference" / "coverage_margins.npy")
    s1["max_abs_diff_vs_reference_margins"] = float(np.abs(a[0] - refm).max())
    fail = np.where((a[0] <= TOL) | (a[1] > 0))[0]
    with (OUT / "failures_round1.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["mask", "margin_pu", "wrong_rows", "boundary_rows"])
        for f in fail:
            w.writerow([f"0x{int(f):04X}", float(a[0][f]), int(a[1][f]), int(a[2][f])])
    np.savez_compressed(OUT / "merged_phases.npz", masks=masks, phases=ph2, margins=b[0], refined=src > 24,
                        phase_order=np.array("theta1,phi1,...,theta7,phi7"), encoding=np.array(ENCODING), topology=np.array("3142132"), loss_db=0.9, R=3.0)
    other = "EPM" if ENCODING == "OOK" else "OOK"
    swapped = ph2.reshape(-1, 7, 2)[:, :, ::-1].reshape(-1, 14)
    neg = {"wrong_encoding_" + other: replay(ph2, masks, encoding=other),
           "swap_theta_phi": replay(swapped, masks),
           "topology_1421324": replay(ph2, masks, rails=[0, 3, 1, 0, 2, 1, 3]),
           "R_2p9": replay(ph2, masks, r=2.9)}
    # 兩種偵測分開記錄：邏輯判錯（真值表翻轉）與裕量偏離存檔值。R 小偏差可能被裕量吸收，邏輯判錯抓不到，要靠裕量比對。
    negative = {k: dict(failed_tables=int(((v[0] <= TOL) | (v[1] > 0)).sum()), wrong_rows=int(v[1].sum()),
                        logic_detected=bool(((v[0] <= TOL) | (v[1] > 0)).any()),
                        max_margin_shift_pu=float(np.abs(v[0] - b[0]).max()),
                        detected=bool(((v[0] <= TOL) | (v[1] > 0)).any() or np.abs(v[0] - b[0]).max() > 1e-6)) for k, v in neg.items()}
    sha = hashlib.sha256((OUT / "merged_phases.npz").read_bytes()).hexdigest()
    doc = dict(source="this round (independent full replay; synth4 not imported)", encoding=ENCODING, topology="3142132", loss_db_per_mzi=0.9, R=3.0,
               round1_24_starts=s1, merged_round1_plus_refine=s2, refined_masks=int((src > 24).sum()), round1_failures=[f"0x{int(f):04X}" for f in fail],
               merged_bank="out/merged_phases.npz", merged_bank_sha256=sha, negative_tests=negative, elapsed_s=round(time.perf_counter() - t0, 1))
    (OUT / "full_replay.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=1))
    ok = s2["passed_tables"] == 65536 and s2["wrong_rows"] == 0 and all(v["detected"] for v in negative.values())
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
