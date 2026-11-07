| 日期 | 修改 | 原因 | 影響 |
|---|---|---|---|
| 2026-10-30 | 建立 `commercial.py`（由 KLayout deck 產生 SVRF 草案；在 EDA_Server 以批次指令執行 strmin、strmout（200／8191）、Calibre DRC；KLayout 比對與逐層幾何比對）與 `figs.py` | 使用者要求參考前版課程使用 Virtuoso／Calibre；使用者同意在 EDA_Server 執行（批次、最多 4 執行緒、結果只寫本步） | `out/commercial.json`、SVRF 草案、strmin／strmout 紀錄檔（當時在 `out/oa/`，第 2 列移到 `out/`）、兩份匯出 GDS、圖 M3-13、M3-14 |
| 2026-10-30 | strmin／strmout 改在 out/ 執行並在匯出後刪除 OA library；執行前刪舊匯出檔 | 中間產物與紀錄檔放在子資料夾，索引找不到產生者；覆寫產生多餘警告 | 結果不變 |
| 2026-10-31 | 配合 M3 s3 的 PAD 外移重跑；文字與圖改為多個 GND PAD | 使用者要求 PAD 在晶片最外圍 | 結果不變（全部通過） |
| 2026-10-31 | 加 .raw 小實驗（raw_vs_clean.lydrc，本機 KLayout）、未移植敘述清單、檢查類別數、cell 名稱與文字標記比對；改圖標題與結論 | M3 關卡審查 R1、R2、R6、R7、R12、R13：33 對 0 的原因是平台 deck 的 .raw 讓 GDS 3 逐塊檢查，不是 Calibre 漏抓 | 小實驗重現 32＋1＝33；合併後 0；結論改寫 |
| 2026-10-31 | 圖號改為 M3-14、M3-15 | M3 s5 新增圖 M3-13 | 只改編號 |
| 2026-10-31 | 圖號再改為 M3-15、M3-16 | M3 s5 再新增一張圖 | 只改編號 |
| 2026-10-31 | 圖號再改為 M3-16、M3-17 | M3 s5 新增 Virtuoso 圖 | 只改編號 |
| 2026-11-07 | 本次重跑：`commercial.py` 新增 `--evidence`：strmin／strmout／Calibre 不在本機執行，紀錄檔與兩份匯出 GDS 以參考專案的既有證據複製到 out/（SHA 記在 commercial.json 的 evidence 欄）；本機重跑 KLayout 部分：200 匯出 33（.raw 逐塊 32＋1）、8191 匯出 0、本次 chip.gds 與 8191 匯出檔逐層幾何差 0、cell 44／文字 62 相同；六項一致性全 True | 本次不啟動 EDA 伺服器 | 只核對既有證據（Calibre 0／2／0／0）＋本機 KLayout 部分本次通過 |
| 2026-11-07 | 採用 EDA_Server 實跑結果：10:58 由子代理非預期觸發 out/run.sh，輸入即本次 chip.gds（SHA a3f27b4d…）與 chip_fault_drc.gds；Calibre 0／2／0／0、KLayout 33／0、六項一致性全 True；參考紀錄移到 out/reference_evidence/，採用紀錄在 out/eda_run_record.json | 使用者決定記錄並採用 | M3 s6 Calibre／strmin／strmout 由「只核對既有證據」改為本次通過 |
