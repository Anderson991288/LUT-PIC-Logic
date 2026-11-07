"""共用的 MZI 與 B7 模型（M1 s2 起）。

用途：
  - T(θ, φ)：單顆 MZI 的 2×2 傳輸矩陣＝H · diag(e^{iθ}, 1) · H · diag(e^{iφ}, 1)。
    右邊兩個因子就是 M1 s1 的「相位＋MMI」混合單元；再加一個內相位 θ 與第二顆 MMI，就能調整分光比。
  - embed：把 2×2 矩陣放到 n 條波導中的相鄰兩條（rail, rail+1）。
  - B7_OPS：B7 的 7 顆 MZI，每顆 (上方波導索引, 層)，波導索引 0–4 由上到下（教學編號 1–5）。
  - b7_matrix(θ, φ)：依 B7_OPS 由左到右相乘，得 5×5 的 U。
  - READ：判讀埠（o2、o4 → 索引 1、3）；R＝3。
輸出：無（被其他程式 import）。
"""
import numpy as np

from common.optics import H

R_AMP = 3.0
B7_OPS = [(0, 0), (3, 0), (1, 1), (0, 2), (2, 2), (1, 3), (3, 3)]   # MZI-1…MZI-7
READ = (1, 3)                                                       # o2、o4


def T(theta, phi):
    return H @ np.diag([np.exp(1j * theta), 1.0]) @ H @ np.diag([np.exp(1j * phi), 1.0])


def T_closed(theta, phi):
    """T 的解析展開（核對用）。"""
    e = np.exp(1j * theta / 2)
    return np.array([[1j * np.exp(1j * phi) * e * np.sin(theta / 2), 1j * e * np.cos(theta / 2)],
                     [1j * np.exp(1j * phi) * e * np.cos(theta / 2), -1j * e * np.sin(theta / 2)]])


def embed(t, rail, n):
    m = np.eye(n, dtype=complex)
    m[rail:rail + 2, rail:rail + 2] = t
    return m


def chain(ops, theta, phi, n):
    """依 ops 順序（光由左到右）相乘：U＝M_last ⋯ M_1。"""
    U = np.eye(n, dtype=complex)
    for (rail, _), th, ph in zip(ops, theta, phi):
        U = embed(T(th, ph), rail, n) @ U
    return U


def b7_matrix(theta, phi):
    return chain(B7_OPS, theta, phi, 5)
