r"""M3 s5：在 Virtuoso 打開交付的 chip.gds（只看、不改），並把畫面存成報告的圖。

用途：
  1. 寫出 out/virtuoso_view.sh、out/virtuoso_view.il、out/virtuoso_colors.drf，並在 EDA 伺服器（WSL 中的 EDA_Server）以 GUI 開啟：
     strmin 把 delivery/layout/chip.gds 匯入 EDA 伺服器的暫存資料夾（/tmp/b7_view_s5；OA library 放在 Windows 磁碟上時
     Virtuoso 打不開 cellview），套用課程配色（GDS 3 藍、4 淺黃、5 粉紅、39 橘、41 綠），隱藏 GDS 99 外框，
     把暫存副本中的文字標記放大（只為了看得清楚；交付的 GDS 不變），只開一個佈局視窗。
     開啟後要在 Options → Display 把 Resolution 調到 Very High，否則 0.45 µm 的波導在全圖下會被顯示過濾掉。
  2. --crop：把螢幕截圖裁成 Virtuoso 視窗，存成 figures/m3/s5_virtuoso.png。
  3. --script-only：只寫出三個 script 檔，不啟動 EDA 伺服器（2026-11-07 重跑：本機不存取 EDA_Server）。
輸入：delivery/layout/chip.gds；EDA 伺服器上的 strmin、virtuoso。
輸出：out/virtuoso_view.sh、out/virtuoso_view.il、out/virtuoso_colors.drf；out/v_chip.png、figures/m3/s5_virtuoso.png（圖 M3-15，--crop 或 --grab）。
執行：.\lab design\m3_layout\s5_delivery\virtuoso_view.py
      .\lab design\m3_layout\s5_delivery\virtuoso_view.py --crop 截圖.png x0 y0 x1 y1
      .\lab design\m3_layout\s5_delivery\virtuoso_view.py --grab（開啟後自動擷取；需要 EDA 伺服器與授權）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import subprocess                                                    # noqa: E402

import paths                                                         # noqa: E402

STEP = "m3_layout/s5_delivery"
DISTRO = "EDA_Server"
WORK = "/tmp/b7_view_s5"                                             # EDA 伺服器上的暫存資料夾（不寫入其系統設定）

COLORS = """drDefineColor(
(display b7Blue 47 111 181)
(display b7Green 44 160 44)
(display b7Orange 255 127 14)
(display b7Yellow 253 230 138)
(display b7Pink 227 119 194)
(display b7Brown 140 86 75)
(display b7Grey 200 200 200)
)
"""

IL = """; 開啟交付的 B7 晶片（唯讀），套用課程配色、放大文字標記、隱藏外框
drLoadDrf("{work}/virtuoso_colors.drf" nil)
let((tf lp)
  tf = techGetTechFile(ddGetObj("B7_LIB"))
  foreach(e list(list("L3" "b7Blue") list("L4" "b7Yellow") list("L5" "b7Pink") list("L39" "b7Orange")
                 list("L41" "b7Green") list("L99" "b7Brown") list("L100" "b7Grey"))
    lp = techGetLP(tf list(car(e) "drawing"))
    when(lp drSetPacket("display" techGetLPPacketName(lp) "solid" "thickLine" cadr(e) cadr(e)))))
foreach(v list(list("layout" "displayStopLevel" 'int 32) list("graphic" "stopLevel" 'int 32)
               list("layout" "filterSize" 'float 0.0) list("layout" "displayPRHighestResolution" 'boolean t))
  errset(envSetVal(nth(0 v) nth(1 v) nth(2 v) nth(3 v)) t))
foreach(r list("Very High" "Highest" "High")
  unless(envGetVal("layout" "displayResolution") == "Very High"
    errset(envSetVal("layout" "displayResolution" 'string r) t)))
procedure(b7Labels(cell h)
  let((cv)
    cv = dbOpenCellViewByType("B7_LIB" cell "layout" "" "a")
    when(cv
      foreach(sh cv~>shapes when(sh~>objType == "label" sh~>height = h sh~>justify = "centerCenter" sh~>font = "stick"))
      dbSave(cv) dbClose(cv))))
b7Labels("B7_CHIP" 30.0)
b7Labels("PCELL_1" 8.0)
wc = car(errset(geOpen(?lib "B7_LIB" ?cell "B7_CHIP" ?view "layout" ?mode "r") t))
when(wc
  errset(wc~>stopLevel = 32 t)
  errset(hiResizeWindow(wc list(40:60 2440:1060)) t)
  errset(leSetLayerVisible(list("L99" "drawing") nil) t)
  hiZoomAbsoluteScale(wc 0.95)
  hiRedraw(wc))
printf("B7 VIEW READY %L\\n" wc)
"""


def wsl_path(p):
    p = Path(p).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def open_view(script_only=False):
    out = paths.OUT(STEP)
    chip = paths.ROOT / "delivery" / "layout" / "chip.gds"
    (out / "virtuoso_colors.drf").write_text(COLORS, encoding="utf-8", newline="\n")
    (out / "virtuoso_view.il").write_text(IL.format(work=WORK), encoding="utf-8", newline="\n")
    sh = ["#!/bin/bash", "set -e", "export DISPLAY=:0",
          "pkill -u \"$USER\" -f 'virtuoso -nocdsinit' || true", "sleep 2",
          f"rm -rf {WORK}", f"mkdir -p {WORK}", f"cd {WORK}",
          f"cp {wsl_path(out / 'virtuoso_colors.drf')} {wsl_path(out / 'virtuoso_view.il')} .",
          f"printf 'DEFINE B7_LIB {WORK}/B7_LIB\\n' > cds.lib",
          f"strmin -library B7_LIB -strmFile {wsl_path(chip)} -topCell B7_CHIP -view layout -logFile strmin.log -dbuPerUU 1000 > /dev/null",
          "grep -h 'Translation completed' strmin.log",
          f"setsid nohup virtuoso -nocdsinit -restore {WORK}/virtuoso_view.il > gui.log 2>&1 < /dev/null &",
          "sleep 40", "grep -h 'B7 VIEW READY' \"$HOME\"/CDS.log* 2>/dev/null | tail -1"]
    (out / "virtuoso_view.sh").write_text("\n".join(sh) + "\n", encoding="utf-8", newline="\n")
    if script_only:
        print(f"只寫出 {rt.rel(out / 'virtuoso_view.sh')}、virtuoso_view.il、virtuoso_colors.drf（未啟動 EDA 伺服器）")
        return
    r = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", f"bash {wsl_path(out / 'virtuoso_view.sh')}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-600:], r.stderr[-300:])
    print("Virtuoso 已開啟")
    if "--grab" in sys.argv[1:]:
        grab_view(out)


def grab_view(out):
    """以 LUT4 s8 的視窗擷取函式存圖：WSLg 視窗要由 Windows 端擷取，游標先移到視窗外。"""
    import importlib.util
    import time
    spec = importlib.util.spec_from_file_location("l4view", paths.ROOT / "design" / "lut4" / "s8_commercial" / "virtuoso_view.py")
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    png = out / "v_chip.png"
    for _ in range(30):
        V.grab("Reading: B7_LIB", png)
        if png.exists() and time.time() - png.stat().st_mtime < 20:
            break
        time.sleep(3)
    else:
        sys.exit("等不到 B7 視窗")
    time.sleep(8)
    V.grab("Reading: B7_LIB", png)
    V.crop(png)
    dst = paths.FIG("m3", "s5_virtuoso.png")
    dst.write_bytes(png.read_bytes())
    print(f"寫出 {rt.rel(dst)}")


def crop(src, box):
    from PIL import Image
    im = Image.open(src).convert("RGB").crop(tuple(int(v) for v in box))
    dst = paths.FIG("m3", "s5_virtuoso.png")
    im.save(dst)
    print(f"寫出 {rt.rel(dst)}（{im.size[0]}×{im.size[1]}）")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--crop":
        crop(sys.argv[2], sys.argv[3:7])
    else:
        open_view(script_only="--script-only" in sys.argv[1:])
