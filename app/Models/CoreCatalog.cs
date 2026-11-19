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
/// <param name="GramsPerMeter">
/// Linear mass of the bare core quoted by the supplier (g/m), null where none was given. With the
/// diameter it gives the core's apparent density, air in the braid included.
/// </param>
/// <param name="Estimated">
/// True when diameter and g/m were deduced from the other cores rather than quoted for this one.
/// </param>
public sealed record CoreSpec(string Material, int PoundTest, double MinMm, double? MaxMm,
                              double? GramsPerMeter = null, bool Estimated = false)
{
    /// <summary>The figure used for drawing and for the file. Midpoint of the range, the quoted
    /// figure when there is one, or the floor when that is all there is.</summary>
    public double NominalMm => MaxMm is double max ? (MinMm + max) / 2.0 : MinMm;

    public string RangeText => MaxMm is double max
        ? (max > MinMm ? $"{MinMm:0.00}–{max:0.00} mm" : $"{MinMm:0.00} mm")
        : $"≥ {MinMm:0.00} mm";

    /// <summary>Apparent density of the core (g/cm³): g/m over the nominal cross-section in mm²,
    /// which is numerically g/cm³. Null when the supplier gave no linear mass.</summary>
    public double? DensityGCm3 => GramsPerMeter is double g
        ? g / (System.Math.PI / 4.0 * NominalMm * NominalMm)
        : null;

    /// <summary>"Polyester 17 lb" — the part of the label that does not change when the supplier's
    /// figures do, used to recognise labels saved by older catalogues.</summary>
    public string Key => $"{Material} {PoundTest} lb";

    /// <summary>What the picker shows and what is stored in the .flp as CoreType.</summary>
    public string Label => $"{Key} — {RangeText}";
}

public static class CoreCatalog
{
    /// <summary>
    /// Supplier specifications, October 2026. Ordered by material then breaking strain.
    ///
    /// 19/11/2026: for 17, 20 and 25 lb the supplier sent one diameter with the weight of a metre
    /// (0.72 mm 0.43 g, 0.82 mm 0.57 g, 0.90 mm 0.61 g). Those pairs are taken as the spec and
    /// replace the old ranges (17 lb was 0.65–0.72, 20 lb 0.82–0.87, 25 lb 0.90–0.95): a range that
    /// wide moved the 17 lb core's density from 1.06 to 1.30. The fourth pair (0.95 mm 0.80 g)
    /// was first left unmatched.
    ///
    /// Deduced the same day, since the supplier cannot be asked again. The three known cores carry
    /// 35–41 lb per g/m (mean 38.5) and have apparent density 0.96–1.08 (mean 1.03).
    ///   - 0.80 g/m as 25 lb would be 31 lb per g/m, out of line; as 30 lb it is 37.5, in line.
    ///     At density 1.03 it measures 0.99 mm, the bottom of the old 30 lb range, so 30 lb =
    ///     1.00 mm 0.80 g/m (density 1.02). The "0.95" the supplier paired with it is the top of
    ///     the 25 lb range, not a 30 lb figure.
    ///   - 12 lb (no data): 0.60 mm, the top of its range, at the mean density 1.03 ⇒ 0.29 g/m,
    ///     i.e. 41 lb per g/m, inside the 35–41 the others show. A first guess of 0.31 g/m (from
    ///     12 / 38.5) gave density 1.10, denser than the 17 lb, which Stefano rightly rejected: a
    ///     thinner braid of the same yarn has no reason to pack tighter. Marked Estimated.
    ///
    /// Kevlar was quoted only as "above 0.90" for both strains, so its diameter is a floor and not
    /// a range: NominalMm is that floor, which is the smallest it can be rather than the likeliest
    /// it is. Worth replacing with real figures before trusting a Kevlar core drawn to scale.
    /// </summary>
    public static readonly IReadOnlyList<CoreSpec> All = new[]
    {
        new CoreSpec("Polyester", 12, 0.60, 0.60, 0.29, Estimated: true),
        new CoreSpec("Polyester", 17, 0.72, 0.72, 0.43),
        new CoreSpec("Polyester", 20, 0.82, 0.82, 0.57),
        new CoreSpec("Polyester", 25, 0.90, 0.90, 0.61),
        new CoreSpec("Polyester", 30, 1.00, 1.00, 0.80),
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
    /// one — in which case the diameter is whatever the project itself recorded. A label saved by
    /// an older catalogue ("Polyester 17 lb — 0.65–0.72 mm") still finds its entry by material and
    /// strain.</summary>
    public static CoreSpec? Find(string? coreType)
    {
        if (string.IsNullOrWhiteSpace(coreType)) return null;
        var t = coreType.Trim();
        return All.FirstOrDefault(c => c.Label == t)
            ?? All.FirstOrDefault(c => t.StartsWith(c.Key + " ", System.StringComparison.Ordinal));
    }
}
