using FlyLinePhysics.Analysis;
using FlyLinePhysics.Model;
using FlyLinePhysics.Physics;
using Xunit;

namespace FlyLinePhysics.Tests;

public class ProfileAnalyzerTests
{
    private static CastScenario DefaultScenario() => new() { AccelerationRefMs2 = 50.0 };

    private static FlyLineProject LinearTaper(double d0Mm, double lengthCm, double d1Mm, double densityGCm3) => new()
    {
        UseSharedDensity = true,
        SharedDensityGCm3 = densityGCm3,
        DesignNodes = new()
        {
            new DesignNode { X = 0, Y = d0Mm },
            new DesignNode { X = lengthCm, Y = d1Mm },
        },
    };

    [Fact]
    public void CumulativeMass_MatchesAnalyticFrustumMass_ForLinearTaper()
    {
        // 100 cm linear taper 2.0mm -> 1.0mm, density 1.0 g/cm3. Total mass = frustum-equivalent
        // integral of rho*pi/4*d(x)^2, computed independently: 1.832595714594046 g.
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.True(report.CumulativeMassG.Length > 0);
        Assert.Equal(0.0, report.CumulativeMassG[0]);
        // End of the design, not of the array: a bare taper auto-detects as a shooting head, so the
        // array continues into the shooting line it tows.
        Assert.Equal(1.832595714594046, report.CumulativeMassG[report.DesignSliceCount - 1], precision: 3);
    }

    [Fact]
    public void LinearMassKgM_MatchesSolidFormula_AtEnds()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        double expectedStart = Physics.MassLinearCalculator.LinearMassSolid(2.0, 1.0);
        double expectedEnd = Physics.MassLinearCalculator.LinearMassSolid(1.0, 1.0);

        Assert.Equal(expectedStart, report.LinearMassKgM[0], precision: 12);
        Assert.Equal(expectedEnd, report.LinearMassKgM[report.DesignSliceCount - 1], precision: 12);
    }

    [Fact]
    public void TaperRate_IsSignedAndPerHundredCm_AndZeroOnACylinder()
    {
        var project = new FlyLineProject
        {
            UseSharedDensity = true, SharedDensityGCm3 = 1.0,
            DesignNodes = new()
            {
                new DesignNode { X = 0,   Y = 1.0 },
                new DesignNode { X = 100, Y = 1.0 },   // cylinder
                new DesignNode { X = 300, Y = 2.0 },   // thickening butt-ward
                new DesignNode { X = 400, Y = 1.0 },   // back taper
            },
        };

        var r = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.Equal(3, r.SegmentTapers.Count);
        Assert.True(r.SegmentTapers[0].IsCylindrical);
        Assert.Equal(0.0, r.SegmentTapers[0].TaperRatePer100Cm, precision: 9);

        // ln(2)/200cm, per 100 cm.
        Assert.Equal(Math.Log(2.0) / 200.0 * 100.0, r.SegmentTapers[1].TaperRatePer100Cm, precision: 6);
        Assert.True(r.SegmentTapers[2].TaperRatePer100Cm < 0);   // falling
    }

    [Fact]
    public void TaperRate_IsARate_SoTheSameShapeOverTwiceTheLengthIsHalfAsSteep()
    {
        // The property that makes it usable while designing: stretch a taper and the number halves,
        // which is what "gentler" has to mean.
        var shortOne = LinearTaper(d0Mm: 1.0, lengthCm: 100.0, d1Mm: 2.0, densityGCm3: 1.0);
        var longOne  = LinearTaper(d0Mm: 1.0, lengthCm: 200.0, d1Mm: 2.0, densityGCm3: 1.0);

        double kShort = ProfileAnalyzer.Analyze(shortOne, DefaultScenario()).SegmentTapers[0].TaperRatePer100Cm;
        double kLong  = ProfileAnalyzer.Analyze(longOne,  DefaultScenario()).SegmentTapers[0].TaperRatePer100Cm;

        Assert.Equal(kShort / 2.0, kLong, precision: 9);
    }

    [Fact]
    public void TaperRate_TracksDensity_NotJustDiameter()
    {
        // rho*d, not d: a zone changes the rate even where the drawn diameters are identical.
        var plain = ZonedCylinder(false);
        var zoned = ZonedCylinder(true);

        var pk = ProfileAnalyzer.Analyze(plain, DefaultScenario()).SegmentTapers;
        var zk = ProfileAnalyzer.Analyze(zoned, DefaultScenario()).SegmentTapers;

        Assert.True(pk[0].IsCylindrical);                       // drawn as one cylinder
        Assert.False(zk.All(t => t.IsCylindrical));             // the zone reshapes it
    }

    [Fact]
    public void SegmentTapers_AreKeyedToNodes_AndTakeTheirNameFromMetadataWhenItMatches()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        project.SegmentMetadata.Add(new SegmentMetadata { StartCm = 0, EndCm = 100, Name = "S1" });

        var r = ProfileAnalyzer.Analyze(project, DefaultScenario());

        var only = Assert.Single(r.SegmentTapers);
        Assert.Equal("S1", only.Name);
        Assert.Equal(0.0, only.StartCm, precision: 9);
        Assert.Equal(100.0, only.EndCm, precision: 9);
        Assert.True(only.MassG > 0);
    }

    [Fact]
    public void SegmentTapers_SurviveMetadataThatDriftedOutOfSyncWithTheNodes()
    {
        // Keyed to the nodes, so stale metadata costs a name and nothing else.
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        project.SegmentMetadata.Add(new SegmentMetadata { StartCm = 7, EndCm = 93, Name = "stale" });

        var r = ProfileAnalyzer.Analyze(project, DefaultScenario());

        var only = Assert.Single(r.SegmentTapers);
        Assert.Equal(string.Empty, only.Name);
        Assert.Equal(0.0, only.StartCm, precision: 9);
        Assert.False(double.IsNaN(only.TaperRatePer100Cm));
    }

    [Fact]
    public void ContinuityIndex_ProducesNaN_WhenSpacingIsDegenerate()
    {
        var pi = new[] { 1.0, 2.0, 3.0 };
        var xs = new[] { 0.0, 0.0, 10.0 };

        var c = StabilityMetrics.ContinuityIndex(xs, pi);

        Assert.True(double.IsNaN(c[0]) || double.IsNaN(c[1]));
        Assert.False(double.IsInfinity(c[2]));
    }

    [Fact]
    public void BareTaper_IsAnalyzedAsShootingHead_AndTowsTheShootingLine()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        var scenario = DefaultScenario();

        var report = ProfileAnalyzer.Analyze(project, scenario);

        Assert.Equal(LineKind.ShootingHead, report.Kind);
        Assert.True(report.XsCm.Length > report.DesignSliceCount);
        Assert.Equal(100.0 + scenario.ShootingLine.LengthCm, report.XsCm[^1], precision: 6);

        // The mono carries no core, whatever core the fly line itself declares.
        double expectedTail = Physics.MassLinearCalculator.LinearMassSolid(
            scenario.ShootingLine.DiameterMm, scenario.ShootingLine.DensityGCm3);
        Assert.Equal(expectedTail, report.LinearMassKgM[^1], precision: 12);
    }

    [Fact]
    public void ShootingLineCore_IsNotInheritedFromTheFlyLine()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        project.CoreDiameterMm = 0.30;
        project.CoreDensityGCm3 = 1.30;
        var scenario = DefaultScenario();

        var report = ProfileAnalyzer.Analyze(project, scenario);

        Assert.Equal(
            Physics.MassLinearCalculator.LinearMassSolid(
                scenario.ShootingLine.DiameterMm, scenario.ShootingLine.DensityGCm3),
            report.LinearMassKgM[^1], precision: 12);
    }

    [Fact]
    public void LongTrailingLevelRun_IsDetectedAsAFullLine_AndTowsNothing()
    {
        // Head down to a running line, then 10 m of it — the shape of every full line in the archive.
        var project = new FlyLineProject
        {
            UseSharedDensity = true,
            SharedDensityGCm3 = 0.95,
            DesignNodes = new()
            {
                new DesignNode { X = 0,    Y = 0.90 },
                new DesignNode { X = 1500, Y = 1.56 },
                new DesignNode { X = 1700, Y = 0.75 },
                new DesignNode { X = 2700, Y = 0.75 },
            },
        };

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.Equal(LineKind.FullLine, report.Kind);
        Assert.Null(report.Junction);
        Assert.Equal(report.DesignSliceCount, report.XsCm.Length);
    }

    [Fact]
    public void JunctionStep_IsTheInertialTaperRatioAcrossTheJoint()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 0.96);
        var scenario = DefaultScenario();

        var report = ProfileAnalyzer.Analyze(project, scenario);

        var j = Assert.IsType<JunctionMetrics>(report.Junction);
        Assert.Equal(100.0, j.PositionCm, precision: 6);
        Assert.Equal(0.96 * 1.0, j.InertialTaperBefore, precision: 9);
        Assert.Equal(1.14 * 0.40, j.InertialTaperAfter, precision: 9);
        Assert.Equal(0.96 / (1.14 * 0.40), j.StepRatio, precision: 6);
    }

    [Fact]
    public void ExplicitKind_OverridesDetection()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        var scenario = DefaultScenario();
        scenario.Kind = LineKind.FullLine;

        var report = ProfileAnalyzer.Analyze(project, scenario);

        Assert.Equal(LineKind.FullLine, report.Kind);
        Assert.Null(report.Junction);
    }

    [Fact]
    public void InertialTaper_IsDensityTimesDiameter()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 0.96);

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.Equal(0.96 * 2.0, report.InertialTaper[0], precision: 9);
        Assert.Equal(0.96 * 1.0, report.InertialTaper[report.DesignSliceCount - 1], precision: 9);
    }

    [Fact]
    public void ScanDesignDelta_IsNaNOverTheShootingLine()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        project.ScanPoints.Add(new ScanPoint { X = 0,   FilteredY = 2.0 });
        project.ScanPoints.Add(new ScanPoint { X = 100, FilteredY = 1.0 });

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        var delta = Assert.IsType<double[]>(report.ScanDesignDeltaMm);
        Assert.False(double.IsNaN(delta[report.DesignSliceCount - 1]));
        Assert.True(double.IsNaN(delta[^1]));
    }

    /// <summary>
    /// A cylinder with a denser zone over its first 200 cm, materials as a real file has them:
    /// M1 is the base and the zone is M2.
    /// </summary>
    private static FlyLineProject ZonedCylinder(bool withZone, bool adapt = true) {
        var p = new FlyLineProject {
            UseSharedDensity = true, SharedDensityGCm3 = 0.96,
            ZoneDensityAdaptDiameters = adapt,
            DesignNodes = new() {
                new DesignNode { X = 0,   Y = 1.00 },
                new DesignNode { X = 500, Y = 1.00 },
            },
            NozzleDefinitions = { new NozzleDefinition { DensityGCm3 = 0.96 } },
        };
        if (withZone) {
            p.NozzleDefinitions.Add(new NozzleDefinition { DensityGCm3 = 1.10 });
            p.NozzleZones.Add(new NozzleZone { StartCm = 0, EndCm = 200, NozzleIndex = 1 });
        }
        return p;
    }

    [Fact]
    public void Zone_PreservesMassInside_AndReshapesTheSegmentOutside()
    {
        // The app treats the zone edge as an exact node and reshapes the segment *just outside*:
        // its near end takes the zone's scaled diameter, its far end stays as drawn. So mass is
        // preserved inside the zone — Stefano's point, thinner at equal mass — and the reshaped
        // outside segment is what gives mass up.
        var plain = ProfileAnalyzer.Analyze(ZonedCylinder(false), DefaultScenario());
        var zoned = ProfileAnalyzer.Analyze(ZonedCylinder(true), DefaultScenario());

        double f = Math.Sqrt(0.96 / 1.10);
        Assert.Equal(1.00 * f, zoned.Diameter[100], precision: 9);
        Assert.Equal(plain.LinearMassKgM[100], zoned.LinearMassKgM[100], precision: 12);

        // Just outside the edge the line is pulled down to the zone's value, then ramps back.
        Assert.True(zoned.Diameter[201] < plain.Diameter[201]);
        Assert.Equal(1.00, zoned.Diameter[500], precision: 9);

        // The reshaped segment is the accepted cost: the head is lighter than drawn.
        int n = zoned.DesignSliceCount;
        Assert.True(zoned.CumulativeMassG[n - 1] < plain.CumulativeMassG[n - 1]);
    }

    [Fact]
    public void ZoneEdge_KeepsTheDiameterContinuous_AndPutsTheWholeJumpIntoTheInertialTaper()
    {
        var r = ProfileAnalyzer.Analyze(ZonedCylinder(true), DefaultScenario());

        // Continuous by construction — one node, one value, shared by both sides.
        Assert.Equal(r.Diameter[199], r.Diameter[201], precision: 3);

        // With the diameter continuous, the whole material jump lands in rho*d — the full ratio,
        // not its square root.
        // Precision 2: indices 199 and 201 straddle the edge by a centimetre each and the outside
        // segment ramps, so the ratio approaches 1.1458 rather than hitting it. Still nowhere near
        // the sqrt(1.10/0.96) = 1.070 a pointwise mass-preserving scale would give.
        Assert.Equal(1.10 / 0.96, r.InertialTaper[199] / r.InertialTaper[201], precision: 2);

        // And so does the linear mass: it steps by the density ratio, the difference the mechanism
        // accepts.
        Assert.Equal(1.10 / 0.96, r.LinearMassKgM[199] / r.LinearMassKgM[201], precision: 2);
    }

    [Fact]
    public void ZoneOfTheBaseMaterial_IsANoOp()
    {
        // Within DensityMergeThreshold of M1 it is the same material, so nothing is reshaped.
        var p = ZonedCylinder(true);
        p.NozzleDefinitions[1].DensityGCm3 = 0.96;

        var zoned = ProfileAnalyzer.Analyze(p, DefaultScenario());
        var plain = ProfileAnalyzer.Analyze(ZonedCylinder(false), DefaultScenario());

        Assert.Equal(plain.Diameter[100], zoned.Diameter[100], precision: 12);
        Assert.Equal(plain.InertialTaper[300], zoned.InertialTaper[300], precision: 12);
        Assert.Empty(zoned.Shape!.BackupSpots);
    }

    [Fact]
    public void WithoutMassAdaptation_TheDrawnDiameterIsKept_AndOnlyDensityChanges()
    {
        var r = ProfileAnalyzer.Analyze(ZonedCylinder(true, adapt: false), DefaultScenario());

        Assert.Equal(1.00, r.Diameter[100], precision: 9);
        Assert.Equal(1.00, r.Diameter[300], precision: 9);
        Assert.Equal(1.10 * 1.00, r.InertialTaper[100], precision: 9);
    }

    [Fact]
    public void DensityZoneOnAFrontTaper_ShowsAsAFrontBackup_AtTheZoneEdge()
    {
        // The archive case: a monotone diameter taper with a denser front-taper zone on top.
        FlyLineProject Build(bool withZone) {
            var p = new FlyLineProject {
                UseSharedDensity = true, SharedDensityGCm3 = 0.96,
                ZoneDensityAdaptDiameters = true,
                DesignNodes = new() {
                    new DesignNode { X = 0,    Y = 0.86 },
                    new DesignNode { X = 310,  Y = 1.11 },
                    new DesignNode { X = 830,  Y = 1.47 },
                    new DesignNode { X = 1000, Y = 1.56 },
                },
                NozzleDefinitions = { new NozzleDefinition { DensityGCm3 = 0.96 } },
            };
            if (withZone) {
                p.NozzleDefinitions.Add(new NozzleDefinition { DensityGCm3 = 1.10 });
                p.NozzleZones.Add(new NozzleZone { StartCm = 0, EndCm = 310, NozzleIndex = 1 });
            }
            return p;
        }

        var zoned = ProfileAnalyzer.Analyze(Build(true), DefaultScenario());
        var shape = Assert.IsType<ShapeMetrics>(zoned.Shape);
        Assert.True(shape.FrontBackupFraction > 0);
        var spot = Assert.Single(shape.BackupSpots);
        Assert.InRange(spot.PositionCm, 305, 310);

        // Same taper without the zone is clean — so it is the density, not the shape.
        var clean = ProfileAnalyzer.Analyze(Build(false), DefaultScenario());
        Assert.Equal(0.0, clean.Shape!.FrontBackupFraction);
        Assert.Empty(clean.Shape.BackupSpots);
    }

    [Fact]
    public void ProjectWithNoDensityAnywhere_IsFlagged_RatherThanReportingZeroes()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 0.0);

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.False(report.HasDensityData);
    }

    [Fact]
    public void MonotoneTaper_HasNoBackup_AndDensityIsCarriedIntoTheShape()
    {
        var project = LinearTaper(d0Mm: 1.0, lengthCm: 100.0, d1Mm: 2.0, densityGCm3: 0.96);

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        var shape = Assert.IsType<ShapeMetrics>(report.Shape);
        Assert.True(report.HasDensityData);
        Assert.Equal(0.0, shape.FrontBackupFraction);
        Assert.Equal(100.0, shape.PeakPositionCm, precision: 6);
        Assert.Equal(0.96 * 2.0, shape.PeakInertialTaper, precision: 9);
    }
}
