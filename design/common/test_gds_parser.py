r"""GDS 解析器的故障測試：放錯的 datatype 與不支援的內容必須立即失敗，正常資料必須讀得出來。

用途：在暫存資料夾寫出小型 GDS（或改寫專案裡實際的晶片 GDS），逐案確認 gds2png.parse／flatten 的反應。
  故障案例（新版都要丟 GdsError）：
    datatype：實際 GDS 全部改 99、只改一筆、TEXTTYPE 改錯
    AREF、NODE、BOX
    PATH：圓頭 1、延伸方頭 2、自訂延伸 4、BGNEXTN、有轉折、負寬度
    cell：SREF 引用不存在的 cell、flatten 指定不存在的 cell、cell 名稱重複
    遞迴：自己引用自己、兩個 cell 互相引用、階層太深
    其他：絕對 MAG、未知記錄、缺 DATATYPE、缺 ENDLIB（檔案截斷）、ENDLIB 後還有資料、缺 UNITS
  正常案例（新版都要讀得出來）：平頭 PATH、Virtuoso 匯出的補零結尾、datatypes=None 時保留 (layer, datatype)、實際 GDS 不變。
  --legacy：另外載入舊版 gds2png.py，確認舊版對故障案例都沒有反應（盲點確實存在）。
輸入：專案裡第一份找得到的晶片 GDS（見 REAL_GDS）；--legacy 指定的舊版程式。
輸出：逐案結果（印出）。全部符合時結束碼 0，否則 1。不寫專案檔案。
執行：python design\common\test_gds_parser.py [--legacy 舊版 gds2png.py]
"""
import importlib.util
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "design"))
from common import gds2png as G                                      # noqa: E402

REAL_GDS = ("delivery_lut4/layout/LUT4_chip.gds", "outputs/m2_s5/b7_ec_pad.gds")     # 各專案的晶片 GDS


def rec(code, payload=b""):
    return struct.pack(">HH", len(payload) + 4, code) + payload


def s16(v):
    return struct.pack(">h", v)


def s32(*v):
    return struct.pack(f">{len(v)}i", *v)


def name(s):
    b = s.encode("ascii")
    return b + b"\0" * (len(b) % 2)


def units():
    # 1e-3 與 1e-9 的 excess-64 實數
    return rec(0x0305, bytes.fromhex("3E4189374BC6A7EF") + bytes.fromhex("3944B82FA09B5A54"))


HEAD = rec(0x0002, s16(600)) + rec(0x0102, s16(0) * 12) + rec(0x0206, name("T")) + units()
SQUARE = (0, 0, 1000, 0, 1000, 1000, 0, 1000, 0, 0)


def boundary(layer=3, datatype=0, xy=SQUARE):
    return rec(0x0800) + rec(0x0D02, s16(layer)) + rec(0x0E02, s16(datatype)) + rec(0x1003, s32(*xy)) + rec(0x1100)


def path(pathtype=0, width=500, xy=(0, 0, 1000, 0), extra=b""):
    return (rec(0x0900) + rec(0x0D02, s16(39)) + rec(0x0E02, s16(0)) + rec(0x2102, s16(pathtype)) + rec(0x0F03, s32(width)) + extra
            + rec(0x1003, s32(*xy)) + rec(0x1100))


def text(texttype=0):
    return rec(0x0C00) + rec(0x0D02, s16(100)) + rec(0x1602, s16(texttype)) + rec(0x1003, s32(0, 0)) + rec(0x1906, name("P01")) + rec(0x1100)


def sref(target, strans=b""):
    return rec(0x0A00) + rec(0x1206, name(target)) + strans + rec(0x1003, s32(0, 0)) + rec(0x1100)


def aref(target):
    return rec(0x0B00) + rec(0x1206, name(target)) + rec(0x1302, s16(2) + s16(2)) + rec(0x1003, s32(0, 0, 2000, 0, 0, 2000)) + rec(0x1100)


def cell(cname, *els):
    return rec(0x0502, s16(0) * 12) + rec(0x0606, name(cname)) + b"".join(els) + rec(0x0700)


def lib(*cells, head=HEAD, tail=rec(0x0400)):
    return head + b"".join(cells) + tail


def retype(data, value, only_first=False):
    """把既有 GDS 的 DATATYPE 記錄改成 value。"""
    out, i = bytearray(data), 0
    n = 0
    while i + 4 <= len(out):
        ln = int.from_bytes(out[i:i + 2], "big")
        if ln == 0:
            break
        if out[i + 2:i + 4] == b"\x0e\x02" and not (only_first and n):
            out[i + 4:i + 6] = s16(value)
            n += 1
        i += ln
    return bytes(out), n


def flat(mod, gds):
    """舊版與新版共用的讀法：parse 後把每個 cell 攤平。"""
    structs, db = mod.parse(str(gds))
    polys = []
    for n in structs:
        mod.flatten(structs, n, np.eye(2), np.zeros(2), polys)
    return structs, polys


def same(a, b):
    return len(a) == len(b) and all(x[0] == y[0] and np.array_equal(x[-1], y[-1]) for x, y in zip(a, b))


def flatten_missing(mod, gds):
    structs, _ = mod.parse(str(gds))
    mod.flatten(structs, "NO_SUCH_CELL", np.eye(2), np.zeros(2), [])


def faults(real):
    cases = [
        ("TEXTTYPE 改成 7", lib(cell("TOP", boundary(), text(7))), flat),
        ("一個多邊形 datatype 改成 1", lib(cell("TOP", boundary(), boundary(datatype=1))), flat),
        ("含 AREF", lib(cell("SUB", boundary()), cell("TOP", aref("SUB"))), flat),
        ("含 NODE", lib(cell("TOP", rec(0x1500) + rec(0x0D02, s16(3)) + rec(0x2A02, s16(0)) + rec(0x1003, s32(0, 0)) + rec(0x1100))), flat),
        ("含 BOX", lib(cell("TOP", rec(0x2D00) + rec(0x0D02, s16(3)) + rec(0x2E02, s16(0)) + rec(0x1003, s32(*SQUARE)) + rec(0x1100))), flat),
        ("PATH 圓頭（型態 1）", lib(cell("TOP", path(1))), flat),
        ("PATH 延伸方頭（型態 2）", lib(cell("TOP", path(2))), flat),
        ("PATH 自訂延伸（型態 4）", lib(cell("TOP", path(4))), flat),
        ("PATH 帶 BGNEXTN", lib(cell("TOP", path(0, extra=rec(0x3003, s32(10))))), flat),
        ("PATH 有轉折", lib(cell("TOP", path(0, xy=(0, 0, 1000, 0, 1000, 1000)))), flat),
        ("PATH 負寬度", lib(cell("TOP", path(0, width=-500))), flat),
        ("SREF 引用不存在的 cell", lib(cell("TOP", boundary(), sref("MISSING"))), flat),
        ("flatten 指定不存在的 cell", lib(cell("TOP", boundary())), flatten_missing),
        ("cell 名稱重複", lib(cell("TOP", boundary()), cell("TOP", boundary(5))), flat),
        ("cell 引用自己", lib(cell("TOP", boundary(), sref("TOP"))), flat),
        ("兩個 cell 互相引用", lib(cell("A", boundary(), sref("B")), cell("B", sref("A"))), flat),
        ("階層超過上限", lib(*[cell(f"C{k}", sref(f"C{k + 1}")) for k in range(25)], cell("C25", boundary())), flat),
        ("SREF 用絕對 MAG", lib(cell("SUB", boundary()), cell("TOP", sref("SUB", rec(0x1A01, struct.pack(">H", 0x0004))))), flat),
        ("未知記錄", lib(cell("TOP", boundary(), rec(0x3C00))), flat),
        ("BOUNDARY 缺 DATATYPE", lib(cell("TOP", rec(0x0800) + rec(0x0D02, s16(3)) + rec(0x1003, s32(*SQUARE)) + rec(0x1100))), flat),
        ("檔案截斷（缺 ENDLIB）", lib(cell("TOP", boundary()), tail=b""), flat),
        ("ENDLIB 後還有資料", lib(cell("TOP", boundary()), tail=rec(0x0400) + rec(0x0800)), flat),
        ("缺 UNITS", lib(cell("TOP", boundary()), head=rec(0x0002, s16(600))), flat),
    ]
    if real:
        data = real.read_bytes()
        cases.insert(0, (f"實際 GDS 全部 DATATYPE 改 99（{retype(data, 99)[1]} 筆）", retype(data, 99)[0], flat))
        cases.insert(1, ("實際 GDS 只改第一筆 DATATYPE", retype(data, 1, only_first=True)[0], flat))
    return cases


def main():
    args = sys.argv[1:]
    legacy = None
    if "--legacy" in args:
        spec = importlib.util.spec_from_file_location("legacy_gds2png", args[args.index("--legacy") + 1])
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
    sys.stdout.reconfigure(encoding="utf-8")
    real = next((ROOT / p for p in REAL_GDS if (ROOT / p).exists()), None)
    print(f"實際 GDS：{real.relative_to(ROOT).as_posix() if real else '找不到，略過相關案例'}")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for k, (label, data, run) in enumerate(faults(real)):
            gds = t / f"case{k}.gds"
            gds.write_bytes(data)
            try:
                run(G, gds)
                new, why = False, "沒有失敗"
            except G.GdsError as e:
                new, why = True, str(e).split("：", 1)[-1]
            line = f"{'抓到' if new else '漏掉'}　{label}：{why[:70]}"
            ok &= new
            if legacy:
                try:
                    run(legacy, gds)
                    blind = True
                except Exception as e:                               # 舊版若碰巧崩潰，就不算盲點，如實列出
                    blind, line = False, line + f"（舊版例外 {type(e).__name__}）"
                ok &= blind
                line += "；舊版" + ("沒有反應" if blind else "有反應")
            print(line)

        # 正常案例
        def check(label, good):
            nonlocal ok
            ok &= bool(good)
            print(f"{'通過' if good else '未通過'}　{label}")

        g = t / "good.gds"
        g.write_bytes(lib(cell("SUB", boundary(), path(0)), cell("TOP", sref("SUB"), text(0))))
        st, polys = flat(G, g)
        check("平頭 PATH 與 SREF、TEXT 讀得出來", len(st["SUB"]["boundaries"]) == 2 and len(polys) == 4 and len(st["TOP"]["srefs"]) == 1)
        g.write_bytes(lib(cell("TOP", boundary()), tail=rec(0x0400) + b"\0" * 512))
        check("ENDLIB 後補零可接受", len(flat(G, g)[1]) == 1)
        g.write_bytes(lib(cell("TOP", boundary(3, 0), boundary(3, 99), boundary(41, 2))))
        st, _ = G.parse(str(g), datatypes=None)
        got = []
        G.flatten(st, "TOP", np.eye(2), np.zeros(2), got, with_datatype=True)
        check("datatypes=None 保留 (layer, datatype)", [(a, b) for a, b, _ in got] == [(3, 0), (3, 99), (41, 2)])
        st, _ = G.parse(str(g), datatypes=(0, 2, 99))
        check("datatypes 可明確指定", st["TOP"]["datatypes"] == [0, 99, 2])
        if real:
            data = real.read_bytes()
            bad = t / "dt99.gds"
            bad.write_bytes(retype(data, 99)[0])
            a, _ = G.parse(str(real))
            b, _ = G.parse(str(bad), datatypes=None)
            check("改 99 後幾何相同，但保留下來的 datatype 不同",
                  all(same(a[n]["boundaries"], b[n]["boundaries"]) for n in a)
                  and {d for n in a for d in a[n]["datatypes"]} == {0} and {d for n in b for d in b[n]["datatypes"]} == {99})
            if legacy:
                check("舊版讀改 99 的檔，結果與原檔完全相同", same(flat(legacy, real)[1], flat(legacy, bad)[1]))
    print("GDS 解析器故障測試全部符合" if ok else "GDS 解析器故障測試有不符合的案例")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
