r"""M3 s5：最終交付——把晶片、介面、驗證結果整理成別人拿到就能用的交付包。

用途：重建根目錄的 delivery/（先清空）：
  layout/        chip.gds（整顆晶片）
  interfaces/    spec.json、tolerance.json、chip_info.json、pads.csv（PAD 對照）、optical_ports.csv（EC 對照）、
                 b7_netlist.json、phases.json（相位起點）、truth_tables.csv（80 組驗收答案）
  verification/  drc_result.json、connectivity.json（M3 s4）、review_checks.json（M3 s2）、sim_results.json（M2 s3）
  figures/       chip.png、nets.png、core.png
  README.md      晶片概要、介面、操作與校正步驟（需求 K1）、驗證結果、已知限制、檔案雜湊
  check_delivery.py  交付檢查程式（只需 numpy；可在交付包內獨立執行）
  MANIFEST.json  每個檔案的 SHA-256、大小與來源步驟
  README 的數字一律從結果檔讀出。
輸入：M1 s5、M2 s1–s3、M3 s1–s4 的結果檔與圖；本步的 check_delivery.py。
輸出：delivery/（上列檔案）。
執行：.\lab design\m3_layout\s5_delivery\package.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import io                                                            # noqa: E402
import json                                                          # noqa: E402
import shutil                                                        # noqa: E402

import paths                                                         # noqa: E402

DEL = paths.ROOT / "delivery"
HERE = Path(__file__).resolve().parent


def J(step, name):
    return json.loads(paths.OUT(step, name).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_csv(path, rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8-sig")


def main():
    if DEL.exists():
        shutil.rmtree(DEL)
    for d in ("layout", "interfaces", "verification", "figures"):
        (DEL / d).mkdir(parents=True)
    src = {}                                                          # 交付檔 → 來源步驟

    def cp(step, name, dst, rename=None):
        target = DEL / dst / (rename or name)
        shutil.copyfile(paths.OUT(step, name) if step else name, target)
        src[target.relative_to(DEL).as_posix()] = step or "figures"

    cp("m3_layout/s3_chip", "chip.gds", "layout")
    for step, name in (("m2_circuit/s1_spec", "spec.json"), ("m2_circuit/s1_spec", "tolerance.json"), ("m3_layout/s3_chip", "chip_info.json"),
                       ("m1_logic/s5_handoff", "b7_netlist.json"), ("m1_logic/s5_handoff", "phases.json"),
                       ("m1_logic/s5_handoff", "truth_tables.csv")):
        cp(step, name, "interfaces")
    for step, name in (("m3_layout/s4_verify", "drc_result.json"), ("m3_layout/s4_verify", "connectivity.json"),
                       ("m3_layout/s2_review", "review_checks.json"), ("m2_circuit/s3_sim", "sim_results.json")):
        cp(step, name, "verification")
    for fig, new in (("s3_chip.png", "chip.png"), ("s4_nets.png", "nets.png"), ("s1_core.png", "core.png")):
        shutil.copyfile(paths.FIG("m3", fig), DEL / "figures" / new)
        src[f"figures/{new}"] = "figures/m3/" + fig
    shutil.copyfile(HERE / "check_delivery.py", DEL / "check_delivery.py")
    src["check_delivery.py"] = "m3_layout/s5_delivery"

    spec, chip, tol = J("m2_circuit/s1_spec", "spec.json"), J("m3_layout/s3_chip", "chip_info.json"), J("m2_circuit/s1_spec", "tolerance.json")
    conn, drc_r = J("m3_layout/s4_verify", "connectivity.json"), J("m3_layout/s4_verify", "drc_result.json")
    sim, rev = J("m2_circuit/s3_sim", "sim_results.json"), J("m3_layout/s2_review", "review_checks.json")
    chan = {c["heater"]: c for c in spec["phase_channels"]}
    pads = []
    for p in sorted(chip["pads"], key=lambda p: (p["side"] != "N", p["xy_um"][0])):
        c = chan.get(p["heater"])
        pads.append(dict(pad=p["name"], side="北" if p["side"] == "N" else "南", x_um=p["xy_um"][0], y_um=p["xy_um"][1],
                         x_die_um=round(p["xy_um"][0] - chip["die_x_um"][0], 3), y_die_um=round(p["xy_um"][1] - chip["die_y_um"][0], 3),
                         role="訊號" if c else "地", heater=p["heater"] or "+".join(p["heaters"]), mzi=c["mzi"] if c else "", phase=c["phase"] if c else ""))
    write_csv(DEL / "interfaces" / "pads.csv", pads, ["pad", "side", "x_um", "y_um", "x_die_um", "y_die_um", "role", "heater", "mzi", "phase"])
    src["interfaces/pads.csv"] = "m3_layout/s3_chip＋m2_circuit/s1_spec"
    sp = {o["port"]: o for o in spec["optical_ports"]}
    ecs = [dict(ec=f"{e['signal']}_{e['port']}", signal=e["signal"], core_port=e["port"], side="西" if e["side"] == "W" else "東",
                facet_x_um=e["facet_um"][0], facet_y_um=e["facet_um"][1], x_die_um=round(e["facet_um"][0] - chip["die_x_um"][0], 3),
                y_die_um=round(e["facet_um"][1] - chip["die_y_um"][0], 3), use=sp[e["port"]]["note"])
           for e in sorted(chip["ec"], key=lambda e: (e["side"] != "W", -e["facet_um"][1]))]
    write_csv(DEL / "interfaces" / "optical_ports.csv", ecs, ["ec", "signal", "core_port", "side", "facet_x_um", "facet_y_um",
                                                              "x_die_um", "y_die_um", "use"])
    src["interfaces/optical_ports.csv"] = "m3_layout/s3_chip＋m2_circuit/s1_spec"

    # ---------- README ----------
    req = {r["id"]: r for r in spec["requirements"]}
    hp = [v["total_mW"] for v in tol["heater_power"].values()]
    dens = chip["current_density"]
    e = conn["electrical"]
    gaps = []
    for side in ("北", "南"):
        xs = sorted(r["x_um"] for r in pads if r["side"] == side)
        gaps += [b - a for a, b in zip(xs[:-1], xs[1:])]
    loss = chip["loss_estimate"]
    tot = [x["total_db"] for x in loss]
    lines = [
        "# B7 單顆 PIC 交付包", "",
        "本交付包包含一顆以 7 個 MZI 組成的可程式化光邏輯晶片（B7）：佈局 GDS、介面規格、驗證結果，以及操作與校正步驟。",
        "晶片不含光源與偵測器；換一組 heater 相位即可在 AND2、OR2、XOR2、AND4、OR4 之間切換。", "",
        "## 1　晶片概要", "",
        f"- 平台：CORNERSTONE SOI 220 nm 被動製程（波導 GDS 3、淺蝕刻 GDS 4、薄矽 GDS 5、TiN heater GDS 39、Ti/AL 接觸墊 GDS 41）。",
        f"- 晶片尺寸：{chip['die_um'][0]:g} × {chip['die_um'][1]:g} µm（GDS 99 外框）；頂層 cell `B7_CHIP`。",
        f"- 座標：GDS 原點在核心輸入引線末端（in0 埠內側 50 µm 處），不是晶片角落；晶片外框 x＝{chip['die_x_um'][0]:g}…{chip['die_x_um'][1]:g}、"
        f"y＝{chip['die_y_um'][0]:g}…{chip['die_y_um'][1]:g} µm。`pads.csv`、`optical_ports.csv` 另附以晶片左下角為原點的座標（x_die_um、y_die_um）。",
        f"- 光學：西緣 5 個輸入、東緣 5 個輸出邊緣耦合器（EC），間距 {chip['ec_pitch_um']:g} µm。",
        f"- 電氣：{sum(1 for p in pads if p['role'] == '訊號')} 個訊號 PAD（P01–P14，對應 heater H01–H14）＋ {chip['n_gnd_pads']} 個 GND PAD（北 GN1…、南 GS1…），"
        f"全部在晶片上下緣最外圍（外緣離晶片邊 {chip['pad_edge_um']:g} µm，為假設值，待平台確認切割道與崩邊餘量）；PAD 為 {80}×{100} µm；PAD 間距不等（{min(gaps):.0f}–{max(gaps):.0f} µm），探針卡需依 `pads.csv` 的座標製作。", "",
        "## 2　檔案", "",
        "| 檔案 | 內容 |", "|---|---|",
        "| `layout/chip.gds` | 整顆晶片佈局（含 PDK 元件幾何，依 PDK 授權使用，請勿公開散布） |",
        "| `interfaces/spec.json` | 介面規格與 12 條需求（光學埠、相位通道、R、輸入相位、heater 功率、校正 K1） |",
        "| `interfaces/pads.csv` | PAD 名稱、座標、訊號／地、對應的 heater 與相位 |",
        "| `interfaces/optical_ports.csv` | EC 名稱、訊號、對應核心埠、端面座標、用途（資料、參考光、判讀、監看） |",
        "| `interfaces/b7_netlist.json`、`phases.json`、`truth_tables.csv` | 固定光路、五個函數的相位起點、80 組驗收答案 |",
        "| `interfaces/tolerance.json`、`chip_info.json` | 容許範圍計算、晶片幾何與電流密度估算 |",
        "| `verification/*.json` | DRC、LVS 與光學連接、佈局審查、電路模擬結果 |",
        "| `figures/*.png` | 晶片全圖、電氣網、核心佈局 |",
        "| `check_delivery.py` | 交付檢查：`python check_delivery.py`（只需 numpy）；可重算檔案雜湊、對照、版本與 80 組真值表，LVS 與光學連接只確認結果檔 |",
        "| `MANIFEST.json` | 每個檔案的 SHA-256 |", "",
        "## 3　光學介面", "",
        f"- 5 路輸入（x1–x4、R）須來自同一顆 1550 nm 雷射（相干），TE 偏振；資料光 0／1 以有光／無光表示。",
        f"- 參考光 R：振幅為一路資料「1」的 {tol['R_nominal']:g} 倍（功率 {tol['R_nominal'] ** 2:g} 倍）；"
        f"在理想元件下容許 {tol['R_range_all'][0]:g}–{tol['R_range_all'][1]:g}。",
        f"- 5 路輸入在晶片入口的相對相位須固定；理想元件下誤差標準差 ≤ {tol['input_phase_sigma_ok']:g} rad。"
        f"晶片上 5 個輸入從 EC 到核心等長（差 {chip['fan_in_spread_um']:g} µm），不會引入隨溫度、波長漂移的相位差；"
        f"核心內每經過一顆 MZI 比直通多走 {rev['mzi_extra_gds_um']:.1f} µm（約 {rev['dphi_dlam_rad_nm']:.2f} rad/nm、{rev['dphi_dT_rad_K']:.4f} rad/K），"
        "校正後需控溫並穩定雷射波長。",
        "- 判讀：ΔP＝P(o2) − P(o4)，ΔP＞0 判 1、ΔP＜0 判 0；兩個偵測器的極性不可接反。o1、o3、o5 為監看埠。",
        f"- EC 為 100 nm 薄矽尖端，配 {chip['ec_pitch_um']:g} µm 間距的 V-groove 光纖陣列（高數值孔徑光纖）。"
        "多專案投片不處理端面：晶片須研磨到尖端定寬段（端面往內 30 µm 內）。"
        f"最外側的 EC 離上下切割邊只有 {chip['ec_edge_min_um']:g} µm，切割崩邊與光纖陣列組裝時要留意。", "",
        "## 4　電氣介面", "",
        "- 每個 heater 一端接自己的訊號 PAD，另一端接地；相鄰兩個 heater 的地線接同一個 GND PAD（對應見 `pads.csv`）。",
        "- **各 GND PAD 在晶片上互不相連，每一個都要接到驅動器的地。**",
        f"- 每個 heater 相位 0–2π，P<sub>π</sub>≈{tol['P_pi_mW']:g} mW（同平台 TiN heater 的實測：B. Pant et al., Opt. Express 29(22), 36461 (2021)）；五個函數的 heater 總功率 {min(hp):.0f}–{max(hp):.0f} mW，"
        f"最壞情況 {tol['worst_case_total_mW']:g} mW。",
        f"- TiN 片電阻沒有公開值，heater 電阻需先量測。加熱條約 {chip['heater_squares']:.0f} 個方塊、TiN 厚 {chip['tin_thickness_um']:g} µm，"
        f"假設 0.5–2 kΩ 對應電阻率 {dens[0]['rho_tin_uohm_cm']:.0f}–{dens[2]['rho_tin_uohm_cm']:.0f} µΩ·cm。若為 1 kΩ，單個 heater 最大約 {dens[1]['I_heater_max_mA']} mA、{dens[1]['V_heater_max_V']} V，"
        f"走線電流密度約 {dens[1]['J_line_mA_um2']} mA/µm²（Ti/AL 厚 {chip['al_thickness_um']:g} µm、寬 {chip['wire_width_um']:g} µm）。"
        f"每條地線只帶自己 heater 的電流，兩條在 GND PAD 上會合；一個 GND PAD 最多約 {dens[1]['I_gnd_pad_worst_mA']:g} mA（兩個 heater 都接近 2π）。"
        "晶片上沒有共用的地線電阻；共用同一個 GND PAD 的兩個 heater 只經由 PAD、探針或打線的接觸電阻（約 1–2 Ω）互相影響，估計 < 0.2%，遠小於熱串擾。"
        "平台沒有公布 Ti/AL 的電流上限；以保守值 1 mA/µm² 比較，走線電流密度偏高，只適合實驗室短時間量測，量到 heater 電阻後要重算。", "",
        "## 5　操作與校正（需求 K1）", "",
        "`phases.json` 的相位是在理想元件下算出的起點；實際晶片的 MMI 損耗、分光偏差、各軌的固定相位差與熱串擾都會改變結果，必須校正：", "",
        "1. 接地：所有 GND PAD（GN1…、GS1…）都接到驅動器的地；量每個 Pn 到地的電阻，確認 14 個 heater 都導通，並依電阻重算電流與電流密度。",
        "2. 端面：研磨兩側端面，對準光纖陣列；只送一路光，用 5 個輸出的總功率估計耦合與傳播損耗。",
        "3. heater 標定：逐一掃描每個 heater 的功率（0 到約 2P<sub>π</sub>），由監看埠與判讀埠的週期變化求出各 heater 的 P<sub>π</sub> 與相位零點。"
        "θ_k 改變 MZI-k 的分光比，送一路光就看得到；φ_k 是 MZI-k 兩個輸入之間的相對相位，只有兩個輸入都有同源光時才看得到："
        "第 1 層的 MZI-1 用 x1＋x2、MZI-2 用 x4＋R，後面幾層先用已標定的前級把光分到兩個輸入。",
        "4. 重新求相位：以量到的 MMI 損耗與分光建立模型，以 `phases.json` 為起點重新找 14 個相位（使判讀 margin 最大）。",
        "5. 驗收：送入 5 路同源光，對每個函數跑 `truth_tables.csv` 的 16 組輸入，確認 ΔP 的正負全對，並記錄 margin。",
        "6. 在校正後的相位下重算 R 與輸入相位的容許範圍（`spec.json` 需求 O2、O3）。", "",
        "## 6　驗證結果", "",
        "| 項目 | 結果 |", "|---|---|",
        f"| DRC（平台 deck {drc_r['n_rules']} 條規則，設計區＝晶片尺寸） | 違規 {drc_r['total']}；GDS 99 {drc_r['n_gds99']} 個 |",
        f"| LVS（從 Ti/AL、TiN 抽出網路與原理圖比對） | {sum(r['ok'] for r in e['channels'])}/14 個 heater 一致，錯誤 {len(e['errors'])} |",
        f"| 光學連接 | {sum(r['ok'] for r in conn['optical']['ec'])}/10 個 EC 接到正確的核心埠 |",
        f"| 佈局審查（由佈局重算 U） | U 差 {rev['U_err_max']:.1e}，真值表 {rev['passed']}/80 |",
        f"| 電路模擬（PDK MMI 模型） | {sim['passed']}/{sim['total']}，U 差 {sim['U_err_max']:.1e} |",
        f"| 故障注入 | {sum(conn['faults'].values())}/{len(conn['faults'])} 種被抓到 |", "",
        "## 7　已知限制與風險", "",
        "- EC 為自建元件，耦合損耗待量測；端面需研磨。GDS 5 的 0.25 µm 窄條（等於最小線寬）與薄矽層的實際製程需向平台確認。",
        f"- 傳播與 MMI 損耗估計（不含 EC、跨越）：各軌 {min(t[0] for t in tot):.1f}–{max(t[1] for t in tot):.1f} dB"
        f"（波導約 {min(x['length_um'] for x in loss) / 1e4:.2f}–{max(x['length_um'] for x in loss) / 1e4:.2f} cm，以平台 strip 波導 "
        f"{chip['loss_db_cm'][0]:g}–{chip['loss_db_cm'][1]:g} dB/cm；每顆 MMI {chip['mmi_loss_db']:g} dB）。",
        f"- Ti/AL 走線跨越波導 {chip['n_crossings']} 次（部分在直段垂直穿越，部分斜穿 S 彎），每次的額外損耗沒有平台數據。",
        f"- MMI 實測損耗（每顆約 0.33 dB）已接近不校正時的容許上限 {sim['nonideal']['loss_range_ok'][1]:g} dB；必須依第 5 節校正。",
        "- 電流密度依賴未知的 TiN 片電阻；容許範圍為單項、理想元件下的評估。",
        "- 本交付只經平台 deck 的 DRC 與本課程的連接檢查，未經晶圓廠正式簽核。", "",
        "## 8　版本", "",
        f"- `chip.gds` SHA-256：`{sha(DEL / 'layout' / 'chip.gds')}`（與 `verification/drc_result.json`、`connectivity.json` 記錄的相同）",
        f"- 接線表 SHA-256：`{spec['source']['netlist_sha256']}`（`phases.json` 只對這份接線表有效）",
        "- 其他檔案的雜湊見 `MANIFEST.json`。", ""]
    (DEL / "README.md").write_text("\n".join(lines), encoding="utf-8")
    src["README.md"] = "m3_layout/s5_delivery"

    files = sorted(p for p in DEL.rglob("*") if p.is_file())
    manifest = dict(name="B7 單顆 PIC 交付包", files=[dict(path=p.relative_to(DEL).as_posix(), sha256=sha(p), bytes=p.stat().st_size,
                                                            source=src.get(p.relative_to(DEL).as_posix(), "")) for p in files])
    (DEL / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"寫出 delivery/：{len(files) + 1} 個檔案（含 MANIFEST.json），共 {sum(p.stat().st_size for p in files) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
