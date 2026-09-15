using FlyLinePhysics.Materials;

namespace FlyLinePhysics.Analysis;

/// <summary>
/// Cast conditions used to evaluate a profile — separate from the .flp file itself, since the same
/// line design can be analyzed under different casting conditions.
/// </summary>
public class CastScenario
{
    public double AirDensityKgM3  { get; set; } = AirProperties.RhoAirKgM3;
    public double AirViscosityPaS { get; set; } = AirProperties.MuAirPaS;

    /// <summary>Reference velocities (m/s) overlaid in the report/chart.</summary>
    public List<double> VelocitiesMs { get; set; } = new() { 15, 25, 35 };

    /// <summary>Which of <see cref="VelocitiesMs"/> is used for the per-segment synthetic score.</summary>
    public double VelocityReferenceMs { get; set; } = 25;

    /// <summary>
    /// Reference acceleration (m/s²) used for Π. No default: there is no single authoritative value
    /// for this in the source paper (it depends on casting stroke and tackle) — must be supplied
    /// explicitly, or calibrated once we have real results to compare against.
    /// </summary>
    public required double AccelerationRefMs2 { get; set; }

    /// <summary>
    /// C(s) warning threshold. Null (default) means no warnings are raised — we don't have a
    /// calibrated value yet; set explicitly once we do.
    /// </summary>
    public double? ContinuityWarningThreshold { get; set; }
}
