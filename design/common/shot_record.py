r"""記錄 Virtuoso 與 Calibre RVE 截圖對應哪一份 GDS，並把結果寫回 commercial.json 的 status。

用途：截圖不能由幾何比對推論，要記錄拍攝時間、圖檔雜湊與當時的 GDS 雜湊。拍完先由人看過畫面，再執行本程式。
輸入：design/<version>/s8_commercial/out/ 的 commercial.json、v_*.png、rve_*.png；delivery 的 GDS；s6 的故障檔。
輸出：out/shot_record.json；commercial.json 的 status.virtuoso_rve_screenshots。
執行：.\lab design\common\shot_record.py lut4
      .\lab design\common\shot_record.py lut4v2
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ("v_chip.png", "v_core.png", "v_mzi.png", "v_fault.png", "rve_chip.png", "rve_fault.png")
DELIVERY = {"lut4": "delivery_lut4", "lut4v2": "delivery_lut4v2"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ver = sys.argv[1]
    out = ROOT / "design" / ver / "s8_commercial" / "out"
    com_p = out / "commercial.json"
    com = json.loads(com_p.read_text(encoding="utf-8"))
    chip = ROOT / DELIVERY[ver] / "layout" / "LUT4_chip.gds"
    fault = ROOT / "design" / ver / "s6_verify" / "out" / "chip_fault_drc.gds"
    run_end = (out / "calibre_strmout_8191.summary").stat().st_mtime
    stamp = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).isoformat()
    shots = {n: dict(sha256=sha(out / n), taken_utc=stamp((out / n).stat().st_mtime)) for n in SHOTS}
    after_run = all((out / n).stat().st_mtime > run_end for n in SHOTS)
    same_gds = com.get("chip_sha256") == sha(chip) and com.get("run_record", {}).get("inputs", {}).get("fault_sha256") == sha(fault)
    ok = after_run and same_gds
    rec = dict(version=ver, chip_sha256=sha(chip), fault_sha256=sha(fault), commercial_run_end_utc=stamp(run_end),
               all_shots_after_commercial_run=after_run, gds_matches_commercial_run=same_gds, shots=shots,
               method="WSLg 視窗由 Windows 螢幕擷取；Virtuoso 開啟本次交付 GDS 與故障檔，RVE 開啟本次 calibre_*.results",
               reviewed="拍完後人工看過畫面：標題為本次 cell、沒有遮擋與反白")
    (out / "shot_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    com.setdefault("status", {})["virtuoso_rve_screenshots"] = dict(
        status="本次通過" if ok else "未驗證", files=list(SHOTS), record="shot_record.json",
        note="截圖由本次交付 GDS 與本次 Calibre 結果拍攝" if ok else "截圖與本次 GDS 或本次 Calibre 執行對不上")
    com_p.write_text(json.dumps(com, ensure_ascii=False, indent=2), encoding="utf-8")
    print(ver, "截圖", com["status"]["virtuoso_rve_screenshots"]["status"], "在實跑之後", after_run, "GDS 相符", same_gds)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
