using FlyLinePhysics.Analysis;
using FlyLinePhysics.Model;
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
        Assert.Equal(1.832595714594046, report.CumulativeMassG[^1], precision: 3);
    }

    [Fact]
    public void LinearMassKgM_MatchesSolidFormula_AtEnds()
    {
        var project = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        double expectedStart = Physics.MassLinearCalculator.LinearMassSolid(2.0, 1.0);
        double expectedEnd = Physics.MassLinearCalculator.LinearMassSolid(1.0, 1.0);

        Assert.Equal(expectedStart, report.LinearMassKgM[0], precision: 12);
        Assert.Equal(expectedEnd, report.LinearMassKgM[^1], precision: 12);
    }

    [Fact]
    public void SegmentScore_IsAlwaysWithinZeroToHundred()
    {
        // Deliberately extreme taper (1mm -> 20mm over 1cm) to try to push the score components to
        // their limits — must still clamp into [0,100], never NaN/negative/over 100.
        var project = LinearTaper(d0Mm: 1.0, lengthCm: 1.0, d1Mm: 20.0, densityGCm3: 5.0);
        project.SegmentMetadata.Add(new SegmentMetadata { StartCm = 0, EndCm = 1, Name = "Extreme" });

        var report = ProfileAnalyzer.Analyze(project, DefaultScenario());

        Assert.Single(report.SegmentScores);
        double score = report.SegmentScores[0].Score;
        Assert.False(double.IsNaN(score));
        Assert.InRange(score, 0.0, 100.0);
    }

    [Fact]
    public void SharpDiameterDiscontinuity_ScoresWorseThanSmoothTaper_OverTheSameWindow()
    {
        var scenario = DefaultScenario();

        var smooth = LinearTaper(d0Mm: 2.0, lengthCm: 100.0, d1Mm: 1.0, densityGCm3: 1.0);
        smooth.SegmentMetadata.Add(new SegmentMetadata { StartCm = 49, EndCm = 51, Name = "Window" });

        var sharp = new FlyLineProject
        {
            UseSharedDensity = true,
            SharedDensityGCm3 = 1.0,
            DesignNodes = new()
            {
                new DesignNode { X = 0, Y = 2.0 },
                new DesignNode { X = 49, Y = 2.0 },
                new DesignNode { X = 51, Y = 0.5 },   // abrupt step over a 2cm span
                new DesignNode { X = 100, Y = 0.5 },
            },
        };
        sharp.SegmentMetadata.Add(new SegmentMetadata { StartCm = 49, EndCm = 51, Name = "Window" });

        var smoothReport = ProfileAnalyzer.Analyze(smooth, scenario);
        var sharpReport = ProfileAnalyzer.Analyze(sharp, scenario);

        var smoothWindow = Assert.Single(smoothReport.SegmentScores);
        var sharpWindow = Assert.Single(sharpReport.SegmentScores);

        Assert.True(sharpWindow.MaxContinuityAtTransitions > smoothWindow.MaxContinuityAtTransitions,
            $"sharp Cmax={sharpWindow.MaxContinuityAtTransitions} should exceed smooth Cmax={smoothWindow.MaxContinuityAtTransitions}");
        Assert.True(sharpWindow.Score < smoothWindow.Score,
            $"sharp score={sharpWindow.Score} should be lower than smooth score={smoothWindow.Score}");
    }
}
