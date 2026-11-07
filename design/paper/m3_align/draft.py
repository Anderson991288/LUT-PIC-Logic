r"""論文 M3：草稿的設定（唯一來源）——草稿表 I、表 II 與 II-A 節的數字，供論文 M3 以後各步引用與比對。

用途：草稿的參數與要重現的數字集中寫在這裡；各步不得自己再寫一份。數字照草稿原文，單位寫在名稱裡。
輸入：無（數字抄自論文草稿 v2：表 I、表 II、II-A、II-B）。
輸出：無（供 import）。
所屬步驟：論文 M3 s1（建立）；M3 s2、s3 以後沿用。
"""

# 表 II：模擬設定
SETTINGS = dict(
    mzi_loss_db=0.9,            # 每顆 MZI（模型值；佈局每欄實際 0.78–0.96 dB）
    ng=4.27,                    # 群折射率
    pu_dbm=-7.0,                # 每路資料光功率；所有正規化功率、margin、護欄的單位
    r_amp=3.0,                  # 參考光場振幅（功率 9 P_u）
    bit_rate_gbps=10.0,
    edge_full_ps=31.25,         # 升餘弦邊緣的全寬
    resp_a_w=0.5,
    tia_noise_pa_rthz=20.0,
    tia_ohm=1000.0,
    rx_bw_ghz=7.0,              # 二階 Butterworth
    rin_db_hz=-140.0,
    pd_mismatch=0.02,
    comp_noise_mv=0.5,
    comp_offset_mv=0.3,
    q=7.0,
    setup_ps=10.0, hold_ps=5.0, jitter_pp_ps=8.0, t_req_ps=23.0,
    dt_ps=(1.0, 0.5),           # 時間格點
    scenario_4in="Euler 序列（256 種有序轉移）＋ 768 個隨機符號",
    delay_scan="12 個方向 × 11 段跨距（0–60 ps）",
    synth="annealed log-sum-exp soft-min ＋ L-BFGS，16 個隨機起點",
)

# II-A：佈局
LAYOUT = dict(column_um=489.0, column_ps=7.0, macro_ps=27.9, skew_macro_ps=0.60, skew_cascade_ps=1.20,
              column_loss_db=(0.78, 0.96))

# 表 I：單一 macro 的 margin（無損、0.9 dB/MZI）與各函數輸出功率下的雜訊護欄（皆以 P_u 為單位）；認證窗（13.2 ps 跨距）
TABLE1 = {
    "AND4":  dict(defn="x1 x2 x3 x4", lossless=1.49, lossy=0.83, guard=0.17, cert_ps=31.5),
    "OR4":   dict(defn="x1+x2+x3+x4", lossless=1.50, lossy=0.79, guard=0.17, cert_ps=None),
    "MAJ4":  dict(defn="至少 3 個為 1", lossless=1.50, lossy=0.81, guard=0.17, cert_ps=32.5),
    "TH2":   dict(defn="至少 2 個為 1", lossless=1.50, lossy=0.80, guard=0.17, cert_ps=None),
    "AND3":  dict(defn="x1 x2 x3", lossless=1.72, lossy=0.87, guard=0.17, cert_ps=None),
    "AND2":  dict(defn="x1 x2", lossless=2.11, lossy=1.02, guard=0.17, cert_ps=None),
    "AND2'": dict(defn="x1 x4", lossless=2.11, lossy=1.16, guard=0.17, cert_ps=None),
    "SOP2":  dict(defn="x1 x2 + x3 x4", lossless=0.54, lossy=0.29, guard=0.15, cert_ps=None),
    "XOR2":  dict(defn="x1 ⊕ x2", lossless=0.49, lossy=0.24, guard=0.14, cert_ps=37.5),
}
GUARD_COVERAGE = 0.20           # 覆蓋率統計用的保守護欄（最大輸出功率時）
TABLE3 = {                      # 表 III：對齊、盒內抽樣點最小（詳細模擬）、認證窗（ps）
    "AND4": dict(aligned=50.5, box_min=37.5, cert=31.5),
    "MAJ4": dict(aligned=52.5, box_min=39.5, cert=32.5),
    "XOR2": dict(aligned=65.5, box_min=52.0, cert=37.5),
}
