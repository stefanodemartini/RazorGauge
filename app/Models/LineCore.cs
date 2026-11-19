using System;
using System.Collections.Generic;
using System.Linq;

namespace DiametroLineaDesktop.Models;

/// <summary>
/// The core of a line as the physics sees it: an envelope of diameter <see cref="DiameterMm"/>
/// whose apparent density <see cref="DensityGCm3"/> includes the air in the braid.
/// </summary>
public readonly record struct CoreModel(double DiameterMm, double DensityGCm3);

/// <summary>
/// Core + coating model (19/11/2026, Stefano's decision: "compound per tutti").
///
/// Every density the app stores or edits — nozzles M1–M4, the shared density, a segment's Sp. W.,
/// a C file's per-slice values — is the density of the <b>compound</b> (what the nozzle extrudes).
/// The line itself is core + coating, so a section of outer diameter D has
///
///   ρ_eff(D) = ρ_coat + (ρ_core − ρ_coat) · (d_core / D)²
///
/// The coating does not penetrate the braid (Stefano's acetone + loop test), so the core is its
/// whole envelope d_core, air included, and the coating is the ring A(D) − A(d_core).
///
/// The physics primitives (SinkingSpeedCalc, the mass helpers) read <see cref="Current"/>, the core
/// of the line being computed: the app sets it when a project is loaded or its core changes, the
/// CLI after loading. Null means no core is known (no diameter, or no density for it) and every
/// formula falls back exactly to the old homogeneous one.
/// </summary>
public static class LineCore
{
    /// <summary>The core of the line currently being computed, or null.</summary>
    public static CoreModel? Current { get; set; }

    /// <summary>Area of a circle of diameter d (mm) in mm².</summary>
    private static double AreaMm2(double dMm) => Math.PI / 4.0 * dMm * dMm;

    /// <summary>
    /// The core of a project: its diameter, and its density — the file's own if it has one, else
    /// the catalogue entry its CoreType names. Null if either is missing.
    /// </summary>
    public static CoreModel? FromProject(FlyLineProject p)
    {
        double? d = p.CoreDiameterMm ?? CoreCatalog.Find(p.CoreType)?.NominalMm;
        double? rho = p.CoreDensityGCm3 ?? CoreCatalog.Find(p.CoreType)?.DensityGCm3;
        return d is > 0 && rho is > 0 ? new CoreModel(d.Value, rho.Value) : null;
    }

    /// <summary>
    /// Effective (whole-section) density of a section of outer diameter <paramref name="dMm"/>
    /// made of compound <paramref name="rhoCoat"/> around <paramref name="core"/>. Where the drawn
    /// line is thinner than the core the section is taken as all core — unbuildable, but the number
    /// stays finite.
    /// </summary>
    public static double Effective(double dMm, double rhoCoat, CoreModel? core)
    {
        if (core is not CoreModel c || dMm <= 0 || rhoCoat <= 0) return rhoCoat;
        double f = Math.Min(1.0, c.DiameterMm * c.DiameterMm / (dMm * dMm));
        return rhoCoat + (c.DensityGCm3 - rhoCoat) * f;
    }

    /// <summary><see cref="Effective(double,double,CoreModel?)"/> with the current core.</summary>
    public static double Effective(double dMm, double rhoCoat) => Effective(dMm, rhoCoat, Current);

    /// <summary>
    /// Mass to add to "volume × ρ_coat" for a piece of length <paramref name="lengthCm"/> whose
    /// diameter runs from d0 to d1: (ρ_core − ρ_coat) × core cross-section × length, in grams.
    /// The core section is capped at the line's own where the line is thinner than the core.
    /// </summary>
    public static double CoreMassCorrectionG(double d0Mm, double d1Mm, double lengthCm, double rhoCoat)
    {
        if (Current is not CoreModel c || lengthCm <= 0 || rhoCoat <= 0) return 0;
        double dMin = Math.Min(d0Mm, d1Mm);
        double coreD = Math.Min(c.DiameterMm, dMin > 0 ? dMin : c.DiameterMm);
        return (c.DensityGCm3 - rhoCoat) * AreaMm2(coreD) / 100.0 * lengthCm; // mm² → cm²
    }

    /// <summary>
    /// The compound that gives a section of diameter D the whole-section density
    /// <paramref name="rhoLine"/>: ρ_coat = (ρ_line·A(D) − ρ_core·A_core) / (A(D) − A_core).
    /// </summary>
    public static double CompoundForLineDensity(double dMm, double rhoLine, CoreModel? core)
    {
        if (core is not CoreModel c || dMm <= c.DiameterMm) return rhoLine;
        double a = AreaMm2(dMm), ac = AreaMm2(c.DiameterMm);
        return (rhoLine * a - c.DensityGCm3 * ac) / (a - ac);
    }

    /// <summary>
    /// Outer diameter that carries mass-per-length <paramref name="massPerLenGPerCm"/> (g/cm) with
    /// compound <paramref name="rhoCoat"/> around the current core: the inverse of the section
    /// mass, used where a diameter is rescaled at constant mass for a new compound.
    /// </summary>
    public static double DiameterForMassPerLength(double massPerLenGPerCm, double rhoCoat)
    {
        if (rhoCoat <= 0) return double.NaN;
        // m [g/cm] = ρ_coat·A(D)/100 + (ρ_core − ρ_coat)·A_core/100  (A in mm²)
        double corr = Current is CoreModel c ? (c.DensityGCm3 - rhoCoat) * AreaMm2(c.DiameterMm) : 0;
        double aMm2 = (massPerLenGPerCm * 100.0 - corr) / rhoCoat;
        return aMm2 > 0 ? Math.Sqrt(aMm2 * 4.0 / Math.PI) : double.NaN;
    }

    /// <summary>Mass per length (g/cm) of a section of diameter D with compound ρ_coat around the
    /// current core.</summary>
    public static double MassPerLengthGPerCm(double dMm, double rhoCoat)
        => Effective(dMm, rhoCoat) * AreaMm2(dMm) / 100.0;

    // ── File conversion: line density (old meaning) → compound ──────────────────────────────

    /// <summary>
    /// Converts a project whose densities still mean "density of the finished line as one
    /// homogeneous body" (every file before 19/11/2026) to compound densities, in place, and marks
    /// it <see cref="FlyLineProject.DensityIsCompound"/>. Returns true if any number changed.
    ///
    /// Each distinct material (a distinct density value) is converted to ONE compound that keeps
    /// the total mass of everywhere that material is used — the same reading as
    /// strumenti/stima_affondamento_core_misurate.py — so the number of distinct materials, the
    /// zones and a C file's ≤ 4 nozzles are all preserved. Inside each material the real density now
    /// varies with D: thin parts move towards the core's density, thick parts towards the compound's.
    /// A project with no known core is only marked: compound and line are the same thing there.
    /// </summary>
    public static bool ConvertLineDensitiesToCompound(FlyLineProject p)
    {
        if (p.DensityIsCompound) return false;
        p.DensityIsCompound = true;
        var core = FromProject(p);
        if (core is not CoreModel c) return false;

        var nodes = p.DesignNodes.OrderBy(n => n.X).ToList();
        if (nodes.Count < 2) return false;

        double DiamAt(double x)
        {
            for (int i = 0; i + 1 < nodes.Count; i++)
                if (x <= nodes[i + 1].X || i + 2 == nodes.Count)
                {
                    double span = nodes[i + 1].X - nodes[i].X;
                    double t = span > 0 ? Math.Clamp((x - nodes[i].X) / span, 0, 1) : 0;
                    return nodes[i].Y + t * (nodes[i + 1].Y - nodes[i].Y);
                }
            return nodes[^1].Y;
        }

        double baseRho = p.NozzleDefinitions.Count > 0 && p.NozzleDefinitions[0].DensityGCm3 > 0
            ? p.NozzleDefinitions[0].DensityGCm3
            : p.SharedDensityGCm3;

        double MaterialAt(double x)
        {
            var z = p.NozzleZones.FirstOrDefault(z => x >= z.StartCm && x < z.EndCm);
            if (z != null && z.NozzleIndex >= 0 && z.NozzleIndex < p.NozzleDefinitions.Count
                && p.NozzleDefinitions[z.NozzleIndex].DensityGCm3 > 0)
                return p.NozzleDefinitions[z.NozzleIndex].DensityGCm3;
            var m = p.SegmentMetadata.FirstOrDefault(m => x >= m.StartCm && x < m.EndCm && m.SpecWeight > 0);
            return m?.SpecWeight ?? baseRho;
        }

        // Σ A(D)·dx and Σ A_core·dx per material, sampled every 0.5 cm along the line.
        static long Key(double rho) => (long)Math.Round(rho * 1e6);
        var sums = new Dictionary<long, (double Rho, double A, double Ac)>();
        double x0 = nodes[0].X, x1 = nodes[^1].X;
        const double step = 0.5;
        double acore = AreaMm2(c.DiameterMm);
        double sumA = 0, sumAc = 0;
        for (double x = x0 + step / 2; x < x1; x += step)
        {
            double rho = MaterialAt(x);
            if (rho <= 0) continue;
            double a = AreaMm2(DiamAt(x));
            double ac = Math.Min(acore, a);
            sumA += a * step; sumAc += ac * step;
            var k = Key(rho);
            var s = sums.TryGetValue(k, out var v) ? v : (rho, 0.0, 0.0);
            sums[k] = (rho, s.Item2 + a * step, s.Item3 + ac * step);
        }

        double Convert(double rho, double a, double ac)
            => a - ac > 1e-9 ? (rho * a - c.DensityGCm3 * ac) / (a - ac) : rho;

        var map = sums.ToDictionary(kv => kv.Key, kv => Convert(kv.Value.Rho, kv.Value.A, kv.Value.Ac));
        // A density with no region of its own (an unused nozzle) uses the whole line's proportions.
        double Map(double rho)
        {
            if (rho <= 0) return rho;
            return map.TryGetValue(Key(rho), out var r) ? r : Convert(rho, sumA, sumAc);
        }

        bool changed = false;
        double Swap(double rho) { double r = Map(rho); if (Math.Abs(r - rho) > 1e-12) changed = true; return r; }

        p.SharedDensityGCm3 = Swap(p.SharedDensityGCm3);
        foreach (var n in p.NozzleDefinitions) n.DensityGCm3 = Swap(n.DensityGCm3);
        foreach (var m in p.SegmentMetadata) m.SpecWeight = Swap(m.SpecWeight);
        return changed;
    }
}
