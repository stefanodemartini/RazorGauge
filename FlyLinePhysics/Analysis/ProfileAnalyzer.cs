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
        int sliceCount = Math.Max(1, (int)Math.Round((endCm - startCm) / SliceLengthCm)) + 1;
        var xsCm = Enumerable.Range(0, sliceCount)
            .Select(i => startCm + i * (endCm - startCm) / (sliceCount - 1))
            .ToArray();

        var outerDiamMm = xsCm.Select(x => InterpolateY(nodes, x)).ToArray();
        var coatingDensity = xsCm.Select(x => DensityAtX(project, nodes, x)).ToArray();
        var linearMassKgM = xsCm.Select((x, i) =>
            MassLinearCalculator.LinearMass(outerDiamMm[i], coatingDensity[i], project.CoreDiameterMm, project.CoreDensityGCm3))
            .ToArray();

        report.XsCm = xsCm;
        report.LinearMassKgM = linearMassKgM;
        report.CumulativeMassG = MassLinearCalculator.CumulativeMassG(xsCm, linearMassKgM);

        if (project.ScanPoints.Count > 0)
        {
            var scanNodes = project.ScanPoints.OrderBy(p => p.X)
                .Select(p => new DesignNode { X = p.X, Y = p.FilteredY }).ToList();
            report.ScanDesignDeltaMm = xsCm
                .Select((x, i) => Math.Abs(InterpolateY(scanNodes, x) - outerDiamMm[i]))
                .ToArray();
        }

        foreach (double v in scenario.VelocitiesMs)
        {
            var series = BuildVelocitySeries(v, xsCm, outerDiamMm, linearMassKgM, scenario);
            report.ByVelocity.Add(series);
        }

        var referenceSeries = report.ByVelocity.FirstOrDefault(s => Math.Abs(s.VelocityMs - scenario.VelocityReferenceMs) < Eps)
            ?? report.ByVelocity.FirstOrDefault();
        if (referenceSeries != null)
        {
            foreach (var meta in project.SegmentMetadata)
                report.SegmentScores.Add(ScoreSegment(meta, xsCm, referenceSeries, report.ScanDesignDeltaMm));
        }

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

    private static SegmentScore ScoreSegment(
        SegmentMetadata meta, double[] xsCm, VelocitySeries series, double[]? scanDelta)
    {
        var indices = Enumerable.Range(0, xsCm.Length)
            .Where(i => xsCm[i] >= meta.StartCm - Eps && xsCm[i] <= meta.EndCm + Eps)
            .ToList();

        var validPi = indices.Select(i => series.Pi[i]).Where(p => !StabilityMetrics.IsDegenerate(p)).ToList();
        double meanPi = validPi.Count > 0 ? validPi.Average() : 0;
        double variance = validPi.Count > 0 ? validPi.Select(p => (p - meanPi) * (p - meanPi)).Average() : 0;
        double coefVarSquared = meanPi != 0 ? variance / (meanPi * meanPi) : 0;

        double maxContinuity = 0;
        if (indices.Count > 0)
        {
            double cStart = series.ContinuityIndex[indices[0]];
            double cEnd = series.ContinuityIndex[indices[^1]];
            var validTransitions = new[] { cStart, cEnd }.Where(c => !double.IsNaN(c)).ToList();
            maxContinuity = validTransitions.Count > 0 ? validTransitions.Max() : 0;
        }

        double meanScanDelta = scanDelta != null && indices.Count > 0
            ? indices.Select(i => scanDelta[i]).Average()
            : 0;

        double penaltyLevel = WeightPiLevel * Math.Clamp(
            meanPi != 0 ? Math.Abs(Math.Log10(Math.Abs(meanPi))) / ScaleLogPi : 1.0, 0, 1);
        double penaltyVariance = WeightPiVariance * Math.Clamp(coefVarSquared / ScaleCoefVarSquared, 0, 1);
        double penaltyContinuity = WeightContinuity * Math.Clamp(maxContinuity / ScaleContinuityPerCm, 0, 1);
        double penaltyScan = WeightScanDelta * Math.Clamp(meanScanDelta / ScaleScanDeltaMm, 0, 1);

        double score = 100.0 - (penaltyLevel + penaltyVariance + penaltyContinuity + penaltyScan);

        return new SegmentScore
        {
            Segment = meta,
            Score = Math.Clamp(score, 0, 100),
            MeanPi = meanPi,
            PiVariance = variance,
            MaxContinuityAtTransitions = maxContinuity,
            MeanScanDesignDeltaMm = meanScanDelta,
        };
    }

    /// <summary>
    /// Coating density (g/cm³) at position x, matching the priority chain
    /// DiametroLineaDesktop.Services.LineDesignBuilder.ToProjectSegments uses: a NozzleZone's own
    /// nozzle density (if set) wins; otherwise the project's shared density when UseSharedDensity is
    /// on; otherwise the SegmentMetadata entry for the design-node interval containing x.
    /// </summary>
    private static double DensityAtX(FlyLineProject project, List<DesignNode> nodes, double x)
    {
        int i = 0;
        while (i < nodes.Count - 2 && x > nodes[i + 1].X) i++;
        double segStart = nodes[i].X;

        var zone = project.NozzleZones.FirstOrDefault(z => x >= z.StartCm && x < z.EndCm);
        if (zone != null && zone.NozzleIndex >= 0 && zone.NozzleIndex < project.NozzleDefinitions.Count
            && project.NozzleDefinitions[zone.NozzleIndex].DensityGCm3 > 0)
            return project.NozzleDefinitions[zone.NozzleIndex].DensityGCm3;

        if (project.UseSharedDensity)
            return project.SharedDensityGCm3;

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
