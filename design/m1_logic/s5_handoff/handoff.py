r"""M1 s5：交接——把「固定光路」與「功能設定」分開保存，交給 M2。

用途：
  1. b7_netlist.json：固定光路。波導數、輸入／輸出的教學編號與佈局埠名、7 顆 MZI 的位置與層、
     MZI 矩陣慣例、R 的振幅、讀取埠與判讀規則。換函數時這個檔完全不變。
  2. phases.json：相位設定檔。五個函數各自的 θ1–θ7、φ1–φ7（rad）、margin、驗證條件，
     並記錄所搭配的 b7_netlist.json 的 SHA-256，避免拿錯版本的接線來用。
  3. truth_tables.csv：80 列（5 函數 × 16 組輸入），每列 x1–x4、目標、P2、P4、ΔP、判讀。
  資料來源是 M1 s4 的 out/gates.json 與 common/mzi.py；本程式只做整理，不重新最佳化。
輸入：common/mzi.py、M1 s4 的 out/gates.json。
輸出：out/b7_netlist.json、out/phases.json、out/truth_tables.csv。
執行：.\lab design\m1_logic\s5_handoff\handoff.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402

import paths                                                         # noqa: E402
from common.mzi import B7_OPS, R_AMP, READ                           # noqa: E402

STEP = "m1_logic/s5_handoff"


def netlist():
    signals = ["x1", "x2", "x3", "x4", "R"]
    return dict(
        name="B7", version="1.0", n_waveguides=5,
        inputs=[dict(index=k + 1, signal=signals[k], layout_port=f"in{k}",
                     amplitude="0／1（√P_u）" if k < 4 else f"{R_AMP:g}（√P_u，固定）") for k in range(5)],
        outputs=[dict(index=k + 1, name=f"o{k + 1}", layout_port=f"out{k}",
                      role="判讀" if k in READ else "終端") for k in range(5)],
        mzis=[dict(name=f"MZI-{k}", waveguides=[rail + 1, rail + 2], layer=lay + 1,
                   theta=f"θ{k}", phi=f"φ{k}") for k, (rail, lay) in enumerate(B7_OPS, 1)],
        order="光由左到右；U＝T̂7·T̂6·…·T̂1（同一層的兩顆可交換）",
        mzi_convention=dict(
            matrix="T(θ, φ)＝H·diag(e^{iθ}, 1)·H·diag(e^{iφ}, 1)，H＝[[1, i], [i, 1]]/√2",
            ports="每顆 MZI 的第 1 列／行＝上方波導（編號較小），第 2 列／行＝下方波導",
            phases="θ：兩顆 MMI 之間、上臂；φ：第一顆 MMI 之前、上臂；單位 rad"),
        readout=dict(ports=["o2", "o4"], rule="ΔP＝P(o2) − P(o4)；ΔP＞0 判 1，ΔP＜0 判 0，ΔP＝0 為邊界（判讀失敗）"),
        model="理想、無損耗、相干輸入、單一波長",
    )


def main():
    net = netlist()
    net_bytes = (json.dumps(net, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    net_path = paths.OUT(STEP, "b7_netlist.json")
    net_path.write_bytes(net_bytes)
    sha = hashlib.sha256(net_bytes).hexdigest()

    g = json.loads(paths.OUT("m1_logic/s4_gates", "gates.json").read_text(encoding="utf-8"))
    funcs = {}
    for name, f in g["funcs"].items():
        funcs[name] = dict(uses=["x1", "x2"] if f["n_inputs"] == 2 else ["x1", "x2", "x3", "x4"],
                           theta=f["theta"], phi=f["phi"], margin=f["margin"],
                           verified=f"{f['passed']}/{f['total']}（16 組四位元輸入，未使用的輸入為任意值）")
    ph = dict(netlist="b7_netlist.json", netlist_sha256=sha, unit="rad", R=R_AMP,
              phase_tolerance=("每個相位誤差標準差 ≤ 0.05 rad（M1 s4：五個函數在 σ＝0.05 時 500 次模擬全對，"
                               "即 95% 信心下失敗率低於約 0.6%；σ＝0.1 時 AND4、OR4 約九成）"),
              functions=funcs)
    paths.OUT(STEP, "phases.json").write_text(json.dumps(ph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = 0
    with open(paths.OUT(STEP, "truth_tables.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["function", "x1", "x2", "x3", "x4", "target", "P2", "P4", "dP", "bit"])
        for name, f in g["funcs"].items():
            for r in f["rows"]:
                w.writerow([name, *r["bits"], r["target"], r["P2"], r["P4"], r["dP"], r["bit"]])
                rows += 1
    print(f"寫出 b7_netlist.json（SHA-256 {sha[:12]}…）、phases.json（{len(funcs)} 個函數）、truth_tables.csv（{rows} 列）")


if __name__ == "__main__":
    main()
