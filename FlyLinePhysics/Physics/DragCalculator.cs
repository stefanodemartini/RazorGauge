namespace FlyLinePhysics.Physics;

/// <summary>
/// Reynolds-number-dependent aerodynamic drag per unit length, normal and tangential to the line —
/// eq. (5) and (6) of Ekander, Perkins &amp; Richards, "Development of a simulation model for fly
/// casting and application to overhead casting" (see FlyLinePhysics/docs/references/
/// articlesportsengineeringrev4d.pdf), a Hoerner-style correlation fitted to experimental data for
/// 1 &lt; Re &lt; 2000. Constants confirmed against the paper's own eq. (5)-(6).
/// </summary>
public static class DragCalculator
{
    private const double ZetaN0 = 1.0;
    private const double ZetaN  = 10.0;
    private const double MN     = -0.75;

    private const double ZetaS0 = 0.0022;
    private const double ZetaS  = 2.0;
    private const double MS     = -0.91;

    /// <summary>
    /// f_n,drag [N/m]: drag normal to the line.
    /// f_n = ζn,0·d·(ρair·|un|·un)/2 + ζn·(ρair·d/μair)^mn · d · 0.5·ρair·|un|^(1+mn)·un
    /// </summary>
    public static double NormalDrag(double diameterM, double velocityNormalMs, double rhoAirKgM3, double muAirPaS)
    {
        double un = velocityNormalMs;
        double reynoldsTerm = Math.Pow(rhoAirKgM3 * diameterM / muAirPaS, MN);
        double term1 = ZetaN0 * diameterM * (rhoAirKgM3 * Math.Abs(un) * un) / 2.0;
        double term2 = ZetaN * reynoldsTerm * diameterM * 0.5 * rhoAirKgM3 * Math.Pow(Math.Abs(un), 1.0 + MN) * un;
        return term1 + term2;
    }

    /// <summary>
    /// f_s,drag [N/m]: drag tangential to the line (skin friction).
    /// f_s = ζs,0·π·d·(ρair/2)·|us|·us + ζs·(ρair·d/μair)^ms · π·d · 0.5·ρair·|us|^(1+ms)·us
    /// </summary>
    public static double TangentialDrag(double diameterM, double velocityTangentialMs, double rhoAirKgM3, double muAirPaS)
    {
        double us = velocityTangentialMs;
        double reynoldsTerm = Math.Pow(rhoAirKgM3 * diameterM / muAirPaS, MS);
        double term1 = ZetaS0 * Math.PI * diameterM * (rhoAirKgM3 / 2.0) * Math.Abs(us) * us;
        double term2 = ZetaS * reynoldsTerm * Math.PI * diameterM * 0.5 * rhoAirKgM3 * Math.Pow(Math.Abs(us), 1.0 + MS) * us;
        return term1 + term2;
    }
}
