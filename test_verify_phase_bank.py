"""Negative test: feed deliberately broken phase data to verify_phase_bank.py and confirm that it catches every case.

Requirements: Python 3 and numpy.
Run:          python test_verify_phase_bank.py

The program builds several broken data sets from the real E± phase data, saves them in a temporary folder,
and hands each one to the verifier. The real data should pass, and every broken data set should be caught.
"""
import contextlib
import io
import sys
import tempfile
from pathlib import Path

import numpy as np

import verify_phase_bank as V

REAL = "design/lut4v2/s0_coverage/out/merged_phases.npz"


def bad_banks(masks, phases):
    one = int(np.where(masks == 0x6996)[0][0])
    swapped = phases.copy()
    swapped[[0, one]] = swapped[[one, 0]]
    repeated = masks.copy()
    repeated[1] = repeated[0]
    outside = masks.copy()
    outside[0] = V.N_TABLES
    with_nan = phases.copy()
    with_nan[0, 0] = np.nan
    return {
        "one truth table repeated 65,536 times": (np.full(V.N_TABLES, masks[one]), np.tile(phases[one], (V.N_TABLES, 1))),
        "a single truth table": (masks[one:one + 1], phases[one:one + 1]),
        "only the first 1,000 tables": (masks[:1000], phases[:1000]),
        "one truth table missing": (masks[:-1], phases[:-1]),
        "one ID repeated": (repeated, phases),
        "one ID out of range": (outside, phases),
        "two extra phases per table": (masks, np.hstack([phases, np.zeros((V.N_TABLES, 2))])),
        "one phase missing per table": (masks, phases[:, :-1]),
        "contains NaN": (masks, with_nan),
        "IDs stored as decimals": (masks.astype(float), phases),
        "phases of two tables swapped": (masks, swapped),
    }


def verdict(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return V.check("test", path, "EPM")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    bank = np.load(V.ROOT / REAL)
    masks, phases = bank["masks"], bank["phases"]
    ok = verdict(REAL)
    print(f"{'Passed' if ok else 'Review'}  real data")
    caught = 0
    cases = bad_banks(masks, phases)
    with tempfile.TemporaryDirectory() as folder:
        for k, (name, (m, p)) in enumerate(cases.items()):
            path = Path(folder) / f"case{k}.npz"
            np.savez(path, masks=m, phases=p)
            hit = not verdict(path)
            caught += hit
            print(f"{'Caught' if hit else 'Review'}  {name}")
    print(f"Result: caught {caught}/{len(cases)} broken data sets, real data {'passed' if ok else 'needs review'}")
    sys.exit(0 if ok and caught == len(cases) else 1)


if __name__ == "__main__":
    main()
