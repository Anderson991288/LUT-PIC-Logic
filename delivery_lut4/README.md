# Programmable Silicon Photonic 4-input LUT Design：交付包（Model-7a）

Model-7a：7 顆 MZI 組合的 a 版（拓樸代碼 3142132：由輸入往輸出，數字 k 表示一顆混合第 k、k＋1 條波導的 MZI）。

以 7 顆熱調 MZI 組成的 4 輸入可程式化光邏輯晶片。接收端固定：三組 PD＋TIA、兩個門檻 0 的比較器、一個 AND。
換邏輯功能只改 14 個 heater 相位。

## 1. 晶片

- 尺寸 4280 × 1200 µm；頂層 cell `L4_CHIP`；平台 CORNERSTONE SOI 220 nm（被動）。
- 光學：10 個邊緣耦合器（西緣 5 入、東緣 5 出），間距 250 µm。
- 電氣：21 個 PAD（訊號 14、GND 7，相鄰兩個 heater 共用一個 GND），都在上下緣最外圍。

## 2. 輸入

- x1–x4：資料光 0／1（強度調變），R：參考光，振幅 3（功率 9 P_u）；5 路來自同一顆雷射，相對相位固定。
- R 容許範圍 2.53–3.49（所附範例函數）。

## 3. 判讀

- 比較器 A：P(o2) ＞ P(o4)；比較器 B：P(o4) ＞ P(o3)；輸出 y＝A AND B。門檻都是 0，不需參考電壓。
- o1、o5 為監看埠（總功率核對、校正）。

## 4. 範例函數

- AND2（0x8888，裕量 1.148 P_u）、OR2（0xEEEE，裕量 1.124 P_u）、XOR2（0x6666，裕量 0.750 P_u）、NAND2（0x7777，裕量 1.062 P_u）、AND4（0x8000，裕量 0.878 P_u）、XOR4（0x6996，裕量 0.069 P_u）、MUX（0xCACA，裕量 0.776 P_u）。
- 相位見 `function/phases.json`（θ_k、φ_k 依 MZI-1…MZI-7，rad；每顆 MZI 0.9 dB 損耗模型）。

## 5. 驗證

- 電路模擬（PDK MMI 確認 U；判讀用每顆 MMI 0.45 dB 模型）：112/112；佈局審查 V1–V11 通過；DRC 違規 0；LVS 14/14；光學 10/10；故障注入全部抓到。
- 收件者可執行 `python check_delivery.py` 重新核對：檔案清單與雜湊、21 個 PAD、10 個 EC，以及由 `function/phases.json` 重算的 112 列真值表（光場 0／1）。DRC、LVS、光學、故障注入、佈局審查與電路模擬僅核對結果檔的紀錄，不重新執行。

## 6. 校正與限制

- 相位是模型值。晶片完成後依量測（MMI 損耗與分光、heater P_π、各軌固定相位差）重新求 14 個相位。
- 三路（PD＋TIA）增益由出廠修整調整。容許量依函數而定，以下是指定函數與模型下的觀察，不是全部真值表的規格（見 `interfaces/spec.json` 的 R2）：確定性增益盒 ε：七個範例最小 9.87%（XOR4）、0x0069 2.95%、全表相位庫逐表最小 1.66%（0x6CA9）；統計成功率另列於 R2。
- heater 回路（模型值，見 `interfaces/spec.json` 的 S6）：heater 1 kΩ、2π 時：相位不足最差 0.174 rad，單路與 14 路同時相同（地線只在 GND PAD 會合）；單路校正後殘差為 0。前提是 PAD 等電位、片外地阻抗為零。
- 系統需求見 `interfaces/spec.json` 的 S1–S6：五路輸入相位穩定（需片外相位鎖定或追蹤）、雷射波長、晶片溫度、消光比、光功率、heater 回路壓降。
- 未完成：輸入相位穩定方案、只用 o1–o5 量測的參數辨識與熱串擾校正、完整雜訊預算、打線／探針／ESD、電遷移上限比對。
- DRC 以 KLayout 與平台被動規則檔執行（0）；Calibre 基本 SVRF 草案（只移植線寬、間距 16 條，不是平台簽核）對本次 GDS 實跑 0（本次通過）。由 Virtuoso 匯出 GDS 時請指定 maxVertices 8191。
- 晶圓廠驗證過的 Calibre 規則檔、熱串擾模擬、雜訊預算尚未完成。

## 7. 檔案

- `layout/LUT4_chip.gds` SHA-256：`c6286b4caddee6daeef4cb6b51d74b2deadd85ccb48ce12c66f3ef13bdc1809f`（與 `verification/drc_result.json`、`connectivity.json` 記錄的相同）。
- 接線表 `function/lut4_netlist.json` SHA-256：`ece36c2a7d0a96a0353aed56c55cc953cbf89a4ca66fb6221e59d384e7a2a10a`（`phases.json` 只對這份接線表有效）。
- 其他檔案的雜湊見 `MANIFEST.json`。
- 交付檢查：`python check_delivery.py`（只需 numpy）；加 `--self-test` 另跑注入錯誤的反向測試。
