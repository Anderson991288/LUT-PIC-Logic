r"""論文全部步驟的唯讀驗收：把各步 out/*.json 的 checks 分成必要檢查與研究結果。

用途：各步程式只計算、保存、列印 checks，自己的結束碼不反映檢查結果，所以 rc＝0 不等於驗收通過。
      本程式讀現有 JSON 判定，不重算、不寫檔。
判定：
  必要檢查（REQUIRED）：程式與數值一致性、界限不得被違反、與草稿的對齊、論文宣告的主張。不成立、缺項或不是布林值都算失敗。
  研究結果（RESEARCH）：結論本身是研究發現，真假都合法，例如「校正迴路會把 AND4 修壞」。只回報；與下表紀錄值不同時列出，
      請人工核對正文，但不影響結束碼。下表的值是 2026-11-07 重現結果。
  數值附註（NUMERIC）：放在 checks 裡的非布林資訊，只列印。
  checks 裡出現表外的項目，或缺少必要檢查，都算失敗，清單才不會無聲變空。
  m4_cert/s3_cert 另由 cert_checks.py 從資料重新推導，不只讀保存值。其他步驟只判定保存值，重新推導需要重算。
輸入：design/paper/**/out/*.json（或 --paper-root 指定的目錄）。
輸出：無檔案。結束碼 0 全部必要檢查通過，1 有失敗。
執行：.\lab design\paper\verify_checks.py [--list]
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PAPER = Path(__file__).resolve().parent
sys.path.insert(0, str(PAPER / "m4_cert" / "s3_cert"))
import cert_checks as CK                                             # noqa: E402

REQUIRED = {
    "m1_timing/s1_budget/out/budget.json": ["o2_o4_latest_equal", "n_mzi", "timing_ok", "power_ok"],
    "m1_timing/s2_interface/out/interface_v2.json": ["resolve_not_worse", "er_found", "bound_fits", "per_input_ok"],
    "m1_timing/s3_tracking/out/tracking.json": ["phi_only_restores", "dither_full_rank", "readout_only_full_rank", "estimate_rms_ok",
                                                "tracked_margin_ok", "alloc_ok"],
    "m1_timing/s4_window/out/window.json": ["window_exists_at_0", "er_window_exists_at_0", "dc_matches_U", "grid_converged",
                                            "penalty_from_margin_ok"],
    "m1_timing/s5_assess/out/assess.json": ["budget_positive", "joint_window_exists", "all_claims_have_evidence"],
    "m1_timing/s5_assess/out/joint.json": ["final_window_exists"],
    "m2_evidence/s1_baseline/out/baseline.json": [],
    "m2_evidence/s2_spec/out/spec.json": ["skew_spec_below_all_1db", "joint_skew_covers_spec", "er_spec_keeps_90pct"],
    "m2_evidence/s3_power/out/power.json": ["tol_above_det", "final_window_at_budget"],
    "m2_evidence/s3_power/out/screen_check.json": ["screen2_within_1pct"],
    "m2_evidence/s4_deviation/out/deviation.json": ["oracle_best_static"],
    "m2_evidence/s5_general/out/general.json": ["all_observable", "synth_matches_course", "swap_equals_xor"],
    "m3_align/s1_params/out/align.json": ["receiver_same", "guard_same_plane_close", "self_consistent_xor2"],
    "m3_align/s2_synth/out/synth.json": ["lossless_match", "lossy_match", "guard_match", "methods_agree"],
    "m3_align/s3_detail/out/detail.json": ["aligned_within_3ps", "box_within_3ps", "box_above_cert", "all_above_treq", "order_same"],
    "m4_cert/s1_quad/out/quad.json": ["exact_words", "exact_random", "exact_time", "q_symmetric"],
    "m4_cert/s2_leaf/out/leaf.json": ["no_violation", "guard_valid", "margin_below_sim", "continuous_valid", "more_leaves_tighter"],
    "m4_cert/s3_cert/out/cert.json": list(CK.REQUIRED),
    "m4_cert/s4_budget/out/budget_ui.json": ["analog_chain", "fine_not_worse", "bw_detail_above_treq", "max_rate_matches_draft", "cert_below_detail"],
    "m4_cert/s4_budget/out/sens.json": ["analog_chain", "fine_not_worse", "bw_detail_above_treq", "max_rate_matches_draft", "cert_below_detail"],
    "m5_cascade/s1_cascade/out/cascade.json": ["all_lossless_realizable", "lossless_ge_lossy", "dual_le_single"],
    "m5_cascade/s2_meander/out/meander.json": ["same_choice", "full_length_match"],
    "m5_cascade/s3_cert/out/cert_cascade.json": ["regression_and4", "no_violation", "guard_valid", "below_sampled", "x1x8_above_treq", "more_leaves_wider"],
    "m5_cascade/s4_screen/out/screen.json": ["n_classes_222", "all_functions", "regression", "cert_le_box", "all_layers", "rule_no_false_members"],
}
RESEARCH = {
    "m1_timing/s1_budget/out/budget.json": {"phase_is_gap": True},
    "m1_timing/s2_interface/out/interface_v2.json": {"er_reduced": True},
    "m1_timing/s3_tracking/out/tracking.json": {"blind_insufficient": True},
    "m1_timing/s5_assess/out/joint.json": {"drift_hurts": True},
    "m2_evidence/s1_baseline/out/baseline.json": {"delay_negligible_both": True, "ranking_same": False, "ranking_reversed_all_tols": True},
    "m2_evidence/s2_spec/out/spec.json": {"five_detectors_needed": True},
    "m2_evidence/s4_deviation/out/deviation.json": {"loop_not_worse": False},
    "m2_evidence/s5_general/out/general.json": {"all_er_keep": False},
    "m3_align/s1_params/out/align.json": {"xor2_guard_smallest": True},
    "m4_cert/s1_quad/out/quad.json": {"not_separable_are_sop2_xor2": True, "not_separable_need_Q": True},
    "m5_cascade/s2_meander/out/meander.json": {"full_eq_shrinks_at_1db": True, "chosen_beats_full_at_1db": True, "stress_needs_meander": True,
                                               "stress_chosen_shorter": True, "stress_chosen_passes_full_fails": True},
}
NUMERIC = {"m2_evidence/s3_power/out/power.json": ["final_window_margin_ps"]}


def judge(rel, data):
    """一個 JSON 的判定：(failures, research_rows)。"""
    checks = data.get("checks")
    if not isinstance(checks, dict) or not checks:
        return ["沒有 checks"], []
    required, research, numeric = REQUIRED[rel], RESEARCH.get(rel, {}), NUMERIC.get(rel, [])
    failures = [f"必要檢查未通過：{k}＝{checks.get(k, '缺項')}" for k in required if checks.get(k) is not True]
    failures += [f"清單外的項目：{k}" for k in checks if k not in required and k not in research and k not in numeric]
    failures += [f"缺研究結果項目：{k}" for k in research if k not in checks]
    rows = []
    for k, recorded in research.items():
        if k in checks:
            rows.append(f"{k}＝{checks[k]}" + ("" if checks[k] == recorded else f"（紀錄值 {recorded}，與紀錄不同，請核對正文）"))
    rows += [f"{k}＝{checks[k]}（數值附註）" for k in numeric if k in checks]
    if rel == "m4_cert/s3_cert/out/cert.json":
        failures += CK.evaluate(data)[0]
    return failures, rows


def verify(root):
    bad = 0
    for rel in REQUIRED:
        path = root / rel
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as ex:
            failures, rows = [f"讀不到：{type(ex).__name__}"], []
        else:
            failures, rows = judge(rel, data)
        bad += len(failures)
        print(f"{'失敗' if failures else '通過'}  {rel}（必要 {len(REQUIRED[rel])} 項）")
        for r in rows:
            print(f"      研究結果：{r}")
        for x in failures:
            print(f"      失敗：{x}")
    n = sum(len(v) for v in REQUIRED.values())
    print(f"共 {len(REQUIRED)} 個 JSON、{n} 項必要檢查、{sum(len(v) for v in RESEARCH.values())} 項研究結果；" + ("全部必要檢查通過" if not bad else f"{bad} 項失敗"))
    return 1 if bad else 0


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    if "--list" in argv:
        for rel, keys in REQUIRED.items():
            print(rel)
            print("   必要：" + ("、".join(keys) or "（無，本步結論都是研究結果）"))
            if rel in RESEARCH:
                print("   研究：" + "、".join(f"{k}（紀錄 {v}）" for k, v in RESEARCH[rel].items()))
        return 0
    root = Path(argv[argv.index("--paper-root") + 1]) if "--paper-root" in argv else PAPER
    return verify(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
