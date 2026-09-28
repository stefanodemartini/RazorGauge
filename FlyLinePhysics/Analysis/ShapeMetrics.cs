namespace FlyLinePhysics.Analysis;

/// <summary>
/// Shape properties of the inertial taper ρ·d over the design profile.
///
/// All three are dimensionless and velocity-free — they describe the *form* of the curve, which is
/// what castability and turnover depend on, not its level (see AnalysisReport.InertialTaper for why
/// the level carries no design information). None of them uses the scan: the design is the real
/// data, the scan is a trace.
/// </summary>
public class ShapeMetrics
{
    /// <summary>Where ρ·d peaks — the belly. Splits the profile into the front taper, which does the
    /// turnover, and the back taper, which hands off to the shooting line.</summary>
    public double PeakPositionCm { get; set; }
    public double PeakInertialTaper { get; set; }

    /// <summary>
    /// How much ρ·d backs up on the way to the tip, as a fraction of the total peak-to-tip drop.
    /// Zero means it falls monotonically. Anything above zero is a spot where the line ahead is
    /// heavier in inertial terms than the line behind it — where a loop hinges or stalls.
    /// </summary>
    public double FrontBackupFraction { get; set; }

    /// <summary>
    /// Where ρ·d climbs on the way to the tip, tip-ward order, with the size of each climb as a
    /// fraction of the peak-to-tip drop. The fraction alone says a line has a hinge; this says where
    /// to go and look. In the archive these land exactly on density-zone edges, which is the point:
    /// the diameter taper there is perfectly smooth and shows nothing.
    /// </summary>
    public List<(double PositionCm, double Fraction)> BackupSpots { get; set; } = new();

    /// <summary>Median of |Δ(ρ·d)/Δs|/(ρ·d) over the design — the line's own baseline taper rate.</summary>
    public double MedianContinuity { get; set; }

    /// <summary>99th percentile of the same.</summary>
    public double P99Continuity { get; set; }

    /// <summary>
    /// P99/median — how far the sharpest local event stands out against this line's own background.
    /// Scale-free on purpose: a steep taper is not a defect, a step against a steady taper is. This
    /// is what catches a density zone landing badly on an otherwise smooth diameter taper.
    /// </summary>
    public double ContinuitySpikiness { get; set; }
}
