using FlyLinePhysics.Materials;
using FlyLinePhysics.Physics;
using Xunit;

namespace FlyLinePhysics.Tests;

public class ReynoldsCalculatorTests
{
    // Sanity checks against the two reference points quoted in the source paper itself
    // (articlesportsengineeringrev4d.pdf, section 2.1.1): "the Reynolds number based on diameter d
    // varies from the order 1 (velocity 0.1 m/s and diameter 0.2e-3 m at the end of the leader) to
    // the order 10^3 (velocity 25 m/s and diameter 1.2e-3 m for the fly line)" — both inside the
    // correlation's stated validity range, 1 < Re < 2000.

    [Fact]
    public void Reynolds_AtLeaderTip_IsOrderOne()
    {
        double re = ReynoldsCalculator.Reynolds(
            diameterM: 0.2e-3, velocityMs: 0.1,
            rhoAirKgM3: AirProperties.RhoAirKgM3, muAirPaS: AirProperties.MuAirPaS);

        Assert.InRange(re, 1.0, 2.0);
    }

    [Fact]
    public void Reynolds_AtFlyLine_IsOrderOfSeveralThousand()
    {
        double re = ReynoldsCalculator.Reynolds(
            diameterM: 1.2e-3, velocityMs: 25.0,
            rhoAirKgM3: AirProperties.RhoAirKgM3, muAirPaS: AirProperties.MuAirPaS);

        Assert.InRange(re, 1500.0, 2500.0);
    }

    [Fact]
    public void Reynolds_IsInsensitiveToVelocitySign()
    {
        double rePositive = ReynoldsCalculator.Reynolds(1e-3, 10.0, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        double reNegative = ReynoldsCalculator.Reynolds(1e-3, -10.0, AirProperties.RhoAirKgM3, AirProperties.MuAirPaS);
        Assert.Equal(rePositive, reNegative);
    }
}
