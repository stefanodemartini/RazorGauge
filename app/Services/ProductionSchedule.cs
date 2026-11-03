using DiametroLineaDesktop.Models;

namespace DiametroLineaDesktop.Services;

/// <summary>One taper (shape) run: where the slope stays one straight line.</summary>
public sealed record TaperRun(double StartCm, double EndCm, string Name, double StartDiamMm, double EndDiamMm)
{
    public double LengthCm => EndCm - StartCm;
}

/// <summary>
/// One nozzle run: a stretch of one material, or the transition between two
/// (<see cref="Nozzle"/> = <see cref="NozzlePattern.Transition"/>, going from <see cref="From"/> to <see cref="To"/>).
/// </summary>
public sealed record NozzleRun(double StartCm, double EndCm, int Nozzle, int From, int To, double StartRho, double EndRho)
{
    public double LengthCm    => EndCm - StartCm;
    public bool IsTransition  => Nozzle == NozzlePattern.Transition;
}

/// <summary>One colour run: the line's real pigment over this stretch.</summary>
public sealed record ColorRun(double StartCm, double EndCm, string Hex);

/// <summary>
/// The three things a producer must never confuse, each on its own: the SHAPE (taper runs — where
/// the slope changes), the NOZZLES (which material, i.e. density, is extruded where, transitions
/// included) and the COLOR (the real pigment). A slope change and a nozzle change are unrelated
/// events that may or may not fall at the same X — the design sheet draws and tabulates them
/// separately (strips under the chart, two tables in the PDF), all from this one model so the
/// chart on screen, the chart image in the PDF and the PDF's tables cannot drift apart.
/// </summary>
public sealed class ProductionSchedule
{
    public List<TaperRun>  Tapers  { get; } = new();
    public List<NozzleRun> Nozzles { get; } = new();
    public List<ColorRun>  Colors  { get; } = new();

    public double StartCm => Tapers.Count > 0 ? Tapers[0].StartCm : 0;
    public double EndCm   => Tapers.Count > 0 ? Tapers[^1].EndCm   : 0;

    /// <param name="segments">Segments with compensation slices (a C file, or a live zone design).</param>
    /// <param name="profile">The profile actually drawn (compensated nodes), for diameters.</param>
    public static ProductionSchedule Build(IReadOnlyList<ProjectSegment> segments, List<(double X, double Y)> profile,
        IReadOnlyList<NozzleZone> zones, IReadOnlyList<NozzleDefinition> nozzles)
    {
        var s = new ProductionSchedule();
        var ordered = segments.OrderBy(x => x.StartCm).ToList();
        if (ordered.Count == 0 || profile.Count < 2) return s;

        // SHAPE — a Name change marks a real taper change (every slice of a C file inherits the
        // Name of the NC segment it was cut from).
        var bounds = ChartGeometry.GetTaperShapeBoundaries(ordered, profile);
        for (int i = 0; i + 1 < bounds.Count; i++)
        {
            double a = bounds[i].X, b = bounds[i + 1].X, mid = (a + b) / 2;
            string name = ordered.FirstOrDefault(x => mid >= x.StartCm && mid <= x.EndCm)?.Name ?? $"S{i + 1}";
            s.Tapers.Add(new TaperRun(a, b, name,
                ChartGeometry.InterpolateProfileY(profile, a), ChartGeometry.InterpolateProfileY(profile, b)));
        }

        // NOZZLES — material spans with every transition ramp as one span of its own
        var isTransition = ChartGeometry.TransitionTest(
            ordered.Where(x => x.HasCompensation).SelectMany(x => x.CompSliceDensities), nozzles);
        var spans = ChartGeometry.GetMaterialZoneSpans(ordered, profile, isTransition);
        if (spans.Count == 0)
        {
            // A plain single-material design: M1 end to end
            double rho = nozzles.Count > 0 ? nozzles[0].DensityGCm3 : ordered[0].SpecWeightGCm3;
            s.Nozzles.Add(new NozzleRun(profile[0].X, profile[^1].X, 0, 0, 0, rho, rho));
        }
        else
        {
            // A nozzle is a compound — density AND colour — so a zone is a nozzle change even
            // where the density stays the same (a colour-only zone): cut each material span at
            // the zone edges inside it, then merge neighbours that end up on the same nozzle.
            var split = new List<(double StartX, double EndX, double Density)>();
            foreach (var sp in spans)
            {
                if (double.IsNaN(sp.Density)) { split.Add(sp); continue; }
                var cs = new SortedSet<double> { sp.StartX, sp.EndX };
                foreach (var z in zones)
                {
                    if (z.StartCm > sp.StartX && z.StartCm < sp.EndX) cs.Add(z.StartCm);
                    if (z.EndCm   > sp.StartX && z.EndCm   < sp.EndX) cs.Add(z.EndCm);
                }
                var cl = cs.ToList();
                for (int k = 0; k + 1 < cl.Count; k++) split.Add((cl[k], cl[k + 1], sp.Density));
            }
            var merged = new List<(double StartX, double EndX, double Density)>();
            var mIdx   = new List<int>();
            foreach (var sp in split)
            {
                int ix = double.IsNaN(sp.Density) ? NozzlePattern.Transition
                    : ChartGeometry.MaterialIndex((sp.StartX + sp.EndX) / 2, sp.Density, zones, nozzles);
                if (merged.Count > 0 && ix != NozzlePattern.Transition && mIdx[^1] == ix)
                    merged[^1] = (merged[^1].StartX, sp.EndX, merged[^1].Density);
                else { merged.Add(sp); mIdx.Add(ix); }
            }
            spans = merged;
            var idx = mIdx;
            for (int i = 0; i < spans.Count; i++)
            {
                var sp = spans[i];
                if (idx[i] != NozzlePattern.Transition)
                {
                    s.Nozzles.Add(new NozzleRun(sp.StartX, sp.EndX, idx[i], idx[i], idx[i], sp.Density, sp.Density));
                    continue;
                }
                int from = i > 0 ? idx[i - 1] : 0, to = i + 1 < spans.Count ? idx[i + 1] : from;
                double r0 = i > 0 ? spans[i - 1].Density : double.NaN;
                double r1 = i + 1 < spans.Count ? spans[i + 1].Density : double.NaN;
                s.Nozzles.Add(new NozzleRun(sp.StartX, sp.EndX, NozzlePattern.Transition, from, to, r0, r1));
            }
        }

        // COLOR — the nozzle's own pigment where a zone covers, M1's elsewhere
        string ColorAt(double x)
        {
            var z = zones.FirstOrDefault(z => x >= z.StartCm && x < z.EndCm);
            int n = z != null && z.NozzleIndex >= 0 && z.NozzleIndex < nozzles.Count ? z.NozzleIndex : 0;
            return nozzles.Count > 0 ? nozzles[n].ColorHex.TrimStart('#').ToUpperInvariant() : "DC3232";
        }
        var cuts = new SortedSet<double> { profile[0].X, profile[^1].X };
        foreach (var z in zones)
        {
            if (z.StartCm > profile[0].X && z.StartCm < profile[^1].X) cuts.Add(z.StartCm);
            if (z.EndCm   > profile[0].X && z.EndCm   < profile[^1].X) cuts.Add(z.EndCm);
        }
        var xs = cuts.ToList();
        for (int i = 0; i + 1 < xs.Count; i++)
        {
            string hex = ColorAt((xs[i] + xs[i + 1]) / 2);
            if (s.Colors.Count > 0 && s.Colors[^1].Hex == hex)
                s.Colors[^1] = s.Colors[^1] with { EndCm = xs[i + 1] };
            else
                s.Colors.Add(new ColorRun(xs[i], xs[i + 1], hex));
        }
        return s;
    }

    /// <summary>"M3", or "M3→M2" for a transition.</summary>
    public static string Label(NozzleRun r) =>
        r.IsTransition ? $"M{r.From + 1}→M{r.To + 1}" : $"M{r.Nozzle + 1}";

    /// <summary>"1.025", or "1.025→1.018" for a transition.</summary>
    public static string DensityText(NozzleRun r) =>
        r.IsTransition ? $"{r.StartRho:0.000}→{r.EndRho:0.000}" : $"{r.StartRho:0.000}";
}
