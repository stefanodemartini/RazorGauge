using FlyLinePhysics.Physics;
using Xunit;

namespace FlyLinePhysics.Tests;

public class MassLinearCalculatorTests
{
    [Fact]
    public void LinearMassSolid_MatchesHandCalculation()
    {
        // d = 1 mm, rho = 1.0 g/cm3 -> m = 1000 kg/m3 * pi/4 * (0.001 m)^2 = 7.853981...e-4 kg/m
        double m = MassLinearCalculator.LinearMassSolid(outerDiameterMm: 1.0, coatingDensityGCm3: 1.0);
        Assert.Equal(7.853981633974483e-4, m, precision: 12);
    }

    [Fact]
    public void LinearMassCored_EqualsSolidCore_WhenCoreFillsWholeDiameter()
    {
        // When the core diameter equals the outer diameter, the coating annulus vanishes and the
        // whole cross-section is core material.
        double cored = MassLinearCalculator.LinearMassCored(
            outerDiameterMm: 1.0, coatingDensityGCm3: 0.9,
            coreDiameterMm: 1.0, coreDensityGCm3: 1.38);
        double solidAtCoreDensity = MassLinearCalculator.LinearMassSolid(1.0, 1.38);

        Assert.Equal(solidAtCoreDensity, cored, precision: 12);
    }

    [Fact]
    public void LinearMassCored_ClampsCoreArea_WhenCoreWiderThanOuter()
    {
        // Inconsistent input (core wider than the finished line) must not go negative or throw —
        // clamp to "all core", same as the core == outer case.
        double clamped = MassLinearCalculator.LinearMassCored(
            outerDiameterMm: 1.0, coatingDensityGCm3: 0.9,
            coreDiameterMm: 2.0, coreDensityGCm3: 1.38);
        double solidAtCoreDensity = MassLinearCalculator.LinearMassSolid(1.0, 1.38);

        Assert.Equal(solidAtCoreDensity, clamped, precision: 12);
    }

    [Fact]
    public void LinearMass_FallsBackToSolid_WhenCoreFieldsAreNull()
    {
        double viaDispatch = MassLinearCalculator.LinearMass(1.2, 0.95, null, null);
        double direct = MassLinearCalculator.LinearMassSolid(1.2, 0.95);
        Assert.Equal(direct, viaDispatch, precision: 12);
    }

    [Fact]
    public void CumulativeMassG_IsZeroAtStart_AndMatchesUniformCylinderAnalytically()
    {
        // A uniform 1 m long, 1 mm diameter, 1 g/cm3 cylinder: mass = rho * volume =
        // 1 g/cm3 * (pi/4 * 0.1cm^2 * 100cm) = pi/4 * 100 * 0.01 g ~= 0.7853981... g
        double mKgM = MassLinearCalculator.LinearMassSolid(1.0, 1.0);
        var xs = new double[] { 0, 50, 100 };
        var m = new double[] { mKgM, mKgM, mKgM };

        var cumulative = MassLinearCalculator.CumulativeMassG(xs, m);

        Assert.Equal(0, cumulative[0]);
        Assert.Equal(Math.PI / 4.0 * 100.0 * 0.01, cumulative[^1], precision: 6);
    }

    [Fact]
    public void LinearMassSolid_ReturnsZero_ForNonPositiveInputs()
    {
        Assert.Equal(0.0, MassLinearCalculator.LinearMassSolid(0.0, 1.0), precision: 12);
        Assert.Equal(0.0, MassLinearCalculator.LinearMassSolid(1.0, -0.5), precision: 12);
    }
}
