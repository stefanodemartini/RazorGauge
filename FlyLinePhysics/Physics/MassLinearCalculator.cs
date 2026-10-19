namespace FlyLinePhysics.Physics;

/// <summary>
/// Linear mass m(s) [kg/m] of a line cross-section, and its cumulative integral M(s) [g].
/// Models the cross-section as a solid coating cylinder, or — when a core is defined — two
/// concentric cylinders (core + coating annulus).
/// </summary>
public static class MassLinearCalculator
{
    /// <summary>
    /// m(s) in kg/m for a solid cross-section of the given outer diameter and coating density.
    /// </summary>
    public static double LinearMassSolid(double outerDiameterMm, double coatingDensityGCm3)
    {
        if (outerDiameterMm <= 0.0 || coatingDensityGCm3 <= 0.0)
            return 0.0;

        double dM = outerDiameterMm / 1000.0;
        double rhoKgM3 = coatingDensityGCm3 * 1000.0;
        return rhoKgM3 * Math.PI / 4.0 * dM * dM;
    }

    /// <summary>
    /// m(s) in kg/m for a cored cross-section: a core cylinder of <paramref name="coreDiameterMm"/>
    /// at <paramref name="coreDensityGCm3"/>, surrounded by a coating annulus up to
    /// <paramref name="outerDiameterMm"/> at <paramref name="coatingDensityGCm3"/>. When
    /// <paramref name="coreDiameterMm"/> exceeds <paramref name="outerDiameterMm"/> (inconsistent
    /// data — the core can't be wider than the finished line), the coating annulus area is clamped
    /// to zero rather than going negative.
    /// </summary>
    public static double LinearMassCored(
        double outerDiameterMm, double coatingDensityGCm3,
        double coreDiameterMm, double coreDensityGCm3)
    {
        if (outerDiameterMm <= 0.0)
            return 0.0;

        double dOuterM = outerDiameterMm / 1000.0;
        double dCoreM = Math.Max(0.0, Math.Min(coreDiameterMm, outerDiameterMm)) / 1000.0;
        double rhoCoatingKgM3 = Math.Max(0.0, coatingDensityGCm3) * 1000.0;
        double rhoCoreKgM3 = Math.Max(0.0, coreDensityGCm3) * 1000.0;

        double coreArea = Math.PI / 4.0 * dCoreM * dCoreM;
        double coatingArea = Math.PI / 4.0 * (dOuterM * dOuterM - dCoreM * dCoreM);

        if (coatingArea < 0.0) coatingArea = 0.0;

        return rhoCoreKgM3 * coreArea + rhoCoatingKgM3 * coatingArea;
    }

    /// <summary>
    /// m(s) in kg/m — dispatches to <see cref="LinearMassCored"/> when both core fields are set,
    /// otherwise falls back to <see cref="LinearMassSolid"/> (the "coating pieno" model, the only
    /// one possible for the vast majority of today's real .flp files, which predate the core
    /// fields).
    /// </summary>
    public static double LinearMass(
        double outerDiameterMm, double coatingDensityGCm3,
        double? coreDiameterMm, double? coreDensityGCm3)
    {
        return coreDiameterMm is double dCore && coreDensityGCm3 is double rhoCore
            ? LinearMassCored(outerDiameterMm, coatingDensityGCm3, dCore, rhoCore)
            : LinearMassSolid(outerDiameterMm, coatingDensityGCm3);
    }

    /// <summary>
    /// M(s) in grams: cumulative trapezoidal integral of m(s) [kg/m] along xsCm [cm], converted to
    /// grams (kg/m · m · 1000 = g). Returns an array the same length as <paramref name="xsCm"/>,
    /// where result[0] = 0 and result[i] = mass of the line from xsCm[0] to xsCm[i].
    /// </summary>
    public static double[] CumulativeMassG(IReadOnlyList<double> xsCm, IReadOnlyList<double> linearMassKgM)
    {
        if (xsCm.Count != linearMassKgM.Count)
            throw new ArgumentException("xsCm and linearMassKgM must have the same length.");

        var result = new double[xsCm.Count];
        for (int i = 1; i < xsCm.Count; i++)
        {
            double dxM = (xsCm[i] - xsCm[i - 1]) / 100.0;
            double avgKgM = (linearMassKgM[i] + linearMassKgM[i - 1]) / 2.0;
            result[i] = result[i - 1] + avgKgM * dxM * 1000.0;
        }
        return result;
    }
}
