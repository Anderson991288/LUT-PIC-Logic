r"""LUT4 s0：參考相位重播（Codex 相位庫）——用獨立的 5×5 矩陣實作，重播 65,536 張 × 16 列的判讀。

資料來源：reference/three_refined_3142132.npz（另一專案已獲准引用的相位庫：65,536 × 14，欄序 θ1, φ1, …, θ7, φ7；
         同拓樸 3142132、同 OOK 輸入、同 R＝3、同每顆 MZI 0.9 dB、同雙差值判讀）。
         這是「參考相位重播」，與本專案自己的 24 起點掃描（cover4.py）是不同資料，教材中必須分開標示。
做法：不 import synth4，只依設計契約重新實作——
  T(θ, φ)＝a·H·diag(e^{iθ}, 1)·H·diag(e^{iφ}, 1)，H＝[[1, i], [i, 1]]/√2，a＝10^(−0.9/20)；
  列＝輸出、欄＝輸入、第 1 列／行＝上方軌；3142132：MZI-1…7 依序混合 (3,4),(1,2),(4,5),(2,3),(1,2),(3,4),(2,3)；
  輸入向量 (x1, x2, x3, x4, 3)，x 以 0／1 振幅；D_a＝P2−P4、D_b＝P4−P3，皆＞0 判 1；
  q＝x1＋2x2＋4x3＋8x4，mask 第 q 位＝目標；列裕量＝(2b−1)·min(D_a, D_b)；mask 裕量＝16 列最小值。
輸入：reference/three_refined_3142132.npz。
輸出：out/bank_replay.json（通過數、判錯列數、最差 mask 與裕量、零值數、與 npz 內存 margins 的最大差）、
      out/bank_replay_margins.npy（65,536 個重播裕量，供 cover4_split.py 分欄）。
執行：.\lab design\lut4\s0_coverage\replay_bank.py
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BANK = HERE / "reference" / "three_refined_3142132.npz"
EXPECTED_SHA_PREFIX = "a09fe8c9"
CODE, R_AMP, LOSS_DB = "3142132", 3.0, 0.9
AMP = 10 ** (-LOSS_DB / 20)
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
X = np.array([[(q >> b) & 1 for b in range(4)] for q in range(16)], float)     # 列 q、欄 b：x_{b+1}＝第 b 位元
V = np.column_stack([X, np.full(16, R_AMP)]).astype(complex)                    # (16, 5)
EXAMPLES = {"AND2": 0x8888, "OR2": 0xEEEE, "XOR2": 0x6666, "NAND2": 0x7777, "AND4": 0x8000, "XOR4": 0x6996, "MUX": 0xCACA}


def T_batch(theta, phi, amp=AMP):
    """(B,) θ、φ → (B, 2, 2)；逐字照契約乘出來，不用三角函數展開。"""
    B = theta.shape[0]
    Dt = np.zeros((B, 2, 2), complex); Dt[:, 0, 0] = np.exp(1j * theta); Dt[:, 1, 1] = 1
    Dp = np.zeros((B, 2, 2), complex); Dp[:, 0, 0] = np.exp(1j * phi); Dp[:, 1, 1] = 1
    return amp * (H[None] @ Dt @ H[None] @ Dp)


def U_batch(phases, amp=AMP):
    """(B, 14) → (B, 5, 5)：U＝T̂7 ⋯ T̂1（光由左到右，後面的乘在左邊）。"""
    B = phases.shape[0]
    U = np.tile(np.eye(5, dtype=complex), (B, 1, 1))
    for q, c in enumerate(CODE):
        m = int(c) - 1                                          # 上方軌（0 起算）
        t = T_batch(phases[:, 2 * q], phases[:, 2 * q + 1], amp)
        E = np.tile(np.eye(5, dtype=complex), (B, 1, 1)); E[:, m:m + 2, m:m + 2] = t
        U = E @ U
    return U


def replay(masks, phases, chunk=4096):
    """回傳 (裕量 (N,), 判錯列數 (N,), 列裕量 (N,16))。"""
    N = len(masks)
    marg = np.empty(N); nerr = np.empty(N, int); rows = np.empty((N, 16))
    bits = ((masks[:, None] >> np.arange(16)[None, :]) & 1).astype(bool)      # (N, 16) 目標
    for s in range(0, N, chunk):
        U = U_batch(phases[s:s + chunk])                        # (B, 5, 5)
        E = U @ V.T[None]                                       # (B, 5, 16)
        P = E.real ** 2 + E.imag ** 2
        Da, Db = P[:, 1] - P[:, 3], P[:, 3] - P[:, 2]           # P2−P4、P4−P3
        y = (Da > 0) & (Db > 0)
        b = bits[s:s + chunk]
        m = np.where(b, 1.0, -1.0) * np.minimum(Da, Db)
        rows[s:s + chunk] = m; marg[s:s + chunk] = m.min(1); nerr[s:s + chunk] = (y != b).sum(1)
    return marg, nerr, rows


def self_test():
    """無損耗時 U 必須是么正矩陣；OOK 輸入 0000 時四路資料為 0，只剩 R。"""
    rng = np.random.default_rng(0)
    U = U_batch(rng.uniform(0, 2 * np.pi, (8, 14)), amp=1.0)
    err = np.max(np.abs(U @ np.conj(U.transpose(0, 2, 1)) - np.eye(5)[None]))
    assert err < 1e-12, err
    return float(err)


def hx(f):
    return f"0x{int(f):04X}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    sha = hashlib.sha256(BANK.read_bytes()).hexdigest()
    z = np.load(BANK)
    phases, stored = z["phases"].astype(float), z["margins"].astype(float)
    assert phases.shape == (65536, 14), phases.shape
    masks = np.arange(65536)
    unit_err = self_test()
    t0 = time.perf_counter()
    marg, nerr, rows = replay(masks, phases)
    el = time.perf_counter() - t0
    np.save(OUT / "bank_replay_margins.npy", marg)
    order = np.argsort(marg)
    ref_npy = HERE / "reference" / "coverage_margins.npy"
    cmp24 = None
    if ref_npy.exists():
        r24 = np.load(ref_npy)
        d = marg - r24
        cmp24 = dict(file="reference/coverage_margins.npy", note="本專案 24 起點掃描（既有證據）與 Codex 相位庫重播是不同資料，只列差異統計",
                     n_bank_better=int((d > 1e-6).sum()), n_scan_better=int((d < -1e-6).sum()), n_equal_1e_6=int((np.abs(d) <= 1e-6).sum()),
                     mean_diff=float(d.mean()), median_diff=float(np.median(d)), max_bank_minus_scan=float(d.max()), min_bank_minus_scan=float(d.min()),
                     scan_min=float(r24.min()), scan_argmin=hx(r24.argmin()), bank_min=float(marg.min()), bank_argmin=hx(order[0]))
    res = dict(
        source="reference phase bank replay (Codex phase bank); NOT this project's 24-start scan",
        bank=dict(file="reference/three_refined_3142132.npz", sha256=sha, sha_prefix_ok=sha.startswith(EXPECTED_SHA_PREFIX),
                  shape=list(phases.shape), column_order="theta1, phi1, ..., theta7, phi7"),
        model=dict(code=CODE, R=R_AMP, loss_db_per_mzi=LOSS_DB, readout="Da = P2 - P4 > 0 AND Db = P4 - P3 > 0", input="OOK 0/1 amplitude",
                   implementation="independent 5x5 matrix replay (no synth4 import)", unitary_selftest_err=unit_err),
        n_masks=65536, n_rows=65536 * 16, elapsed_s=round(el, 2),
        n_pass=int((nerr == 0).sum()), n_fail=int((nerr > 0).sum()), n_row_errors=int(nerr.sum()),
        n_zero_margin_rows=int((rows == 0).sum()), n_zero_margin_masks=int((marg == 0).sum()), n_nonpositive_masks=int((marg <= 0).sum()),
        n_zero_phase_rows=int((np.abs(phases).sum(1) == 0).sum()),
        margin=dict(min=float(marg.min()), argmin=hx(order[0]), median=float(np.median(marg)), max=float(marg.max()), argmax=hx(order[-1]),
                    ge_0p05=int((marg >= 0.05).sum()), ge_0p1=int((marg >= 0.1).sum()), ge_0p15=int((marg >= 0.15).sum())),
        worst10=[[hx(f), round(float(marg[f]), 6)] for f in order[:10]],
        examples={k: round(float(marg[v]), 6) for k, v in EXAMPLES.items()},
        stored_margins=dict(min=float(stored.min()), argmin=hx(stored.argmin()), max_abs_diff_vs_replay=float(np.max(np.abs(marg - stored))),
                            n_diff_gt_1e_6=int((np.abs(marg - stored) > 1e-6).sum())),
        compare_scan24=cmp24,
    )
    (OUT / "bank_replay.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"相位庫 SHA-256 {sha[:16]}…（前綴 {EXPECTED_SHA_PREFIX} 相符：{res['bank']['sha_prefix_ok']}）")
    print(f"重播 65,536 張 × 16 列：通過 {res['n_pass']}，判錯列 {res['n_row_errors']}，零裕量列 {res['n_zero_margin_rows']}，{el:.1f} 秒")
    print(f"最差 {res['margin']['argmin']} 裕量 {res['margin']['min']:.10f}；中位 {res['margin']['median']:.4f}；與 npz 內存 margins 最大差 {res['stored_margins']['max_abs_diff_vs_replay']:.2e}")
    print("範例", res["examples"])
    if cmp24:
        print("與 24 起點掃描比較", {k: cmp24[k] for k in ("n_bank_better", "n_scan_better", "scan_min", "bank_min")})
    sys.exit(0 if res["n_row_errors"] == 0 and res["bank"]["sha_prefix_ok"] else 1)


if __name__ == "__main__":
    main()
