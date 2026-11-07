r"""論文 M2 s2：介面規格與餘裕——把 M1 各步的需求整理成一張表，每一項都附「依據的數字」與「離失效還有多遠」。

用途：M1 的規格散在各步，修正（外部審查）之後有幾項失去餘裕或前後不一致。本步只讀 JSON、不做新計算：
  1. 時間對齊：各函數 skew 額外代價達 1 dB 的點（M1 s4，名義模型、無 MMI 偏差），最小者決定規格；規格取 SKEW_SPEC_PS，
     餘裕＝最小 1 dB 點 − 規格（同時列出倍數）。
  2. 相對相位：δ_det 的幅度相加分配（M1 s3）；可追漂移速度對光纖漂移的倍數，分「5 個輸出都有偵測器」與「只用判讀埠」兩種。
  3. 消光比：解析近似的需求（25.8 dB 時 XOR 類 margin 只保留 89.8%，略低於 90%）與 0.5 dB 格點結果；規格取格點結果 26 dB
     （審查 R11）。所有模擬仍以 25.8 dB 計算，殘留較大，偏保守。
  4. 功率：逐函數總預算（M1 s5），以及聯合驗收與分項相加的差（M1 s5 joint）。
  5. 操作模式：哪些校正在資料傳送前做一次、哪些在傳送中持續做、哪些尚未建模。
每一項給狀態（審查 R10：一律用倍數＝依據／規格，時間項另列距離）：有餘裕（倍數 ≥ OK_RATIO）、餘裕小（1–OK_RATIO）、不足（< 1）、未驗證。
輸入：design/paper/m1_timing/s1_budget/out/budget.json、s2_interface/out/interface_v2.json、s3_tracking/out/tracking.json、
      s4_window/out/window.json、s5_assess/out/assess.json、s5_assess/out/joint.json。
輸出：design/paper/m2_evidence/s2_spec/out/spec.json。
執行：.\lab design\paper\m2_evidence\s2_spec\spec.py（約 1 秒）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import json                                                          # noqa: E402
import math                                                          # noqa: E402

import paths                                                         # noqa: E402

STEP = "paper/m2_evidence/s2_spec"
BASE = "paper/m1_timing"
SKEW_SPEC_PS = 15                                                    # 時間對齊規格：比最小 1 dB 點留 3 ps（1.2 倍）
OK_RATIO = 1.5


def load(sub, name):
    return json.loads(paths.OUT(f"{BASE}/{sub}", name).read_text(encoding="utf-8"))


def status_ratio(r):
    return "有餘裕" if r >= OK_RATIO else ("餘裕小" if r >= 1.0 else "不足")


def main():
    s1, s2, s3 = load("s1_budget", "budget.json"), load("s2_interface", "interface_v2.json"), load("s3_tracking", "tracking.json")
    s4, s5, J = load("s4_window", "window.json"), load("s5_assess", "assess.json"), load("s5_assess", "joint.json")
    er_fn = s2["er_hardest_function"]
    er_spec = s2["er_need_resolved_db"][er_fn]                        # 規格取格點結果（審查 R11）
    # 1. 時間對齊
    allow, extra_at_spec = {}, {}
    for fn, r in s4["functions"].items():
        rows = r["ideal"]["rows"]
        sk = [x["skew_ps"] for x in rows]
        pe = [(x["penalty_db"] if x["penalty_db"] is not None else 99) - rows[0]["penalty_db"] for x in rows]
        v = sk[-1]
        for k in range(1, len(sk)):
            if pe[k] >= 1.0:
                v = sk[k - 1] + (1.0 - pe[k - 1]) / (pe[k] - pe[k - 1]) * (sk[k] - sk[k - 1])
                break
        allow[fn] = round(v, 1)
        k = sk.index(SKEW_SPEC_PS)
        extra_at_spec[fn] = round(pe[k], 3)
    fn_skew = min(allow, key=allow.get)
    skew_margin = round(allow[fn_skew] - SKEW_SPEC_PS, 1)
    skew_ratio = round(allow[fn_skew] / SKEW_SPEC_PS, 2)
    # 2. 相對相位與追蹤
    lag = s3["phase_alloc"]["lag_rad"]
    ramp_all = s3["ramp_rate_allow_rad_s"]
    ramp_ro = lag * 2 * math.pi * s3["loop_bw_readout_only_hz"]
    fiber = s3["fiber_ramp_rad_s"]
    # 4. 功率與聯合驗收
    b = s5["budget"]
    items = [
        dict(item="時間對齊", spec=f"5 路到達時間差 ≤ {SKEW_SPEC_PS} ps",
             evidence=f"最小 1 dB 點 {allow[fn_skew]} ps（{fn_skew}，名義模型、未含 MMI 偏差）；規格處 skew 額外代價最多 {max(extra_at_spec.values()):.2f} dB",
             margin=f"{skew_margin} ps（{skew_ratio} 倍）", status=status_ratio(skew_ratio), source="M1 s4、M2 s1"),
        dict(item="相對相位（合計）", spec=f"估計誤差（3σ）、追蹤落後、快速擾動幅度相加 ≤ δ_det＝{s1['phase']['det_rad']} rad",
             evidence=f"估計 3σ {s3['phase_alloc']['est_3sigma_rad']:.3f}＋落後 {lag:.3f}＋快速 {s3['phase_alloc']['fast_rad']:.3f}",
             margin="用滿", status="餘裕小", source="M1 s1、s3"),
        dict(item="快速擾動", spec=f"快於回授頻寬的相位擾動 ≤ {s3['phase_alloc']['fast_rad']:.3f} rad（發射端負責）",
             evidence="振動、氣流；未量測", margin="—", status="未驗證", source="M1 s3"),
        dict(item="監測偵測器", spec="5 個輸出都要有偵測器",
             evidence=f"可追漂移：5 個 {ramp_all:.3f}、只用 o2、o4 {ramp_ro:.3f} rad/s；光纖 {fiber:g} rad/s",
             margin=f"{ramp_all / fiber:.2f} 倍（只用判讀埠 {ramp_ro / fiber:.2f} 倍）", status=status_ratio(ramp_all / fiber), source="M1 s3"),
        dict(item="資料", spec="隨機資料（例如擾碼）", evidence="擺動量測的雜訊估計假設各位元獨立", margin="—", status="假設", source="M1 s3"),
        dict(item="消光比", spec=f"≥ {er_spec:g} dB（晶片依殘留重新求相位）",
             evidence=f"格點結果 {er_spec:g} dB（{er_fn}）；解析近似 {s2['er_required_db']:.2f} dB 時 XOR 類只保留 89.8%（略低於 90%），模擬都用 {s2['er_required_db']:.1f} dB（偏保守）；轉態時多 {s4['er_extra_db_max']:.3f} dB",
             margin="以 margin 保留 90% 定義（規格處剛好 90%）", status="餘裕小", source="M1 s2、s4、M2 s5"),
        dict(item="功率", spec=f"每根資料光纖 ≥ {b['fiber_data_dbm']:.2f} dBm、參考光纖 ≥ {b['fiber_ref_dbm']:.2f} dBm",
             evidence=f"{b['limiting_function']} 決定；聯合驗收與分項相加差 ≤ {max(abs(v['sum_minus_joint_db']) for v in s5['joint'].values()):.2f} dB",
             margin="已含各項代價（不另留餘裕）", status="需求", source="M1 s5"),
    ]
    modes = [
        dict(phase="上線前（一次）", action="量發射端的殘留光大小與相位；以已知輸入字直接量 o2、o4 的功率差，依量到的 margin 重新求 14 個相位（靜態校正，含 MMI 等硬體偏差，M2 s4）", data="不傳資料", status="參考解已模擬（已知硬體、靜態最佳，M2 s4）；量測型重解（量測次數、誤差、收斂）未建模"),
        dict(phase="啟動", action="把 4 路輸入相位拉到追蹤的可用範圍內（初始對準）", data="不傳資料或用已知字", status="未建模"),
        dict(phase="運作中（持續）", action="7 個 heater 同時小幅擺動、同步偵測，只調 φ 追蹤漂移（動態校正）", data="照常傳送，資料需隨機", status="已模擬（一階回授）"),
        dict(phase="異常", action="漂移超出追蹤範圍或判讀錯誤率上升時，回到啟動", data="中斷", status="未建模"),
    ]
    res = dict(skew_spec_ps=SKEW_SPEC_PS, skew_allow_1db_ps=allow, skew_extra_at_spec_db=extra_at_spec, skew_limit_function=fn_skew,
               skew_margin_ps=skew_margin, skew_margin_ratio=skew_ratio, ok_ratio=OK_RATIO, er_spec_db=er_spec, er_sim_db=s2["er_required_db"],
               joint_skew_ps=J["skew_ps"], ramp_all_rad_s=ramp_all, ramp_readout_only_rad_s=round(ramp_ro, 4), fiber_ramp_rad_s=fiber,
               ramp_ratio_all=round(ramp_all / fiber, 2), ramp_ratio_readout_only=round(ramp_ro / fiber, 2),
               items=items, modes=modes,
               checks=dict(skew_spec_below_all_1db=all(v > SKEW_SPEC_PS for v in allow.values()),
                           five_detectors_needed=ramp_ro < fiber <= ramp_all,
                           joint_skew_covers_spec=J["skew_ps"] >= SKEW_SPEC_PS,
                           er_spec_keeps_90pct=(1 - 10 ** (-er_spec / 20)) ** 2 >= 0.9))
    paths.OUT(STEP, "spec.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for i in items:
        print(f"{i['item']}：{i['spec']}｜{i['evidence']}｜餘裕 {i['margin']}（{i['status']}）")
    for m in modes:
        print(f"{m['phase']}：{m['action']}；資料 {m['data']}；{m['status']}")
    print("檢查：", res["checks"])


if __name__ == "__main__":
    main()
