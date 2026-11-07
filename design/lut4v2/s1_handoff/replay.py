r"""LUT4 s1：獨立重播器——只依交接檔（lut4_netlist.json、phases.json、truth_tables.csv）的慣例重算 112 列判讀，並做竄改測試。

用途：不 import 本專案任何模組（只用 numpy／json／csv／hashlib），由接線表的文字慣例自行實作：
  T(θ, φ)＝a·H·diag(e^{iθ}, 1)·H·diag(e^{iφ}, 1)，H＝[[1, i], [i, 1]]/√2，a＝10^(−L/20)；列＝輸出、行＝輸入、第 1 列／行＝上方波導；
  MZI-1…7 依序作用在 waveguides 指定的相鄰兩條波導；資料埠光場 +1／−1（位元 0＝+E、1＝−E），R＝phases.json 的 R（+3，與位元 0 同相）；
  Da＝P(o2)−P(o4)、Db＝P(o4)−P(o3)，皆＞0 判 1；x＝x1＋2x2＋4x3＋8x4。
檢查：
  1. 接線表 SHA-256 與 phases.json、spec.json 記錄的一致。
  2. 7 個函數 × 16 列：判讀位元＝csv 的 bit＝目標；P2／P3／P4／Da／Db 與 csv 相差 ≤ 1e-5；最小裕量與 phases.json 相差 ≤ 1e-5。
  3. 竄改測試（每一項都必須被抓到＝有任何一列位元不同，或功率與 csv 差超過 1e-5）：
     OOK 0／1 向量、θ 與 φ 對調、改接線（MZI-3 改混合 (3,4)）、讀取埠對調（o2↔o3）、R 改 2.9、R 與位元 0 反相（−3）、略過損耗（a＝1）。
輸入：out/lut4_netlist.json、out/phases.json、out/truth_tables.csv、out/spec.json。
輸出：out/replay.json；回傳碼 0＝112/112 且竄改全部抓到。
執行：.\lab design\lut4v2\s1_handoff\replay.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "out"
TOL = 1e-5
H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)


def T(th, ph, a):
    return a * H @ np.diag([np.exp(1j * th), 1.0]) @ H @ np.diag([np.exp(1j * ph), 1.0])


def U_of(net, theta, phi, a, mzis=None, swap_theta_phi=False):
    n = net["n_waveguides"]
    U = np.eye(n, dtype=complex)
    for k, m in enumerate(mzis or net["mzis"]):
        r = m["waveguides"][0] - 1                                    # 上方波導（0 起算）
        assert m["waveguides"][1] == m["waveguides"][0] + 1
        th, ph = (phi[k], theta[k]) if swap_theta_phi else (theta[k], phi[k])
        E = np.eye(n, dtype=complex)
        E[r:r + 2, r:r + 2] = T(th, ph, a)
        U = E @ U                                                     # 光由左到右：U＝T̂7·…·T̂1
    return U


def inputs(R, ook=False):
    X = np.array([[x >> b & 1 for b in range(4)] for x in range(16)], float)   # x1 為最低位元
    V = np.zeros((16, 5), complex)
    V[:, :4] = X if ook else 1 - 2 * X                                # E±：位元 0 → +1、1 → −1；OOK（竄改）：0／1
    V[:, 4] = R
    return V


def judge(U, V, ports=(1, 3, 2)):
    """ports＝(上界, 中間, 下界) 的輸出索引（0 起算）：預設 o2、o4、o3。"""
    P = np.abs(V @ U.T) ** 2
    a, b, c = ports
    Da, Db = P[:, a] - P[:, b], P[:, b] - P[:, c]
    return P, Da, Db, (Da > 0) & (Db > 0)


def main():
    nb = (OUT / "lut4_netlist.json").read_bytes()
    net = json.loads(nb)
    sha = hashlib.sha256(nb).hexdigest()
    ph = json.loads((OUT / "phases.json").read_text(encoding="utf-8"))
    spec = json.loads((OUT / "spec.json").read_text(encoding="utf-8"))
    with open(OUT / "truth_tables.csv", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    a = 10 ** (-ph["loss_db_per_mzi"] / 20)
    R = ph["R"]
    assert net["topology"] == "".join(str(m["waveguides"][0]) for m in net["mzis"])
    assert [p for p in net["readout"]["ports"]] == ["o2", "o4", "o3"]
    sha_ok = sha == ph["netlist_sha256"] == spec["source"]["netlist_sha256"]

    def run(theta_phi_of, V, ports=(1, 3, 2), mzis=None, swap=False, amp=a):
        """回傳 (位元對的列數, 功率對的列數, 最大功率差, 每函數最小裕量)。"""
        bits_ok, pw_ok, dmax, marg = 0, 0, 0.0, {}
        for name, f in ph["functions"].items():
            th, pp = theta_phi_of(f)
            U = U_of(net, th, pp, amp, mzis, swap)
            P, Da, Db, y = judge(U, V, ports)
            ins = np.array([int(f["truth_hex"], 16) >> x & 1 for x in range(16)], bool)
            marg[name] = float(np.where(ins, np.minimum(Da, Db), np.maximum(-Da, -Db)).min())
            for r in (r for r in rows if r["function"] == name):
                x = int(r["x1"]) + 2 * int(r["x2"]) + 4 * int(r["x3"]) + 8 * int(r["x4"])
                assert int(r["target"]) == ins[x]
                same_bit = int(y[x]) == int(r["bit"]) == int(r["target"])
                d = max(abs(P[x, 1] - float(r["P2"])), abs(P[x, 2] - float(r["P3"])), abs(P[x, 3] - float(r["P4"])),
                        abs(Da[x] - float(r["Da"])), abs(Db[x] - float(r["Db"])))
                dmax = max(dmax, d)
                bits_ok += int(same_bit); pw_ok += int(d <= TOL)
        return int(bits_ok), int(pw_ok), float(dmax), marg

    nominal = lambda f: (f["theta"], f["phi"])
    V = inputs(R)
    b_ok, p_ok, dmax, marg = run(nominal, V)
    marg_ok = all(abs(marg[n] - f["margin"]) <= TOL for n, f in ph["functions"].items())
    n_rows = len(rows)
    base = dict(rows=n_rows, bits_ok=b_ok, powers_ok=p_ok, max_power_diff=dmax, margin_match=marg_ok,
                margins={n: round(v, 6) for n, v in marg.items()})

    # 竄改測試：每一項都必須被抓到
    mz_wire = json.loads(json.dumps(net["mzis"])); mz_wire[2]["waveguides"] = [3, 4]      # MZI-3 原本混合 (4,5)
    tampers = {
        "ook_01_vectors": dict(V=inputs(R, ook=True)),
        "swap_theta_phi": dict(swap=True),
        "wiring_mzi3_to_34": dict(mzis=mz_wire),
        "readout_o2_o3_swapped": dict(ports=(2, 3, 1)),
        "R_2p9": dict(V=inputs(2.9)),
        "R_inverted": dict(V=inputs(-R)),
        "no_loss_a1": dict(amp=1.0),
    }
    tres = {}
    for k, kw in tampers.items():
        kw = dict(kw); Vt = kw.pop("V", V)
        tb, tp, td, tm = run(nominal, Vt, **kw)
        tres[k] = dict(bits_ok=tb, powers_ok=tp, max_power_diff=round(td, 6), caught=bool(tb < n_rows or tp < n_rows),
                       min_margin=round(min(tm.values()), 6))
    ok = sha_ok and b_ok == p_ok == n_rows == 112 and marg_ok and all(v["caught"] for v in tres.values())
    out = dict(netlist_sha256=sha, sha_match=sha_ok, nominal=base, tampers=tres, all_ok=bool(ok),
               convention="T＝a·H·diag(e^{iθ},1)·H·diag(e^{iφ},1)；E± 向量 1−2x；R＝+3；Da＝P2−P4、Db＝P4−P3")
    (OUT / "replay.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"SHA 一致 {sha_ok}；位元 {b_ok}/{n_rows}；功率 {p_ok}/{n_rows}（最大差 {dmax:.1e}）；裕量一致 {marg_ok}")
    for k, v in tres.items():
        print(f"  竄改 {k:24s} 位元 {v['bits_ok']:3d}/{n_rows} 功率 {v['powers_ok']:3d}/{n_rows} → {'抓到' if v['caught'] else '沒抓到'}")
    print("全部通過" if ok else "未通過")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
