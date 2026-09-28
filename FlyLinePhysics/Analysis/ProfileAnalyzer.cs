using FlyLinePhysics.Model;
using FlyLinePhysics.Physics;

namespace FlyLinePhysics.Analysis;

/// <summary>
/// Samples a FlyLineProject's design profile on a fixed grid and computes every Level-2 metric
/// (m, M, Re, drag, Π, C) plus a per-segment synthetic score.
///
/// Simplification: Π and the drag series treat each CastScenario.VelocitiesMs entry as a single
/// scalar characteristic velocity, fed as both the normal and tangential velocity component. A
/// real cast has a normal/tangential split that depends on loop geometry and changes over time —
/// modelling that requires an actual kinematic simulation (out of scope here; see the Gatti-Bono/
/// Perkins coupled model). This gives a steady, comparable-across-designs approximation, not a
/// time-accurate one.
/// </summary>
public static class ProfileAnalyzer
{
    private const double SliceLengthCm = 1.0;
    private const double Eps = 1e-6;

    // Both mirror MainWindow/SinkingSpeedCalc — a zone this close to the base is the same material,
    // and no real material is thinner than RhoFloor.
    private const double DensityMergeThreshold = 0.02;
    private const double RhoFloor = 0.94;

    // Score weights and scales — first pass, not yet calibrated against real designs. Revisit once
    // ProfileAnalyzer has been run on a range of Stefano's real .flp files.
    private const double WeightPiLevel     = 25.0;
    private const double WeightPiVariance  = 25.0;
    private const double WeightContinuity  = 25.0;
    private const double WeightScanDelta   = 25.0;
    private const double ScaleLogPi            = 1.0;   // |log10(meanPi)| == 1 (10x off) -> max penalty
    private const double ScaleCoefVarSquared   = 1.0;   // stdev == mean -> max penalty
    private const double ScaleContinuityPerCm  = 0.05;  // |ΔΠ/Δs|/Π == 5%/cm -> max penalty
    private const double ScaleScanDeltaMm      = 1.0;   // 1 mm mean deviation -> max penalty

    public static AnalysisReport Analyze(FlyLineProject project, CastScenario scenario)
    {
        var nodes = project.DesignNodes.OrderBy(n => n.X).ToList();
        var report = new AnalysisReport();
        if (nodes.Count < 2) return report;

        double startCm = nodes[0].X, endCm = nodes[^1].X;
        int designSlices = Math.Max(1, (int)Math.Round((endCm - startCm) / SliceLengthCm)) + 1;
        var designXs = Enumerable.Range(0, designSlices)
            .Select(i => startCm + i * (endCm - startCm) / (designSlices - 1))
            .ToArray();

        // DesignNodes hold the *drawn* profile; a nozzle zone reshapes it as a live overlay that is
        // never written back, so the nodes alone are not the geometry.
        var resolved = Resolve(project, nodes);
        var designDiamMm  = designXs.Select(resolved.DiameterAt).ToArray();
        var designDensity = designXs.Select(resolved.DensityAt).ToArray();
        var designMassKgM = designXs.Select((x, i) =>
            MassLinearCalculator.LinearMass(designDiamMm[i], designDensity[i], project.CoreDiameterMm, project.CoreDensityGCm3))
            .ToArray();

        // A shooting head is only half a system: what it tows is not in the file. Append it, so the
        // two families are evaluated as the same kind of object instead of being compared as if a
        // head simply stopped where a full line keeps going.
        report.HasDensityData = designDensity.Any(d => d > 0);

        var kind = ResolveKind(scenario, nodes);
        report.Kind = kind;
        report.DesignSliceCount = designSlices;

        double[] xsCm, outerDiamMm, linearMassKgM, inertialTaper;
        var designTaper = designXs.Select((x, i) => designDensity[i] * designDiamMm[i]).ToArray();

        if (kind == LineKind.ShootingHead && scenario.ShootingLine.LengthCm > 0)
        {
            var tail = scenario.ShootingLine;
            int tailSlices = Math.Max(1, (int)Math.Round(tail.LengthCm / SliceLengthCm));
            var tailXs = Enumerable.Range(1, tailSlices).Select(i => endCm + i * SliceLengthCm).ToArray();
            // Solid, never MassLinearCalculator.LinearMass: the project's core belongs to the fly
            // line, and applying it to a monofilament would invent a core the mono does not have.
            double tailMassKgM = MassLinearCalculator.LinearMassSolid(tail.DiameterMm, tail.DensityGCm3);

            xsCm          = designXs.Concat(tailXs).ToArray();
            outerDiamMm   = designDiamMm.Concat(tailXs.Select(_ => tail.DiameterMm)).ToArray();
            linearMassKgM = designMassKgM.Concat(tailXs.Select(_ => tailMassKgM)).ToArray();
            inertialTaper = designTaper.Concat(tailXs.Select(_ => tail.InertialTaper)).ToArray();
        }
        else
        {
            xsCm = designXs; outerDiamMm = designDiamMm;
            linearMassKgM = designMassKgM; inertialTaper = designTaper;
        }

        report.XsCm = xsCm;
        report.LinearMassKgM = linearMassKgM;
        report.Diameter = outerDiamMm;
        report.InertialTaper = inertialTaper;
        report.CumulativeMassG = MassLinearCalculator.CumulativeMassG(xsCm, linearMassKgM);

        if (kind == LineKind.ShootingHead && xsCm.Length > designSlices)
        {
            double headMassG = report.CumulativeMassG[designSlices - 1];
            report.Junction = new JunctionMetrics
            {
                PositionCm          = endCm,
                InertialTaperBefore = designTaper[^1],
                InertialTaperAfter  = scenario.ShootingLine.InertialTaper,
                StepRatio           = scenario.ShootingLine.InertialTaper > 0
                                        ? designTaper[^1] / scenario.ShootingLine.InertialTaper
                                        : double.NaN,
                HeadMassG           = headMassG,
                TowedMassG          = report.CumulativeMassG[^1] - headMassG,
            };
        }

        if (project.ScanPoints.Count > 0)
        {
            var scanNodes = project.ScanPoints.OrderBy(p => p.X)
                .Select(p => new DesignNode { X = p.X, Y = p.FilteredY }).ToList();
            // NaN past the design: there is nothing scanned out there to compare against.
            report.ScanDesignDeltaMm = xsCm
                .Select((x, i) => i < designSlices
                    ? Math.Abs(InterpolateY(scanNodes, x) - outerDiamMm[i])
                    : double.NaN)
                .ToArray();
        }

        report.Shape = ComputeShape(designXs, designTaper);

        foreach (double v in scenario.VelocitiesMs)
        {
            var series = BuildVelocitySeries(v, xsCm, outerDiamMm, linearMassKgM, scenario);
            report.ByVelocity.Add(series);
        }

        report.SegmentTapers = BuildSegmentTapers(project, nodes, designXs, designTaper, report.CumulativeMassG);

        return report;
    }

    private static VelocitySeries BuildVelocitySeries(
        double v, double[] xsCm, double[] outerDiamMm, double[] linearMassKgM, CastScenario scenario)
    {
        int n = xsCm.Length;
        var reynolds = new double[n];
        var normalDrag = new double[n];
        var tangentialDrag = new double[n];
        var pi = new double[n];

        for (int i = 0; i < n; i++)
        {
            double dM = outerDiamMm[i] / 1000.0;
            reynolds[i] = ReynoldsCalculator.Reynolds(dM, v, scenario.AirDensityKgM3, scenario.AirViscosityPaS);
            normalDrag[i] = DragCalculator.NormalDrag(dM, v, scenario.AirDensityKgM3, scenario.AirViscosityPaS);
            tangentialDrag[i] = DragCalculator.TangentialDrag(dM, v, scenario.AirDensityKgM3, scenario.AirViscosityPaS);
            pi[i] = StabilityMetrics.MomentumToDragRatio(linearMassKgM[i], scenario.AccelerationRefMs2, normalDrag[i]);
        }

        var continuity = StabilityMetrics.ContinuityIndex(xsCm, pi);
        var warning = continuity.Select(c =>
            scenario.ContinuityWarningThreshold is double t && !double.IsNaN(c) && c > t).ToArray();

        return new VelocitySeries
        {
            VelocityMs = v,
            Reynolds = reynolds,
            NormalDragNPerM = normalDrag,
            TangentialDragNPerM = tangentialDrag,
            Pi = pi,
            ContinuityIndex = continuity,
            Warning = warning,
        };
    }

    /// <summary>
    /// One entry per design-node interval — the unit a design change is made in. Keyed to the nodes
    /// rather than to SegmentMetadata so it still describes the real geometry when the metadata has
    /// drifted out of sync with the nodes; a matching metadata entry only supplies the name.
    /// </summary>
    private static List<SegmentTaper> BuildSegmentTapers(
        FlyLineProject project, List<DesignNode> nodes,
        double[] xsCm, double[] taper, double[] cumulativeMassG)
    {
        var list = new List<SegmentTaper>();
        for (int i = 0; i < nodes.Count - 1; i++)
        {
            double a = nodes[i].X, b = nodes[i + 1].X;
            if (b - a <= Eps) continue;

            int ia = NearestIndex(xsCm, a), ib = NearestIndex(xsCm, b);
            double ta = taper[ia], tb = taper[ib];

            list.Add(new SegmentTaper
            {
                Name = project.SegmentMetadata
                           .FirstOrDefault(m => Math.Abs(m.StartCm - a) < Eps)?.Name ?? string.Empty,
                StartCm = a,
                EndCm = b,
                InertialTaperStart = ta,
                InertialTaperEnd = tb,
                MassG = cumulativeMassG[ib] - cumulativeMassG[ia],
                // A log ratio over length: a rate, comparable between a 20 cm tip and a 600 cm belly.
                TaperRatePer100Cm = ta > 0 && tb > 0
                    ? Math.Log(tb / ta) / (b - a) * 100.0
                    : double.NaN,
            });
        }
        return list;
    }

    private static int NearestIndex(double[] xs, double x)
    {
        if (xs.Length == 0) return 0;
        int best = 0; double bestD = Math.Abs(xs[0] - x);
        for (int i = 1; i < xs.Length; i++)
        {
            double d = Math.Abs(xs[i] - x);
            if (d >= bestD) { if (xs[i] > x) break; continue; }
            best = i; bestD = d;
        }
        return best;
    }

    /// <summary>
    /// Shape of ρ·d over the design profile — deliberately over the design only: the appended
    /// shooting line is constant, and the step into it is reported separately as JunctionMetrics
    /// because it is a design choice, not a defect.
    /// </summary>
    private static ShapeMetrics? ComputeShape(double[] xsCm, double[] taper)
    {
        if (taper.Length < 3) return null;

        int peak = 0;
        for (int i = 1; i < taper.Length; i++) if (taper[i] > taper[peak]) peak = i;

        // Walk from the belly to the tip. ρ·d should fall the whole way; sum whatever climbs back.
        double backup = 0;
        var spots = new List<(double, double)>();
        for (int i = peak; i > 0; i--)
        {
            double rise = taper[i - 1] - taper[i];
            if (rise > 0) { backup += rise; spots.Add((xsCm[i - 1], rise)); }
        }
        double drop = taper[peak] - taper[0];

        var c = StabilityMetrics.ContinuityIndex(xsCm, taper)
            .Where(x => !double.IsNaN(x) && x > 0)
            .OrderBy(x => x)
            .ToArray();

        double median = Percentile(c, 0.50), p99 = Percentile(c, 0.99);

        return new ShapeMetrics
        {
            PeakPositionCm      = xsCm[peak],
            PeakInertialTaper   = taper[peak],
            // Relative to the drop it is a fraction of; with no drop at all there is nothing for a
            // backup to be a fraction of, so report it as absent rather than as a divide-by-zero.
            FrontBackupFraction = drop > Eps ? backup / drop : double.NaN,
            BackupSpots         = drop > Eps
                ? spots.Select(t => (t.Item1, t.Item2 / drop)).ToList()
                : new List<(double, double)>(),
            MedianContinuity    = median,
            P99Continuity       = p99,
            ContinuitySpikiness = median > 0 ? p99 / median : double.NaN,
        };
    }

    /// <summary>Linear-interpolated percentile of an already-sorted array.</summary>
    private static double Percentile(double[] sorted, double p)
    {
        if (sorted.Length == 0) return double.NaN;
        if (sorted.Length == 1) return sorted[0];
        double pos = p * (sorted.Length - 1);
        int lo = (int)Math.Floor(pos);
        int hi = Math.Min(lo + 1, sorted.Length - 1);
        return sorted[lo] + (pos - lo) * (sorted[hi] - sorted[lo]);
    }

    /// <summary>
    /// Decides whether the profile already carries its own running line. A full line ends in a long
    /// constant-diameter run (Stefano's trail 960-1475 cm); a shooting head ends at its back taper
    /// (at most 30 cm level), and everything past that point is a monofilament the file never
    /// mentions.
    /// </summary>
    private static LineKind ResolveKind(CastScenario scenario, List<DesignNode> nodes)
    {
        if (scenario.Kind != LineKind.Auto) return scenario.Kind;

        double endY = nodes[^1].Y;
        double levelFromX = nodes[^1].X;
        for (int i = nodes.Count - 1; i > 0; i--)
        {
            if (Math.Abs(nodes[i - 1].Y - endY) > Eps) break;
            levelFromX = nodes[i - 1].X;
        }
        return nodes[^1].X - levelFromX >= scenario.IntegratedRunningLineMinCm
            ? LineKind.FullLine
            : LineKind.ShootingHead;
    }

    /// <summary>M1, the base material every zone factor is relative to. Falls back to the shared
    /// density when no nozzle is defined, which is the case for most files in the archive.</summary>
    private static double BaseDensity(FlyLineProject project)
    {
        double m1 = project.NozzleDefinitions.Count > 0 ? project.NozzleDefinitions[0].DensityGCm3 : 0;
        return m1 > 0 ? m1 : project.SharedDensityGCm3;
    }

    /// <summary>
    /// The profile a nozzle zone actually produces, resolved the way
    /// MainWindow.ApplyZoneDensities produces it.
    ///
    /// The zone edge is an exact breakpoint, never a blend: the diameter there is the zone's own
    /// scaled value, and the segment *just outside* the zone is reshaped — its near end takes that
    /// scaled value, its far end stays at the drawn diameter, linear in between. So the diameter is
    /// continuous across the edge by construction, and the mass the reshaped outside segment gives
    /// up is the accepted cost. The density, by contrast, is hard-edged, so the whole material jump
    /// lands in ρ·d.
    ///
    /// Sampling is piece-based: every zone edge is a breakpoint, so each piece lies wholly inside or
    /// wholly outside a zone and its density is read once at its midpoint. That sidesteps the
    /// question of which side of an edge a sample belongs to, which is exactly where a grid landing
    /// on whole centimetres would otherwise disagree with the app.
    /// </summary>
    private sealed class ResolvedProfile
    {
        public double[] Bp = Array.Empty<double>();
        public double[] BpDiameter = Array.Empty<double>();
        /// <summary>Density of piece i, spanning Bp[i]..Bp[i+1].</summary>
        public double[] PieceDensity = Array.Empty<double>();

        private int PieceOf(double x)
        {
            if (Bp.Length < 2) return 0;
            for (int i = 0; i < Bp.Length - 1; i++) if (x < Bp[i + 1] - Eps) return i;
            return Bp.Length - 2;
        }

        public double DiameterAt(double x)
        {
            if (Bp.Length == 0) return 0;
            if (Bp.Length == 1 || x <= Bp[0]) return BpDiameter[0];
            if (x >= Bp[^1]) return BpDiameter[^1];
            int i = PieceOf(x);
            double span = Bp[i + 1] - Bp[i];
            if (span <= Eps) return BpDiameter[i];
            return BpDiameter[i] + (x - Bp[i]) / span * (BpDiameter[i + 1] - BpDiameter[i]);
        }

        public double DensityAt(double x) =>
            PieceDensity.Length == 0 ? 0 : PieceDensity[Math.Min(PieceOf(x), PieceDensity.Length - 1)];
    }

    private static ResolvedProfile Resolve(FlyLineProject project, List<DesignNode> nodes)
    {
        double baseDensity = BaseDensity(project);

        // A zone within DensityMergeThreshold of the base is the same material for every purpose,
        // exactly as the app treats it — not a pointless near-1 scale factor.
        var realZones = project.NozzleZones
            .Where(z => z.EndCm > z.StartCm)
            .Select(z => (z.StartCm, z.EndCm, Rho: NozzleDensity(project, z)))
            .Where(z => z.Rho > 0 && Math.Abs(z.Rho - baseDensity) > DensityMergeThreshold)
            .ToList();

        double FactorAt(double x)
        {
            if (!project.ZoneDensityAdaptDiameters || baseDensity <= 0) return 1.0;
            // Closed on both edges: the shared node takes the zone's value, which is what makes the
            // diameter continuous. Two zones meeting on one node cannot both hold it, so they split
            // the difference — the app's choice, with a non-blocking warning.
            var claiming = realZones.Where(z => x >= z.StartCm - Eps && x <= z.EndCm + Eps).ToList();
            return claiming.Count == 0
                ? 1.0
                : claiming.Average(z => Math.Sqrt(baseDensity / Math.Max(z.Rho, RhoFloor)));
        }

        // Two deliberate divergences from MainWindow.ApplyZoneDensities, both about not inventing
        // data the file does not carry:
        //  - the app clamps *every* piece to RhoFloor, base material included. Here only a zone's
        //    own density is clamped. RhoFloor is the compensation solver's manufacturing limit; a
        //    hand-set shared density below it is a stated design input, and several real files sit
        //    at 0.917-0.92. Clamping those would report a line that is not the one on file.
        //  - a zone pointing at an undefined nozzle (rho 0) falls back to the base material rather
        //    than yielding density 0, which would zero the mass of that stretch.
        double DensityHardAt(double x)
        {
            var zone = realZones.FirstOrDefault(z => x >= z.StartCm && x < z.EndCm);
            if (zone.Rho > 0) return Math.Max(zone.Rho, RhoFloor);
            return BaseDensityAt(project, nodes, x);
        }

        double lo = nodes[0].X, hi = nodes[^1].X;
        var bp = new SortedSet<double>(nodes.Select(n => n.X));
        foreach (var z in realZones)
        {
            if (z.StartCm > lo + Eps && z.StartCm < hi - Eps) bp.Add(z.StartCm);
            if (z.EndCm   > lo + Eps && z.EndCm   < hi - Eps) bp.Add(z.EndCm);
        }

        var xs = bp.ToArray();
        var profile = new ResolvedProfile
        {
            Bp = xs,
            BpDiameter = xs.Select(x => InterpolateY(nodes, x) * FactorAt(x)).ToArray(),
            PieceDensity = xs.Length < 2
                ? new[] { DensityHardAt(lo) }
                : Enumerable.Range(0, xs.Length - 1)
                    .Select(i => DensityHardAt((xs[i] + xs[i + 1]) / 2.0)).ToArray(),
        };
        return profile;
    }

    private static double NozzleDensity(FlyLineProject project, NozzleZone z) =>
        z.NozzleIndex >= 0 && z.NozzleIndex < project.NozzleDefinitions.Count
            ? project.NozzleDefinitions[z.NozzleIndex].DensityGCm3
            : 0;

    /// <summary>
    /// Density where no zone covers, matching the priority chain
    /// DiametroLineaDesktop.Services.LineDesignBuilder.ToProjectSegments uses: the project's shared
    /// density when UseSharedDensity is on, otherwise the SegmentMetadata entry for the design-node
    /// interval containing x.
    /// </summary>
    private static double BaseDensityAt(FlyLineProject project, List<DesignNode> nodes, double x)
    {
        if (project.UseSharedDensity) return project.SharedDensityGCm3;

        int i = 0;
        while (i < nodes.Count - 2 && x > nodes[i + 1].X) i++;
        double segStart = nodes[i].X;
        var meta = project.SegmentMetadata.FirstOrDefault(m => Math.Abs(m.StartCm - segStart) < Eps);
        return meta?.SpecWeight ?? 0;
    }

    /// <summary>Piecewise-linear interpolation of Y over sorted (X,Y) nodes, clamped at the ends —
    /// equivalent to DiametroLineaDesktop.Services.ChartGeometry.InterpolateProfileY, reimplemented
    /// here since this library cannot reference the WPF assembly.</summary>
    private static double InterpolateY(List<DesignNode> sorted, double x)
    {
        if (sorted.Count == 0) return 0;
        if (x <= sorted[0].X) return sorted[0].Y;
        if (x >= sorted[^1].X) return sorted[^1].Y;
        for (int i = 0; i < sorted.Count - 1; i++)
        {
            if (x >= sorted[i].X && x <= sorted[i + 1].X)
            {
                double t = (x - sorted[i].X) / (sorted[i + 1].X - sorted[i].X);
                return sorted[i].Y + t * (sorted[i + 1].Y - sorted[i].Y);
            }
        }
        return sorted[^1].Y;
    }
}
