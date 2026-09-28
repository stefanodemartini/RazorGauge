namespace FlyLinePhysics.Analysis;

/// <summary>
/// What a shooting head tows behind it.
///
/// Deliberately *not* stored in the .flp: it describes how the line is fished, not the line itself.
/// The same head is cast on different shooting lines, so it lives here as an analysis parameter with
/// a global default rather than in the file format.
///
/// Defaults are Stefano's reference setup: 0.40 mm nylon monofilament, 40 m (the most he ever
/// carries). A full line needs none of this — its running line is already part of the profile.
/// </summary>
public class ShootingLineSpec
{
    public double DiameterMm  { get; set; } = 0.40;
    /// <summary>Nylon. Fluorocarbon would be ~1.78, which changes the junction step substantially.</summary>
    public double DensityGCm3 { get; set; } = 1.14;
    public double LengthCm    { get; set; } = 4000.0;

    /// <summary>ρ·d [g/cm³·mm] — the inertial taper value of the shooting line (see InertialTaper).</summary>
    public double InertialTaper => DensityGCm3 * DiameterMm;
}

/// <summary>
/// Which of the two structurally different systems a project describes. They cannot be compared
/// slice-for-slice without this: a full line carries its running line inside the profile, a shooting
/// head stops at its rear and tows a monofilament that is nowhere in the file.
/// </summary>
public enum LineKind
{
    /// <summary>Decide from the profile: a long constant-diameter trailing run means the running
    /// line is already part of it.</summary>
    Auto,
    ShootingHead,
    FullLine,
}
