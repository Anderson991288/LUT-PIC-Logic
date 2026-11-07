# 檔案索引（由 tools/make_index.py 自動產生，不要手改）

| 檔案 | 大小 | 用途／產生者 | 所屬步驟 |
|---|---|---|---|
| `design/common/concept.py` | 2.6 KB | 共用的概念圖版型（每步開頭的「本步概念」圖）。 | 共用 |
| `design/common/draw.py` | 2.9 KB | 共用的示意圖元件（M1 s2 起）：MZI 方塊與 B7 接線圖，所有步驟畫 B7 都用這裡，確保接線與 common/mzi.py 一致。 | 共用 |
| `design/common/drc/cornerstone_Si220_passive.lydrc` | 6.9 KB | CORNERSTONE DRC deck（平台提供，不匯出） | 共用 |
| `design/common/drc.py` | 4.4 KB | KLayout 批次 DRC（CORNERSTONE Si220 被動 deck）（M0 s1 起使用）。 | 共用 |
| `design/common/gds2png.py` | 15.3 KB | 自包含 GDS -> PNG 渲染器（繪製層俯視圖，依 layer 分色）。 | 共用 |
| `design/common/mzi.py` | 1.7 KB | 共用的 MZI 與 B7 模型（M1 s2 起）。 | 共用 |
| `design/common/optics.py` | 0.7 KB | 共用的理想光學元件（M1 s1 起）。 | 共用 |
| `design/common/runtime.py` | 2.9 KB | 共用執行環境設定（M0 s1）。 | 共用 |
| `design/common/shot_record.py` | 2.9 KB | 記錄 Virtuoso 與 Calibre RVE 截圖對應哪一份 GDS，並把結果寫回 commercial.json 的 status。 | 共用 |
| `design/common/synth.py` | 1.4 KB | 共用的相位合成（M1 s2 起）：給定電路與目標真值表，找出讓判讀 margin 最大的相位。 | 共用 |
| `design/common/test_gds_parser.py` | 10.1 KB | GDS 解析器的故障測試：放錯的 datatype 與不支援的內容必須立即失敗，正常資料必須讀得出來。 | 共用 |
| `design/lut4/build_study.py` | 127.4 KB | 組裝 report/LUT4_Study.html：沿用原課程頁的版型與 M1 s1，M1 s2 起改為 LUT4 架構（Model-7a＋雙差值判讀）。 | 共用 |
| `design/lut4/s0_algebra/algebra.py` | 5.1 KB | LUT4 s0：3142132 的矩陣運算——沿路徑求 U 的元素、逐層光場、雙差值的二次式。 | 共用 |
| `design/lut4/s0_algebra/out/algebra.json` | 5.5 KB | 產生者：algebra.py | 共用 |
| `design/lut4/s0_basics/basics.py` | 2.9 KB | LUT4 s0：重算 M1 s2 ①② 的兩張表——單顆 MZI、二顆 MZI＋R 在固定門檻下能實現哪些二輸入邏輯。 | 共用 |
| `design/lut4/s0_basics/out/basics.json` | 0.5 KB | 產生者：basics.py | 共用 |
| `design/lut4/s0_coverage/cover4.py` | 12.6 KB | LUT4 s0：Model-7a 的邏輯涵蓋——4 輸入真值表逐張合成，保存 mask、14 個相位與裕量。 | 共用 |
| `design/lut4/s0_coverage/cover4_split.py` | 4.2 KB | LUT4 s0：把 65,536 張真值表依 PTF2／非 PTF2 分組，並對兩組裕量資料分欄統計。 | 共用 |
| `design/lut4/s0_coverage/out/bank_replay.json` | 2.3 KB | 產生者：replay_bank.py | 共用 |
| `design/lut4/s0_coverage/out/bank_replay_margins.npy` | 512.1 KB | 產生者：replay_bank.py | 共用 |
| `design/lut4/s0_coverage/out/coverage.json` | 3.7 KB | 產生者：cover4.py | 共用 |
| `design/lut4/s0_coverage/out/coverage_margins.npy` | 512.1 KB | ？ | 共用 |
| `design/lut4/s0_coverage/out/coverage_phases.npz` | 8.6 MB | 產生者：cover4.py | 共用 |
| `design/lut4/s0_coverage/out/coverage_split.json` | 3.3 KB | 產生者：cover4_split.py | 共用 |
| `design/lut4/s0_coverage/out/failures_round1.csv` | 0.0 KB | 產生者：replay_full.py | 共用 |
| `design/lut4/s0_coverage/out/full_replay.json` | 1.9 KB | 產生者：replay_full.py | 共用 |
| `design/lut4/s0_coverage/out/merged_phases.npz` | 7.3 MB | 產生者：replay_full.py | 共用 |
| `design/lut4/s0_coverage/out/ptf2_flags.npy` | 64.1 KB | 產生者：cover4_split.py | 共用 |
| `design/lut4/s0_coverage/out/refine.json` | 17.7 KB | 產生者：refine.py | 共用 |
| `design/lut4/s0_coverage/out/refine_phases.npz` | 6.1 KB | 產生者：refine.py | 共用 |
| `design/lut4/s0_coverage/out/sample_coverage.json` | 1.7 KB | ？ | 共用 |
| `design/lut4/s0_coverage/out/sample_masks.json` | 3.3 KB | 產生者：cover4.py | 共用 |
| `design/lut4/s0_coverage/out/sample_phases.npz` | 31.4 KB | ？ | 共用 |
| `design/lut4/s0_coverage/out/sample_refine.json` | 9.7 KB | ？ | 共用 |
| `design/lut4/s0_coverage/out/sample_refine_phases.npz` | 1.8 KB | ？ | 共用 |
| `design/lut4/s0_coverage/reference/coverage.json` | 0.6 KB | 產生者：cover4.py | 共用 |
| `design/lut4/s0_coverage/reference/coverage_margins.npy` | 512.1 KB | ？ | 共用 |
| `design/lut4/s0_coverage/reference/coverage_split.json` | 0.6 KB | 產生者：cover4_split.py | 共用 |
| `design/lut4/s0_coverage/reference/refine.json` | 6.2 KB | 產生者：refine.py | 共用 |
| `design/lut4/s0_coverage/reference/three_refined_3142132.npz` | 7.3 MB | ？ | 共用 |
| `design/lut4/s0_coverage/refine.py` | 5.9 KB | LUT4 s0：對涵蓋掃描中裕量最差的函數，增加起點數重新合成相位，看裕量能提高多少；相位一併保存。 | 共用 |
| `design/lut4/s0_coverage/replay_bank.py` | 7.9 KB | LUT4 s0：參考相位重播（Codex 相位庫）——用獨立的 5×5 矩陣實作，重播 65,536 張 × 16 列的判讀。 | 共用 |
| `design/lut4/s0_coverage/replay_full.py` | 7.1 KB | LUT4 s0：全表獨立重播——把本次第一輪相位與補強相位合併成可重播的相位庫，逐張重算 65,536 張 × 16 列。 | 共用 |
| `design/lut4/s0_coverage/run.log` | 1.8 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_full.log` | 1.5 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_refine_full.log` | 6.7 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_replay_full.log` | 1.9 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_sample.log` | 0.9 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_split.log` | 1.5 KB | ？ | 共用 |
| `design/lut4/s0_coverage/run_split_full.log` | 2.0 KB | ？ | 共用 |
| `design/lut4/s1_handoff/handoff.py` | 14.1 KB | LUT4 s1：交接與介面規格——3142132 的固定光路、功能設定與晶片介面。 | 共用 |
| `design/lut4/s1_handoff/out/lut4_netlist.json` | 3.0 KB | ？ | 共用 |
| `design/lut4/s1_handoff/out/phases.json` | 4.7 KB | ？ | 共用 |
| `design/lut4/s1_handoff/out/replay.json` | 1.7 KB | 產生者：replay.py | 共用 |
| `design/lut4/s1_handoff/out/spec.json` | 7.6 KB | ？ | 共用 |
| `design/lut4/s1_handoff/out/tolerance.json` | 3.0 KB | ？ | 共用 |
| `design/lut4/s1_handoff/out/truth_tables.csv` | 6.9 KB | ？ | 共用 |
| `design/lut4/s1_handoff/replay.py` | 8.7 KB | LUT4 s1：只用交接檔重播——拿到 lut4_netlist.json、phases.json、truth_tables.csv 的人，能不能自己算出同樣的結果？ | 共用 |
| `design/lut4/s1_handoff/run.log` | 2.4 KB | ？ | 共用 |
| `design/lut4/s2_sim/out/sim_results.json` | 3.9 KB | 產生者：sim.py | 共用 |
| `design/lut4/s2_sim/out/sim_truth.csv` | 6.9 KB | 產生者：sim.py | 共用 |
| `design/lut4/s2_sim/run.log` | 1.2 KB | ？ | 共用 |
| `design/lut4/s2_sim/sim.py` | 7.1 KB | LUT4 s2：電路模擬——3142132 換成 PDK 的 MMI 模型、用 IPKISS 電路模擬（Caphe）求散射矩陣，雙差值判讀還對嗎？ | 共用 |
| `design/lut4/s3_core/figs.py` | 7.4 KB | 核心佈局：圖——LUT4 核心全圖（標出 MZI、heater 編號、光學埠）、單顆 MZI 尺寸、heater 端點放大。 | 共用 |
| `design/lut4/s3_core/layout.py` | 21.0 KB | 核心佈局：IPKISS 佈局：LUT4 核心——電路連接怎麼變成實體幾何？ | 共用 |
| `design/lut4/s3_core/out/l4_core.gds` | 17.1 KB | 產生者：layout.py | 共用 |
| `design/lut4/s3_core/out/l4_core_framed.gds` | 17.2 KB | 產生者：layout.py | 共用 |
| `design/lut4/s3_core/out/l4_core_framed_drc.lyrdb` | 4.2 KB | 產生者：layout.py | 共用 |
| `design/lut4/s3_core/out/layout_info.json` | 11.2 KB | 產生者：layout.py | 共用 |
| `design/lut4/s3_core/run_figs.log` | 0.1 KB | ？ | 共用 |
| `design/lut4/s3_core/run_layout.log` | 1.0 KB | ？ | 共用 |
| `design/lut4/s4_review/figs.py` | 8.2 KB | 佈局審查：圖——從 GDS 抽出的光路（每段波導一種顏色）、審查放大圖、由佈局重算 U 的結果。 | 共用 |
| `design/lut4/s4_review/out/extracted.json` | 9.9 KB | 產生者：review.py | 共用 |
| `design/lut4/s4_review/out/review_checks.json` | 5.2 KB | 產生者：review.py | 共用 |
| `design/lut4/s4_review/review.py` | 21.9 KB | 佈局審查：佈局審查——佈局有沒有照電路圖？埠序、直通線、彎道、金屬位置合理嗎？ | 共用 |
| `design/lut4/s4_review/run_figs.log` | 0.1 KB | ？ | 共用 |
| `design/lut4/s4_review/run_review.log` | 1.3 KB | ？ | 共用 |
| `design/lut4/s5_chip/chip.py` | 28.2 KB | 晶片整合：晶片整合：EC 與 PAD——光怎麼進出晶片？heater 怎麼繞線到 PAD？ | 共用 |
| `design/lut4/s5_chip/figs.py` | 7.0 KB | 晶片整合：圖——整顆晶片（EC、扇出、PAD、繞線）、EC 放大、繞線放大（橫移與跨越波導）、電流密度。 | 共用 |
| `design/lut4/s5_chip/out/chip.gds` | 79.9 KB | 產生者：chip.py | 共用 |
| `design/lut4/s5_chip/out/chip_drc.lyrdb` | 4.4 KB | 產生者：chip.py | 共用 |
| `design/lut4/s5_chip/out/chip_info.json` | 21.6 KB | 產生者：chip.py | 共用 |
| `design/lut4/s5_chip/run_chip.log` | 2.0 KB | ？ | 共用 |
| `design/lut4/s5_chip/run_figs.log` | 0.1 KB | ？ | 共用 |
| `design/lut4/s6_verify/figs.py` | 6.4 KB | 連接檢查：圖——從 GDS 抽出的電氣網（每個網一種顏色）、LVS 對照表與故障注入結果。 | 共用 |
| `design/lut4/s6_verify/gnd_net.py` | 18.8 KB | heater 供電回路的電阻網路：依每段走線的長、寬、厚度建立節點方程式，求多個 heater 同時驅動時的電壓、功率與相位誤差。 | 共用 |
| `design/lut4/s6_verify/out/chip_fault_drc.gds` | 81.8 KB | 產生者：verify.py | 共用 |
| `design/lut4/s6_verify/out/chip_fault_drc_drc.lyrdb` | 5.0 KB | 產生者：verify.py | 共用 |
| `design/lut4/s6_verify/out/connectivity.json` | 26.7 KB | 產生者：verify.py | 共用 |
| `design/lut4/s6_verify/out/drc_result.json` | 2.0 KB | 產生者：verify.py | 共用 |
| `design/lut4/s6_verify/out/gnd_segments.json` | 14.2 KB | 產生者：gnd_net.py、verify.py | 共用 |
| `design/lut4/s6_verify/run_figs.log` | 0.0 KB | ？ | 共用 |
| `design/lut4/s6_verify/run_verify.log` | 1.4 KB | ？ | 共用 |
| `design/lut4/s6_verify/verify.py` | 19.1 KB | 連接檢查：DRC 與連接檢查——能不能製造？每個 heater 真的接到對的 PAD 嗎？光真的接到對的 EC 嗎？ | 共用 |
| `design/lut4/s7_delivery/check_delivery.py` | 54.8 KB | 交付檢查（LUT4 s7）：拿到交付包的人，用這支程式確認檔案完整、彼此一致、結果可以重算。 | 共用 |
| `design/lut4/s7_delivery/out/delivery_check.json` | 30.7 KB | 產生者：check_delivery.py、package.py | 共用 |
| `design/lut4/s7_delivery/out/package.json` | 0.2 KB | 產生者：package.py | 共用 |
| `design/lut4/s7_delivery/package.py` | 17.6 KB | LUT4 s7：交付包——把佈局、介面、功能設定與驗證結果整理成一包，並附 SHA-256 清單。 | 共用 |
| `design/lut4/s7_delivery/run_package.log` | 0.3 KB | ？ | 共用 |
| `design/lut4/s8_commercial/commercial.py` | 29.1 KB | LUT4 s8（由 M3 s6 複製，輸入改為 LUT4 交付包）：商用工具對照：Virtuoso／Calibre——同一份交付 GDS，換成業界常用的工具，結果一樣嗎？ | 共用 |
| `design/lut4/s8_commercial/figs.py` | 5.5 KB | M3 s6：圖——KLayout 平台 deck 與 Calibre 草案在四份 GDS 上的結果、maxVertices＝200 匯出後的接縫放大。 | 共用 |
| `design/lut4/s8_commercial/out/calibre_chip.log` | 49.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_chip.results` | 2.7 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_chip.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_fault.log` | 50.3 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_fault.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_fault.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_200.log` | 49.6 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_200.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_200.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_8191.log` | 49.6 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_8191.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/calibre_strmout_8191.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/cds.lib` | 0.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/commercial.json` | 12.7 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/cornerstone_basic_draft_chip.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/cornerstone_basic_draft_fault.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/cornerstone_basic_draft_strmout_200.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/cornerstone_basic_draft_strmout_8191.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/eda_run_record.json` | 2.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/raw_vs_clean.lydrc` | 0.7 KB | CORNERSTONE DRC deck（平台提供，不匯出） | 共用 |
| `design/lut4/s8_commercial/out/raw_vs_clean_chip.lyrdb` | 1.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/raw_vs_clean_strmout_200.lyrdb` | 11.9 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/chip_fault_drc.gds` | 81.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/commercial.json` | 8.4 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/cornerstone_basic_draft_chip.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/cornerstone_basic_draft_fault.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/cornerstone_basic_draft_strmout_200.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/cornerstone_basic_draft_strmout_8191.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/reference_evidence/LUT4_chip.gds` | 79.9 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/run.sh` | 1.2 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/rve.sh` | 0.2 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/rve_chip.log` | 0.9 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/rve_chip.png` | 24.5 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/rve_fault.log` | 0.9 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/rve_fault.png` | 25.1 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/shot_record.json` | 1.9 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/strmin.log` | 7.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_200.gds` | 78.0 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_200.log` | 10.9 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_200_drc.lyrdb` | 16.3 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_8191.gds` | 76.0 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_8191.log` | 7.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/strmout_8191_drc.lyrdb` | 4.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/out/v_chip.png` | 147.7 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/v_core.png` | 143.4 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/v_fault.png` | 136.4 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/v_mzi.png` | 150.3 KB | ？ | 共用 |
| `design/lut4/s8_commercial/out/virtuoso_colors.drf` | 0.2 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/virtuoso_view.il` | 3.0 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/virtuoso_view.sh` | 0.9 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4/s8_commercial/out/xStrmOut_layerMap.txt` | 0.5 KB | 產生者：commercial.py | 共用 |
| `design/lut4/s8_commercial/run_commercial.log` | 3.0 KB | ？ | 共用 |
| `design/lut4/s8_commercial/run_figs.log` | 0.0 KB | ？ | 共用 |
| `design/lut4/s8_commercial/run_view_script_only.log` | 0.1 KB | ？ | 共用 |
| `design/lut4/s8_commercial/virtuoso_view.py` | 11.9 KB | LUT4 s8：在 Virtuoso 打開交付的 LUT4 晶片（只看、不改），以 Virtuoso 自己的存圖函式輸出畫面；Calibre RVE 開啟故障檔的結果。 | 共用 |
| `design/lut4/s9_system/gain_box.py` | 13.2 KB | LUT4 s9：增益盒的確定性檢查——三路增益各在 [1−ε, 1+ε] 內時，16 組判讀是否全部正確。 | 共用 |
| `design/lut4/s9_system/gain_robust.py` | 6.1 KB | LUT4 s9：TIA 增益失配的補強——(A) 量測增益後重新求相位；(B) 合成時挑耐增益誤差的相位解。 | 共用 |
| `design/lut4/s9_system/out/gain_box.json` | 8.5 KB | 產生者：gain_box.py | 共用 |
| `design/lut4/s9_system/out/gain_robust.json` | 3.4 KB | 產生者：gain_robust.py | 共用 |
| `design/lut4/s9_system/out/system.json` | 8.1 KB | 產生者：system.py | 共用 |
| `design/lut4/s9_system/reference/chip_info.json` | 20.0 KB | ？ | 共用 |
| `design/lut4/s9_system/reference/review_checks.json` | 5.0 KB | ？ | 共用 |
| `design/lut4/s9_system/run_gain_box.log` | 1.5 KB | ？ | 共用 |
| `design/lut4/s9_system/run_gain_robust.log` | 1.2 KB | ？ | 共用 |
| `design/lut4/s9_system/run_system_layout.log` | 2.6 KB | ？ | 共用 |
| `design/lut4/s9_system/system.py` | 10.4 KB | LUT4 s9：系統層級分析——晶片走線損耗、TIA 三路同時偏差、波長與溫度、消光比、光功率預算。 | 共用 |
| `design/lut4/synth4.py` | 7.5 KB | 加速版合成：批次向量化的光路計算與批次數值梯度。 | 共用 |
| `design/lut4/v2_epm/epm_eval.py` | 2.2 KB | LUT4v2：Model-7a 以 OOK（0/1）與 E+/E-（±1）輸入的小比較。只算 7 個範例函數。 | 共用 |
| `design/lut4/v2_epm/full_eval.py` | 3.0 KB | LUT4v2：E± 輸入（0＝+E、1＝−E）＋R＝3（+E）、Model-7a 雙差值＋AND，逐張驗證 65536 張真值表。 | 共用 |
| `design/lut4/v2_epm/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/lut4/v2_epm/make_v2.py` | 18.6 KB | LUT4v2：由 report/LUT4_Study.html 複製出 report/LUT4v2_study.html，插入「v2 節」並在 OOK 數字處加註。 | 共用 |
| `design/lut4/v2_epm/noref_eval.py` | 1.5 KB | LUT4v2：E± 輸入、不用參考光（R=0）、兩個差動對（Model-7a 雙差值＋AND）。 | 共用 |
| `design/lut4/v2_epm/ref_eval.py` | 0.9 KB | LUT4v2：參考光強度的比較。E± 輸入時參考只用一路與資料同振幅的 E+（R=1，同 ALU8 的「一個 E+」）， | 共用 |
| `design/lut4/v2_epm/sample_eval.py` | 1.3 KB | LUT4v2：E± 輸入＋R=3、Model-7a 雙差值，抽樣檢查真值表是否都能實現（不跑全部 65536）。 | 共用 |
| `design/lut4/v2_epm/worst_eval.py` | 0.9 KB | LUT4v2：逐張驗證中最差的真值表（0x96e9）不設停止門檻，以 400 個起點（16 個 worker 各 25 個）求較完整的裕量。 | 共用 |
| `design/lut4v2/_logs/algebra.log` | 1.0 KB | ？ | 共用 |
| `design/lut4v2/_logs/basics.log` | 1.1 KB | ？ | 共用 |
| `design/lut4v2/_logs/cover4_sample.log` | 1.3 KB | ？ | 共用 |
| `design/lut4v2/_logs/encoding.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/epm.log` | 2.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/figs_basics.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/gain_robust.log` | 1.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/handoff.log` | 2.5 KB | ？ | 共用 |
| `design/lut4v2/_logs/refine_sample.log` | 1.7 KB | ？ | 共用 |
| `design/lut4v2/_logs/replay.log` | 0.8 KB | ？ | 共用 |
| `design/lut4v2/_logs/run.sh` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/_logs/sample_masks.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/sim.log` | 1.3 KB | ？ | 共用 |
| `design/lut4v2/_logs/solve_demo.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/_logs/system.log` | 2.7 KB | ？ | 共用 |
| `design/lut4v2/_logs/try_one.log` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/build_study.py` | 163.9 KB | 組裝 report/LUT4v2_study.html（v2：資料輸入改為 E+／E− 二相位光）：沿用原課程頁的版型與 M1 s1，新增 M1 s1b（二相位輸入與讀出方式），M1 s2 起為 Model-7a＋雙差值判讀。 | 共用 |
| `design/lut4v2/epm_section.py` | 10.4 KB | LUT4 v2 課程：M1 s1b「E+／E− 二相位輸入與讀出方式」的內容（由 build_study.py 呼叫）。 | 共用 |
| `design/lut4v2/HISTORY.md` | 9.6 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/lut4v2/s0_algebra/algebra.py` | 5.4 KB | LUT4 v2 s0（輸入 E+／E−）：3142132 的矩陣運算——沿路徑求 U 的元素、逐層光場、雙差值的二次式。 | 共用 |
| `design/lut4v2/s0_algebra/out/algebra.json` | 5.5 KB | 產生者：algebra.py | 共用 |
| `design/lut4v2/s0_basics/basics.py` | 6.5 KB | LUT4 s0（M1 s2 ①②）：E+／E− 輸入下，單顆 MZI、二顆 MZI＋R 以一組差動對判讀能實現哪些二輸入邏輯。 | 共用 |
| `design/lut4v2/s0_basics/encoding.py` | 4.8 KB | LUT4 s0（M1 s1 ②）：圖——同一組位元以強度編碼（OOK）與 E+／E− 二相位編碼送出時的光波、功率與判讀。 | 共用 |
| `design/lut4v2/s0_basics/figs.py` | 6.9 KB | LUT4 s0（M1 s2 ①②）：圖——E± 輸入時單顆 MZI、二顆 MZI＋R 的接法與判讀結果。 | 共用 |
| `design/lut4v2/s0_basics/out/basics.json` | 32.3 KB | 產生者：basics.py | 共用 |
| `design/lut4v2/s0_coverage/cover4.py` | 12.9 KB | LUT4 s0：Model-7a 的邏輯涵蓋——4 輸入真值表逐張合成（E+／E− 輸入），同時保存 mask、14 個相位與裕量。 | 共用 |
| `design/lut4v2/s0_coverage/cover4_split.py` | 2.0 KB | LUT4 s0：把逐張合成的 65,536 個裕量（cover4.py）依 PTF2／非 PTF2 分組，並依裕量分段計數。 | 共用 |
| `design/lut4v2/s0_coverage/out/coverage.json` | 1.2 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/coverage_margins.npy` | 512.1 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/coverage_phases.npz` | 8.3 MB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/coverage_split.json` | 0.6 KB | 產生者：cover4_split.py | 共用 |
| `design/lut4v2/s0_coverage/out/failures_round1.csv` | 0.1 KB | 產生者：replay_full.py | 共用 |
| `design/lut4v2/s0_coverage/out/full_replay.json` | 1.9 KB | 產生者：replay_full.py | 共用 |
| `design/lut4v2/s0_coverage/out/merged_phases.npz` | 7.2 MB | 產生者：replay_full.py | 共用 |
| `design/lut4v2/s0_coverage/out/refine.json` | 10.0 KB | 產生者：refine.py | 共用 |
| `design/lut4v2/s0_coverage/out/refine_phases.npz` | 17.5 KB | 產生者：refine.py | 共用 |
| `design/lut4v2/s0_coverage/out/sample_coverage.json` | 29.0 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/sample_phases.npz` | 29.8 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/sample_refine.json` | 17.1 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/out/sample_refine_phases.npz` | 4.3 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/reference/coverage.json` | 0.6 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/reference/coverage_margins.npy` | 512.1 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/reference/refine.json` | 6.3 KB | 產生者：refine.py | 共用 |
| `design/lut4v2/s0_coverage/refine.py` | 8.5 KB | LUT4 s0：對第一輪（cover4.py，24 個起點）裕量最差的真值表增加起點數重新合成相位，保存相位，看裕量能提高多少。 | 共用 |
| `design/lut4v2/s0_coverage/replay_full.py` | 7.1 KB | LUT4 s0：全表獨立重播——把本次第一輪相位與補強相位合併成可重播的相位庫，逐張重算 65,536 張 × 16 列。 | 共用 |
| `design/lut4v2/s0_coverage/run_full.log` | 4.1 MB | ？ | 共用 |
| `design/lut4v2/s0_coverage/run_refine_full.log` | 4.9 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/run_replay_full.log` | 1.9 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/run_split_full.log` | 0.5 KB | ？ | 共用 |
| `design/lut4v2/s0_coverage/sample_masks.json` | 6.1 KB | 產生者：sample_masks.py | 共用 |
| `design/lut4v2/s0_coverage/sample_masks.py` | 2.2 KB | LUT4 s0：產生本輪全覆蓋抽樣的真值表清單 sample_masks.json（給 cover4.py --masks 用）。 | 共用 |
| `design/lut4v2/s0_epm/epm.py` | 4.0 KB | LUT4 v2 s0：E+／E− 二相位輸入與 OOK 的比較，以及不用參考光時能做的真值表。 | 共用 |
| `design/lut4v2/s0_epm/out/epm.json` | 2.8 KB | 產生者：epm.py | 共用 |
| `design/lut4v2/s0_student/out/solve_demo.json` | 0.1 KB | 產生者：solve_demo.py | 共用 |
| `design/lut4v2/s0_student/solve_demo.py` | 4.5 KB | 學員示範：相位怎麼求——從一張真值表反推 Model-7a 的 14 個相位（教學版，與 synth4.py 的正式求解同一個模型）。 | 共用 |
| `design/lut4v2/s0_student/try_one.py` | 3.2 KB | 學員練習：選一張真值表，求 14 個相位，逐列驗收，再故意用錯輸入編碼看會發生什麼。 | 共用 |
| `design/lut4v2/s1_handoff/handoff.py` | 14.5 KB | LUT4 v2 s1（輸入 E+／E−）：交接與介面規格——3142132 的固定光路、功能設定與晶片介面。 | 共用 |
| `design/lut4v2/s1_handoff/out/lut4_netlist.json` | 3.1 KB | ？ | 共用 |
| `design/lut4v2/s1_handoff/out/phases.json` | 4.7 KB | ？ | 共用 |
| `design/lut4v2/s1_handoff/out/replay.json` | 1.6 KB | 產生者：replay.py | 共用 |
| `design/lut4v2/s1_handoff/out/spec.json` | 7.9 KB | ？ | 共用 |
| `design/lut4v2/s1_handoff/out/tolerance.json` | 3.0 KB | ？ | 共用 |
| `design/lut4v2/s1_handoff/out/truth_tables.csv` | 6.9 KB | ？ | 共用 |
| `design/lut4v2/s1_handoff/replay.py` | 6.9 KB | LUT4 s1：獨立重播器——只依交接檔（lut4_netlist.json、phases.json、truth_tables.csv）的慣例重算 112 列判讀，並做竄改測試。 | 共用 |
| `design/lut4v2/s2_sim/out/sim_results.json` | 3.8 KB | 產生者：sim.py | 共用 |
| `design/lut4v2/s2_sim/out/sim_truth.csv` | 6.9 KB | 產生者：sim.py | 共用 |
| `design/lut4v2/s2_sim/sim.py` | 7.2 KB | LUT4 s2：電路模擬——3142132 換成 PDK 的 MMI 模型、用 IPKISS 電路模擬（Caphe）求散射矩陣，雙差值判讀還對嗎？ | 共用 |
| `design/lut4v2/s3_core/_logs/ALL_STEPS.log` | 0.6 KB | ？ | 共用 |
| `design/lut4v2/s3_core/_logs/figs.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s3_core/_logs/layout.log` | 1.1 KB | ？ | 共用 |
| `design/lut4v2/s3_core/figs.py` | 7.4 KB | 核心佈局：圖——LUT4 核心全圖（標出 MZI、heater 編號、光學埠）、單顆 MZI 尺寸、heater 端點放大。 | 共用 |
| `design/lut4v2/s3_core/layout.py` | 21.0 KB | 核心佈局：IPKISS 佈局：LUT4 核心——電路連接怎麼變成實體幾何？ | 共用 |
| `design/lut4v2/s3_core/out/l4_core.gds` | 17.1 KB | 產生者：layout.py | 共用 |
| `design/lut4v2/s3_core/out/l4_core_framed.gds` | 17.2 KB | 產生者：layout.py | 共用 |
| `design/lut4v2/s3_core/out/l4_core_framed_drc.lyrdb` | 4.2 KB | 產生者：layout.py | 共用 |
| `design/lut4v2/s3_core/out/layout_info.json` | 11.2 KB | 產生者：layout.py | 共用 |
| `design/lut4v2/s4_review/_logs/figs.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s4_review/_logs/review.log` | 1.4 KB | ？ | 共用 |
| `design/lut4v2/s4_review/figs.py` | 8.2 KB | 佈局審查：圖——從 GDS 抽出的光路（每段波導一種顏色）、審查放大圖、由佈局重算 U 的結果。 | 共用 |
| `design/lut4v2/s4_review/out/extracted.json` | 9.9 KB | 產生者：review.py | 共用 |
| `design/lut4v2/s4_review/out/review_checks.json` | 5.2 KB | 產生者：review.py | 共用 |
| `design/lut4v2/s4_review/review.py` | 22.0 KB | 佈局審查：佈局審查——佈局有沒有照電路圖？埠序、直通線、彎道、金屬位置合理嗎？ | 共用 |
| `design/lut4v2/s5_chip/_logs/chip.log` | 2.1 KB | ？ | 共用 |
| `design/lut4v2/s5_chip/_logs/figs.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s5_chip/_logs/layer_view.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s5_chip/chip.py` | 33.5 KB | 晶片整合：晶片整合：EC 與 PAD——光怎麼進出晶片？heater 怎麼繞線到 PAD？ | 共用 |
| `design/lut4v2/s5_chip/figs.py` | 7.9 KB | 晶片整合：圖——整顆晶片（EC、扇出、PAD、繞線）、EC 放大、繞線放大（橫移與跨越波導）、電流密度。 | 共用 |
| `design/lut4v2/s5_chip/layer_view.py` | 6.9 KB | LUT4 v2 晶片整合：可縮放的 GDS 圖層檢視——在瀏覽器裡放大、拖曳整顆晶片，逐層開關。 | 共用 |
| `design/lut4v2/s5_chip/out/chip.gds` | 79.0 KB | 產生者：chip.py | 共用 |
| `design/lut4v2/s5_chip/out/chip_drc.lyrdb` | 4.4 KB | 產生者：chip.py | 共用 |
| `design/lut4v2/s5_chip/out/chip_info.json` | 19.7 KB | 產生者：chip.py | 共用 |
| `design/lut4v2/s6_verify/_logs/figs.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s6_verify/_logs/verify.log` | 1.4 KB | ？ | 共用 |
| `design/lut4v2/s6_verify/figs.py` | 6.3 KB | 連接檢查：圖——從 GDS 抽出的電氣網（每個網一種顏色）、LVS 對照表與故障注入結果。 | 共用 |
| `design/lut4v2/s6_verify/gnd_net.py` | 18.8 KB | heater 供電回路的電阻網路：依每段走線的長、寬、厚度建立節點方程式，求多個 heater 同時驅動時的電壓、功率與相位誤差。 | 共用 |
| `design/lut4v2/s6_verify/out/chip_fault_drc.gds` | 80.9 KB | 產生者：verify.py | 共用 |
| `design/lut4v2/s6_verify/out/chip_fault_drc_drc.lyrdb` | 5.0 KB | 產生者：verify.py | 共用 |
| `design/lut4v2/s6_verify/out/connectivity.json` | 26.9 KB | 產生者：verify.py | 共用 |
| `design/lut4v2/s6_verify/out/drc_result.json` | 2.0 KB | 產生者：verify.py | 共用 |
| `design/lut4v2/s6_verify/out/gnd_segments.json` | 12.0 KB | 產生者：gnd_net.py、verify.py | 共用 |
| `design/lut4v2/s6_verify/verify.py` | 19.3 KB | 連接檢查：DRC 與連接檢查——能不能製造？每個 heater 真的接到對的 PAD 嗎？光真的接到對的 EC 嗎？ | 共用 |
| `design/lut4v2/s7_delivery/_logs/package.log` | 0.3 KB | ？ | 共用 |
| `design/lut4v2/s7_delivery/_logs/package_pass1.log` | 0.3 KB | ？ | 共用 |
| `design/lut4v2/s7_delivery/check_delivery.py` | 54.9 KB | 交付檢查（LUT4 E± s7）：拿到交付包的人，用這支程式確認檔案完整、彼此一致、結果可以重算。 | 共用 |
| `design/lut4v2/s7_delivery/out/delivery_check.json` | 30.7 KB | 產生者：check_delivery.py、package.py | 共用 |
| `design/lut4v2/s7_delivery/out/package.json` | 0.2 KB | 產生者：package.py | 共用 |
| `design/lut4v2/s7_delivery/package.py` | 17.8 KB | LUT4 s7：交付包——把佈局、介面、功能設定與驗證結果整理成一包，並附 SHA-256 清單。 | 共用 |
| `design/lut4v2/s8_commercial/_logs/commercial_evidence.log` | 2.7 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/commercial_noflag.log` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/commercial_script_only.log` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/figs.log` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/virtuoso_evidence.log` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/virtuoso_noflag.log` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/_logs/virtuoso_script_only.log` | 0.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/commercial.py` | 26.3 KB | LUT4 s8（由 M3 s6 複製，輸入改為 LUT4 交付包）：商用工具對照：Virtuoso／Calibre——同一份交付 GDS，換成業界常用的工具，結果一樣嗎？ | 共用 |
| `design/lut4v2/s8_commercial/figs.py` | 5.4 KB | M3 s6：圖——KLayout 平台 deck 與 Calibre 草案在四份 GDS 上的結果、maxVertices＝200 匯出後的接縫放大。 | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_chip.log` | 49.5 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_chip.results` | 2.7 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_chip.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_fault.log` | 50.3 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_fault.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_fault.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_200.log` | 49.7 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_200.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_200.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_8191.log` | 49.7 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_8191.results` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/calibre_strmout_8191.summary` | 3.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/cds.lib` | 0.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/commercial.json` | 12.7 KB | 產生者：commercial.py、virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/cornerstone_basic_draft_chip.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/cornerstone_basic_draft_fault.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/cornerstone_basic_draft_strmout_200.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/cornerstone_basic_draft_strmout_8191.svrf` | 2.8 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/eda_run_record.json` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/raw_vs_clean.lydrc` | 0.7 KB | CORNERSTONE DRC deck（平台提供，不匯出） | 共用 |
| `design/lut4v2/s8_commercial/out/raw_vs_clean_chip.lyrdb` | 1.1 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/raw_vs_clean_strmout_200.lyrdb` | 11.9 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/run.sh` | 1.2 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/rve.sh` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/rve_chip.log` | 0.9 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/rve_chip.png` | 24.5 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/rve_fault.log` | 0.9 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/rve_fault.png` | 25.1 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/cornerstone_basic_draft_chip.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/cornerstone_basic_draft_fault.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/cornerstone_basic_draft_strmout_200.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/cornerstone_basic_draft_strmout_8191.svrf` | 2.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/run.sh` | 1.2 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/virtuoso_colors.drf` | 0.2 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/virtuoso_view.il` | 3.0 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/script_only/virtuoso_view.sh` | 0.9 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/shot_record.json` | 1.9 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/strmin.log` | 7.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_200.gds` | 78.0 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_200.log` | 10.9 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_200_drc.lyrdb` | 16.3 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_8191.gds` | 74.0 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_8191.log` | 7.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/strmout_8191_drc.lyrdb` | 4.4 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/out/v_chip.png` | 139.4 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/v_core.png` | 130.9 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/v_fault.png` | 134.1 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/v_mzi.png` | 147.2 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/virtuoso_colors.drf` | 0.2 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/virtuoso_evidence.json` | 0.8 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/out/virtuoso_view.il` | 3.0 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/virtuoso_view.sh` | 0.9 KB | 產生者：virtuoso_view.py | 共用 |
| `design/lut4v2/s8_commercial/out/xStrmOut_layerMap.txt` | 0.5 KB | 產生者：commercial.py | 共用 |
| `design/lut4v2/s8_commercial/reference/chip.gds` | 79.0 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/reference/chip_fault_drc.gds` | 80.9 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/reference/commercial_reference.json` | 8.4 KB | ？ | 共用 |
| `design/lut4v2/s8_commercial/virtuoso_view.py` | 14.1 KB | LUT4 s8：在 Virtuoso 打開交付的 LUT4 晶片（只看、不改），以 Virtuoso 自己的存圖函式輸出畫面；Calibre RVE 開啟故障檔的結果。 | 共用 |
| `design/lut4v2/s9_system/_logs/gain_box.log` | 1.5 KB | ？ | 共用 |
| `design/lut4v2/s9_system/_logs/system.log` | 2.6 KB | ？ | 共用 |
| `design/lut4v2/s9_system/gain_box.py` | 13.3 KB | LUT4 v2 s9（輸入 E+／E−）：增益盒的確定性檢查——三路增益各在 [1−ε, 1+ε] 內時，16 組判讀是否全部正確。 | 共用 |
| `design/lut4v2/s9_system/gain_robust.py` | 6.1 KB | LUT4 s9：TIA 增益失配的補強——(A) 量測增益後重新求相位；(B) 合成時挑耐增益誤差的相位解。 | 共用 |
| `design/lut4v2/s9_system/out/gain_box.json` | 8.5 KB | 產生者：gain_box.py | 共用 |
| `design/lut4v2/s9_system/out/gain_robust.json` | 3.4 KB | 產生者：gain_robust.py | 共用 |
| `design/lut4v2/s9_system/out/system.json` | 7.3 KB | 產生者：system.py | 共用 |
| `design/lut4v2/s9_system/reference/chip_info.json` | 18.2 KB | ？ | 共用 |
| `design/lut4v2/s9_system/reference/review_checks.json` | 5.1 KB | ？ | 共用 |
| `design/lut4v2/s9_system/system.py` | 10.4 KB | LUT4 v2 s9（輸入 E+／E−）：系統層級分析——晶片走線損耗、TIA 三路同時偏差、波長與溫度、二相位誤差、光功率預算。 | 共用 |
| `design/lut4v2/synth4.py` | 7.7 KB | （v2：輸入為 E+／E− 二相位光，R＝+E）加速版合成：批次向量化的光路計算與批次數值梯度。 | 共用 |
| `design/m0_env/concept.py` | 4.2 KB | M0 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/m0_env/s1_check/check_env.py` | 9.3 KB | M0 s1：環境確認——這台電腦能不能跑 IPKISS、CORNERSTONE PDK 與 KLayout DRC。 | M0 s1 |
| `design/m0_env/s1_check/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M0 s1 |
| `design/m0_env/s1_check/out/env.json` | 3.8 KB | 產生者：check_env.py | M0 s1 |
| `design/m0_env/s1_check/out/mmi_test.gds` | 1.5 KB | 產生者：check_env.py | M0 s1 |
| `design/m0_env/s1_check/out/mmi_test_drc.lyrdb` | 3.8 KB | 產生者：check_env.py | M0 s1 |
| `design/m0_env/s2_tools/HISTORY.md` | 2.7 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M0 s2 |
| `design/m0_env/s2_tools/out/index_stats.json` | 0.0 KB | 產生者：make_index.py | M0 s2 |
| `design/m0_env/s2_tools/out/tool_tests.json` | 7.4 KB | 產生者：test_tools.py | M0 s2 |
| `design/m0_env/s2_tools/test_tools.py` | 9.1 KB | M0 s2：報告組裝程式的故障注入測試——檢查真的抓得到錯嗎？ | M0 s2 |
| `design/m1_logic/concept.py` | 10.4 KB | M1 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/m1_logic/s1_signal/and2_readout.py` | 7.7 KB | M1 s1：光訊號與邏輯——用一顆 MMI 加一個相位，看光怎麼被讀成 AND2，以及為什麼需要參考光。 | M1 s1 |
| `design/m1_logic/s1_signal/concept_figs.py` | 9.6 KB | M1 s1：概念示意圖——光路與讀取鏈、光場箭頭的相加與抵消、參考光 R 的作用。 | M1 s1 |
| `design/m1_logic/s1_signal/HISTORY.md` | 1.2 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M1 s1 |
| `design/m1_logic/s1_signal/out/and2.json` | 3.0 KB | 產生者：and2_readout.py | M1 s1 |
| `design/m1_logic/s2_b7/capability.py` | 7.4 KB | M1 s2：從單顆 MZI 到 B7——每一種結構能做幾種二輸入邏輯？為什麼 B7 是 7 顆、4 層？ | M1 s2 |
| `design/m1_logic/s2_b7/figs.py` | 6.7 KB | M1 s2：圖——單顆 MZI 的構造與分光比、兩顆 MZI＋R 的接法、三種結構的二輸入涵蓋、B7 接線圖。 | M1 s2 |
| `design/m1_logic/s2_b7/HISTORY.md` | 0.9 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M1 s2 |
| `design/m1_logic/s2_b7/out/capability.json` | 37.9 KB | 產生者：capability.py | M1 s2 |
| `design/m1_logic/s3_matrix/b7_algebra.py` | 8.7 KB | M1 s3：B7 的矩陣運算——14 個相位如何決定「每個輸出是各輸入的加權和」，以及判讀量為什麼是二次式。 | M1 s3 |
| `design/m1_logic/s3_matrix/figs.py` | 6.2 KB | M1 s3：圖——沿路徑求 u（x4 → o2、x4 → o4 的兩條路徑）、1100 的逐層功率、ΔP 的常數／一次／二次分解。 | M1 s3 |
| `design/m1_logic/s3_matrix/HISTORY.md` | 0.9 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M1 s3 |
| `design/m1_logic/s3_matrix/out/algebra.json` | 11.1 KB | 產生者：b7_algebra.py | M1 s3 |
| `design/m1_logic/s4_gates/figs.py` | 6.3 KB | M1 s4：圖——同一串輸入、五組相位得到五種輸出（可程式化）、五個函數的 ΔP 真值表、14 個相位設定、相位誤差的影響。 | M1 s4 |
| `design/m1_logic/s4_gates/gates.py` | 5.2 KB | M1 s4：AND／OR／XOR 實例——同一顆 B7、同一組接線，只換 14 個相位，就換成不同的邏輯函數。 | M1 s4 |
| `design/m1_logic/s4_gates/HISTORY.md` | 1.6 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M1 s4 |
| `design/m1_logic/s4_gates/out/gates.json` | 17.8 KB | 產生者：gates.py | M1 s4 |
| `design/m1_logic/s4_gates/reference/phases.json` | 3.4 KB | ？ | M1 s4 |
| `design/m1_logic/s5_handoff/figs.py` | 4.7 KB | M1 s5：圖——三個交接檔各裝什麼、交給 M2 的誰；B7 的教學編號與佈局埠名對照。 | M1 s5 |
| `design/m1_logic/s5_handoff/handoff.py` | 4.6 KB | M1 s5：交接——把「固定光路」與「功能設定」分開保存，交給 M2。 | M1 s5 |
| `design/m1_logic/s5_handoff/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M1 s5 |
| `design/m1_logic/s5_handoff/out/b7_netlist.json` | 2.9 KB | 產生者：handoff.py | M1 s5 |
| `design/m1_logic/s5_handoff/out/phases.json` | 3.6 KB | 產生者：handoff.py | M1 s5 |
| `design/m1_logic/s5_handoff/out/replay.json` | 0.8 KB | 產生者：replay.py | M1 s5 |
| `design/m1_logic/s5_handoff/out/truth_tables.csv` | 3.5 KB | 產生者：handoff.py | M1 s5 |
| `design/m1_logic/s5_handoff/replay.py` | 7.3 KB | M1 s5：只用交接檔重播——拿到 b7_netlist.json、phases.json、truth_tables.csv 的人，能不能自己算出同樣的結果？ | M1 s5 |
| `design/m2_circuit/concept.py` | 5.7 KB | M2 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/m2_circuit/s1_spec/figs.py` | 8.7 KB | M2 s1：圖——晶片與外部設備的邊界、14 個相位控制通道的對應、介面容許範圍。 | M2 s1 |
| `design/m2_circuit/s1_spec/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M2 s1 |
| `design/m2_circuit/s1_spec/out/spec.json` | 7.7 KB | 產生者：spec.py | M2 s1 |
| `design/m2_circuit/s1_spec/out/tolerance.json` | 1.5 KB | 產生者：spec.py | M2 s1 |
| `design/m2_circuit/s1_spec/spec.py` | 11.1 KB | M2 s1：PIC 功能與介面規格——晶片和外部設備的邊界在哪？14 個相位怎麼接到 PAD？外部設備要多準？ | M2 s1 |
| `design/m2_circuit/s2_flow/figs.py` | 10.6 KB | M2 s2：圖——從規格到交付的流程、PDK cell 的實際外形、元件在晶片上的位置與來源。 | M2 s2 |
| `design/m2_circuit/s2_flow/flow.py` | 16.4 KB | M2 s2：設計流程與 PDK——從規格到 GDS 要經過哪些步驟、每個元件用 PDK 的哪個 cell？ | M2 s2 |
| `design/m2_circuit/s2_flow/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_HeaterPad.gds` | 0.2 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_HeaterPad_drc.lyrdb` | 3.7 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_2x2_MMI.gds` | 1.5 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_2x2_MMI_drc.lyrdb` | 3.8 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_GC.gds` | 0.9 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_GC_drc.lyrdb` | 3.9 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing.gds` | 0.9 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_SOI220nm_1550nm_TE_STRIP_Waveguide_Crossing_drc.lyrdb` | 3.8 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_StraightHeaterFilament.gds` | 22.9 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/cell_StraightHeaterFilament_drc.lyrdb` | 5.1 MB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/components.json` | 10.4 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/flow.json` | 2.6 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s2_flow/out/pdk_cells_geom.json` | 56.1 KB | 產生者：flow.py | M2 s2 |
| `design/m2_circuit/s3_sim/figs.py` | 6.6 KB | M2 s3：圖——PDK 模型與 M1 的比對、故障注入、MMI 不理想時的 margin 與重新校正。 | M2 s3 |
| `design/m2_circuit/s3_sim/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M2 s3 |
| `design/m2_circuit/s3_sim/out/mmi_sweep.json` | 20.7 KB | 產生者：sim.py | M2 s3 |
| `design/m2_circuit/s3_sim/out/sim_results.json` | 6.4 KB | 產生者：sim.py | M2 s3 |
| `design/m2_circuit/s3_sim/out/sim_truth.csv` | 3.5 KB | 產生者：sim.py | M2 s3 |
| `design/m2_circuit/s3_sim/sim.py` | 19.5 KB | M2 s3：電路模擬——把 B7 換成 PDK 的 MMI 模型、用 IPKISS 電路模擬求散射矩陣，真值表還對嗎？MMI 不理想時呢？ | M2 s3 |
| `design/m3_layout/concept.py` | 12.4 KB | M3 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/m3_layout/s1_core/figs.py` | 7.4 KB | M3 s1：圖——B7 核心全圖（標出 MZI、heater 編號、光學埠）、單顆 MZI 尺寸、heater 端點放大。 | M3 s1 |
| `design/m3_layout/s1_core/HISTORY.md` | 1.9 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s1 |
| `design/m3_layout/s1_core/layout.py` | 21.0 KB | M3 s1：IPKISS 佈局：B7 核心——電路連接怎麼變成實體幾何？ | M3 s1 |
| `design/m3_layout/s1_core/out/b7_core.gds` | 17.1 KB | 產生者：layout.py | M3 s1 |
| `design/m3_layout/s1_core/out/b7_core_framed.gds` | 17.2 KB | 產生者：layout.py | M3 s1 |
| `design/m3_layout/s1_core/out/b7_core_framed_drc.lyrdb` | 4.2 KB | 產生者：layout.py | M3 s1 |
| `design/m3_layout/s1_core/out/layout_info.json` | 11.2 KB | 產生者：layout.py | M3 s1 |
| `design/m3_layout/s2_review/figs.py` | 8.2 KB | M3 s2：圖——從 GDS 抽出的光路（每段波導一種顏色）、審查放大圖、由佈局重算 U 的結果。 | M3 s2 |
| `design/m3_layout/s2_review/HISTORY.md` | 1.2 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s2 |
| `design/m3_layout/s2_review/out/extracted.json` | 9.9 KB | 產生者：review.py | M3 s2 |
| `design/m3_layout/s2_review/out/review_checks.json` | 5.0 KB | 產生者：review.py | M3 s2 |
| `design/m3_layout/s2_review/review.py` | 21.2 KB | M3 s2：佈局審查——佈局有沒有照電路圖？埠序、直通線、彎道、金屬位置合理嗎？ | M3 s2 |
| `design/m3_layout/s3_chip/chip.py` | 27.4 KB | M3 s3：晶片整合：EC 與 PAD——光怎麼進出晶片？heater 怎麼繞線到 PAD？ | M3 s3 |
| `design/m3_layout/s3_chip/figs.py` | 7.0 KB | M3 s3：圖——整顆晶片（EC、扇出、PAD、繞線）、EC 放大、繞線放大（橫移與跨越波導）、電流密度。 | M3 s3 |
| `design/m3_layout/s3_chip/HISTORY.md` | 1.9 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s3 |
| `design/m3_layout/s3_chip/out/chip.gds` | 79.5 KB | 產生者：chip.py | M3 s3 |
| `design/m3_layout/s3_chip/out/chip_drc.lyrdb` | 4.4 KB | 產生者：chip.py | M3 s3 |
| `design/m3_layout/s3_chip/out/chip_info.json` | 21.6 KB | 產生者：chip.py | M3 s3 |
| `design/m3_layout/s4_verify/figs.py` | 6.8 KB | M3 s4：圖——從 GDS 抽出的電氣網（每個網一種顏色）、LVS 對照表與故障注入結果。 | M3 s4 |
| `design/m3_layout/s4_verify/HISTORY.md` | 1.6 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s4 |
| `design/m3_layout/s4_verify/out/chip_fault_drc.gds` | 81.4 KB | 產生者：verify.py | M3 s4 |
| `design/m3_layout/s4_verify/out/chip_fault_drc_drc.lyrdb` | 5.0 KB | 產生者：verify.py | M3 s4 |
| `design/m3_layout/s4_verify/out/connectivity.json` | 7.4 KB | 產生者：verify.py | M3 s4 |
| `design/m3_layout/s4_verify/out/drc_result.json` | 2.0 KB | 產生者：verify.py | M3 s4 |
| `design/m3_layout/s4_verify/verify.py` | 17.6 KB | M3 s4：DRC 與連接檢查——能不能製造？每個 heater 真的接到對的 PAD 嗎？光真的接到對的 EC 嗎？ | M3 s4 |
| `design/m3_layout/s5_delivery/check_delivery.py` | 42.2 KB | 交付檢查（M3 s5）：拿到交付包的人，用這支程式確認檔案完整、彼此一致、結果可以重算。 | M3 s5 |
| `design/m3_layout/s5_delivery/figs.py` | 14.4 KB | M3 s5：圖——交付包的檔案結構與交付檢查結果；交付的整顆晶片（標出每個 PAD 的功能與每個 EC 的訊號）；最終晶片的 B7 核心放大（標出 MZI、φ／θ 與對應 PAD、光學埠）。 | M3 s5 |
| `design/m3_layout/s5_delivery/HISTORY.md` | 3.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s5 |
| `design/m3_layout/s5_delivery/out/delivery_check.json` | 22.7 KB | 產生者：check_delivery.py | M3 s5 |
| `design/m3_layout/s5_delivery/out/v_chip.png` | 147.7 KB | 產生者：virtuoso_view.py | M3 s5 |
| `design/m3_layout/s5_delivery/out/virtuoso_colors.drf` | 0.2 KB | 產生者：virtuoso_view.py | M3 s5 |
| `design/m3_layout/s5_delivery/out/virtuoso_view.il` | 1.6 KB | 產生者：virtuoso_view.py | M3 s5 |
| `design/m3_layout/s5_delivery/out/virtuoso_view.sh` | 0.8 KB | 產生者：virtuoso_view.py | M3 s5 |
| `design/m3_layout/s5_delivery/package.py` | 16.6 KB | M3 s5：最終交付——把晶片、介面、驗證結果整理成別人拿到就能用的交付包。 | M3 s5 |
| `design/m3_layout/s5_delivery/virtuoso_view.py` | 6.8 KB | M3 s5：在 Virtuoso 打開交付的 chip.gds（只看、不改），並把畫面存成報告的圖。 | M3 s5 |
| `design/m3_layout/s6_commercial/commercial.py` | 17.0 KB | M3 s6：商用工具對照：Virtuoso／Calibre——同一份交付 GDS，換成業界常用的工具，結果一樣嗎？ | M3 s6 |
| `design/m3_layout/s6_commercial/figs.py` | 5.4 KB | M3 s6：圖——KLayout 平台 deck 與 Calibre 草案在四份 GDS 上的結果、maxVertices＝200 匯出後的接縫放大。 | M3 s6 |
| `design/m3_layout/s6_commercial/HISTORY.md` | 2.5 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_chip.log` | 49.5 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_chip.results` | 2.7 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_chip.summary` | 3.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_fault.log` | 50.4 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_fault.results` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_fault.summary` | 3.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_200.log` | 49.7 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_200.results` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_200.summary` | 3.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_8191.log` | 49.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_8191.results` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/calibre_strmout_8191.summary` | 3.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/cds.lib` | 0.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/commercial.json` | 11.0 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/cornerstone_basic_draft_chip.svrf` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/cornerstone_basic_draft_fault.svrf` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/cornerstone_basic_draft_strmout_200.svrf` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/cornerstone_basic_draft_strmout_8191.svrf` | 2.8 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/eda_run_record.json` | 3.8 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/raw_vs_clean.lydrc` | 0.7 KB | CORNERSTONE DRC deck（平台提供，不匯出） | M3 s6 |
| `design/m3_layout/s6_commercial/out/raw_vs_clean_chip.lyrdb` | 1.1 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/raw_vs_clean_strmout_200.lyrdb` | 11.9 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_chip.log` | 49.2 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_chip.results` | 2.7 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_chip.summary` | 3.0 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_fault.log` | 50.1 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_fault.results` | 2.8 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_fault.summary` | 3.0 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_200.log` | 49.4 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_200.results` | 2.8 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_200.summary` | 3.1 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_8191.log` | 49.4 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_8191.results` | 2.8 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/calibre_strmout_8191.summary` | 3.1 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/cds.lib` | 0.1 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/commercial.json` | 11.0 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmin.log` | 7.4 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_200.gds` | 78.0 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_200.log` | 10.9 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_200_drc.lyrdb` | 16.3 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_8191.gds` | 76.0 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_8191.log` | 7.4 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/reference_evidence/strmout_8191_drc.lyrdb` | 4.4 KB | ？ | M3 s6 |
| `design/m3_layout/s6_commercial/out/run.sh` | 1.2 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmin.log` | 7.4 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_200.gds` | 78.0 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_200.log` | 10.9 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_200_drc.lyrdb` | 16.3 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_8191.gds` | 76.0 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_8191.log` | 7.4 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/strmout_8191_drc.lyrdb` | 4.4 KB | 產生者：commercial.py | M3 s6 |
| `design/m3_layout/s6_commercial/out/xStrmOut_layerMap.txt` | 0.5 KB | 產生者：commercial.py | M3 s6 |
| `design/paper/dual_difference_study/compare_rerun.py` | 2.3 KB | 比較雙差分研究的重跑結果與原有輸出，寫出 rerun_20261107/compare.json。 | 共用 |
| `design/paper/dual_difference_study/low_crosscheck.log` | 0.0 KB | ？ | 共用 |
| `design/paper/dual_difference_study/pilot.json` | 10.7 KB | ？ | 共用 |
| `design/paper/dual_difference_study/pilot.log` | 0.4 KB | ？ | 共用 |
| `design/paper/dual_difference_study/pilot_deep.py` | 0.8 KB | （缺 docstring） | 共用 |
| `design/paper/dual_difference_study/pilot_first.log` | 0.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/port_refine.log` | 1.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/port_refine.py` | 1.1 KB | Retest the most promising fixed port orders with equal restart budgets. | 共用 |
| `design/paper/dual_difference_study/port_screen.json` | 239.1 KB | ？ | 共用 |
| `design/paper/dual_difference_study/port_screen.log` | 1.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/port_screen.py` | 5.4 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/port_screen_refined.json` | 239.1 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/compare.json` | 1.7 KB | 產生者：compare_rerun.py | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/pilot.json` | 11.1 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/pilot_deep.log` | 0.4 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/pilot_deep.py` | 0.8 KB | （缺 docstring） | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/pilot_first.log` | 0.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_refine.log` | 1.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_refine.py` | 1.1 KB | Retest the most promising fixed port orders with equal restart budgets. | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_screen.json` | 248.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_screen.log` | 1.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_screen.py` | 5.4 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/port_screen_refined.json` | 248.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/scan.log` | 3.2 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/scan.npz` | 7.5 MB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/scan_checkpoint.npz` | 7.5 MB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/simulate.py` | 6.0 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/steps.tsv` | 0.2 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/summary.json` | 5.8 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_parity.json` | 185.0 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_refine.log` | 0.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_refine.py` | 1.0 KB | （缺 docstring） | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_refined.json` | 16.5 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_screen.json` | 234.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_screen.log` | 0.0 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/topology_screen.py` | 6.0 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/verified_scan.npz` | 7.3 MB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/verify.log` | 3.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/verify_scan.py` | 2.0 KB | Replay the exhaustive scan and deepen searches on low-margin masks. | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/window_low_class.json` | 58.9 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/window_low_class.log` | 0.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/rerun_20261107/window_low_class.py` | 0.9 KB | Re-evaluate the original window on the reported low-margin NPN orbit. | 共用 |
| `design/paper/dual_difference_study/run_rerun.sh` | 1.2 KB | ？ | 共用 |
| `design/paper/dual_difference_study/scan.log` | 3.2 KB | ？ | 共用 |
| `design/paper/dual_difference_study/scan.npz` | 7.5 MB | ？ | 共用 |
| `design/paper/dual_difference_study/scan_checkpoint.npz` | 7.5 MB | ？ | 共用 |
| `design/paper/dual_difference_study/simulate.py` | 6.0 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/summary.json` | 5.5 KB | ？ | 共用 |
| `design/paper/dual_difference_study/topology_parity.json` | 177.8 KB | ？ | 共用 |
| `design/paper/dual_difference_study/topology_refine.py` | 1.0 KB | （缺 docstring） | 共用 |
| `design/paper/dual_difference_study/topology_refined.json` | 15.9 KB | ？ | 共用 |
| `design/paper/dual_difference_study/topology_screen.json` | 225.2 KB | ？ | 共用 |
| `design/paper/dual_difference_study/topology_screen.log` | 0.0 KB | ？ | 共用 |
| `design/paper/dual_difference_study/topology_screen.py` | 6.0 KB | Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND. | 共用 |
| `design/paper/dual_difference_study/verified_scan.npz` | 7.3 MB | ？ | 共用 |
| `design/paper/dual_difference_study/verify.log` | 3.6 KB | ？ | 共用 |
| `design/paper/dual_difference_study/verify_scan.py` | 2.0 KB | Replay the exhaustive scan and deepen searches on low-margin masks. | 共用 |
| `design/paper/dual_difference_study/window_low_class.json` | 56.4 KB | ？ | 共用 |
| `design/paper/dual_difference_study/window_low_class.log` | 0.3 KB | ？ | 共用 |
| `design/paper/dual_difference_study/window_low_class.py` | 0.9 KB | Re-evaluate the original window on the reported low-margin NPN orbit. | 共用 |
| `design/paper/m1_timing/concept.py` | 11.8 KB | 論文 M1 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/paper/m1_timing/model.py` | 4.4 KB | 論文 M1 的共用模型：含 MMI 實測損耗的 B7，與在此模型下重新校正的相位（M1 s1–s5 一律用這一份）。 | 共用 |
| `design/paper/m1_timing/out/phases_lossy.json` | 3.3 KB | 產生者：model.py | 共用 |
| `design/paper/m1_timing/s1_budget/budget.py` | 20.4 KB | 論文 M1 s1：現有晶片要以 10 Gb/s 運作，時序、功率、相位各差多少（預算表）。 | 共用 |
| `design/paper/m1_timing/s1_budget/figs.py` | 6.4 KB | 論文 M1 s1：圖——時序（skew 來源與允許值）、相位（溫度容許與路徑長度）、功率（由接收端反推到光纖）。 | 共用 |
| `design/paper/m1_timing/s1_budget/HISTORY.md` | 2.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m1_timing/s1_budget/out/budget.json` | 7.5 KB | 產生者：budget.py | 共用 |
| `design/paper/m1_timing/s2_interface/figs.py` | 3.5 KB | 論文 M1 s2：圖——發射端消光比與 margin（沿用原相位 vs 重新求相位）。 | 共用 |
| `design/paper/m1_timing/s2_interface/HISTORY.md` | 2.0 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m1_timing/s2_interface/interface.py` | 9.6 KB | 論文 M1 s2：輸入介面規格——片外發射端要給什麼樣的光，B7 才能在 10 Gb/s 判對（晶片只有 heater MZI）。 | 共用 |
| `design/paper/m1_timing/s2_interface/out/interface_v2.json` | 14.4 KB | 產生者：interface.py | 共用 |
| `design/paper/m1_timing/s3_tracking/figs.py` | 5.5 KB | 論文 M1 s3：圖——補償與量測（漂移前後的 margin、兩種量法能分辨幾個相位）、擺動幅度的取捨。 | 共用 |
| `design/paper/m1_timing/s3_tracking/HISTORY.md` | 2.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m1_timing/s3_tracking/out/tracking.json` | 9.6 KB | 產生者：track.py | 共用 |
| `design/paper/m1_timing/s3_tracking/track.py` | 15.0 KB | 論文 M1 s3：輸入相位追蹤——只用晶片上原有的 heater MZI，能不能追上 5 路輸入光之間的相位漂移。 | 共用 |
| `design/paper/m1_timing/s4_window/figs.py` | 4.7 KB | 論文 M1 s4：圖——動態 margin 隨取樣相位的變化（眼圖的最差邊界）、功率代價與 skew。 | 共用 |
| `design/paper/m1_timing/s4_window/HISTORY.md` | 2.8 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m1_timing/s4_window/out/window.json` | 177.5 KB | 產生者：window.py | 共用 |
| `design/paper/m1_timing/s4_window/window.py` | 17.4 KB | 論文 M1 s4：10 Gb/s 取樣窗——輸入轉態時的干涉、skew、消光比與晶片內路徑差會吃掉多少取樣窗。 | 共用 |
| `design/paper/m1_timing/s5_assess/assess.py` | 8.6 KB | 論文 M1 s5：介面規格、總預算與論文重點——逐函數合成 10 Gb/s 的總功率預算，並把結果整理成三個重點（完整版研究的簡化版）。 | 共用 |
| `design/paper/m1_timing/s5_assess/figs.py` | 6.2 KB | 論文 M1 s5：圖——10 Gb/s 總功率預算（每項代價發生在訊號鏈的哪裡、加起來要多少光）。 | 共用 |
| `design/paper/m1_timing/s5_assess/HISTORY.md` | 3.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m1_timing/s5_assess/joint.py` | 7.3 KB | 論文 M1 s5：校正後的聯合驗收——同時加入所有誤差，在同一個 23 ps 取樣窗內重算 margin。 | 共用 |
| `design/paper/m1_timing/s5_assess/out/assess.json` | 4.2 KB | 產生者：assess.py | 共用 |
| `design/paper/m1_timing/s5_assess/out/joint.json` | 3.8 KB | 產生者：joint.py | 共用 |
| `design/paper/m2_evidence/concept.py` | 6.2 KB | 論文 M2 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/paper/m2_evidence/s1_baseline/baseline.py` | 14.1 KB | 論文 M2 s1：與固定加總模型比較——只數 MZI 的延遲與損耗，能不能預測 10 Gb/s 下的結果？ | 共用 |
| `design/paper/m2_evidence/s1_baseline/figs.py` | 3.6 KB | 論文 M2 s1：圖——固定加總模型與時域流程的三項對照（skew 容許、功率需求的排序、相位與殘留光的影響）。 | 共用 |
| `design/paper/m2_evidence/s1_baseline/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m2_evidence/s1_baseline/out/baseline.json` | 15.4 KB | 產生者：baseline.py | 共用 |
| `design/paper/m2_evidence/s2_spec/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m2_evidence/s2_spec/out/spec.json` | 4.0 KB | 產生者：spec.py | 共用 |
| `design/paper/m2_evidence/s2_spec/spec.py` | 8.6 KB | 論文 M2 s2：介面規格與餘裕——把 M1 各步的需求整理成一張表，每一項都附「依據的數字」與「離失效還有多遠」。 | 共用 |
| `design/paper/m2_evidence/s3_power/figs.py` | 3.6 KB | 論文 M2 s3：圖——相位偏差所需的最小 P_u，以及三種情況下取樣窗寬度隨 P_u 的變化。 | 共用 |
| `design/paper/m2_evidence/s3_power/HISTORY.md` | 1.1 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m2_evidence/s3_power/out/power.json` | 8.8 KB | 產生者：power.py | 共用 |
| `design/paper/m2_evidence/s3_power/out/screen_check.json` | 9.9 KB | 產生者：screen_check.py | 共用 |
| `design/paper/m2_evidence/s3_power/power.py` | 11.3 KB | 論文 M2 s3：功率餘裕與相位失敗——相位偏差讓取樣窗消失時，多給光能不能救回來？要多給多少？ | 共用 |
| `design/paper/m2_evidence/s3_power/screen_check.py` | 6.3 KB | 論文 M2 s3（審查 R6）：靜態篩選是否漏掉窗內最差的組合？ | 共用 |
| `design/paper/m2_evidence/s4_deviation/deviation.py` | 17.0 KB | 論文 M2 s4：一種模型偏差——用名義模型設計與校正、用有 MMI 分光誤差的「硬體」驗收，結果還一致嗎？ | 共用 |
| `design/paper/m2_evidence/s4_deviation/figs.py` | 3.1 KB | 論文 M2 s4：圖——MMI 分光誤差下，名義相位、名義校正後、已知硬體的參考解三種狀態的 margin 與所需光功率。 | 共用 |
| `design/paper/m2_evidence/s4_deviation/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m2_evidence/s4_deviation/out/deviation.json` | 80.1 KB | 產生者：deviation.py | 共用 |
| `design/paper/m2_evidence/s5_general/figs.py` | 3.5 KB | 論文 M2 s5：圖——16 個函數的光功率需求（靜態與聯合驗收）與各步執行時間。 | 共用 |
| `design/paper/m2_evidence/s5_general/general.py` | 12.4 KB | 論文 M2 s5：通用性與執行時間——同一套流程能不能用在 B7 能做的所有函數？每一步要算多久？ | 共用 |
| `design/paper/m2_evidence/s5_general/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m2_evidence/s5_general/out/general.json` | 16.0 KB | 產生者：general.py | 共用 |
| `design/paper/m3_align/concept.py` | 4.1 KB | 論文 M3 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/paper/m3_align/draft.py` | 2.9 KB | 論文 M3：草稿的設定（唯一來源）——草稿表 I、表 II 與 II-A 節的數字，供論文 M3 以後各步引用與比對。 | 共用 |
| `design/paper/m3_align/s1_params/align.py` | 11.1 KB | 論文 M3 s1：參數對齊與護欄差異——草稿的設定和我們目前的設定差在哪？XOR2 的雜訊護欄為何看起來差約 2 倍？ | 共用 |
| `design/paper/m3_align/s1_params/figs.py` | 4.5 KB | 論文 M3 s1：圖——同一參考面的雜訊護欄（我們、草稿式、草稿表 I）與護欄隨偵測器端功率的變化。 | 共用 |
| `design/paper/m3_align/s1_params/HISTORY.md` | 1.0 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m3_align/s1_params/out/align.json` | 8.5 KB | 產生者：align.py | 共用 |
| `design/paper/m3_align/s2_synth/figs.py` | 3.2 KB | 論文 M3 s2：圖——9 個函數的 margin（無損、0.9 dB／MZI）與草稿表 I、偵測器端 −7 dBm 的護欄、16 個起點的收斂。 | 共用 |
| `design/paper/m3_align/s2_synth/HISTORY.md` | 0.8 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m3_align/s2_synth/out/synth.json` | 14.6 KB | 產生者：synth.py | 共用 |
| `design/paper/m3_align/s2_synth/synth.py` | 9.2 KB | 論文 M3 s2：依論文草稿式 2 合成——共用零門檻下，讓最差 margin 最大的 14 個相位；重現草稿表 I。 | 共用 |
| `design/paper/m3_align/s3_detail/detail.py` | 14.8 KB | 論文 M3 s3：依論文草稿的設定做詳細模擬——AND4、MAJ4、XOR2 在對齊時與 13.2 ps 延遲盒抽樣點上的共同取樣窗；重現草稿表 III 的「詳細模擬」兩欄。 | 共用 |
| `design/paper/m3_align/s3_detail/figs.py` | 4.8 KB | 論文 M3 s3：圖——(a) 三個函數在對齊與盒內 41 點逐點最小時的 margin 減護欄對取樣相位；(b) 與草稿表 III 的窗寬比較； | 共用 |
| `design/paper/m3_align/s3_detail/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m3_align/s3_detail/out/detail.json` | 8.6 KB | 產生者：detail.py | 共用 |
| `design/paper/m4_cert/concept.py` | 5.3 KB | 論文 M4 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/paper/m4_cert/s1_quad/figs.py` | 4.3 KB | 論文 M4 s1：圖——(a) XOR2 的時域 D(t)：逐點模擬與二次式重疊，下方為兩者的差；(b) 9 個函數的 margin， | 共用 |
| `design/paper/m4_cert/s1_quad/HISTORY.md` | 0.8 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m4_cert/s1_quad/out/quad.json` | 13.1 KB | 產生者：quad.py | 共用 |
| `design/paper/m4_cert/s1_quad/quad.py` | 7.4 KB | 論文 M4 s1：二次式判讀——偵測功率差 D 是輸入包絡的精確二次式 D(x)＝d0＋lᵀx＋xᵀQx（草稿式 6）。 | 共用 |
| `design/paper/m4_cert/s2_leaf/figs.py` | 3.9 KB | 論文 M4 s2：圖——(a) AND4 的 margin 下界（1 個、16 個葉盒）與 41 個盒內抽樣點的模擬最小值；(b) 下界扣掉的兩項（一階項、餘項）隨取樣相位的變化； | 共用 |
| `design/paper/m4_cert/s2_leaf/HISTORY.md` | 1.4 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m4_cert/s2_leaf/leaf.py` | 17.7 KB | 論文 M4 s2：葉盒下界與時變雜訊界——給一個延遲盒，判讀量的保守下界（草稿式 7–8、III-E；補充資料 S1 步驟 1–6）。 | 共用 |
| `design/paper/m4_cert/s2_leaf/out/curves_AND4.npz` | 37.0 KB | 產生者：leaf.py | 共用 |
| `design/paper/m4_cert/s2_leaf/out/curves_MAJ4.npz` | 37.0 KB | 產生者：leaf.py | 共用 |
| `design/paper/m4_cert/s2_leaf/out/curves_XOR2.npz` | 37.0 KB | 產生者：leaf.py | 共用 |
| `design/paper/m4_cert/s2_leaf/out/leaf.json` | 5.0 KB | 產生者：leaf.py | 共用 |
| `design/paper/m4_cert/s3_cert/cert.py` | 12.6 KB | 論文 M4 s3：13.2 ps 盒的認證窗——整個延遲盒（每路 ±6.6 ps）、宣告的情境序列與全部資料歷史下，共同取樣窗至少多寬（草稿式 9、命題 1、表 III 認證欄）。 | 共用 |
| `design/paper/m4_cert/s3_cert/cert_checks.py` | 5.9 KB | 論文 M4 s3 的判定邏輯：必要檢查與研究結果分開，不重算、不寫檔。 | 共用 |
| `design/paper/m4_cert/s3_cert/figs.py` | 4.6 KB | 論文 M4 s3：圖——(a) AND4 情境序列的認證 margin（1、16、256 個葉盒）與 41 點模擬 margin，標出認證窗； | 共用 |
| `design/paper/m4_cert/s3_cert/HISTORY.md` | 1.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m4_cert/s3_cert/out/cert.json` | 10.8 KB | 產生者：cert.py | 共用 |
| `design/paper/m4_cert/s3_cert/out/curves_AND4.npz` | 47.3 KB | 產生者：cert.py | 共用 |
| `design/paper/m4_cert/s3_cert/out/curves_MAJ4.npz` | 47.3 KB | 產生者：cert.py | 共用 |
| `design/paper/m4_cert/s3_cert/out/curves_XOR2.npz` | 47.3 KB | 產生者：cert.py | 共用 |
| `design/paper/m4_cert/s4_budget/figs.py` | 5.4 KB | 論文 M4 s4：圖——(a) 10 Gb/s 一個 UI 的分配（類比接收端、延伸到盒內最小與認證窗；另附數位接收端與草稿表 VI 的 AND4）； | 共用 |
| `design/paper/m4_cert/s4_budget/HISTORY.md` | 1.6 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m4_cert/s4_budget/out/budget_ui.json` | 2.6 KB | 產生者：ui.py | 共用 |
| `design/paper/m4_cert/s4_budget/out/sens.json` | 9.3 KB | 產生者：ui.py | 共用 |
| `design/paper/m4_cert/s4_budget/ui.py` | 12.8 KB | 論文 M4 s4：UI 預算與接收端敏感度——一個 UI 被誰吃掉？接收端頻寬 5–9 GHz、位元率提高時窗還夠嗎（草稿表 VI、IV-F）？ | 共用 |
| `design/paper/m5_cascade/concept.py` | 6.3 KB | 論文 M5 各步的概念圖（每步開頭「本步概念」）。 | 共用 |
| `design/paper/m5_cascade/s1_cascade/cascade.py` | 16.5 KB | 論文 M5 s1：兩級串接與 8 輸入合成——4 顆 B7 不在中間判讀，能做 x1x8、AND8、MAJ8、同步字等 8 輸入函數嗎（草稿 II-C、圖 3）？ | 共用 |
| `design/paper/m5_cascade/s1_cascade/figs.py` | 2.8 KB | 論文 M5 s1：圖——(a) 14 個 8 輸入單判讀函數、(b) 8 組雙判讀聯合指派的 margin（無損、0.9 dB／MZI）， | 共用 |
| `design/paper/m5_cascade/s1_cascade/HISTORY.md` | 1.7 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m5_cascade/s1_cascade/out/cascade.json` | 70.9 KB | 產生者：cascade.py | 共用 |
| `design/paper/m5_cascade/s1_cascade/out/runs.jsonl` | 418.0 KB | 產生者：cascade.py | 共用 |
| `design/paper/m5_cascade/s1_cascade/ref_evidence/cascade_ref.json` | 70.9 KB | ？ | 共用 |
| `design/paper/m5_cascade/s2_meander/figs.py` | 3.7 KB | 論文 M5 s2：圖——(a) 草稿表 IV 的 9 個案例：選擇的蛇形（全部 0 mm）的最差角落窗與完整等長的窗，對照草稿； | 共用 |
| `design/paper/m5_cascade/s2_meander/HISTORY.md` | 1.5 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m5_cascade/s2_meander/meander.py` | 19.9 KB | 論文 M5 s2：依時序限制選蛇形（草稿 III-F 演算法 1、表 IV）——補長度會同時延遲與衰減，最短且通過驗收的候選是哪一個？ | 共用 |
| `design/paper/m5_cascade/s2_meander/out/meander.json` | 33.4 KB | 產生者：meander.py | 共用 |
| `design/paper/m5_cascade/s3_cert/cert_cascade.py` | 18.9 KB | 論文 M5 s3：串接的盒證明——兩級串接的 x1x8 在 13.2 ps 盒（8 路各 ±6.6 ps）下，共同取樣窗至少多寬（草稿表 III x1x8 列）？ | 共用 |
| `design/paper/m5_cascade/s3_cert/figs.py` | 4.1 KB | 論文 M5 s3 的圖：串接的認證窗。 | 共用 |
| `design/paper/m5_cascade/s3_cert/HISTORY.md` | 1.5 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m5_cascade/s3_cert/out/cert_cascade.json` | 7.3 KB | 產生者：cert_cascade.py | 共用 |
| `design/paper/m5_cascade/s3_cert/out/curves.npz` | 84.4 KB | 產生者：cert_cascade.py | 共用 |
| `design/paper/m5_cascade/s4_screen/check_static_sample.py` | 2.8 KB | 論文 M5 s4 的重現抽查：靜態合成全量（平行度 2 約 135 分鐘）本次未重跑，screen.py 沿用參考快取 static.jsonl； | 共用 |
| `design/paper/m5_cascade/s4_screen/figs.py` | 5.2 KB | 論文 M5 s4 的圖：全類別的三層篩選與推測指標。 | 共用 |
| `design/paper/m5_cascade/s4_screen/HISTORY.md` | 2.6 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paper/m5_cascade/s4_screen/out/screen.json` | 422.3 KB | 產生者：screen.py | 共用 |
| `design/paper/m5_cascade/s4_screen/out/static.jsonl` | 2.2 MB | 產生者：screen.py | 共用 |
| `design/paper/m5_cascade/s4_screen/out/static_rerun.jsonl` | 2.2 MB | 產生者：rerun_static.py | 共用 |
| `design/paper/m5_cascade/s4_screen/out/static_rerun_check.json` | 0.2 KB | 產生者：rerun_static.py | 共用 |
| `design/paper/m5_cascade/s4_screen/out/static_sample_check.json` | 37.5 KB | 產生者：check_static_sample.py | 共用 |
| `design/paper/m5_cascade/s4_screen/reference/npn_check_b7_cache.jsonl` | 82.5 KB | ？ | 共用 |
| `design/paper/m5_cascade/s4_screen/reference/npn_check_b7_result.json` | 3.5 KB | ？ | 共用 |
| `design/paper/m5_cascade/s4_screen/reference/SOURCE.md` | 0.3 KB | ？ | 共用 |
| `design/paper/m5_cascade/s4_screen/rerun_static.py` | 2.9 KB | 論文 M5 s4 的靜態合成全量重跑：不動 screen.py 使用的 static.jsonl（參考快取），另寫 static_rerun.jsonl，逐筆比對兩者。 | 共用 |
| `design/paper/m5_cascade/s4_screen/screen.py` | 24.2 KB | 論文 M5 s4：全類別的時序篩選——靜態可實現的 4 輸入 NPN 類別中，有多少在 10 Gb/s 下真的有取樣窗？只看靜態 margin 能預測嗎？ | 共用 |
| `design/paper/run_logs/build_paper.log` | 6.5 KB | ？ | 共用 |
| `design/paper/run_logs/laneA1_chain.log` | 0.3 KB | ？ | 共用 |
| `design/paper/run_logs/laneA2_chain.log` | 0.2 KB | ？ | 共用 |
| `design/paper/run_logs/laneA3_chain.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/laneB_chain.log` | 0.2 KB | ？ | 共用 |
| `design/paper/run_logs/laneC_chain.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_chain.log` | 0.3 KB | ？ | 共用 |
| `design/paper/run_logs/m1_concept.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_model.log` | 0.3 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s1.log` | 1.0 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s1_figs.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s2.log` | 1.5 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s2_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s3.log` | 2.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s3_figs.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s4.log` | 1.7 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s4_figs.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s5_assess.log` | 1.4 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s5_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m1_s5_joint.log` | 0.8 KB | ？ | 共用 |
| `design/paper/run_logs/m2_concept.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m2_concept_v2.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s1.log` | 3.9 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s1_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s2.log` | 2.2 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s3.log` | 1.8 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s3_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s3_screen.log` | 0.4 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s4.log` | 6.1 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s4_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s5.log` | 5.0 KB | ？ | 共用 |
| `design/paper/run_logs/m2_s5_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m3_concept.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s1.log` | 2.9 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s1_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s2.log` | 1.8 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s2_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s3.log` | 1.5 KB | ？ | 共用 |
| `design/paper/run_logs/m3_s3_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m4_concept.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s1.log` | 1.6 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s1_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s2.log` | 1.8 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s2_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s3.log` | 2.9 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s3_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s4.log` | 2.6 KB | ？ | 共用 |
| `design/paper/run_logs/m4_s4_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_concept.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s1_cascade.log` | 3.1 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s1_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s1_full.log` | 3.1 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s1_full_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s2.log` | 3.8 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s2_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s3.log` | 2.7 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s3_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s4.log` | 2.5 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s4_figs.log` | 0.0 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s4_sample.log` | 0.1 KB | ？ | 共用 |
| `design/paper/run_logs/m5_s4_static_full.log` | 0.2 KB | ？ | 共用 |
| `design/paper/run_logs/steps.tsv` | 3.6 KB | ？ | 共用 |
| `design/paper/verify_checks.py` | 7.9 KB | 論文全部步驟的唯讀驗收：把各步 out/*.json 的 checks 分成必要檢查與研究結果。 | 共用 |
| `design/paper_v2/a1_lut4/cells.py` | 8.7 KB | 論文 v2 附錄 A：LUT4 第一級的 14 個 2 輸入光學單元，時序窗是否都通過？ | 共用 |
| `design/paper_v2/a1_lut4/HISTORY.md` | 0.3 KB | 修改歷史（人工維護，組裝時帶入附錄 B） | 共用 |
| `design/paths.py` | 2.0 KB | 專案路徑的唯一來源（M0 s1）。 | 共用 |
| `design/ptf2/out/ptf2.json` | 5.6 KB | 產生者：ptf2_check.py | 共用 |
| `design/ptf2/out/ptf2_flags.npy` | 64.1 KB | ？ | 共用 |
| `design/ptf2/out/ptf2_table8.json` | 1.1 KB | ？ | 共用 |
| `design/ptf2/out/ptf2_table8_fixed.json` | 1.8 MB | ？ | 共用 |
| `design/ptf2/ptf2_check.py` | 14.9 KB | PTF2 數學驗證——report/PTF2.html 頁內數字的獨立重算。 | 共用 |
| `design/ptf2/ptf2_table8.py` | 3.9 KB | PTF2 補充：report/PTF2.html 表 8「上限（Receiver 任意加權）」欄的獨立重算——兩個四階輸入＋R 的一次判讀涵蓋（NPN 類）。 | 共用 |
| `design/ptf2/ptf2_table8_fixed.py` | 24.2 KB | PTF2 補充：report/PTF2.html 表 8「固定 o2−o4」與「裕量中位數」欄的重建（下限搜尋，不是證明）。 | 共用 |
| `design/ptf2/run.log` | 2.1 KB | ？ | 共用 |
| `design/ptf2/run_table8.log` | 0.8 KB | ？ | 共用 |
| `figures/lut4/s1_core.png` | 112.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s1_heater.png` | 47.6 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s1_mzi.png` | 95.3 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s2_checks.png` | 153.7 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s2_extract.png` | 104.1 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s2_zoom.png` | 89.1 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s3_chip.png` | 191.3 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s3_ec.png` | 106.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s3_route.png` | 237.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s4_checks.png` | 142.0 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s4_nets.png` | 172.2 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4/s8_compare.png` | 66.5 KB | ？ | 共用 |
| `figures/lut4/s8_rve_chip.png` | 24.5 KB | ？ | 共用 |
| `figures/lut4/s8_rve_fault.png` | 25.1 KB | ？ | 共用 |
| `figures/lut4/s8_seam.png` | 93.8 KB | ？ | 共用 |
| `figures/lut4/s8_v_chip.png` | 147.7 KB | ？ | 共用 |
| `figures/lut4/s8_v_core.png` | 143.4 KB | ？ | 共用 |
| `figures/lut4/s8_v_fault.png` | 136.4 KB | ？ | 共用 |
| `figures/lut4/s8_v_mzi.png` | 150.3 KB | ？ | 共用 |
| `figures/lut4v2/s1_core.png` | 112.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s1_encoding.png` | 210.5 KB | 產生者：encoding.py | 共用 |
| `figures/lut4v2/s1_heater.png` | 47.6 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s1_mzi.png` | 95.3 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s2_checks.png` | 160.1 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s2_extract.png` | 104.1 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s2_single_epm.png` | 130.6 KB | 產生者：figs.py | 共用 |
| `figures/lut4v2/s2_two_epm.png` | 74.3 KB | 產生者：figs.py | 共用 |
| `figures/lut4v2/s2_zoom.png` | 89.1 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s3_chip.png` | 135.0 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s3_ec.png` | 106.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s3_route.png` | 235.8 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s4_checks.png` | 142.5 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s4_nets.png` | 90.0 KB | 產生者：figs.py、figs.py、figs.py | 共用 |
| `figures/lut4v2/s8_compare.png` | 66.5 KB | ？ | 共用 |
| `figures/lut4v2/s8_rve_chip.png` | 24.5 KB | ？ | 共用 |
| `figures/lut4v2/s8_rve_fault.png` | 25.1 KB | ？ | 共用 |
| `figures/lut4v2/s8_seam.png` | 93.8 KB | ？ | 共用 |
| `figures/lut4v2/s8_v_chip.png` | 139.4 KB | ？ | 共用 |
| `figures/lut4v2/s8_v_core.png` | 130.9 KB | ？ | 共用 |
| `figures/lut4v2/s8_v_fault.png` | 134.1 KB | ？ | 共用 |
| `figures/lut4v2/s8_v_mzi.png` | 147.2 KB | ？ | 共用 |
| `figures/m0/s1_concept.png` | 117.8 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M0 s1 |
| `figures/m0/s1_mmi_layout.png` | 29.7 KB | 產生者：check_env.py | M0 s1 |
| `figures/m0/s2_concept.png` | 104.0 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M0 s2 |
| `figures/m1/s1_circuit.png` | 74.2 KB | 產生者：concept_figs.py | M1 s1 |
| `figures/m1/s1_concept.png` | 99.4 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M1 s1 |
| `figures/m1/s1_deltaP_phase.png` | 53.0 KB | 產生者：and2_readout.py | M1 s1 |
| `figures/m1/s1_phasor.png` | 65.8 KB | 產生者：concept_figs.py | M1 s1 |
| `figures/m1/s1_reference.png` | 56.2 KB | 產生者：concept_figs.py | M1 s1 |
| `figures/m1/s1_waveform.png` | 40.8 KB | 產生者：and2_readout.py | M1 s1 |
| `figures/m1/s2_b7.png` | 55.0 KB | 產生者：figs.py | M1 s2 |
| `figures/m1/s2_concept.png` | 105.6 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M1 s2 |
| `figures/m1/s2_coverage.png` | 51.8 KB | 產生者：figs.py | M1 s2 |
| `figures/m1/s2_mzi.png` | 76.7 KB | 產生者：figs.py | M1 s2 |
| `figures/m1/s2_two_mzi.png` | 29.3 KB | 產生者：figs.py | M1 s2 |
| `figures/m1/s3_concept.png` | 82.7 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M1 s3 |
| `figures/m1/s3_layers.png` | 49.1 KB | 產生者：figs.py | M1 s3 |
| `figures/m1/s3_paths.png` | 193.2 KB | 產生者：figs.py | M1 s3 |
| `figures/m1/s3_quadratic.png` | 51.5 KB | 產生者：figs.py | M1 s3 |
| `figures/m1/s4_concept.png` | 121.1 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M1 s4 |
| `figures/m1/s4_phases.png` | 88.2 KB | 產生者：figs.py | M1 s4 |
| `figures/m1/s4_program.png` | 71.5 KB | 產生者：figs.py | M1 s4 |
| `figures/m1/s4_robust.png` | 58.6 KB | 產生者：figs.py | M1 s4 |
| `figures/m1/s4_truth.png` | 91.9 KB | 產生者：figs.py | M1 s4 |
| `figures/m1/s5_concept.png` | 91.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py | M1 s5 |
| `figures/m1/s5_handoff.png` | 155.2 KB | 產生者：figs.py | M1 s5 |
| `figures/m1/s5_ports.png` | 63.6 KB | 產生者：figs.py | M1 s5 |
| `figures/m2/s1_boundary.png` | 93.7 KB | 產生者：figs.py | M2 s1 |
| `figures/m2/s1_channels.png` | 77.8 KB | 產生者：figs.py | M2 s1 |
| `figures/m2/s1_concept.png` | 101.5 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M2 s1 |
| `figures/m2/s1_tolerance.png` | 80.3 KB | 產生者：figs.py | M2 s1 |
| `figures/m2/s2_cells.png` | 90.0 KB | 產生者：figs.py | M2 s2 |
| `figures/m2/s2_components.png` | 59.7 KB | 產生者：figs.py | M2 s2 |
| `figures/m2/s2_concept.png` | 109.8 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M2 s2 |
| `figures/m2/s2_flow.png` | 140.4 KB | 產生者：figs.py | M2 s2 |
| `figures/m2/s3_concept.png` | 103.2 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M2 s3 |
| `figures/m2/s3_nonideal.png` | 175.7 KB | 產生者：figs.py | M2 s3 |
| `figures/m2/s3_verify.png` | 88.9 KB | 產生者：figs.py | M2 s3 |
| `figures/m3/s1_concept.png` | 132.8 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M3 s1 |
| `figures/m3/s1_core.png` | 112.0 KB | 產生者：figs.py、figs.py、figs.py | M3 s1 |
| `figures/m3/s1_heater.png` | 46.0 KB | 產生者：figs.py、figs.py、figs.py | M3 s1 |
| `figures/m3/s1_mzi.png` | 92.4 KB | 產生者：figs.py、figs.py、figs.py | M3 s1 |
| `figures/m3/s2_checks.png` | 152.0 KB | 產生者：figs.py、figs.py、figs.py | M3 s2 |
| `figures/m3/s2_concept.png` | 117.6 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M3 s2 |
| `figures/m3/s2_extract.png` | 104.2 KB | 產生者：figs.py、figs.py、figs.py | M3 s2 |
| `figures/m3/s2_zoom.png` | 86.6 KB | 產生者：figs.py、figs.py、figs.py | M3 s2 |
| `figures/m3/s3_chip.png` | 186.0 KB | 產生者：figs.py、figs.py、figs.py | M3 s3 |
| `figures/m3/s3_concept.png` | 119.6 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M3 s3 |
| `figures/m3/s3_ec.png` | 106.5 KB | 產生者：figs.py、figs.py、figs.py | M3 s3 |
| `figures/m3/s3_route.png` | 171.5 KB | 產生者：figs.py、figs.py、figs.py | M3 s3 |
| `figures/m3/s4_checks.png` | 142.0 KB | 產生者：figs.py、figs.py、figs.py | M3 s4 |
| `figures/m3/s4_concept.png` | 126.7 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | M3 s4 |
| `figures/m3/s4_nets.png` | 147.2 KB | 產生者：figs.py、figs.py、figs.py | M3 s4 |
| `figures/m3/s5_chip.png` | 259.0 KB | 產生者：figs.py | M3 s5 |
| `figures/m3/s5_concept.png` | 117.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py | M3 s5 |
| `figures/m3/s5_core.png` | 200.2 KB | 產生者：figs.py | M3 s5 |
| `figures/m3/s5_delivery.png` | 248.0 KB | 產生者：figs.py | M3 s5 |
| `figures/m3/s5_virtuoso.png` | 147.7 KB | 產生者：virtuoso_view.py | M3 s5 |
| `figures/m3/s6_compare.png` | 66.2 KB | 產生者：figs.py、figs.py、figs.py | M3 s6 |
| `figures/m3/s6_concept.png` | 132.1 KB | 產生者：concept.py | M3 s6 |
| `figures/m3/s6_seam.png` | 94.3 KB | 產生者：figs.py、figs.py、figs.py | M3 s6 |
| `figures/paper/m1/flow.png` | 92.8 KB | 產生者：concept.py | 共用 |
| `figures/paper/m1/s1_concept.png` | 121.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m1/s1_phase.png` | 162.1 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s1_power.png` | 79.0 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s1_skew.png` | 91.7 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s2_concept.png` | 126.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m1/s2_er.png` | 200.0 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s3_concept.png` | 124.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m1/s3_dither.png` | 126.1 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s3_track.png` | 115.5 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s4_concept.png` | 121.4 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m1/s4_margin.png` | 236.6 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s4_penalty.png` | 147.1 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s5_budget.png` | 173.9 KB | 產生者：figs.py | 共用 |
| `figures/paper/m1/s5_concept.png` | 110.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s1_baseline.png` | 100.4 KB | 產生者：figs.py | 共用 |
| `figures/paper/m2/s1_concept.png` | 108.8 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s2_concept.png` | 104.2 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s3_concept.png` | 80.7 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s3_power.png` | 175.9 KB | 產生者：figs.py | 共用 |
| `figures/paper/m2/s4_concept.png` | 99.4 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s4_deviation.png` | 135.3 KB | 產生者：figs.py | 共用 |
| `figures/paper/m2/s5_concept.png` | 82.2 KB | 產生者：concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m2/s5_general.png` | 102.9 KB | 產生者：figs.py | 共用 |
| `figures/paper/m3/s1_align.png` | 135.7 KB | 產生者：figs.py | 共用 |
| `figures/paper/m3/s1_concept.png` | 101.1 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m3/s2_concept.png` | 94.7 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m3/s2_synth.png` | 94.2 KB | 產生者：figs.py | 共用 |
| `figures/paper/m3/s3_concept.png` | 101.1 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m3/s3_detail.png` | 178.6 KB | 產生者：figs.py | 共用 |
| `figures/paper/m4/s1_concept.png` | 89.2 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m4/s1_quad.png` | 137.3 KB | 產生者：figs.py | 共用 |
| `figures/paper/m4/s2_concept.png` | 94.6 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m4/s2_leaf.png` | 188.2 KB | 產生者：figs.py | 共用 |
| `figures/paper/m4/s3_cert.png` | 184.1 KB | 產生者：figs.py、figs.py | 共用 |
| `figures/paper/m4/s3_concept.png` | 99.5 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m4/s4_budget.png` | 194.8 KB | 產生者：figs.py | 共用 |
| `figures/paper/m4/s4_concept.png` | 97.9 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m5/s1_cascade.png` | 90.1 KB | 產生者：figs.py | 共用 |
| `figures/paper/m5/s1_concept.png` | 114.6 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m5/s2_concept.png` | 107.5 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m5/s2_meander.png` | 127.7 KB | 產生者：figs.py | 共用 |
| `figures/paper/m5/s3_cert.png` | 122.5 KB | 產生者：figs.py、figs.py | 共用 |
| `figures/paper/m5/s3_concept.png` | 103.3 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m5/s4_concept.png` | 113.5 KB | 產生者：concept.py、concept.py、concept.py、concept.py、concept.py、concept.py | 共用 |
| `figures/paper/m5/s4_screen.png` | 111.2 KB | 產生者：figs.py | 共用 |
