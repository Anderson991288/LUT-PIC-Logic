| 日期 | 修改 | 原因 | 影響 |
|---|---|---|---|
| 2026-10-30 | 最佳化移到 `common/synth.py`（M1 s2 改用它，結果逐位元組相同）；建立 `gates.py`，五個函數只要求 x3＝x4＝0（合計 44 組） | M1 s4：求 AND2、OR2、XOR2、AND4、OR4 的相位與真值表 | `out/gates.json` |
| 2026-10-30 | 二輸入函數改為 x3、x4 任意（每個函數 16 組，合計 80 組）；保留 x3＝x4＝0 作對照；新增相位誤差模擬、內部核對 `check_reference.py`、`figs.py` | 晶片上未使用的輸入不一定是暗的；對照顯示 margin 完全不變 | `out/gates.json`、`out/reference_check.json`、圖 M1-13～M1-16 |
| 2026-10-30 | 相位誤差通過率顯示到 0.1%；移除學員報告中與前版結果的比較（只留內部核對）；補 R 權重 \|u25\|、\|u45\| 解釋相位敏感度、500 次試驗的解析度；圖 M1-14 圖說補權重為 0 的說明；「自己動手」改為預測加短程式 | M1 審查 R2、R4、R8、R9、R12 | `out/gates.json`、報告 ③④⑤ |
| 2026-10-30 | 銜接框改為「B7 用一組固定讀取埠做到所有二輸入函數」 | 連貫性檢視：與 M1 s2 審查後的結論一致 | 銜接框 |
| 2026-11-07 | 本次重跑：`gates.py` 80/80，margin AND2 2.115、OR2 2.121、XOR2 0.486、AND4 1.496、OR4 1.500 與參考相同；`check_reference.py` 改為讀 `reference/phases.json`（參考實作 M1 s5 交接相位，由 port.py 複製）做「參考相位重播」：80/80、margin 差 0 | 原本讀的 參考 證據檔不在新工作區 | `out/reference_check.json` 欄位改為 replay_margin／ref_declared_margin；本次通過 |
