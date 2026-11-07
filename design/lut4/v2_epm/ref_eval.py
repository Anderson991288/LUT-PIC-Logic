r"""LUT4v2：參考光強度的比較。E± 輸入時參考只用一路與資料同振幅的 E+（R=1，同 ALU8 的「一個 E+」），
並與 OOK R=1、R=0 對照；60 個起點。執行：.\lab design\lut4\v2_epm\ref_eval.py → out/ref.json"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from epm_eval import arch, FUNCS, comp_sym  # noqa: E402
import synth4 as S  # noqa: E402

t0 = time.time(); res = {}
for name, f in FUNCS.items():
    row = {}
    for enc, r in [("epm", 1.0), ("ook", 1.0), ("ook", 0.0)]:
        m, _ = S.synth(f, arch(enc, r), nst=60, seed=11)
        row[f"{enc}_R{r:g}"] = round(m, 3)
    res[name] = row; print(name, row, flush=True)
res["time_s"] = round(time.time() - t0, 1)
(Path(__file__).parent / "out" / "ref.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(res["time_s"])
