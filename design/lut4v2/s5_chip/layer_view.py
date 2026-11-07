r"""LUT4 v2 晶片整合：可縮放的 GDS 圖層檢視——在瀏覽器裡放大、拖曳整顆晶片，逐層開關。

用途：多邊形一律從 chip.gds 讀回（攤平所有 cell），依層寫成一張 SVG（座標單位 µm，取到 0.01 µm），
  包在一個獨立的 HTML 裡：滑鼠滾輪或「＋／−」縮放、拖曳平移、跳到輸入端／核心／輸出端，各層可勾選開關，
  另可顯示 EC 與 PAD 的文字標記、切換淺色背景。細線描邊只為螢幕辨識，實際尺寸以 GDS 為準。
輸入：本步的 out/chip.gds、out/chip_info.json（晶片外框）；LUT4 v2 s3 的 out/layout_info.json（核心埠位置）。
輸出：report/LUT4v2_layout_view.html（由 LUT4v2_study.html 以 iframe 嵌入）。
執行：.\lab design\lut4v2\s5_chip\layer_view.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import numpy as np                                                   # noqa: E402

import paths                                                         # noqa: E402
from common import gds2png as G                                      # noqa: E402

STEP = "lut4v2/s5_chip"
LAYERS = [  # (GDS 層, 名稱, 深色背景用色, 淺色背景用色)；先畫的在下面
    (99, "晶片外框（GDS 99）", "#e0b8a8", "#8a5a48"),
    (4, "EC 薄矽開窗（GDS 4）", "#ffe680", "#c9a400"),
    (5, "EC 薄矽（GDS 5）", "#ff7ae0", "#b0329a"),
    (3, "矽波導（GDS 3）", "#7fd4ff", "#1565c0"),
    (39, "TiN heater（GDS 39）", "#ffb347", "#e65100"),
    (41, "Ti/AL 引線與 PAD（GDS 41）", "#5ee36f", "#2e9e3e"),
]


def main():
    CI = json.loads(paths.OUT(STEP, "chip_info.json").read_text(encoding="utf-8"))
    structs, dbu = G.parse(str(paths.OUT(STEP, "chip.gds")))
    flat = []
    G.flatten(structs, "L4_CHIP", np.eye(2), np.zeros(2), flat)
    sc = dbu / 1e-6
    x0, x1 = CI["die_x_um"]
    y0, y1 = CI["die_y_um"]
    groups = []
    for layer, name, col, _ in LAYERS:
        pts = [" ".join(f"{x:.2f},{-y:.2f}" for x, y in xy * sc) for l, xy in flat if l == layer]
        fill = "none" if layer == 99 else col
        op = ' fill-opacity=".72"' if layer == 41 else ""
        sw = {3: 1.8, 99: 1.5}.get(layer, 1.0)                             # 波導很細，描邊加粗才看得到
        body = "".join(f'<polygon points="{p}" vector-effect="non-scaling-stroke"/>' for p in pts)
        groups.append(f'<g id="l{layer}" fill="{fill}"{op} stroke="{col}" stroke-width="{sw}">{body}</g>')
    texts = [(xy * sc, s) for l, xy, s in structs["L4_CHIP"]["texts"] if l == 100]
    lab = "".join(f'<text x="{x:.1f}" y="{-y:.1f}">{s}</text>' for (x, y), s in texts)
    groups.append(f'<g id="labels" fill="#f3f3f3" font-size="14" text-anchor="middle" style="display:none">{lab}</g>')
    boxes = "".join(f'<label><input type="checkbox" data-layer="l{l}" checked><span class="sw" style="background:{c}"></span>{n}</label>'
                    for l, n, c, _ in LAYERS[::-1])
    light_css = "".join(f"svg.light #l{l}{{stroke:{c2};{'' if l == 99 else 'fill:' + c2}}}" for l, _, _, c2 in LAYERS)
    core_x = [p["xy_um"][0] for p in json.loads(paths.OUT("lut4v2/s3_core", "layout_info.json").read_text(encoding="utf-8"))["ports"]]
    cx0, cx1 = min(core_x), max(core_x)
    views = {"all": [x0, -y1, x1 - x0, y1 - y0], "left": [x0 - 20, -y1, (cx0 - x0) + 300, y1 - y0],
             "middle": [cx0 - 100, -300, cx1 - cx0 + 200, 500], "right": [cx1 - 300, -y1, (x1 - cx1) + 320, y1 - y0]}
    html = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LUT4 晶片圖層檢視</title>
<style>body{{font:14px system-ui,"Microsoft JhengHei",sans-serif;margin:6px;color:#172131;background:#fff}}
.bar{{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center;margin:3px 0}}button{{font:inherit;padding:2px 9px}}
label{{white-space:nowrap}}svg{{display:block;width:100%;height:calc(100vh - 92px);min-height:320px;background:#0b0f15;touch-action:none;cursor:grab}}
svg.drag{{cursor:grabbing}}#scale{{color:#5b6573;margin-left:auto}}.sw{{display:inline-block;width:12px;height:12px;border-radius:2px;margin:0 4px -1px 0;border:1px solid #0003}}
svg.light{{background:#fbfcfe}}svg.light #labels{{fill:#172131}}{light_css}</style></head><body>
<div class="bar"><button data-view="all">全片</button><button data-view="left">輸入端</button><button data-view="middle">核心與繞線</button><button data-view="right">輸出端</button>
<button id="zin" aria-label="放大">＋</button><button id="zout" aria-label="縮小">−</button><label><input type="checkbox" id="bg">淺色背景</label><span id="scale"></span></div>
<div class="bar">{boxes}<label><input type="checkbox" data-layer="labels">EC 與 PAD 標記</label></div>
<svg id="v" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LUT4 晶片各層佈局">{"".join(groups)}</svg>
<script>
(function(){{var s=document.getElementById('v'),V={json.dumps(views)},vb=V.all.slice();
function set(){{s.setAttribute('viewBox',vb.join(' '));document.getElementById('scale').textContent='視窗寬 '+Math.round(vb[2])+' µm';}}
function zoom(f,cx,cy){{if(cx===undefined){{cx=vb[0]+vb[2]/2;cy=vb[1]+vb[3]/2;}}vb=[cx-(cx-vb[0])*f,cy-(cy-vb[1])*f,vb[2]*f,vb[3]*f];set();}}
function pt(e){{var r=s.getBoundingClientRect(),k=Math.max(vb[2]/r.width,vb[3]/r.height);
return [vb[0]+vb[2]/2+(e.clientX-r.left-r.width/2)*k,vb[1]+vb[3]/2+(e.clientY-r.top-r.height/2)*k,k];}}
s.addEventListener('wheel',function(e){{e.preventDefault();var p=pt(e);zoom(e.deltaY>0?1.25:0.8,p[0],p[1]);}},{{passive:false}});
var d=null;s.addEventListener('pointerdown',function(e){{d=[e.clientX,e.clientY];s.setPointerCapture(e.pointerId);s.classList.add('drag');}});
s.addEventListener('pointermove',function(e){{if(!d)return;var k=pt(e)[2];vb[0]-=(e.clientX-d[0])*k;vb[1]-=(e.clientY-d[1])*k;d=[e.clientX,e.clientY];set();}});
s.addEventListener('pointerup',function(){{d=null;s.classList.remove('drag');}});
document.getElementById('zin').onclick=function(){{zoom(0.6);}};document.getElementById('zout').onclick=function(){{zoom(1/0.6);}};
[].forEach.call(document.querySelectorAll('[data-view]'),function(b){{b.onclick=function(){{vb=V[b.dataset.view].slice();set();}};}});
[].forEach.call(document.querySelectorAll('[data-layer]'),function(c){{c.onchange=function(){{document.getElementById(c.dataset.layer).style.display=c.checked?'':'none';}};}});
document.getElementById('bg').onchange=function(){{s.classList.toggle('light',this.checked);}};
set();}})();
</script></body></html>"""
    out = paths.REPORT / "LUT4v2_layout_view.html"
    out.write_text(html, encoding="utf-8")
    print(out.name, f"{out.stat().st_size / 1e6:.2f} MB", {l: sum(1 for ll, _ in flat if ll == l) for l, _, _, _ in LAYERS})


if __name__ == "__main__":
    main()
