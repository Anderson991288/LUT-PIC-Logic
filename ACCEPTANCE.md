# LUT_Claude 驗收紀錄（2026-11-07）

狀態只用五種：本次通過、本次未通過、只核對既有證據、未驗證、原範圍待辦。

## 狀態彙總

| 狀態 | 項數 |
|---|---|
| 本次通過 | 27 |
| 本次未通過 | 1 |
| 原範圍待辦 | 1 |
| 未驗證 | 1 |

## 逐項結果

| 項目 | 狀態 | 結果 | 證據 |
|---|---|---|---|
| M0 s1 環境確認 | 本次通過 | 13/13。今天 16:01 重跑補回證據，原因見下方差異說明。 | `env.json` |
| M0 s2 報告工具故障注入 | 本次通過 | 24/24。 | `tool_tests.json` |
| B7 M1–M3 與設計資料包 | 本次通過 | 80/80、Caphe 80/80、平台預檢 DRC 0、LVS 14/14、光學 10/10、故障 8/8。 | 工作紀錄 |
| B7 M3 s6 Calibre、strmin、strmout | 本次通過 | EDA_Server 實跑，Calibre 0／2／0／0、KLayout 33／0。 | `eda_run_record.json` |
| B7 M3 s6 Virtuoso 截圖 | 本次通過 | 由本次 chip.gds 重拍，波導展開、21 PAD，人工看過。 | `s5_virtuoso.png` |
| LUT4 OOK 全表合成 | 本次通過 | 65,536 張。補強後最低 0.0578＠0x7996。獨立重播 1,048,576 列判錯 0。 | `full_replay.json` |
| LUT4 OOK layout 到設計資料 | 本次通過 | 平台預檢 DRC 0、14/14、10/10、8/8、MANIFEST 18/18。 | 工作紀錄 |
| LUT4 OOK Calibre、strmin、strmout | 本次通過 | 本次 GDS 實跑，Calibre 0／2／0／0、KLayout 33／0。 | `eda_run_record.json` |
| LUT4 OOK Virtuoso、RVE 截圖 | 本次通過 | 6 張重拍，對應本次 GDS，人工看過畫面。 | `shot_record.json` |
| LUT4 E± 全表合成 | 本次通過 | 第一輪 65,535 張。補強後 65,536 張全部 ≥0.1，最小 0.235＠0x967A。 | `full_replay.json` |
| LUT4 E± layout 到設計資料 | 本次通過 | 平台預檢 DRC 0、14/14、10/10、8/8、MANIFEST 18/18。 | 工作紀錄 |
| LUT4 E± Calibre、strmin、strmout | 本次通過 | 本次 GDS 實跑，Calibre 0／2／0／0、KLayout 33／0。 | `eda_run_record.json` |
| LUT4 E± Virtuoso、RVE 截圖 | 本次通過 | 6 張重拍，對應本次 GDS，人工看過畫面。 | `shot_record.json` |
| PTF2 分組 | 本次通過 | 57,574／7,962，表 8 上限欄 161／174／116／195／89 都相同。 | 工作紀錄 |
| PTF2 表 8 固定讀取欄 | 本次未通過 | 依頁面定義重建：相位兩列相同，其餘三列多 4–9 類，PAM4 二進位多 1 個三次類。原始程式不存在，使用者決定保留原頁數字。 | `ptf2_table8_fixed.json` |
| 論文 M1–M5 | 本次通過 | 54 步回傳碼全 0。JSON 除耗時外與參考相同。M4 單葉窗 30.5／33／37 ps，M5 44／34、42／32 類。 | 工作紀錄 |
| 論文 paper.html | 本次通過 | 不加 --force 建置 0 錯誤，連結與圖片檢查通過。逐圖目視另列。 | `paper.html` |
| 論文 M5 s4 參考核對 | 本次通過 | reference_check.json 與參考完全相同。資料副本來自 reference，來源見 SOURCE.md。 | `reference_check.json` |
| 雙差分研究 | 本次通過 | 9 步約 5 分鐘重跑，65,536 張 margin 差 0，8 份 JSON 差 0。 | `compare.json` |
| 論文 M6–M8 | 原範圍待辦 | 參考專案本來就沒有完成。 | 工作紀錄 |
| 報告審改 | 本次通過 | 移除 MZM 與設計外元件，修正內容錯誤，補術語與頁首說明，用語改為書面語。紀錄在 reader_review。 | `claude_main.md` |
| B7 設計資料驗收器 | 本次通過 | 改為固定完整集合，78 種竄改全部拒絕，正常資料與 K10 重跑平台預檢 DRC 通過。 | `delivery_check.json` |
| LUT4 設計資料關卡 | 本次通過 | 兩版新增 check_delivery，固定完整集合，各 128/128 反向測試通過，真值表由相位獨立重算。 | `delivery_check.json` |
| GDS 解析器 | 本次通過 | 保留 datatype，不支援的內容立即失敗，25/25 故障案例抓到。53 份 GDS 新舊相同，GC 的 AREF 展開與 KLayout 一致。 | `test_gds_parser.py` |
| 論文總驗收 | 本次通過 | verify_checks.py 檢查 24 個 JSON、86 項必要檢查，研究結果另列。其餘 22 支步驟程式的結束碼仍不反映檢查結果。 | `verify_checks.py` |
| LUT4 增益容差 | 本次通過 | 統計結果與確定性 ε 分開記錄，不再寫成全部真值表的規格。全表最小 ε：OOK 1.66%、E± 4.36%。 | `gain_box.json` |
| E± 共地壓降 | 未驗證 | 模型估算：heater 1 kΩ 時單路校正後殘差 0.117 rad，全表 4,721 張判錯。聯合校正尚未驗證，14×14 矩陣須由量測取得。 | `connectivity.json` |
| 教材頁、入口頁組裝 | 本次通過 | 入口與 m0–m3、LUT4 兩版建置 0 錯誤，連結、錨點、圖片檢查通過。 | `page_check.json` |
| 頁面逐圖目視 | 本次通過 | 223 處全部看過。內容錯誤與會讀錯的問題已修，輕微外觀問題列在清單未修。 | `claude_main.md` |
| README、環境探測、SHA-256 清單 | 本次通過 | 已產生，清單最後才計算。 | `ACCEPTANCE.md` |
