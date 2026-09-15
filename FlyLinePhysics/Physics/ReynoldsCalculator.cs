namespace FlyLinePhysics.Physics;

/// <summary>Reynolds number for flow around a line cross-section: Re = ρ_air·|v|·d/μ_air.</summary>
public static class ReynoldsCalculator
{
    /// <param name="diameterM">Characteristic diameter, in metres.</param>
    /// <param name="velocityMs">Characteristic velocity, in m/s.</param>
    public static double Reynolds(double diameterM, double velocityMs, double rhoAirKgM3, double muAirPaS) =>
        rhoAirKgM3 * Math.Abs(velocityMs) * diameterM / muAirPaS;
}
