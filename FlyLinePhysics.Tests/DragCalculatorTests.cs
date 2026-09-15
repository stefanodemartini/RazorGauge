using FlyLinePhysics.Materials;
using FlyLinePhysics.Physics;
using Xunit;

namespace FlyLinePhysics.Tests;

public class DragCalculatorTests
{
    // Reference values computed independently (Python, not from this implementation) from eq. (5)
    // and (6) of the source paper, to lock the exact formula and catch silent regressions.

    [Theory]
    [InlineData(1.2e-3, 25.0, 0.46510930782824883)]
    [InlineData(0.6e-3, 15.0, 0.08770928334688058)]
    public void NormalDrag_MatchesIndependentReferenceValue(double diameterM, double velocityMs, double expected)
    {
        double fn = DragCalculator.NormalDrag(diameterM, velocityMs, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        Assert.Equal(expected, fn, precision: 10);
    }

    [Theory]
    [InlineData(1.2e-3, 25.0, 0.005926254271852945)]
    [InlineData(0.6e-3, 15.0, 0.0020759629683661405)]
    public void TangentialDrag_MatchesIndependentReferenceValue(double diameterM, double velocityMs, double expected)
    {
        double fs = DragCalculator.TangentialDrag(diameterM, velocityMs, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        Assert.Equal(expected, fs, precision: 10);
    }

    [Fact]
    public void NormalDrag_IsOddFunctionOfVelocity()
    {
        double positive = DragCalculator.NormalDrag(1e-3, 20.0, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        double negative = DragCalculator.NormalDrag(1e-3, -20.0, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        Assert.Equal(-positive, negative, precision: 12);
    }

    [Fact]
    public void NormalDrag_IsZero_AtZeroVelocity()
    {
        double fn = DragCalculator.NormalDrag(1e-3, 0.0, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        Assert.Equal(0.0, fn);
    }
}
