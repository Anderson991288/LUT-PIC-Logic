| 日期 | 修改 | 原因 | 影響 |
|---|---|---|---|
| 2026-10-30 | 建立 `flow.py`（由 spec.json 推出元件數量；逐項查 PDK cell 的層、尺寸、埠與模型；讀 DRC 規則；8 步流程與輸入輸出核對）與 `figs.py` | M2 s2：佈局前先決定每個元件用 PDK cell 或自建 | `out/components.json`、`out/flow.json`、`out/pdk_cells_geom.json`、圖 M2-4～M2-6 |
| 2026-10-30 | EC 名稱比對改為只認 Edge 開頭或 EC、SSC 縮寫；加熱條線寬改讀 Path 的線寬 | 第一版把 HeaterWedge 誤判為 EC；加熱條是 Path，量多邊形得到 0 µm | `components.json` 的 `ec_like_cells`、`heater_width_um` |
| 2026-10-30 | 流程檢查改為依序累積（輸入必須是更前面步驟的輸出）；C6 繞線數量改為 14 條訊號線＋GND 匯流線 | M2 審查 R6、R13 | `flow.json`、`components.json` 的 C6 |
| 2026-10-30 | 每個 PDK cell 單獨寫成 GDS 跑平台 DRC；C3 heater 依結果改為自建；波導寬度改取 MMI 埠的 0.45 µm | M3 s1 發現 PDK 加熱條本身有 16208 處 DRC 違規；技術檔 0.5、模板 0.4、MMI 埠 0.45 µm 不一致 | `components.json`：PDK 4 項、自建 4 項；圖 M2-5、M2-6 與本步概念圖更新 |
| 2026-11-07 | 本次重跑：`flow.py` 10 項元件、PDK cell 各自 DRC（加熱條 16208 處為預期，其餘 0）、一致性 6/6，三個 JSON 與參考逐項相同 | 重建工作區 | 本次通過 |
