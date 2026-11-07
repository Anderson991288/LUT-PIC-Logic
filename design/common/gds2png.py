# -*- coding: utf-8 -*-
"""
自包含 GDS -> PNG 渲染器（繪製層俯視圖，依 layer 分色）。
M0 s2 引入為共用模組（取自參考實作，未修改演算法）；佈局出圖一律用它。
輸出：指定的 PNG 檔（render(gds, png, title)）。
解析器只接受看得懂的內容：保留 (layer, datatype)，預設只收 datatype 0；不支援的元素、缺 cell、循環引用立即丟 GdsError。
故障測試見 test_gds_parser.py。
只需 numpy + matplotlib，不需 IPKISS。
用法: python gds2png.py <in.gds> <out.png> [title]
"""
import sys, struct, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]   # 圖例用中文
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

LAYER_COLOR = {3: "#1f77b4", 4: "#fde68a", 5: "#e377c2", 39: "#ff7f0e", 41: "#2ca02c", 99: "#8c564b", 100: "#7f7f7f"}   # 固定配色：PAD（41）一律綠色

def _real8(b):
    """GDS 8-byte excess-64 浮點 -> float"""
    sign = -1.0 if (b[0] & 0x80) else 1.0
    exp = (b[0] & 0x7F) - 64
    mant = int.from_bytes(b[1:], "big") / float(1 << 56)
    return sign * mant * (16.0 ** exp)

class GdsError(ValueError):
    """GDS 含本解析器不支援或不完整的內容。一律立即失敗，不靜默略過，也不猜測。"""


MAX_DEPTH = 20                                                       # 階層上限（頂層算第 0 層）
NO_EFFECT = {0x0002, 0x0102, 0x0206, 0x1F06, 0x2006, 0x2202, 0x2306, 0x3602, 0x3706, 0x3800,   # 檔頭與函式庫資訊
             0x0502, 0x3402}                                         # BGNSTR、STRCLASS
EL_NO_EFFECT = {0x1701, 0x2601, 0x2B02, 0x2C06, 0x2F03}              # PRESENTATION、ELFLAGS、PROPATTR、PROPVALUE、PLEX：不影響幾何
UNSUPPORTED = {0x0B00: "AREF", 0x1500: "NODE", 0x2D00: "BOX", 0x3003: "PATH 的 BGNEXTN", 0x3103: "PATH 的 ENDEXTN"}


def _name(payload):
    return payload.split(b"\x00")[0].decode("ascii", "ignore")


def _path_rects(xy, width):
    """PATH（平頭端，pathtype 0）→ 每段一個矩形；單位與 xy 相同（dbunit）。只接受直線 PATH，轉折在 parse 就擋下。"""
    out = []
    for a, b in zip(xy[:-1], xy[1:]):
        d = b - a
        n = np.hypot(*d)
        if n == 0:
            continue
        o = np.array([-d[1], d[0]]) / n * width / 2
        out.append(np.array([a + o, b + o, b - o, a - o]))
    return out


def _check_hierarchy(structs, path):
    """每個引用的 cell 都要存在；不可循環；階層不可超過 MAX_DEPTH。"""
    height = {}

    def walk(name, stack):
        if name in stack:
            raise GdsError(f"{path}：cell 循環引用 {' → '.join(stack + [name])}")
        if name not in height:
            for s in structs[name]["srefs"]:
                if s["sname"] not in structs:
                    raise GdsError(f"{path}：cell {name} 引用的 {s['sname']} 不存在")
            height[name] = 1 + max((walk(s["sname"], stack + [name]) for s in structs[name]["srefs"]), default=0)
        return height[name]

    for name in structs:
        if walk(name, []) > MAX_DEPTH + 1:
            raise GdsError(f"{path}：cell {name} 的階層超過 {MAX_DEPTH} 層")


def parse(path, datatypes=(0,), expand_aref=False):
    """讀 GDS，回傳 (structs, dbunit_m)。

    structs[cell]：boundaries＝[(layer, xy)]、datatypes＝與 boundaries 逐筆對應的 datatype、srefs、
    texts＝[(layer, xy, string)]、texttypes＝與 texts 逐筆對應的 texttype。
    expand_aref：預設遇到 AREF 就失敗；True 時把陣列展開成多筆 srefs（只支援正交的列與行間距）。
    datatypes：允許的 DATATYPE／TEXTTYPE，預設只收 0；其他值會讓 parse 失敗。傳 None 表示全部接受，由呼叫端自己看 (layer, datatype)。
    不支援的內容（AREF、NODE、BOX、非平頭或有轉折的 PATH、絕對 MAG／ANGLE、未知記錄）、缺 cell、循環引用、檔案不完整都丟 GdsError。
    """
    data = open(path, "rb").read()
    allowed = None if datatypes is None else set(datatypes)
    structs = {}             # name -> dict
    cur = None
    cur_name = None
    i = 0
    dbunit_m = None
    el = None                # current element being read

    def fail(msg):
        where = f"cell {cur_name}" if cur is not None else "cell 之外"
        raise GdsError(f"{path}（位移 {i}，{where}）：{msg}")

    def begin(**kw):
        if cur is None or el is not None:
            fail("元素的位置不合法")
        return kw

    def need(*kinds):
        if el is None or el["kind"] not in kinds:
            fail(f"記錄 0x{code:04X} 不在預期的元素內")

    def check_type(value, what):
        if value is None:
            fail(f"{what} 缺少")
        if allowed is not None and value not in allowed:
            fail(f"layer {el['layer']} 的 {what} 是 {value}，允許的值是 {sorted(allowed)}")

    while True:
        if i + 4 > len(data):
            fail("檔案在 ENDLIB 之前就結束")
        ln = struct.unpack(">H", data[i:i+2])[0]
        if ln < 4 or ln % 2 or i + ln > len(data):
            fail(f"記錄長度 {ln} 不合法")
        rt, dt = data[i+2], data[i+3]
        code = (rt << 8) | dt
        payload = data[i+4:i+ln]
        if code == 0x0400:   # ENDLIB：之後只能是補零
            if cur is not None or any(data[i+ln:]):
                fail("ENDLIB 的位置不合法或其後還有資料")
            break
        elif code == 0x0B00 and expand_aref:  # AREF
            el = begin(kind="a", sname=None, xy=None, angle=0.0, mag=1.0, reflect=False, cols=None, rows=None)
        elif code == 0x1302:  # COLROW
            need("a")
            el["cols"], el["rows"] = struct.unpack(">hh", payload[:4])
        elif code in UNSUPPORTED:
            fail(f"不支援的記錄 {UNSUPPORTED[code]}")
        elif code in NO_EFFECT:
            pass
        elif code == 0x0305:  # UNITS: 2 reals (user-in-dbunit, meters-in-dbunit)
            dbunit_m = _real8(payload[8:16])
        elif code == 0x0606:  # STRNAME
            cur_name = _name(payload)
            if cur is not None or cur_name in structs:
                fail(f"STRNAME {cur_name} 重複或巢狀")
            cur = {"boundaries": [], "datatypes": [], "srefs": [], "texts": [], "texttypes": []}
            structs[cur_name] = cur
        elif code == 0x0700:  # ENDSTR
            if cur is None or el is not None:
                fail("ENDSTR 的位置不合法")
            cur = None
        elif code == 0x0800:  # BOUNDARY
            el = begin(kind="b", layer=None, datatype=None, xy=None)
        elif code == 0x0C00:  # TEXT（文字標記，例如 heater 編號）
            el = begin(kind="t", layer=None, texttype=None, xy=None, string="")
        elif code == 0x1906:  # STRING
            need("t")
            el["string"] = _name(payload)
        elif code == 0x0900:  # PATH（例如 PDK 的 TiN 加熱條）：讀入後轉成每段一個矩形
            el = begin(kind="p", layer=None, datatype=None, xy=None, width=None, pathtype=0)
        elif code == 0x0F03:  # WIDTH（TEXT 的 WIDTH 不影響幾何）
            need("p", "t")
            if el["kind"] == "p":
                el["width"] = struct.unpack(">i", payload[:4])[0]
        elif code == 0x2102:  # PATHTYPE（TEXT 的 PATHTYPE 不影響幾何）
            need("p", "t")
            if el["kind"] == "p":
                el["pathtype"] = struct.unpack(">h", payload[:2])[0]
        elif code == 0x0A00:  # SREF
            el = begin(kind="s", sname=None, ox=0, oy=0, xy=None, angle=0.0, mag=1.0, reflect=False)
        elif code == 0x0D02:  # LAYER
            need("b", "p", "t")
            el["layer"] = struct.unpack(">h", payload[:2])[0]
        elif code == 0x0E02:  # DATATYPE
            need("b", "p")
            el["datatype"] = struct.unpack(">h", payload[:2])[0]
        elif code == 0x1602:  # TEXTTYPE
            need("t")
            el["texttype"] = struct.unpack(">h", payload[:2])[0]
        elif code == 0x1206:  # SNAME
            need("s", "a")
            el["sname"] = _name(payload)
        elif code == 0x1A01:  # STRANS（TEXT 的 STRANS 只影響字形）
            need("s", "a", "t")
            flags = struct.unpack(">H", payload[:2])[0]
            if el["kind"] in ("s", "a"):
                if flags & 0x0006:
                    fail(f"SREF {el['sname']} 用絕對 MAG／ANGLE，不支援")
                el["reflect"] = bool(flags & 0x8000)
        elif code == 0x1B05:  # MAG
            need("s", "a", "t")
            el["mag"] = _real8(payload[:8])
        elif code == 0x1C05:  # ANGLE
            need("s", "a", "t")
            el["angle"] = _real8(payload[:8])
        elif code == 0x1003:  # XY
            need("b", "p", "t", "s", "a")
            n = len(payload) // 4
            vals = struct.unpack(">%di" % n, payload[:4*n])
            el["xy"] = np.array(vals, dtype=float).reshape(-1, 2)
        elif code == 0x1100:  # ENDEL
            if el is None or el["xy"] is None:
                fail("元素沒有 XY")
            xy, kind = el["xy"], el["kind"]
            if kind == "b":
                check_type(el["datatype"], "DATATYPE")
                if el["layer"] is None or len(xy) < 4 or not (xy[0] == xy[-1]).all():
                    fail("BOUNDARY 沒有 LAYER 或不是封閉多邊形")
                cur["boundaries"].append((el["layer"], xy))
                cur["datatypes"].append(el["datatype"])
            elif kind == "t":
                check_type(el["texttype"], "TEXTTYPE")
                if el["layer"] is None or len(xy) != 1:
                    fail("TEXT 沒有 LAYER 或座標不是一點")
                cur["texts"].append((el["layer"], xy[0], el["string"]))
                cur["texttypes"].append(el["texttype"])
            elif kind == "p":
                check_type(el["datatype"], "DATATYPE")
                if el["pathtype"] != 0:
                    fail(f"不支援的 PATHTYPE {el['pathtype']}（只支援平頭端 0）")
                if el["layer"] is None or el["width"] is None or el["width"] <= 0:
                    fail(f"PATH 的 LAYER 或 WIDTH 不支援（WIDTH {el['width']}）")
                d = np.diff(xy, axis=0)
                d = d[np.hypot(d[:, 0], d[:, 1]) > 0]
                if len(d) == 0 or (d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0]).any() or ((d[:-1] * d[1:]).sum(axis=1) < 0).any():
                    fail("PATH 長度為零或有轉折：每段各自成矩形會缺角，不支援")
                rects = _path_rects(xy, el["width"])
                cur["boundaries"].extend((el["layer"], q) for q in rects)
                cur["datatypes"].extend([el["datatype"]] * len(rects))
            elif kind == "a":
                if el["sname"] is None or len(xy) != 3 or not el["cols"] or not el["rows"] or el["cols"] < 1 or el["rows"] < 1:
                    fail("AREF 缺 SNAME、COLROW 或三點 XY")
                step_c = (xy[1] - xy[0]) / el["cols"]
                step_r = (xy[2] - xy[0]) / el["rows"]
                for c in range(el["cols"]):
                    for r in range(el["rows"]):
                        o = xy[0] + c * step_c + r * step_r
                        cur["srefs"].append(dict(el, kind="s", ox=o[0], oy=o[1]))
            else:
                if el["sname"] is None or len(xy) != 1:
                    fail("SREF 沒有 SNAME 或座標不是一點")
                el["ox"], el["oy"] = xy[0]
                cur["srefs"].append(el)
            el = None
        elif code in EL_NO_EFFECT:
            need("b", "p", "t", "s", "a")
        else:
            fail(f"未知的記錄 0x{code:04X}")
        i += ln
    if dbunit_m is None:
        raise GdsError(f"{path}：沒有 UNITS")
    _check_hierarchy(structs, path)
    return structs, dbunit_m

def affine(reflect, angle_deg, mag, ox, oy):
    th = np.deg2rad(angle_deg)
    c, s = np.cos(th), np.sin(th)
    ry = -1.0 if reflect else 1.0
    # p' = R * (mag * (x, ry*y)) + (ox, oy)
    a = mag * c;        b = -mag * s * ry
    cc = mag * s;       d = mag * c * ry
    return np.array([[a, b], [cc, d]]), np.array([ox, oy])

def flatten(structs, name, M, T, out, depth=0, with_datatype=False):
    """攤平 cell：out 收 (layer, 多邊形)；with_datatype=True 時收 (layer, datatype, 多邊形)。cell 不存在或階層過深時丟 GdsError。"""
    if name not in structs:
        raise GdsError(f"cell {name} 不存在")
    if depth > MAX_DEPTH:
        raise GdsError(f"cell {name} 超過 {MAX_DEPTH} 層，可能是循環引用")
    st = structs[name]
    for (layer, xy), datatype in zip(st["boundaries"], st["datatypes"]):
        p = xy @ M.T + T
        out.append((layer, datatype, p) if with_datatype else (layer, p))
    for s in st["srefs"]:
        M2, T2 = affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        flatten(structs, s["sname"], M @ M2, M @ T2 + T, out, depth+1, with_datatype)

def render(gds, png, title=None):
    structs, dbunit_m = parse(gds)
    referenced = set()
    for st in structs.values():
        for s in st["srefs"]:
            referenced.add(s["sname"])
    tops = [n for n in structs if n not in referenced] or list(structs)
    top = tops[0]
    polys = []
    flatten(structs, top, np.eye(2), np.zeros(2), polys)
    scale = dbunit_m / 1e-6   # dbunit -> um
    layers = sorted(set(l for l, _ in polys))
    cmap = plt.get_cmap("tab10")
    colors = {l: LAYER_COLOR.get(l, cmap(i % 10)) for i, l in enumerate(layers)}
    # 畫布依佈局長寬比：接近正方形的 die／晶片用方形畫布（顯示面積約為寬版的 2 倍）、圖例分兩列；寬扁佈局維持 14 × 5
    allp = np.vstack([p for _, p in polys]) * (dbunit_m / 1e-6)
    aspect = (allp[:, 0].max() - allp[:, 0].min()) / max(allp[:, 1].max() - allp[:, 1].min(), 1e-9)
    square = aspect < 2.2
    fig, ax = plt.subplots(figsize=(8.5, 8.5 / aspect + 0.6) if square else (14, 5))
    # 一般層：填色；GDS99(design-area 框)：只畫外框線以免蓋住設計
    fill_patches, fill_colors = [], []
    for l, p in polys:
        if l == 99:
            ax.add_patch(Polygon(p * scale, closed=True, fill=False,
                                 edgecolor=colors[l], linewidth=1.4))
        else:
            fill_patches.append(Polygon(p * scale, closed=True))
            fill_colors.append(colors[l])
    pc = PatchCollection(fill_patches, facecolor=fill_colors, edgecolor="black",
                         linewidth=0.15, alpha=0.75)
    ax.add_collection(pc)
    ax.autoscale(); ax.set_aspect("equal")
    ax.set_xlabel("x（µm）"); ax.set_ylabel("y（µm）")
    if title: ax.set_title(title)
    import matplotlib.patches as mp
    ax.legend([mp.Patch(color=colors[l]) for l in layers],
              [{3: "GDS 3  矽波導", 4: "GDS 4  120 nm 蝕刻窗", 5: "GDS 5  脊型保護（100 nm 矽）", 39: "GDS 39  加熱器", 41: "GDS 41  電極／接觸墊", 99: "GDS 99  晶片外框", 100: "GDS 100  文字標記"}.get(l, "GDS 圖層 %d" % l) for l in layers], loc="upper center", bbox_to_anchor=(0.5, 0.0),
              borderaxespad=4.5, ncol=(4 if square else len(layers)), fontsize=9, frameon=False)   # 圖例放在圖框下方，不遮住電路
    fig.tight_layout(); fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("rendered", png, "layers", layers, "polys", len(polys))

if __name__ == "__main__":
    g = sys.argv[1]; p = sys.argv[2]
    t = sys.argv[3] if len(sys.argv) > 3 else None
    render(g, p, t)
