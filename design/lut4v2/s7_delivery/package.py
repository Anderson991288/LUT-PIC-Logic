r"""LUT4 s7：交付包——把佈局、介面、功能設定與驗證結果整理成一包，並附 SHA-256 清單。

用途：
  1. layout/：晶片 GDS（頂層 cell L4_CHIP）。
  2. interfaces/：pads.csv（PAD 名稱、座標、對應 heater、相位）、optical_ports.csv（EC 座標、訊號、用途）、spec.json。
  3. function/：接線表、相位設定、真值表、容許範圍。
  4. verification/：電路模擬、佈局審查、晶片 DRC、連接檢查（LVS、光學、故障注入）的結果。
  5. figures/：核心、晶片、繞線圖。
  6. README.md（操作、判讀、校正、限制）與 MANIFEST.json（每個檔案的 SHA-256 與大小）。
  7. check_delivery.py：交付檢查程式，放進交付包，MANIFEST 含它。
  交付前檢查：gate 的各項由 check_delivery.py 的固定集合判定（DRC 0、LVS、光學 10、故障注入固定清單、模擬 112、審查 V 清單、GDS 雜湊）；
  打包完成後再對整包跑 check_delivery.py --self-test（檔案清單、19 個 PAD、10 個 EC、由相位以光場 1−2x 重算 112 列、反向測試），通過才算交付。
輸入：LUT4 s1–s6 的 out/ 與 figures/lut4v2/。
輸出：專案根目錄 delivery_lut4v2/；本步 out/package.json、out/delivery_check.json。
執行：.\lab design\lut4v2\s7_delivery\package.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # design/
from common import runtime as rt                                     # noqa: E402
rt.setup(plot=False)

import csv                                                           # noqa: E402
import hashlib                                                       # noqa: E402
import json                                                          # noqa: E402
import os                                                            # noqa: E402
import shutil                                                        # noqa: E402
import subprocess                                                    # noqa: E402

import paths                                                         # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_delivery as CD                                          # noqa: E402

STEP = "lut4v2/s7_delivery"
DEL = paths.ROOT / "delivery_lut4v2"


def J(step, name):
    return json.loads(paths.OUT(step, name).read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEL.exists():
        shutil.rmtree(DEL)
    for d in ("layout", "interfaces", "function", "verification", "figures"):
        (DEL / d).mkdir(parents=True)
    cp = lambda step, name, d: shutil.copyfile(paths.OUT(step, name), DEL / d / name)
    cp("lut4v2/s5_chip", "chip.gds", "layout")
    (DEL / "layout" / "chip.gds").rename(DEL / "layout" / "LUT4_chip.gds")
    for n in ("lut4_netlist.json", "phases.json", "truth_tables.csv", "tolerance.json"):
        cp("lut4v2/s1_handoff", n, "function")
    # 規格：交接的介面規格再加上系統層級需求（LUT4 s9），R2 改用三路同時偏差的結果
    spec_d = J("lut4v2/s1_handoff", "spec.json")
    sysj = J("lut4v2/s9_system", "system.json")
    gb, gr, conn0 = J("lut4v2/s9_system", "gain_box.json"), J("lut4v2/s9_system", "gain_robust.json"), J("lut4v2/s6_verify", "connectivity.json")
    fs, lib = gb["functions"], gb["library"]
    w7 = min((k for k in fs if k != "0x0069"), key=lambda k: fs[k]["eps"])
    hard = sysj["tia_hard"]["0x0069"]["mc"]
    re_min = min(v["resolved_pass"] for g in ("0x0069", "XOR4") for v in gr[g]["remeasure"].values())
    # 2026-11-07：R2 改為觀察性敘述，統計成功率與確定性容差分開；數字都由 JSON 帶入
    for r in spec_d["requirements"]:
        if r["id"] == "R2":
            r["value"] = ("觀察性敘述，不是全部真值表的通用規格：結果限於指定函數、樣本數與模型（每顆 MZI 0.9 dB、R＝3、相位固定、只有三路增益誤差）。"
                          "三路（PD＋TIA）增益由出廠修整調整；任一真值表的容許量須依其相位以 gain_box.py 逐表計算。")
            r["statistical"] = (f"統計成功率：三路增益各 N(1, σ²)，各 σ 抽 2,000 次（種子 900）。七個範例函數全對的最大 σ 為 {sysj['tia_sigma_ok'] * 100:g}%；"
                                f"0x0069 在 σ＝1%、3%、5% 時全對 {hard['0.01'] * 100:.1f}%、{hard['0.03'] * 100:.1f}%、{hard['0.05'] * 100:.1f}%。"
                                f"量測增益後重求相位（0x0069、XOR4；σ＝2%、3%、5% 各 100 次，假設量測無誤差）全對比例最低 {re_min * 100:.0f}%。"
                                "這些是指定樣本下的成功率；常態分布的標準差不是最大誤差界。")
            r["deterministic"] = (f"確定性增益盒：三路增益各在 [1−ε, 1+ε] 內任何組合下 16 組全對的最大 ε（標稱相位；目標 0 用線性規劃）。"
                                  f"七個範例最小 {fs[w7]['eps_pct']:.2f}%（{w7}）；0x0069 {fs['0x0069']['eps_pct']:.2f}%；"
                                  f"全表相位庫逐表最小 {lib['eps_min_pct']:.2f}%（{lib['mask']}），見 verification/gain_box.json。")
            r["verify"] = "LUT4 s9：system.py、gain_robust.py、gain_box.py（模型值）"
    gn = conn0["electrical"]["gnd_network"]
    g1 = gn["by_R_heater_kohm"]["1"]
    if gn["shared_gnd_pairs"]:
        loop = (f"heater 1 kΩ、2π 時：單路驅動相位不足最差 {g1['single']['max_rad']:.3f} rad（單路校正可吸收）；14 路同時最差 {g1['multi']['max_rad']:.3f} rad；"
                f"單路校正後殘差最差 {g1['single_cal_residual']['max_rad']:.3f} rad，隨同組其他 heater 改變，單路校正吸收不了；"
                f"跨通道聯合校正在模型內可消除，所需電壓約增 {g1['joint_cal']['v_increase_vs_ideal_max_pct']:.1f}%，須由量測取得傳輸矩陣")
    else:
        loop = (f"heater 1 kΩ、2π 時：相位不足最差 {g1['single']['max_rad']:.3f} rad，單路與 14 路同時相同（地線只在 GND PAD 會合）；"
                "單路校正後殘差為 0。前提是 PAD 等電位、片外地阻抗為零")
    spec_d["requirements"] += [
        dict(id="S1", item="輸入相位穩定", value="五路輸入相干、同一偏振（TE）；相對相位誤差 σ ≤ 0.02 rad（XOR4），需片外相位鎖定或追蹤", verify="量測"),
        dict(id="S2", item="雷射波長", value=f"±{sysj['dlambda_tol_nm']['XOR4']:g} nm（XOR4；模型只含各軌固定路徑差）", verify="LUT4 s9"),
        dict(id="S3", item="晶片溫度", value=f"±{sysj['dT_tol_K']['XOR4']:g} K（XOR4；同上）；需溫控", verify="LUT4 s9"),
        dict(id="S4", item="二相位調變的 π 誤差", value=f"≤ {sysj['dphi_max_deg']}°（位元 1 的光場為 −E·e^(iδ)）", verify="LUT4 s9"),
        dict(id="S5", item="光功率（靜態讀取 1 MHz）", value=f"每根資料光纖約 {sysj['budget']['cases']['1 MHz']['XOR4']['per_data_fiber_dBm']:+.0f} dBm（假設見 system_requirements.json）", verify="LUT4 s9"),
        dict(id="S6", item="heater 回路壓降", value=loop, verify="LUT4 s6 節點分析 gnd_net.py（模型值，不是寄生萃取或量測）"),
    ]
    (DEL / "interfaces" / "spec.json").write_text(json.dumps(spec_d, ensure_ascii=False, indent=2), encoding="utf-8")
    (DEL / "interfaces" / "system_requirements.json").write_text(json.dumps(dict(
        tia_sigma_ok=sysj["tia_sigma_ok"], dlambda_tol_nm=sysj["dlambda_tol_nm"], dT_tol_K=sysj["dT_tol_K"], dphi_max_deg=sysj["dphi_max_deg"],
        tia_sigma_ok_scope="七個範例函數、各 σ 2,000 次全對的最大 σ；統計觀察，不是通用規格；確定性 ε 見 verification/gain_box.json",
        budget=sysj["budget"], route=sysj["route"]), ensure_ascii=False, indent=1), encoding="utf-8")
    for st, n in (("lut4v2/s2_sim", "sim_results.json"), ("lut4v2/s4_review", "review_checks.json"),
                  ("lut4v2/s6_verify", "drc_result.json"), ("lut4v2/s6_verify", "connectivity.json"),
                  ("lut4v2/s6_verify", "gnd_segments.json"), ("lut4v2/s9_system", "gain_box.json"), ("lut4v2/s9_system", "gain_robust.json")):
        cp(st, n, "verification")
    for f in ("s1_core.png", "s3_chip.png", "s3_route.png", "s3_ec.png"):
        shutil.copyfile(paths.FIG("lut4v2", f), DEL / "figures" / f)
    shutil.copyfile(Path(__file__).resolve().parent / "check_delivery.py", DEL / "check_delivery.py")

    spec, chip = J("lut4v2/s1_handoff", "spec.json"), J("lut4v2/s5_chip", "chip_info.json")
    ph, tol = J("lut4v2/s1_handoff", "phases.json"), J("lut4v2/s1_handoff", "tolerance.json")
    sim, rev = J("lut4v2/s2_sim", "sim_results.json"), J("lut4v2/s4_review", "review_checks.json")
    drc_r, conn = J("lut4v2/s6_verify", "drc_result.json"), J("lut4v2/s6_verify", "connectivity.json")
    ch = {c["heater"]: c for c in spec["phase_channels"]}
    with open(DEL / "interfaces" / "pads.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["pad", "side", "x_um", "y_um", "kind", "heater", "mzi", "phase", "heaters_on_gnd"])
        for p in chip["pads"]:
            c = ch.get(p["heater"]) if p["heater"] else None
            w.writerow([p["name"], p["side"], p["xy_um"][0], p["xy_um"][1], "訊號" if c else "GND",
                        p["heater"] or "", c["mzi"] if c else "", c["phase"] if c else "", "" if c else "＋".join(sorted(p["heaters"]))])
    sp = {o["port"]: o for o in spec["optical_ports"]}
    with open(DEL / "interfaces" / "optical_ports.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["port", "signal", "edge", "facet_x_um", "facet_y_um", "use"])
        for e in chip["ec"]:
            w.writerow([e["port"], e["signal"], e["side"], e["facet_um"][0], e["facet_um"][1], sp[e["port"]]["note"]])

    chip_sha = sha(DEL / "layout" / "LUT4_chip.gds")
    # Calibre 的敘述依 s8 的實際狀態寫：只有 commercial.json 對應本次 GDS 且既有證據適用時才引用數字，否則寫未驗證
    com_p = paths.STEP("lut4v2/s8_commercial") / "out" / "commercial.json"
    com = json.loads(com_p.read_text(encoding="utf-8")) if com_p.exists() else {}
    ev = com.get("evidence") or {}
    if com.get("chip_sha256") == chip_sha and ev.get("applies"):
        cal_line = (f"Calibre 規則草案（只移植線寬、間距 {com['ported']} 條）{com['calibre']['chip']['total']}"
                    "（既有證據：本次未執行 Calibre；本次 GDS 與該次執行的 GDS 逐層幾何相同）")
    elif com.get("chip_sha256") == chip_sha and com.get("calibre") and not com.get("evidence"):
        cal_line = (f"Calibre 規則草案（只移植線寬、間距 {com['ported']} 條，不是平台簽核）對本次 GDS 實跑 "
                    f"{com['calibre']['chip']['total']}（{com['status']['calibre_basic_svrf_draft']['status']}）")
    else:
        cal_line = "Calibre 規則草案：未驗證（本次未執行 Calibre）"
    # 2026-11-07：gate 一律由 check_delivery 的固定集合判定，不再只比 passed＝total、空集合為真或信任 faults_caught
    ok = lambda fn: CD.guarded(fn, DEL)[0] is True
    gate = dict(drc=ok(CD.k9_drc), lvs=ok(CD.k10_lvs),
                gds_sha=ok(CD.k6_layout) and rev["gds_sha256"] == sha(paths.OUT("lut4v2/s3_core", "l4_core.gds")),   # 驗證結果必須對應交付的這一份 GDS
                optical=ok(CD.k11_optical), faults=ok(CD.k12_faults), sim=ok(CD.k14_sim), review=ok(CD.k13_review))
    fl = "、".join(f"{n}（{f['truth_hex']}，裕量 {f['margin']:.3f} P_u）" for n, f in ph["functions"].items())
    # 2026-11-07：驗證句的數字一律由本次結果檔取得，不寫死
    chans, ecs = conn["electrical"]["channels"], conn["optical"]["ec"]
    verify_line = (f"- 電路模擬（PDK MMI 確認 U；判讀用每顆 MMI 0.45 dB 模型）：{sim['passed']}/{sim['total']}；"
                   f"佈局審查 V1–V11 {'通過' if gate['review'] else '未通過'}；DRC 違規 {drc_r['total']}；"
                   f"LVS {sum(c['ok'] for c in chans)}/{len(chans)}；光學 {sum(e['ok'] for e in ecs)}/{len(ecs)}；"
                   f"故障注入{'全部抓到' if gate['faults'] else '有未抓到項目'}。")
    check_line = (f"- 收件者可執行 `python check_delivery.py` 重新核對：檔案清單與雜湊、{len(CD.ALL_PADS)} 個 PAD、{len(CD.EC_SIGNAL)} 個 EC，"
                  f"以及由 `function/phases.json` 重算的 {len(CD.TT_KEYS)} 列真值表（光場 1−2x）。DRC、LVS、光學、故障注入、佈局審查與電路模擬僅核對結果檔的紀錄，不重新執行。")
    lines = [
        "# Programmable Silicon Photonic 4-input LUT Design：交付包（Model-7a）", "",
        "Model-7a：7 顆 MZI 組合的 a 版（拓樸代碼 3142132：由輸入往輸出，數字 k 表示一顆混合第 k、k＋1 條波導的 MZI）。", "",
        "以 7 顆熱調 MZI 組成的 4 輸入可程式化光邏輯晶片。接收端固定：三組 PD＋TIA、兩個門檻 0 的比較器、一個 AND。",
        "換邏輯功能只改 14 個 heater 相位。", "",
        "## 1. 晶片", "",
        f"- 尺寸 {chip['die_um'][0]:g} × {chip['die_um'][1]:g} µm；頂層 cell `L4_CHIP`；平台 CORNERSTONE SOI 220 nm（被動）。",
        f"- 光學：10 個邊緣耦合器（西緣 5 入、東緣 5 出），間距 {chip['ec_pitch_um']:g} µm。",
        f"- 電氣：{chip['n_pads']} 個 PAD（訊號 14、GND {chip['n_gnd_pads']}；地端在核心內連成 {len(chip['gnd_groups'])} 組共用地網，每組一條地線），都在上下緣最外圍。", "",
        "## 2. 輸入", "",
        "- x1–x4：資料光 E+／E−（二相位，位元 0＝+E、1＝−E，每路功率恆為 P_u），R：參考光，振幅 3（功率 9 P_u），與位元 0 同相；5 路來自同一顆雷射，相對相位固定。",
        f"- R 容許範圍 {tol['R_range_all'][0]:g}–{tol['R_range_all'][1]:g}（所附範例函數）。", "",
        "## 3. 判讀", "",
        "- 比較器 A：P(o2) ＞ P(o4)；比較器 B：P(o4) ＞ P(o3)；輸出 y＝A AND B。門檻都是 0，不需參考電壓。",
        "- o1、o5 為監看埠（總功率核對、校正）。", "",
        "## 4. 範例函數", "", f"- {fl}。", "- 相位見 `function/phases.json`（θ_k、φ_k 依 MZI-1…MZI-7，rad；每顆 MZI 0.9 dB 損耗模型）。", "",
        "## 5. 驗證", "",
        verify_line, check_line, "",
        "## 6. 校正與限制", "",
        "- 相位是模型值。晶片完成後依量測（MMI 損耗與分光、heater P_π、各軌固定相位差）重新求 14 個相位。",
        ("- 三路（PD＋TIA）增益由出廠修整調整。容許量依函數而定，以下是指定函數與模型下的觀察，不是全部真值表的規格（見 `interfaces/spec.json` 的 R2）："
         f"確定性增益盒 ε：七個範例最小 {fs[w7]['eps_pct']:.2f}%（{w7}）、0x0069 {fs['0x0069']['eps_pct']:.2f}%、全表相位庫逐表最小 {lib['eps_min_pct']:.2f}%（{lib['mask']}）；"
         f"統計成功率另列於 R2。"),
        f"- heater 回路（模型值，見 `interfaces/spec.json` 的 S6）：{loop}。",
        "- 系統需求見 `interfaces/spec.json` 的 S1–S6：五路輸入相位穩定（需片外相位鎖定或追蹤）、雷射波長、晶片溫度、二相位調變的 π 誤差、光功率、heater 回路壓降。",
        "- 未完成：輸入相位穩定方案、只用 o1–o5 量測的參數辨識與熱串擾校正、完整雜訊預算、打線／探針／ESD、電遷移上限比對。",
        f"- DRC 以 KLayout 與平台被動規則檔執行（{drc_r['total']}）；{cal_line}。由 Virtuoso 匯出 GDS 時請指定 maxVertices 8191。",
        "- 晶圓廠驗證過的 Calibre 規則檔、熱串擾模擬、雜訊預算尚未完成。", "",
        "## 7. 檔案", "",
        f"- `layout/LUT4_chip.gds` SHA-256：`{chip_sha}`（與 `verification/drc_result.json`、`connectivity.json` 記錄的相同）。",
        f"- 接線表 `function/lut4_netlist.json` SHA-256：`{spec['source']['netlist_sha256']}`（`phases.json` 只對這份接線表有效）。",
        "- 其他檔案的雜湊見 `MANIFEST.json`。",
        "- 交付檢查：`python check_delivery.py`（只需 numpy）；加 `--self-test` 另跑注入錯誤的反向測試。",
    ]
    (DEL / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    files = sorted(p for p in DEL.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    man = dict(name="Programmable Silicon Photonic 4-input LUT Design：交付包（Model-7a）", gate=gate,
               files=[dict(path=p.relative_to(DEL).as_posix(), sha256=sha(p), bytes=p.stat().st_size) for p in files])

    def write_manifest():
        (DEL / "MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")

    # 交付檢查：對打包好的這一包跑全部固定集合與反向測試，跑過才算通過。檢查含 MANIFEST 的 gate，所以先寫 true，沒過再改回 false
    gate["delivery_check"] = True
    write_manifest()
    run = subprocess.run([sys.executable, str(DEL / "check_delivery.py"), str(DEL), "--self-test", "--out", str(paths.OUT(STEP, "delivery_check.json"))],
                         capture_output=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    print(run.stdout.strip().splitlines()[-2:] if run.stdout.strip() else run.stderr[-400:])
    gate["delivery_check"] = run.returncode == 0
    if not gate["delivery_check"]:
        print(run.stdout[-3000:], run.stderr[-1000:])
        write_manifest()
    out = dict(n_files=len(files) + 1, gate=gate, all_pass=all(gate.values()),
               bytes=sum(p.stat().st_size for p in files))
    paths.OUT(STEP, "package.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)
    sys.exit(0 if out["all_pass"] else 1)


if __name__ == "__main__":
    main()
