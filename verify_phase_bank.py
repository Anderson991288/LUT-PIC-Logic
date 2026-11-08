"""Check it yourself: recompute all 65,536 truth tables with matrices and confirm that every row reads correctly.

Requirements: Python 3 and numpy.
Run:          python verify_phase_bank.py

This program is self-contained. It reads only the two phase files design/lut4*/s0_coverage/out/merged_phases.npz.
It first confirms that the data is complete: each of the 65,536 truth-table IDs appears once, and every table has 14 valid phases.
It then uses the mathematical model of the optical circuit to compute the output power for every input combination
and compares the result with the target truth table.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RAILS = [2, 0, 3, 1, 0, 2, 1]               # the pair of rails each of the 7 MZIs connects (index of the upper rail, from 0)
LOSS = 10 ** (-0.9 / 20)                    # 0.9 dB loss per MZI, as a field amplitude ratio
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)   # 50:50 splitter
ROWS = np.arange(16)                        # the 16 combinations of four inputs
BITS = np.stack([(ROWS >> j) & 1 for j in range(4)]).astype(float)
TOLERANCE = 1e-8
N_TABLES = 1 << 16                          # all truth tables of four inputs
N_PHASES = 14                               # phases per truth table


def input_fields(encoding):
    """Inputs on the five rails: x1 to x4 and the reference light R = 3."""
    data = BITS if encoding == "OOK" else 1 - 2 * BITS      # OOK: 0 / 1.  E±: +1 / -1
    return np.vstack([data, np.full(16, 3.0)]).astype(complex)


def output_power(phases, encoding):
    """Columns of phases are θ1, φ1, ..., θ7, φ7. Returns the optical power of the five outputs."""
    n = len(phases)
    field = np.broadcast_to(input_fields(encoding), (n, 5, 16)).copy()
    for k, rail in enumerate(RAILS):
        theta = np.zeros((n, 2, 2), complex)
        theta[:, 0, 0] = np.exp(1j * phases[:, 2 * k])
        theta[:, 1, 1] = 1
        phi = np.zeros((n, 2, 2), complex)
        phi[:, 0, 0] = np.exp(1j * phases[:, 2 * k + 1])
        phi[:, 1, 1] = 1
        mzi = LOSS * (H @ theta @ H @ phi)
        field[:, rail:rail + 2] = np.einsum("bij,bjq->biq", mzi, field[:, rail:rail + 2])
    return np.abs(field) ** 2


def bank_problems(masks, phases):
    """List what needs fixing in the phase data; returns an empty list when the data is complete."""
    if masks.shape != (N_TABLES,):
        return [f"truth-table IDs have shape {masks.shape}; expected ({N_TABLES},)"]
    if phases.shape != (N_TABLES, N_PHASES):
        return [f"phase data has shape {phases.shape}; expected ({N_TABLES}, {N_PHASES})"]
    problems = []
    if not np.issubdtype(masks.dtype, np.integer):
        problems.append(f"truth-table IDs have type {masks.dtype}; expected integers")
    elif not np.array_equal(np.sort(masks), np.arange(N_TABLES)):
        problems.append(f"truth-table IDs should cover 0 to {N_TABLES - 1}, each exactly once")
    if not np.isfinite(phases).all():
        problems.append("phase data contains NaN or infinity")
    return problems


def check(name, path, encoding):
    bank = np.load(ROOT / path)
    masks, phases = bank["masks"], bank["phases"]
    problems = bank_problems(masks, phases)
    if problems:
        print(f"{name}: data needs fixing")
        for problem in problems:
            print(f"  {problem}")
        return False
    worst, wrong = np.inf, 0
    margins = np.empty(len(masks))
    for start in range(0, len(masks), 2048):
        part = slice(start, start + 2048)
        power = output_power(phases[part], encoding)
        d_a = power[:, 1] - power[:, 3]                     # comparator A: positive when o2 is brighter than o4
        d_b = power[:, 3] - power[:, 2]                     # comparator B: positive when o4 is brighter than o3
        target = ((masks[part, None] >> ROWS) & 1).astype(bool)
        answer = (d_a > 0) & (d_b > 0)                      # the two comparators feed an AND gate
        wrong += int((answer != target).sum())
        margin = np.where(target, np.minimum(d_a, d_b), -np.minimum(d_a, d_b))
        margins[part] = margin.min(axis=1)
    worst = margins.min()
    passed = int(((margins > TOLERANCE)).sum())
    print(f"{name}: checking {len(masks):,} truth tables, {16 * len(masks):,} rows")
    print(f"  Data complete: each of the {N_TABLES:,} IDs appears once, {N_PHASES} phases per table")
    print(f"  Truth tables read correctly: {passed:,}")
    print(f"  Rows read incorrectly: {wrong:,}")
    print(f"  Smallest margin: {worst:.4f} (truth table 0x{int(masks[int(margins.argmin())]):04X})")
    print(f"  Median margin: {float(np.median(margins)):.4f}")
    return wrong == 0 and passed == len(masks)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ok = check("LUT4 OOK", "design/lut4/s0_coverage/out/merged_phases.npz", "OOK")
    ok = check("LUT4 E±", "design/lut4v2/s0_coverage/out/merged_phases.npz", "EPM") and ok
    print("Result: all checks passed" if ok else "Result: some items need review")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
