r"""LUT4v2：E± 輸入（0＝+E、1＝−E）＋R＝3（+E）、Model-7a 雙差值＋AND，逐張驗證 65536 張真值表。
每張 24 個起點，裕量達 0.05 Pu 即停（所以裕量是下限）；找不到的再以 100 個起點重試。
每 4096 張存一次 out/full_part.json，中斷後重跑會從斷點續算。
worker 數：環境變數 LAB_WORKERS（預設 18，上限 24）；BLAS 單執行緒、低優先權（Windows BELOW_NORMAL，子程序繼承）。
執行：.\lab design\lut4\v2_epm\full_eval.py（18 個 worker 約 10 分鐘）→ out/full.json"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"
WORKERS = min(int(os.environ.get("LAB_WORKERS", 18)), 24)
if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
import sys, json, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from epm_eval import arch  # noqa: E402
import synth4 as S  # noqa: E402

OUT = Path(__file__).parent / "out"
PART, FINAL = OUT / "full_part.json", OUT / "full.json"
STOP, NST, NST2, BLOCK = 0.05, 24, 100, 4096


def job(f):
    if f in (0, 0xFFFF):
        return f, None
    m, _ = S.synth(f, arch("epm", 3.0), nst=NST, seed=f, stop=STOP)
    return f, round(float(m), 4)


def retry(f):
    m, _ = S.synth(f, arch("epm", 3.0), nst=NST2, seed=100000 + f, stop=STOP)
    return f, round(float(m), 4)


if __name__ == "__main__":
    t0 = time.time()
    done = {int(k): v for k, v in json.loads(PART.read_text()).items()} if PART.exists() else {}
    todo = [f for f in range(65536) if f not in done]
    print(f"已完成 {len(done)}，待算 {len(todo)}", flush=True)
    print(f"worker {WORKERS}", flush=True)
    with ProcessPoolExecutor(WORKERS) as ex:
        for i in range(0, len(todo), BLOCK):
            for f, m in ex.map(job, todo[i:i + BLOCK], chunksize=32):
                done[f] = m
            PART.write_text(json.dumps(done))
            print(f"{len(done)}／65536  {time.time() - t0:.0f} s", flush=True)
        fail = [f for f, m in done.items() if m is not None and m <= 0]
        print("第一輪找不到：", len(fail), flush=True)
        for f, m in ex.map(retry, fail):
            done[f] = m
    ms = [m for m in done.values() if m is not None]
    fail = sorted(f for f, m in done.items() if m is not None and m <= 0)
    out = dict(encoding="0=+E, 1=-E, R=+3", n=len(ms), ok=sum(m > 0 for m in ms), fail=[hex(f) for f in fail],
               ge_stop=sum(m >= STOP for m in ms), min_margin=min(ms), worst=hex(min(done, key=lambda f: done[f] if done[f] is not None else 9)),
               stop=STOP, starts=[NST, NST2], time_s=round(time.time() - t0, 1))
    FINAL.write_text(json.dumps(dict(summary=out, margins={hex(f): m for f, m in sorted(done.items())}), indent=0), encoding="utf-8")
    print(out)
