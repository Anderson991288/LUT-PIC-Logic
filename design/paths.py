"""專案路徑的唯一來源（M0 s1）。

用途：所有程式由這裡取得專案根目錄、步驟資料夾、out/ 與 figures/，不寫絕對路徑，
      也不用相對路徑去拼別的步驟資料夾。外部工具位置只讀環境變數或使用者資料夾的預設位置。
用法：
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # design/<mN>/<sN>/x.py → design/
    from paths import OUT, FIG, STEP
    OUT("m1_logic/s4_gates", "phases.json")      # 讀前一步的交接檔
    FIG("m3", "s4_drc.png")                      # 圖的輸出位置
輸出：無（只提供路徑）。
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # 專案根目錄
DESIGN = ROOT / "design"
COMMON = DESIGN / "common"
FIGURES = ROOT / "figures"
REPORT = ROOT / "report"
DELIVERY = ROOT / "delivery"

# 外部工具：環境變數優先，否則用使用者資料夾的預設安裝位置
KLAYOUT_EXE = Path(os.environ.get("KLAYOUT_EXE") or Path(os.environ.get("APPDATA", "")) / "KLayout" / "klayout_app.exe")
PDK_NAME = "cornerstone"                            # IPKISS 以 import cornerstone 載入，不複製、不修改
DRC_DECK = COMMON / "drc" / "cornerstone_Si220_passive.lydrc"

# 里程碑資料夾（PLAN.md 的 M0–M3；論文延伸在 design/paper/）
MILESTONES = {"m0": "m0_env", "m1": "m1_logic", "m2": "m2_circuit", "m3": "m3_layout"}


def STEP(step):
    """'m1_logic/s4_gates' → 該步驟資料夾。"""
    p = DESIGN / step
    if not p.is_dir():
        raise FileNotFoundError(f"沒有步驟資料夾 design/{step}")
    return p


def OUT(step, name=None):
    """步驟的 out/ 資料夾，或其中的檔案。"""
    p = STEP(step) / "out"
    p.mkdir(exist_ok=True)
    return p / name if name else p


def FIG(milestone, name):
    """figures/<mN>/<name>；milestone 寫 'm0'…'m3'，論文延伸寫 'paper/m1' 等。"""
    p = FIGURES / milestone
    p.mkdir(parents=True, exist_ok=True)
    return p / name
