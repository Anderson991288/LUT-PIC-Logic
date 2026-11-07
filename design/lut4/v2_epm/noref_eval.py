r"""LUT4v2：E± 輸入、不用參考光（R=0）、兩個差動對（Model-7a 雙差值＋AND）。
16 列分成 8 組互補對（x 與 15−x）；逐一合成「每組兩列輸出相同」的全部 2^8 種設定，看是否都做得到。
執行：.\lab design\lut4\v2_epm\noref_eval.py（6 個 worker）→ out/noref.json"""
import sys, json, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from epm_eval import arch  # noqa: E402
import synth4 as S  # noqa: E402

PAIRS = [(x, 15 - x) for x in range(8)]


def table(k):
    f = 0
    for i, (a, b) in enumerate(PAIRS):
        if k >> i & 1:
            f |= (1 << a) | (1 << b)
    return f


def job(k):
    f = table(k)
    if f in (0, 0xFFFF):
        return k, f, None
    m, _ = S.synth(f, arch("epm", 0.0), nst=24, seed=k, stop=0.05)
    return k, f, round(m, 4)


if __name__ == "__main__":
    t0 = time.time()
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(job, range(256)))
    ms = [m for _, _, m in res if m is not None]
    fail = [hex(f) for _, f, m in res if m is not None and m <= 0]
    out = dict(n=len(ms), ok=sum(m > 0 for m in ms), fail=fail, min_margin=min(m for m in ms if m > 0),
               xor4=[m for _, f, m in res if f == 0x6996][0], time_s=round(time.time() - t0, 1))
    (Path(__file__).parent / "out" / "noref.json").write_text(json.dumps(dict(summary=out, all=res), indent=0), encoding="utf-8")
    print(out)
