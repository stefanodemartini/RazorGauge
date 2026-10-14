using System.Collections.Generic;
using System.Linq;

namespace DiametroLineaDesktop.Models;

/// <summary>
/// One core the supplier actually stocks: a material, a breaking strain and the diameter it comes
/// in. The supplier quotes a range rather than a figure, so both ends are kept and
/// <see cref="NominalMm"/> is their midpoint — that is what gets drawn and stored, while the range
/// stays visible in the picker so the tolerance is never lost behind a single number.
/// </summary>
/// <param name="MaxMm">
/// Top of the supplier's range. Equal to <paramref name="MinMm"/> when a single figure was quoted,
/// and null only when the supplier gave a floor and no figure at all — the two are not the same
/// thing and must not print the same way.
/// </param>
public sealed record CoreSpec(string Material, int PoundTest, double MinMm, double? MaxMm)
{
    /// <summary>The figure used for drawing and for the file. Midpoint of the range, the quoted
    /// figure when there is one, or the floor when that is all there is.</summary>
    public double NominalMm => MaxMm is double max ? (MinMm + max) / 2.0 : MinMm;

    public string RangeText => MaxMm is double max
        ? (max > MinMm ? $"{MinMm:0.00}–{max:0.00} mm" : $"{MinMm:0.00} mm")
        : $"≥ {MinMm:0.00} mm";

    /// <summary>What the picker shows and what is stored in the .flp as CoreType.</summary>
    public string Label => $"{Material} {PoundTest} lb — {RangeText}";
}

public static class CoreCatalog
{
    /// <summary>
    /// Supplier specifications, October 2026. Ordered by material then breaking strain.
    ///
    /// Kevlar was quoted only as "above 0.90" for both strains, so its diameter is a floor and not
    /// a range: NominalMm is that floor, which is the smallest it can be rather than the likeliest
    /// it is. Worth replacing with real figures before trusting a Kevlar core drawn to scale.
    /// </summary>
    public static readonly IReadOnlyList<CoreSpec> All = new[]
    {
        new CoreSpec("Polyester", 12, 0.55, 0.60),
        new CoreSpec("Polyester", 17, 0.65, 0.72),
        new CoreSpec("Polyester", 20, 0.82, 0.87),
        new CoreSpec("Polyester", 25, 0.90, 0.95),
        new CoreSpec("Polyester", 30, 1.00, 1.05),
        new CoreSpec("Polyester", 35, 1.15, 1.15),   // a single quoted figure, not a floor
        new CoreSpec("Kevlar",    60, 0.90, null),
        new CoreSpec("Kevlar",    80, 0.90, null),
    };

    /// <summary>
    /// Generic descriptions kept from before the catalogue existed: they carry no diameter, so a
    /// project using one still opens and still prints, it just draws no core.
    /// </summary>
    public static readonly IReadOnlyList<string> GenericTypes = new[]
    {
        "Braided multifilament nylon",
        "Braided monofilament nylon",
        "Monofilament nylon (single strand)",
        "GSP braid (Spectra / Dyneema)",
        "Polyester (Dacron) braid",
        "Kevlar / aramid braid",
        "Coreless / PU monocore",
    };

    /// <summary>Everything the picker offers, catalogue first.</summary>
    public static IReadOnlyList<string> PickerItems { get; } =
        All.Select(c => c.Label).Concat(GenericTypes).ToList();

    /// <summary>The catalogue entry a stored CoreType names, or null for a generic or hand-typed
    /// one — in which case the diameter is whatever the project itself recorded.</summary>
    public static CoreSpec? Find(string? coreType) =>
        string.IsNullOrWhiteSpace(coreType)
            ? null
            : All.FirstOrDefault(c => c.Label == coreType.Trim());
}
