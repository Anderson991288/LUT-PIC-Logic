"""共用的理想光學元件（M1 s1 起）。

用途：所有步驟共用同一套符號與埠序，避免各自重寫而不一致。
  - H：理想 50:50 MMI，第 1 列／行＝上方埠、第 2 列／行＝下方埠（與 PDK 的 in2/out2＝上、in1/out1＝下 對應，M0 s1 已驗證 PDK 模型等於 H）。
  - phase(φ)：只在上臂加相位 φ 的對角矩陣。
  - power(y)：光場 → 功率 |y|²（偵測器量到的是功率，不是光場）。
輸出：無（被其他程式 import）。
"""
import numpy as np

H = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)


def phase(phi):
    """上臂相位 φ（rad），下臂不變。"""
    return np.diag([np.exp(1j * phi), 1.0])


def power(y):
    return np.abs(np.asarray(y)) ** 2
