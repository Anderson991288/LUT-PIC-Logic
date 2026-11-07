r"""論文 M1 s5：介面規格、總預算與論文重點——逐函數合成 10 Gb/s 的總功率預算，並把結果整理成三個重點（完整版研究的簡化版）。

用途：
  1. 總功率預算：逐函數合成——每個函數的靜態需求（M1 s1，B7 輸入端 P_u）加上它自己的各項代價：消光比的靜態損失、
     轉態與接收端頻寬（skew 0，已含晶片內路徑差）、skew 到介面上限、7 個 heater 同時擺動、相位誤差用滿 δ_det；再取最大者。
     晶片內路徑差已在 s4 的時域模型裡（含路徑延遲），不再另外相加，只列為診斷值。
     代價以 margin 比值換算（前提：雜訊不隨光功率變，M1 s1 熱雜訊加比較器占 99%）；各項直接相加是近似，項目之間的交互作用只部分納入。
     每一項都換成 dB（margin 降為 r 倍 → 代價 −10 log10 r）。最後換算成每根資料光纖與 5 根合計的功率。
  2. 聯合驗收（joint.py 的結果）：把上面分項相加的近似，與同時加入所有誤差的時域計算比較。
  3. 三個重點：時序分析、靜態校正、動態校正與校正後驗收；每個重點列出支撐的數字（直接讀各步 JSON）與在完整版研究中的對應。
輸入：design/paper/m1_timing/s1_budget/out/budget.json、s2_interface/out/interface_v2.json、s3_tracking/out/tracking.json、
      s4_window/out/window.json、s5_assess/out/joint.json。
輸出：design/paper/m1_timing/s5_assess/out/assess.json。
執行：.\lab design\paper\m1_timing\s5_assess\assess.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import math                                                          # noqa: E402

import paths                                                         # noqa: E402

STEP = "paper/m1_timing/s5_assess"
BASE = "paper/m1_timing"


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def db(r):
    """margin 降為 r 倍時要多給的光功率（dB）。"""
    return -10 * math.log10(r)


def main():
    s1, s2 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json")
    s3, s4 = load("s3_tracking", "tracking.json"), load("s4_window", "window.json")
    J = load("s5_assess", "joint.json")
    F3, F4 = s3["functions"], s4["functions"]
    k_s = s4["skews_ps"].index(20)                                   # 介面規格 15 ps（M2 s2），預算取 20 ps 的代價（偏保守）
    pw = s1["power"]
    names = [("消光比（靜態）", "M1 s2、s4：殘留光讓靜態 margin 下降（重新求相位後）"),
             ("轉態與接收端頻寬", "M1 s4：skew 0 時的代價（含殘留光與晶片內路徑差）"),
             ("skew ≤ 15 ps", "M1 s4：以 skew 20 ps 相對 skew 0 的額外代價計（偏保守）"),
             ("heater 擺動", "M1 s3：7 個 heater 同時擺動時的 margin 損失"),
             ("相位誤差（≤ δ_det）", "M1 s1、s3：估計誤差（3σ）、追蹤落後、快速擾動幅度相加用滿 δ_det")]
    per = {}
    for f in F4:
        r = F4[f]["er"]["rows"]
        vals = [10 * math.log10(F4[f]["ideal"]["m0"] / F4[f]["er"]["m0"]), r[0]["penalty_db"], r[k_s]["penalty_db"] - r[0]["penalty_db"],
                db(F3[f]["dither_margin"]), s1["phase"]["det_loss_db"][f]]
        static = pw["pu_core_per_function_dbm"][f]
        per[f] = dict(static_dbm=static, chip_diag_db=s4["chip_penalty_db"][f], items=[dict(item=n, db=round(v, 3), source=src) for (n, src), v in zip(names, vals)],
                      dynamic_db=round(sum(vals), 3), total_dbm=round(static + sum(vals), 2))
    # 聯合驗收：同時加入所有誤差的時域代價（joint.py），與分項相加比較；不含相位與擺動以外的交互作用時兩者應接近
    joint = {f: dict(joint_db=v["final"]["penalty_db"], sum_db=per[f]["dynamic_db"],
                     sum_minus_joint_db=round(per[f]["dynamic_db"] - v["final"]["penalty_db"], 3)) for f, v in J["functions"].items()}
    lim = max(per, key=lambda f: per[f]["total_dbm"])                # 逐函數合成後取最大：決定功率需求的函數
    items = per[lim]["items"]
    dyn = per[lim]["dynamic_db"]
    pu_static = per[lim]["static_dbm"]
    pu_total = per[lim]["total_dbm"]
    fiber = pu_total + pw["ec_loss_db"]
    total = fiber + 10 * math.log10(13)
    budget = dict(limiting_function=lim, pu_static_dbm=pu_static, dynamic_db=round(dyn, 2), pu_total_dbm=round(pu_total, 2),
                  fiber_data_dbm=round(fiber, 2), fiber_ref_dbm=round(fiber + 10 * math.log10(9), 2),
                  total_dbm=round(total, 2), items=items, per_function={f: dict(static_dbm=v["static_dbm"], dynamic_db=v["dynamic_db"],
                                                                                   total_dbm=v["total_dbm"]) for f, v in per.items()})
    # 三個重點（完整版研究的簡化版：保留這三項，其餘壓縮或省略）
    claims = [
        dict(id="K1", point="時序分析", claim="判讀量是輸入光場的二次式，時序要看取樣窗內的判讀量；以功率代價把 skew 寫成發射端規格",
             evidence=(f"skew 0 已有 ≤ {s4['penalty0_max_ideal']:.1f} dB；skew 額外 0.5／1／2 dB 在 {s4['skew_at_db']['0.5']:g}／"
                       f"{s4['skew_at_db']['1.0']:g}／{s4['skew_at_db']['2.0']:g} ps；晶片內路徑差 ≤ {s4['chip_bound_db']:.2f} dB"),
             full_version="保留（時序模型與 UI 預算）；延遲盒認證與補長壓縮成一段"),
        dict(id="K2", point="靜態校正", claim="固定的誤差（消光比的殘留）只調 heater 重新求相位即可吸收，需求可用解析近似估計（數值支持的縮放關係）",
             evidence=(f"消光比需求 {s2['er_fixed_db']:g} → {s2['er_required_db']:.1f} dB（{s2['er_hardest_function']}）；"
                       f"margin ≈ (1−a0)^n m0，n＝{ {k: round(v) for k, v in s2['order'].items()} }"),
             full_version="保留（設計與校正分工）"),
        dict(id="K3", point="動態校正與校正後驗收", claim="輸入相位漂移只調 φ 可補回；最佳點上平均功率一階不敏感，以 heater 擺動加同步偵測在資料傳送中追蹤；校正後時域驗收",
             evidence=(f"擺動 {s3['dither_rad']:g} rad（7 個同時擺動損失 ≤ 3%）、回授 {s3['loop_bw_hz']:g} Hz、可追 {s3['ramp_rate_allow_rad_s']:g} rad/s"
                       f"（光纖熱漂移約 {s3['fiber_ramp_rad_s']:g}）；聯合驗收校正後 23 ps 窗仍在，聯合代價 "
                       + "、".join("%s %.2f dB（分項相加 %.2f）" % (f, v["joint_db"], v["sum_db"]) for f, v in joint.items())),
             full_version="保留（校正後重新驗收）；動態校正在資料傳送中進行"),
    ]
    compressed = [f"分欄同步佈局：判讀路徑相差 {s1['timing']['readout']['spread_ps']} ps，不需補長",
                  f"總功率預算：決定需求的是 {lim}，每根資料光纖 {fiber:.1f} dBm、5 根合計 {total:.1f} dBm"]
    limits = ["全部是模擬，沒有量測晶片", "M1 s1–s5 統一用含 MMI 損耗（0.33 dB）的 B7；MMI 的相位與分光誤差、波長相依未納入",
              "heater 熱時間常數、接收端參數、EC 損耗是假設值；監測需要 5 個輸出都有偵測器（只用 o2、o4 時回授頻寬較低）", "skew 只取延遲角落；回授只做一階估計；heater 熱串擾與相位重設未建模",
              "只有單一 B7（7 顆 MZI）；串接與更多輸入未評估"]
    res = dict(budget=budget, joint=joint, claims=claims, compressed=compressed, limits=limits,
               checks=dict(budget_positive=fiber < 10, joint_window_exists=all(v["final"]["m_win"] > 0 for v in J["functions"].values()), all_claims_have_evidence=all(c["evidence"] for c in claims)))
    paths.OUT(STEP, "assess.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for i in items:
        print(f"代價：{i['item']} {i['db']:.3f} dB（{i['source']}）")
    print(f"各函數合計：{ {f: v['total_dbm'] for f, v in per.items()} } → 決定需求的是 {lim}")
    print(f"靜態 P_u {pu_static} dBm ＋ 動態 {dyn:.2f} dB → {pu_total:.2f} dBm；每根資料光纖 {fiber:.2f} dBm、參考 {budget['fiber_ref_dbm']} dBm、合計 {total:.2f} dBm")
    for c in claims:
        print(f"{c['id']} {c['point']}：{c['evidence']}")


if __name__ == "__main__":
    main()
