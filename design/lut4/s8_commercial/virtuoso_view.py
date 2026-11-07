r"""LUT4 s8：在 Virtuoso 打開交付的 LUT4 晶片（只看、不改），以 Virtuoso 自己的存圖函式輸出畫面；Calibre RVE 開啟故障檔的結果。

用途（在 WSL 的 EDA_Server 以 GUI 執行；暫存資料夾 /tmp/l4_view，不寫入其系統設定）：
  1. strmin 把 delivery_lut4/layout/LUT4_chip.gds 與故障檔 chip_fault_drc.gds 匯入同一個 OA library（兩個 library 會互蓋顯示設定）。
  2. 套用課程配色（GDS 3 藍、4 淺黃、5 粉紅、39 橘、41 綠），隱藏 GDS 99 外框，暫存副本中的文字標記放大（交付的 GDS 不變）。
  3. hiWindowSaveImage 依序存：全晶片、LUT4 核心放大、故障檔的兩處違規放大 → out/v_*.png。
  4. calibre -rve 開啟 calibre_fault.results（由 commercial.py 產生）；--grab 以 Windows 螢幕擷取 RVE 視窗。
輸入：delivery_lut4/layout/LUT4_chip.gds；LUT4 s6 的 out/chip_fault_drc.gds；本步 out/calibre_fault.results。
輸出：out/virtuoso_view.sh、out/virtuoso_view.il、out/virtuoso_colors.drf、out/v_chip.png、out/v_core.png、out/v_fault.png；
      --grab：out/rve_fault.png。圖複製到 figures/lut4/。
執行：.\lab design\lut4\s8_commercial\virtuoso_view.py --script-only（2026-11-07 重跑：只寫出 virtuoso_view.sh、.il、.drf，不呼叫 wsl、不讀 EDA_Server 的路徑）
      .\lab design\lut4\s8_commercial\virtuoso_view.py --run-eda（開 Virtuoso；需使用者授權）
      .\lab design\lut4\s8_commercial\virtuoso_view.py --run-eda --rve
      沒有 --run-eda 一律不會呼叫 wsl。
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import paths                                                         # noqa: E402

STEP = "lut4/s8_commercial"
DISTRO = "EDA_Server"
WORK = "/tmp/l4_view"

COLORS = """drDefineColor(
(display l4Blue 47 111 181)
(display l4Green 44 160 44)
(display l4Orange 255 127 14)
(display l4Yellow 253 230 138)
(display l4Pink 227 119 194)
(display l4Brown 140 86 75)
(display l4Grey 200 200 200)
)
"""

IL = r"""; 開啟交付的 LUT4 晶片（唯讀），套用課程配色、放大文字標記、隱藏外框，存三張圖
drLoadDrf("{work}/virtuoso_colors.drf" nil)
let((tf lp)
  tf = techGetTechFile(ddGetObj("L4_LIB"))
  foreach(e list(list("L3" "l4Blue") list("L4" "l4Yellow") list("L5" "l4Pink") list("L39" "l4Orange")
                 list("L41" "l4Green") list("L99" "l4Brown") list("L100" "l4Grey"))
    lp = techGetLP(tf list(car(e) "drawing"))
    when(lp drSetPacket("display" techGetLPPacketName(lp) "solid" "thickLine" cadr(e) cadr(e)))))
; 顯示過濾：filterSize（預設 6.0 像素，型別 float）以下的形狀不畫，0.45 µm 波導在縮小時會斷開；displayResolution 預設 Medium
foreach(v list(list("layout" "displayStopLevel" 'int 32) list("graphic" "stopLevel" 'int 32)
               list("layout" "filterSize" 'float 0.0) list("layout" "displayPRHighestResolution" 'boolean t))
  errset(envSetVal(nth(0 v) nth(1 v) nth(2 v) nth(3 v)) t))
foreach(r list("Very High" "Highest" "High")
  unless(envGetVal("layout" "displayResolution") == "Very High"
    errset(envSetVal("layout" "displayResolution" 'string r) t)))
printf("L4 ENV filterSize=%L displayResolution=%L PRHighest=%L\n" envGetVal("layout" "filterSize")
       envGetVal("layout" "displayResolution") envGetVal("layout" "displayPRHighestResolution"))
procedure(l4Labels(cell h)
  let((cv)
    cv = dbOpenCellViewByType("L4_LIB" cell "layout" "" "a")
    when(cv
      foreach(sh cv~>shapes when(sh~>objType == "label" sh~>height = h sh~>justify = "centerCenter" sh~>font = "stick"))
      dbSave(cv) dbClose(cv))))
l4Labels("L4_CHIP" 30.0)
l4Labels("PCELL_1" 8.0)
procedure(l4Show(w box)
  errset(w~>stopLevel = 32 t)
  errset(hiResizeWindow(w list(40:60 2440:1060)) t)
  errset(leSetLayerVisible(list("L99" "drawing") nil) t)
  if(box then hiZoomIn(w box) else hiZoomAbsoluteScale(w 0.95))
  hiRedraw(w))
; 依序切換畫面：每張寫 ready_<name>，等 Windows 端擷取後寫 done_<name> 再換下一張
l4Views = list(list("L4_CHIP" nil "chip") list("L4_CHIP" list(-80:-170 2440:70) "core")
               list("L4_CHIP" list(-20:-150 620:50) "mzi") list("L4_CHIP_FAULT" list(-480:495 -150:595) "fault"))
l4Win = nil l4Cur = nil l4Cell = nil l4Box = nil
procedure(l4Next()
  let((v)
    if(l4Views then
      v = car(l4Views) l4Views = cdr(l4Views) l4Cur = nth(2 v)
      unless(l4Cell == car(v)
        when(l4Win errset(hiCloseWindow(l4Win) t))
        l4Win = car(errset(geOpen(?lib "L4_LIB" ?cell car(v) ?view "layout" ?mode "r") t))
        l4Cell = car(v))
      l4Show(l4Win cadr(v)) l4Box = cadr(v)
      hiRegTimer("l4Zoom()" 30)
    else
      printf("L4 VIEW DONE\n"))))
procedure(l4Zoom()
  when(l4Box hiZoomIn(l4Win l4Box)) hiRedraw(l4Win)
  hiRegTimer("l4Mark()" 20))
procedure(l4Mark()
  let((f) f = outfile(strcat("{work}/ready_" l4Cur)) fprintf(f "%s\n" l4Cur) close(f))
  hiRegTimer("l4Wait()" 10))
procedure(l4Wait()
  if(isFile(strcat("{work}/done_" l4Cur)) then l4Next() else hiRegTimer("l4Wait()" 10)))
l4Next()
printf("L4 VIEW READY\n")
"""


def wsl_path(p):
    p = Path(p).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


def run(cmd):
    if "--run-eda" not in sys.argv[1:] or "--script-only" in sys.argv[1:]:     # 第二道閘門：任何路徑走到這裡都擋下
        sys.exit("未指定 --run-eda：不呼叫 EDA_Server。")
    r = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-1500:], r.stderr[-500:])
    return r


def view(script_only=False):
    out = paths.OUT(STEP)
    chip = paths.ROOT / "delivery_lut4" / "layout" / "LUT4_chip.gds"
    fault = paths.OUT("lut4/s6_verify", "chip_fault_drc.gds")
    (out / "virtuoso_colors.drf").write_text(COLORS, encoding="utf-8", newline="\n")
    (out / "virtuoso_view.il").write_text(IL.replace("{work}", WORK), encoding="utf-8", newline="\n")
    sh = ["#!/bin/bash", "set -e", "export DISPLAY=:0",
          "pkill -u \"$USER\" -f 'virtuoso -nocdsinit' || true", "sleep 2",
          f"rm -rf {WORK}", f"mkdir -p {WORK}", f"cd {WORK}",
          f"cp {wsl_path(out / 'virtuoso_colors.drf')} {wsl_path(out / 'virtuoso_view.il')} .",
          f"printf 'DEFINE L4_LIB {WORK}/L4_LIB\\n' > cds.lib",
          f"strmin -library L4_LIB -strmFile {wsl_path(chip)} -topCell L4_CHIP -view layout -logFile strmin.log -dbuPerUU 1000 > /dev/null",
          f"strmin -library L4_LIB -strmFile {wsl_path(fault)} -topCell L4_CHIP_FAULT -view layout -logFile strmin_fault.log -dbuPerUU 1000 > /dev/null",
          "grep -h 'Translation completed' strmin.log strmin_fault.log",
          f"setsid nohup virtuoso -nocdsinit -restore {WORK}/virtuoso_view.il > gui.log 2>&1 < /dev/null &",
          "sleep 5", "echo STARTED"]
    (out / "virtuoso_view.sh").write_text(chr(10).join(sh) + chr(10), encoding="utf-8", newline=chr(10))
    if script_only:
        print(f"只寫出 {rt.rel(out / 'virtuoso_view.sh')}、virtuoso_view.il、virtuoso_colors.drf（未呼叫 wsl）")
        return
    run(f"bash {wsl_path(out / 'virtuoso_view.sh')}")
    share = Path("//wsl.localhost") / DISTRO / WORK.strip("/")       # EDA_Server 的 /tmp/l4_view（Windows 端讀寫就緒檔）
    for name in ("chip", "core", "mzi", "fault"):
        for _ in range(200):
            if (share / f"ready_{name}").exists():
                break
            if name == "fault" and _ % 5 == 4:
                grab("Layout XL", None, mode="enter")                 # 關掉「沒有 validLayers 限制」的提示框
            time.sleep(1)
        else:
            sys.exit(f"等不到 {name} 畫面")
        time.sleep(2)
        png = out / f"v_{name}.png"
        grab("Reading: L4_LIB", png)
        crop(png)
        (share / f"done_{name}").write_text("ok", encoding="utf-8")
        shutil.copyfile(png, paths.FIG("lut4", f"s8_v_{name}.png"))
        print("寫出", rt.rel(paths.FIG("lut4", f"s8_v_{name}.png")))


PS_GRAB = r"""
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class W { public delegate bool EP(IntPtr h, IntPtr l);
[DllImport("user32.dll")] public static extern bool EnumWindows(EP f, IntPtr l);
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
[DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int a, out RECT r, int n);
public struct RECT { public int L,T,R,B; } }
'@
[W]::SetProcessDPIAware() | Out-Null
$script:hit = $null
[W]::EnumWindows({ param($h,$l) if ([W]::IsWindowVisible($h)) { $sb = New-Object System.Text.StringBuilder 300; [void][W]::GetWindowText($h,$sb,300); if ($sb.ToString() -like '*__KEY__*') { $script:hit = $h } }; return $true }, [IntPtr]::Zero) | Out-Null
if (-not $script:hit) { Write-Output 'NOWIN'; exit 1 }
if ('__MODE__' -eq 'enter') { [W]::SetForegroundWindow($script:hit) | Out-Null; Start-Sleep -Milliseconds 500
  Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); Write-Output 'ENTER'; exit 0 }
[W]::SetForegroundWindow($script:hit) | Out-Null
[W]::SetCursorPos(5, 5) | Out-Null; Start-Sleep -Milliseconds 1500
$r = New-Object W+RECT; [void][W]::DwmGetWindowAttribute($script:hit, 9, [ref]$r, 16)
$w = $r.R - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $h; $g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size); $bmp.Save('__OUT__'); $g.Dispose(); $bmp.Dispose()
Write-Output "GRAB $w x $h"
"""


CROP = (36, 33, 2448, 1066)      # WSLg 視窗矩形包含外圍透明邊，依 Virtuoso 外框裁切（視窗位置固定為 40:60 2440:1060）


def crop(png):
    from PIL import Image
    im = Image.open(png)
    im.crop(CROP).save(png)


def grab(key, png, mode="grab"):
    """以 Windows 螢幕擷取標題含 key 的視窗（WSLg 視窗無法用 Virtuoso 自己的存圖函式輸出，會是全黑）。"""
    ps = PS_GRAB.replace("__KEY__", key).replace("__OUT__", str(png)).replace("__MODE__", mode)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip(), r.stderr.strip()[-300:])


def rve():
    out = paths.OUT(STEP)
    from PIL import Image
    for tag in ("fault", "chip"):
        sh = ["#!/bin/bash", "export DISPLAY=:0", f"cd {wsl_path(out)}",
              f"setsid nohup calibre -rve -drc calibre_{tag}.results > rve_{tag}.log 2>&1 < /dev/null &",
              "sleep 30", f"tail -2 rve_{tag}.log"]
        (out / "rve.sh").write_text(chr(10).join(sh) + chr(10), encoding="utf-8", newline=chr(10))
        run(f"bash {wsl_path(out / 'rve.sh')}")
        png = out / f"rve_{tag}.png"
        grab(f"calibre_{tag}.results", png)
        im = Image.open(png)
        im.crop((33, 32, im.size[0] - 32, im.size[1] - 32)).save(png)     # 去掉 WSLg 視窗外圍透明邊
        shutil.copyfile(png, paths.FIG("lut4", f"s8_rve_{tag}.png"))
        print("寫出", rt.rel(paths.FIG("lut4", f"s8_rve_{tag}.png")))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--script-only" in args:
        view(script_only=True)
    elif "--run-eda" not in args:
        sys.exit("未指定 --script-only 或 --run-eda：不呼叫 EDA_Server。本波未獲授權實跑，請用 --script-only。")
    elif "--rve" in args:
        rve()
    else:
        view()
