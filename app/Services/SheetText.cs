using System.Globalization;

namespace DiametroLineaDesktop.Services;

/// <summary>Language of the design sheet (the PDF only — the app itself stays in English).</summary>
public enum SheetLanguage { English, Chinese, Bilingual }

/// <summary>
/// The design sheet's fixed wording in English and Simplified Chinese. Keyed by the English
/// text itself, so every call site still reads as English. A key missing from the table prints
/// in English — never blank — and <see cref="Missing"/> lists such keys for a check.
/// Translations are a first draft: the trade's own Chinese terms should be confirmed with the
/// producer before relying on them.
/// </summary>
public static class SheetText
{
    public static SheetLanguage Parse(string? code) => code switch
    {
        "zh"    => SheetLanguage.Chinese,
        "en+zh" => SheetLanguage.Bilingual,
        _       => SheetLanguage.English,
    };

    public static string Code(SheetLanguage l) => l switch
    {
        SheetLanguage.Chinese   => "zh",
        SheetLanguage.Bilingual => "en+zh",
        _                       => "en",
    };

    /// <summary>A block of text: bilingual puts the Chinese on its own line under the English.</summary>
    public static string T(SheetLanguage lang, string en, params object[] args) => Render(lang, en, args, "\n");

    /// <summary>A short inline value (a table cell): bilingual keeps both on one line.</summary>
    public static string Ti(SheetLanguage lang, string en, params object[] args) => Render(lang, en, args, " / ");

    public static readonly HashSet<string> Missing = new();

    /// <summary>The compensation note under the chart — uniform target speed, or per-zone materials.</summary>
    public static string CompNote(SheetLanguage lang, double? uniformSinkIns) => uniformSinkIns is double v
        ? T(lang, "Compensated profile — target sink {0} in/s. Diameters are mass-preserving compensated values. Manufacture each section at the exact density shown.", $"{v:0.00}")
        : T(lang, "Multi-material design — each zone uses its own material. Diameters are mass-preserving values. Manufacture each section at the exact density shown.");

    private static string Render(SheetLanguage lang, string en, object[] args, string sep)
    {
        string F(string s) => args.Length > 0 ? string.Format(CultureInfo.InvariantCulture, s, args) : s;
        if (lang == SheetLanguage.English) return F(en);
        if (!Zh.TryGetValue(en, out var zh)) { Missing.Add(en); return F(en); }
        return lang == SheetLanguage.Chinese ? F(zh) : F(en) + sep + F(zh);
    }

    private static readonly Dictionary<string, string> Zh = new()
    {
        // ── heading, notes ─────────────────────────────────────────────────
        ["This document and its contents are the property of the designer. All dimensions are confidential and must not be disclosed without written consent."]
            = "本文件及其内容归设计者所有。所有尺寸均属机密，未经书面同意不得泄露。",
        ["Compensated profile"] = "补偿轮廓",
        ["Original profile"]    = "原始轮廓",
        ["Floating"] = "浮水",
        ["Neutral"]  = "中性",
        ["Sinking"]  = "沉水",
        ["Full Line"]     = "全长线",
        ["Shooting Head"] = "射头",
        ["Salt water"]    = "海水",
        ["Fresh water"]   = "淡水",
        ["All dimensions are in millimeters. Diameters shown are compensated values."]
            = "所有尺寸单位均为毫米。所示直径为补偿后的数值。",
        ["Compensated profile — uniform sink speed {0} in/s. Density varies along the line ({1}) — each zone must be produced at the exact specified density."]
            = "补偿轮廓 — 均匀下沉速度 {0} in/s。密度沿线变化（{1}）— 每一段必须严格按规定密度生产。",
        ["Multi-material profile — each zone sinks at its own speed (see table). Density varies along the line ({0}) — each zone must be produced at the exact specified density."]
            = "多材料轮廓 — 每一段以各自的速度下沉（见表）。密度沿线变化（{0}）— 每一段必须严格按规定密度生产。",
        ["Compensated profile. Density varies along the line ({0})."]
            = "补偿轮廓。密度沿线变化（{0}）。",
        ["Do not alter diameters. Each section must be manufactured at the exact density shown — the density is calculated and fixed."]
            = "请勿更改直径。每一段必须按所示密度精确生产 — 密度为计算所得的固定值。",
        ["All dimensions are in millimeters, unless otherwise indicated."]
            = "除非另有说明，所有尺寸单位均为毫米。",
        ["With diameters indicated and target weight the density of the line is {0}."]
            = "按所示直径和目标重量，线的密度为 {0}。",
        ["Line density: {0}."] = "线密度：{0}。",
        ["Do not change length and diameters of segments."] = "请勿更改各段的长度和直径。",
        ["Compensated profile — target sink {0} in/s. Diameters are mass-preserving compensated values. Manufacture each section at the exact density shown."]
            = "补偿轮廓 — 目标下沉速度 {0} in/s。直径为保持质量不变的补偿值。每一段须按所示密度精确生产。",
        ["Multi-material design — each zone uses its own material. Diameters are mass-preserving values. Manufacture each section at the exact density shown."]
            = "多材料设计 — 每一段使用各自的材料。直径为保持质量不变的数值。每一段须按所示密度精确生产。",

        // ── spec line ──────────────────────────────────────────────────────
        ["Type"]         = "类型",
        ["Format"]       = "形式",
        ["Density"]      = "密度",
        ["Total length"] = "总长度",
        ["Head length"]  = "线头长度",
        ["Head weight"]  = "线头重量",
        ["Total weight"] = "总重量",
        ["CoM (head)"]   = "重心（线头）",
        ["Character"]    = "特性",
        ["Target sink"]  = "目标下沉速度",
        ["Water"]        = "水域",
        ["Warning"]      = "警告",
        ["(per zone)"] = "（分段）",
        ["Compensated — uniform sink"]     = "补偿 — 均匀下沉",
        ["Multi-material — per-zone sink"] = "多材料 — 分段下沉",
        ["⚠ sections at ρ min (0.94)"]     = "⚠ 部分段处于最低密度 (0.94)",
        ["Front-loaded · power"]   = "前重 · 力量型",
        ["Semi front-loaded"]      = "偏前重",
        ["Neutral · all-round"]    = "中性 · 全能型",
        ["Semi rear-loaded"]       = "偏后重",
        ["Rear-loaded · distance"] = "后重 · 远投型",

        // ── SHAPE / NOZZLES / COLOR summary and legend ─────────────────────
        ["SHAPE"]             = "形状",
        ["NOZZLES · DENSITY"] = "喷嘴 · 密度",
        ["COLOR"]             = "颜色",
        ["{0} taper sections (S). Slope changes drawn as solid lines."]
            = "{0} 个锥度段 (S)。坡度变化以实线表示。",
        ["One nozzle (M1) over the whole line — single density."]
            = "全线一个喷嘴 (M1) — 单一密度。",
        ["{0} nozzles ({1}), {2} linear density transitions of {3} cm. Boundaries drawn dashed."]
            = "{0} 个喷嘴（{1}），{2} 处 {3} cm 线性密度过渡。边界以虚线表示。",
        ["{0} nozzles ({1}), no transitions. Boundaries drawn dashed."]
            = "{0} 个喷嘴（{1}），无过渡。边界以虚线表示。",
        ["{0} over the whole line — the nozzles differ in density only."]
            = "全线颜色 {0} — 各喷嘴仅密度不同。",
        ["{0} over the whole line."] = "全线颜色 {0}。",
        ["slope change (taper S)"]     = "坡度变化（锥度段 S）",
        ["nozzle change (density M)"]  = "喷嘴变化（密度 M）",
        ["linear density transition"]  = "线性密度过渡",
        ["the profile is drawn in the real line color only"] = "轮廓仅以线的实际颜色绘制",

        // ── cards, notes ───────────────────────────────────────────────────
        ["Materials"] = "材料",
        ["Nozzles — each nozzle is one compound: density + color"] = "喷嘴 — 每个喷嘴对应一种配料：密度 + 颜色",
        ["color"] = "颜色",
        ["Core"]      = "芯线",
        ["full line"] = "全线",
        ["Compensated profile:"] = "补偿轮廓：",
        ["Density zones"] = "密度区段",
        ["Laser mark:"]   = "激光标记：",
        ["Note"]          = "备注",

        // ── tables ─────────────────────────────────────────────────────────
        ["1 · TAPER — shape only (no density here)"] = "1 · 锥度段 — 仅形状（此处不含密度）",
        ["2 · NOZZLES — material along the line (the shape is in table 1)"] = "2 · 喷嘴 — 沿线材料（形状见表 1）",
        ["Taper"]    = "锥度段",
        ["Start"]    = "起点",
        ["End"]      = "终点",
        ["Length"]   = "长度",
        ["Len"]      = "长度",
        ["Ø start"]  = "Ø 起点",
        ["Ø end"]    = "Ø 终点",
        ["Slope"]    = "坡度",
        ["Section"]  = "部位",
        ["HEAD"]     = "线头",
        ["RUN"]      = "后导线",
        ["Nozzle"]   = "喷嘴",
        ["From"]     = "起点",
        ["To"]       = "终点",
        ["Kind"]     = "类别",
        ["Color"]    = "颜色",
        ["Mass"]     = "质量",
        ["Sink"]     = "下沉",
        ["linear transition"] = "线性过渡",
        ["full material"]     = "纯材料",
        ["TOTAL"]    = "合计",
        ["Name"]     = "名称",
        ["ρ avg"]    = "ρ 平均",
        ["OK"]       = "合格",
        ["⚠ ρ min"]  = "⚠ ρ 最低",

        // ── footer ─────────────────────────────────────────────────────────
        ["Head:"]    = "线头：",
        ["Total:"]   = "总计：",
        ["Confidential"] = "机密",
        ["Generated by RazorGauge"] = "由 RazorGauge 生成",

        // ── chart ──────────────────────────────────────────────────────────
        ["Length (cm)"]   = "长度 (cm)",
        ["Diameter (mm)"] = "直径 (mm)",
        ["TAPER"]   = "锥度段",
        ["NOZZLE"]  = "喷嘴",
        ["DENSITY"] = "密度",
    };
}
