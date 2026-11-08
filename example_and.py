"""Worked example: follow x1 AND x2 from the inputs to the answer.

Requirements: Python 3 and numpy.
Run:          python example_and.py

The program reads the 14 phases of AND2 for the OOK version and lists, for all 16 inputs,
the brightness of o2, o4 and o3, the decisions of the two comparators, and the answer.
Brightness comes from the mathematical model of the optical circuit, in units of the power of one data beam.
"""
import json
import sys

import numpy as np

import verify_phase_bank as V

PHASES = "design/lut4/s1_handoff/out/phases.json"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    setting = json.loads((V.ROOT / PHASES).read_text(encoding="utf-8"))["functions"]["AND2"]
    phases = np.array([p for pair in zip(setting["theta"], setting["phi"]) for p in pair])[None]
    power = V.output_power(phases, "OOK")[0]
    print("x1 x2 x3 x4 |   o2    o4    o3 | Comp. A  Comp. B | Answer")
    matched = 0
    for row in V.ROWS:
        bits = [int(b) for b in V.BITS[:, row]]
        o2, o3, o4 = power[1, row], power[2, row], power[3, row]
        a, b = o2 > o4, o4 > o3
        answer = int(a and b)
        matched += answer == (bits[0] & bits[1])
        print(f" {bits[0]}  {bits[1]}  {bits[2]}  {bits[3]} | {o2:5.2f} {o4:5.2f} {o3:5.2f} |   {'yes' if a else 'no ':3}      {'yes' if b else 'no ':3}   |   {answer}")
    print(f"Result: {matched}/{len(V.ROWS)} inputs match x1 AND x2")
    sys.exit(0 if matched == len(V.ROWS) else 1)


if __name__ == "__main__":
    main()
