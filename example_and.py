"""完整範例：用 x1 AND x2 看一次從輸入到答案的過程。

需要的軟體：Python 3 與 numpy。
執行方式：python example_and.py

程式讀取 OOK 版 AND2 的 14 個相位，列出 16 組輸入的 o2、o4、o3 亮度、兩個比較器的判斷與答案。
亮度來自光路的數學模型，單位是一道資料光的功率。
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
    print("x1 x2 x3 x4 |   o2    o4    o3 | 比較器 A  比較器 B | 答案")
    matched = 0
    for row in V.ROWS:
        bits = [int(b) for b in V.BITS[:, row]]
        o2, o3, o4 = power[1, row], power[2, row], power[3, row]
        a, b = o2 > o4, o4 > o3
        answer = int(a and b)
        matched += answer == (bits[0] & bits[1])
        print(f" {bits[0]}  {bits[1]}  {bits[2]}  {bits[3]} | {o2:5.2f} {o4:5.2f} {o3:5.2f} |    {'是' if a else '否'}        {'是' if b else '否'}    |  {answer}")
    print(f"結果：{matched}／{len(V.ROWS)} 組輸入符合 x1 AND x2")
    sys.exit(0 if matched == len(V.ROWS) else 1)


if __name__ == "__main__":
    main()
