r"""M0 s1：環境確認——這台電腦能不能跑 IPKISS、CORNERSTONE PDK 與 KLayout DRC。

用途：逐項檢查後面每個步驟會用到的工具，任何一項失敗就停在這一步，不要等到佈局或 DRC 才發現。
  每一項都是真的判定：出錯時記為「失敗」並繼續檢查下一項，最後一定寫出 out/env.json（M0 審查 R5）。
  1. Python 與數值套件可 import；BLAS 實際只用 1 個執行緒（大矩陣相乘時，行程 CPU 時間約等於經過時間）；
     平行上限不超過 6。
  2. matplotlib 中文字型。
  3. IPKISS 與 CORNERSTONE PDK（SOI220 變體）可 import；版本。
  4. PDK 的 2×2 MMI：電路模型在 1.50、1.55、1.60 µm 的 S 矩陣與理想 50:50 耦合器 H 的差（M0 審查 R7）；反射。
  5. PDK 的 2×2 MMI：佈局可產生、埠位可讀（in2／out2 的 y 座標大於 in1／out1，M0 審查 R6）、GDS 可寫出。
  6. KLayout 批次模式可執行，CORNERSTONE DRC deck 可對測試 GDS 跑完並回報規則數。
輸入：無（PDK 由 IPKISS 載入；KLayout 位置見 design/paths.py）。
輸出：out/env.json（各檢查項的結果、版本、數值）、out/mmi_test.gds、out/mmi_test_drc.lyrdb、
      figures/m0/s1_mmi_layout.png（圖 M0-1）。
執行：.\lab design\m0_env\s1_check\check_env.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup()                                                           # 必須在 import numpy 之前

import json                                                          # noqa: E402
import platform                                                      # noqa: E402
import subprocess                                                    # noqa: E402
import traceback                                                     # noqa: E402

import numpy as np                                                   # noqa: E402
import paths                                                         # noqa: E402

STEP = "m0_env/s1_check"
WAVELENGTHS_UM = [1.50, 1.55, 1.60]
checks = []
ctx = {}                                                             # 前面檢查的產物，後面的檢查要用


def check(name, expect, fn, note=""):
    """fn() 回傳 (是否通過, 實際值)；丟出例外時記為失敗並繼續。"""
    try:
        ok, value = fn()
    except Exception as e:                                           # noqa: BLE001
        ok, value = False, f"{type(e).__name__}: {e}"
        traceback.print_exc(limit=1)
    checks.append(dict(name=name, ok=bool(ok), value=value, expect=expect, note=note))
    print(f"[{'通過' if ok else '失敗'}] {name}：{value}（預期 {expect}）{note}")
    return ok


def c_packages():
    import matplotlib
    import shapely
    import scipy
    return True, f"{np.__version__}／{scipy.__version__}／{matplotlib.__version__}／{shapely.__version__}"


def c_blas():
    """單執行緒時，大矩陣相乘的行程 CPU 時間 ≈ 經過時間；多執行緒時 CPU 時間會是數倍。"""
    a = np.random.default_rng(0).standard_normal((1500, 1500))
    t0, c0 = time.perf_counter(), time.process_time()
    for _ in range(3):
        a @ a
    ratio = (time.process_time() - c0) / (time.perf_counter() - t0)
    return ratio < 1.5, f"CPU 時間／經過時間＝{ratio:.2f}"


def c_workers():
    import os
    return rt.MAX_WORKERS <= 6, f"CPU {os.cpu_count()} 核，程式上限 {rt.MAX_WORKERS} 個 worker"


def c_font():
    from matplotlib import font_manager
    f = font_manager.findfont("Microsoft JhengHei", fallback_to_default=False)
    return Path(f).exists(), Path(f).name


def c_pdk():
    from cornerstone.technology import select_technology_variant, CornerstoneVariant
    select_technology_variant(CornerstoneVariant.SOI220)              # 要在 import cornerstone 之前選定變體
    import cornerstone
    import cornerstone.all as cs
    ctx["cs"] = cs
    ctx["versions"] = dict(ipkiss=cornerstone.get_pdk_config().get("ipkiss_version"), cornerstone=str(cornerstone.__version__))
    ctx["cells"] = sorted(n for n in dir(cs) if n.startswith("SOI220nm_1550nm_TE"))
    return str(cornerstone.__version__).startswith("2.6"), (f"IPKISS {ctx['versions']['ipkiss']}、CORNERSTONE "
                                                            f"{ctx['versions']['cornerstone']}（安裝資料夾 "
                                                            f"{Path(cornerstone.__file__).resolve().parents[2].name}）")


def c_cells():
    return len(ctx["cells"]) > 0, f"{len(ctx['cells'])} 種"


def c_smatrix():
    """S 依埠序 [上, 下]＝[in2/out2, in1/out1] 排成 2×2，與 H＝[[1, i], [i, 1]]/√2 比較；三個波長。"""
    mmi = ctx["cs"].SOI220nm_1550nm_TE_STRIP_2x2_MMI()
    ctx["mmi"] = mmi
    S = mmi.CircuitModel().get_smatrix(wavelengths=np.array(WAVELENGTHS_UM))
    order_in, order_out = ["in2", "in1"], ["out2", "out1"]
    Hi = np.array([[1, 1j], [1j, 1]]) / np.sqrt(2)
    errs, power = {}, None
    for k, wl in enumerate(WAVELENGTHS_UM):
        Hk = np.array([[S[o, i][k] for i in order_in] for o in order_out])
        errs[f"{wl:.2f}"] = float(np.max(np.abs(Hk - Hi)))
        if abs(wl - 1.55) < 1e-9:
            power = np.round(np.abs(Hk) ** 2, 6).tolist()
    refl = float(np.max(np.abs([S[a, b][k] for a in order_in for b in order_in for k in range(len(WAVELENGTHS_UM))])))
    ctx.update(err_by_wl=errs, power=power, refl=refl)
    e155 = errs["1.55"]
    return e155 < 1e-9, "最大誤差 " + "、".join(f"{wl} µm：{e:.1e}" for wl, e in errs.items())


def c_refl():
    return ctx["refl"] < 1e-6, f"{ctx['refl']:.1e}"


def c_layout():
    lay = ctx["mmi"].Layout()
    ports = {p.name: [round(float(p.position.x), 3), round(float(p.position.y), 3)] for p in lay.ports}
    gds = paths.OUT(STEP, "mmi_test.gds")
    lay.write_gdsii(str(gds))
    si = lay.size_info()
    ctx.update(ports=ports, size=[round(si.width, 3), round(si.height, 3)], gds=gds)
    from common import gds2png
    gds2png.render(str(gds), str(paths.FIG("m0", "s1_mmi_layout.png")), "CORNERSTONE SOI220 2x2 MMI")
    return gds.exists() and len(ports) == 4, f"埠 {sorted(ports)}，外框 {ctx['size']} µm"


def c_port_order():
    p = ctx["ports"]
    ok = p["in2"][1] > p["in1"][1] and p["out2"][1] > p["out1"][1]
    return ok, f"in2.y＝{p['in2'][1]}、in1.y＝{p['in1'][1]}；out2.y＝{p['out2'][1]}、out1.y＝{p['out1'][1]}"


def c_klayout():
    exe = paths.KLAYOUT_EXE
    ver = subprocess.run([str(exe), "-b", "-v"], capture_output=True, text=True).stdout.strip() if exe.exists() else ""
    ctx["klayout"] = ver
    return bool(ver), ver or "找不到執行檔"


def c_drc():
    from common import drc
    r = drc.run(ctx["gds"])
    ctx["drc"] = dict(rules=len(r["rules"]), total=r["total"], counts=r["counts"], design_area_source=r["design_area_source"])
    return len(r["rules"]) > 0, f"規則 {len(r['rules'])} 條，單顆 MMI 違規 {r['total']}（設計區：{r['design_area_source']}）"


def main():
    t0 = time.time()
    check("Python", "≥ 3.9", lambda: (sys.version_info >= (3, 9), platform.python_version()))
    check("numpy／scipy／matplotlib／shapely", "可 import", c_packages)
    check("BLAS 單執行緒", "CPU 時間／經過時間 < 1.5", c_blas)
    check("平行上限", "≤ 6 個 worker", c_workers)
    check("中文字型", "微軟正黑體", c_font)
    pdk = check("IPKISS 與 CORNERSTONE PDK", "CORNERSTONE 2.6.x", c_pdk)
    if pdk:
        check("PDK 的 SOI220 1550 nm TE 元件", "> 0 種", c_cells)
        check("MMI S 矩陣＝理想 H（1.55 µm）", "< 1e-9；另記 1.50、1.60 µm", c_smatrix,
              "（只驗證電路模型；1.50、1.60 µm 只記錄不判定）")
        check("MMI 反射", "< 1e-6", c_refl)
        check("MMI 佈局與 GDS", "4 個埠、GDS 寫出", c_layout)
        check("PDK 埠的上下順序", "in2、out2 在上", c_port_order)
    check("KLayout 批次模式", "可執行", c_klayout, "（位置由環境變數 KLAYOUT_EXE 或使用者資料夾預設位置決定）")
    if pdk and "gds" in ctx:
        check("DRC deck 執行", "跑完並回報規則", c_drc, "（單顆 MMI 沒有晶片外框，違規數只作參考，M3 s4 才驗收）")

    res = dict(step="M0 s1", date=time.strftime("%Y-%m-%d"), passed=sum(c["ok"] for c in checks), total=len(checks),
               checks=checks, wavelengths_um=WAVELENGTHS_UM,
               versions=dict(python=platform.python_version(), numpy=np.__version__, klayout=ctx.get("klayout", ""),
                             **ctx.get("versions", {})),
               pdk_cells=len(ctx.get("cells", [])),
               mmi=dict(cell="SOI220nm_1550nm_TE_STRIP_2x2_MMI", max_err_vs_H=ctx.get("err_by_wl", {}).get("1.55"),
                        err_by_wavelength=ctx.get("err_by_wl"), reflection=ctx.get("refl"), power=ctx.get("power"),
                        ports_um=ctx.get("ports"), size_um=ctx.get("size")),
               drc=ctx.get("drc"), gds=rt.rel(ctx["gds"]) if "gds" in ctx else None, elapsed_s=round(time.time() - t0, 1))
    out = paths.OUT(STEP, "env.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n{res['passed']}/{res['total']} 項通過，寫出 {rt.rel(out)}（{res['elapsed_s']} s）")
    sys.exit(0 if res["passed"] == res["total"] else 1)


if __name__ == "__main__":
    main()
