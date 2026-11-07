"""共用執行環境設定（M0 s1）。

用途：所有 design/ 程式的第一個 import，統一執行緒數、編碼、路徑、亂數種子與 matplotlib 字型。
用法（必須在 import numpy 之前）：
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from common import runtime as rt          # 由 design/<mN>/<sN>/ 的程式呼叫時 parents[2] = design/
    rt.setup()
輸出：無檔案；設定環境變數與 matplotlib rcParams。
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # 專案根目錄
DESIGN = ROOT / "design"
FIGURES = ROOT / "figures"
REPORT = ROOT / "report"

MAX_WORKERS = 6                                      # 平行程序上限（32 核心機器也只用 6）
THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
MC_SEED_BASE = 700                                   # Monte Carlo 實例 k 的種子 = 700 + k
FONT_FAMILY = ["Microsoft JhengHei", "DejaVu Sans"]  # 中文用微軟正黑體，缺字退回 DejaVu


def set_threads(n=1):
    """BLAS／OpenMP 執行緒數。本環境 BLAS 是 MKL，OPENBLAS_NUM_THREADS 單獨設定無效，四個都設。"""
    if "numpy" in sys.modules:
        if all(os.environ.get(v) == str(n) for v in THREAD_VARS):
            return                                  # 已設定成同樣的值（例如被另一支程式 import 時重複呼叫）
        raise RuntimeError("runtime.set_threads() 必須在 import numpy 之前呼叫")
    for v in THREAD_VARS:
        os.environ[v] = str(n)


def setup(threads=1, plot=True):
    """一般程式的標準設定：單執行緒 BLAS、UTF-8 輸出、中文字型。"""
    set_threads(threads)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if plot:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.family"] = FONT_FAMILY
        matplotlib.rcParams["axes.unicode_minus"] = False   # 負號用 ASCII，避免中文字型缺字
        matplotlib.rcParams["mathtext.fontset"] = "cm"


def rng(k=0):
    """Monte Carlo 實例 k 的亂數產生器（種子 700＋k）。"""
    import numpy as np
    return np.random.default_rng(MC_SEED_BASE + k)


def out_dir(script_file):
    """程式同資料夾的 out/（不存在就建立）。"""
    d = Path(script_file).resolve().parent / "out"
    d.mkdir(exist_ok=True)
    return d


def fig_path(milestone, name):
    """figures/<mN>/<name>，例如 fig_path('m0', 's1_font_check.png')；新程式請改用 paths.FIG。"""
    d = FIGURES / milestone
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def rel(p):
    """相對專案根目錄的路徑字串（寫進 JSON 與報告用，不留本機絕對路徑）。"""
    return Path(p).resolve().relative_to(ROOT).as_posix()
