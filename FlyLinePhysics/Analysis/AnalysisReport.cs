using FlyLinePhysics.Model;

namespace FlyLinePhysics.Analysis;

/// <summary>Result of <see cref="ProfileAnalyzer.Analyze"/>: per-slice arrays plus per-segment scores.</summary>
public class AnalysisReport
{
    /// <summary>Slice centres, cm from the tip — the common grid every array below is sampled on.</summary>
    public double[] XsCm { get; set; } = Array.Empty<double>();
    public double[] LinearMassKgM { get; set; } = Array.Empty<double>();

    /// <summary>Outer diameter per slice, mm — the *real* geometry, so inside a mass-preserving
    /// nozzle zone this is the adapted value, not what DesignNodes draw.</summary>
    public double[] Diameter { get; set; } = Array.Empty<double>();
    public double[] CumulativeMassG { get; set; } = Array.Empty<double>();

    /// <summary>
    /// ρ·d [g/cm³·mm] per slice — the "inertial taper".
    ///
    /// Within the diameters and speeds a fly line actually sees, the Re-dependent part of the normal
    /// drag is only 2-11% of the total, so Π ≈ 1.31·ρ·d·a/v² to within ~5%. Velocity and acceleration
    /// are therefore pure scale factors: they move Π's level but not its shape along s. Since
    /// castability and turnover depend on the shape, this curve carries the design information
    /// without needing either of them — which is why it, and not Π, is the one to reason about.
    ///
    /// The practical consequence is that diameter and density trade 1:1: −10% diameter at +10%
    /// density leaves the casting character unchanged.
    /// </summary>
    public double[] InertialTaper { get; set; } = Array.Empty<double>();

    /// <summary>
    /// How many leading entries of every array belong to the design profile. The rest, if any, is
    /// the appended shooting line. Equal to the array length for a full line.
    /// </summary>
    public int DesignSliceCount { get; set; }

    /// <summary>Which system this was analysed as, after resolving <see cref="LineKind.Auto"/>.</summary>
    public LineKind Kind { get; set; }

    /// <summary>The head-to-shooting-line handoff. Null for a full line, which has no such joint.</summary>
    public JunctionMetrics? Junction { get; set; }

    /// <summary>Shape of the inertial taper over the design profile. Null when it is too short to
    /// have a shape.</summary>
    public ShapeMetrics? Shape { get; set; }

    /// <summary>
    /// False when the project sets no density anywhere, so every mass, Π and ρ·d in this report is
    /// zero. Three files in the archive are like this — they carry a traced profile and no material
    /// — and silently reporting "0.0 g" for them reads like an answer instead of a missing input.
    /// </summary>
    public bool HasDensityData { get; set; }

    /// <summary>|scan − design| diameter per slice, in mm, NaN over the appended shooting line.
    /// Null when the project has no scan points.</summary>
    public double[]? ScanDesignDeltaMm { get; set; }

    /// <summary>One series per <see cref="CastScenario.VelocitiesMs"/> entry, same order.</summary>
    public List<VelocitySeries> ByVelocity { get; set; } = new();

    /// <summary>One entry per design-node interval, tip to butt.</summary>
    public List<SegmentTaper> SegmentTapers { get; set; } = new();
}

/// <summary>Re/drag/Π/C sampled on the report's common grid, for one cast velocity.</summary>
public class VelocitySeries
{
    public double VelocityMs { get; set; }
    public double[] Reynolds { get; set; } = Array.Empty<double>();
    public double[] NormalDragNPerM { get; set; } = Array.Empty<double>();
    public double[] TangentialDragNPerM { get; set; } = Array.Empty<double>();
    public double[] Pi { get; set; } = Array.Empty<double>();
    public double[] ContinuityIndex { get; set; } = Array.Empty<double>();

    /// <summary>True where ContinuityIndex exceeds CastScenario.ContinuityWarningThreshold (always
    /// false when the threshold is unset).</summary>
    public bool[] Warning { get; set; } = Array.Empty<bool>();
}

/// <summary>
/// How fast the inertial taper changes across one design-node interval — the readout a design
/// change actually moves.
///
/// The 0-100 synthetic score this replaces did not work: measured across 363 real segments it sat
/// between 70 and 75 for 94% of them, and the global shape metrics fared no better — changing a
/// front taper's length or diameters moved them either not at all or with the wrong sign, because
/// they were summaries of the whole line while a design change is local. This is keyed to the thing
/// that gets edited instead.
/// </summary>
public class SegmentTaper
{
    /// <summary>SegmentMetadata's name for this interval when there is one, else empty.</summary>
    public string Name { get; set; } = string.Empty;
    public double StartCm { get; set; }
    public double EndCm { get; set; }
    public double LengthCm => EndCm - StartCm;

    public double InertialTaperStart { get; set; }
    public double InertialTaperEnd { get; set; }

    /// <summary>Mass of this interval, grams.</summary>
    public double MassG { get; set; }

    /// <summary>
    /// ln(ρ·d_end / ρ·d_start) / L, per 100 cm. Positive where the line thickens butt-ward (front
    /// taper, belly), negative down the back taper, ~0 on a cylinder. A rate, so it compares across
    /// segments of different length and across designs; NaN if either end is non-positive.
    /// </summary>
    public double TaperRatePer100Cm { get; set; }

    /// <summary>Below <see cref="TaperReference.CylindricalBand"/> in magnitude — level, not tapered.</summary>
    public bool IsCylindrical => Math.Abs(TaperRatePer100Cm) <= TaperReference.CylindricalBand;
}

/// <summary>
/// What |TaperRatePer100Cm| looks like across Stefano's archive — 345 intervals over 52 designs,
/// measured, not chosen. Reference only: nothing here is a verdict, and the commercial band is the
/// tighter, more useful comparison of the two.
/// </summary>
public static class TaperReference
{
    /// <summary>Below this a segment is level rather than tapered.</summary>
    public const double CylindricalBand = 0.005;

    // Rising segments (front taper and belly), whole archive.
    public const double RisingP10 = 0.016;
    public const double RisingP25 = 0.037;
    public const double RisingMedian = 0.074;
    public const double RisingP75 = 0.093;
    public const double RisingP90 = 0.125;

    // Falling segments (back taper), whole archive — a far wider spread than the rising ones.
    public const double FallingP25 = 0.045;
    public const double FallingMedian = 0.126;
    public const double FallingP75 = 0.371;

    /// <summary>
    /// Rising segments of the copied commercial lines (SA MED, ICFS, Med Official). The SA MED's own
    /// six sit inside 0.073-0.103, tight enough to read as a deliberate design rule — against which
    /// the ST27/STD27 family's median is 0.046, about half as steep, spread over 0.007-0.644.
    /// </summary>
    public const double CommercialRisingLo = 0.065;
    public const double CommercialRisingHi = 0.103;
}

/// <summary>
/// The joint between a shooting head and its shooting line — the one discontinuity a head has by
/// construction and a full line does not.
///
/// It is reported on its own rather than folded into C(s) because it is not a defect: it is the
/// price of the shooting head, and what matters is its size, which the head's back taper controls.
/// </summary>
public class JunctionMetrics
{
    /// <summary>Where the head ends, cm from the tip.</summary>
    public double PositionCm { get; set; }

    /// <summary>ρ·d on the head side of the joint.</summary>
    public double InertialTaperBefore { get; set; }

    /// <summary>ρ·d on the shooting-line side.</summary>
    public double InertialTaperAfter { get; set; }

    /// <summary>Before/after — how abruptly the casting character changes across the joint.</summary>
    public double StepRatio { get; set; }

    /// <summary>Mass of the head itself, in grams.</summary>
    public double HeadMassG { get; set; }

    /// <summary>Mass of shooting line towed behind it, in grams.</summary>
    public double TowedMassG { get; set; }

    /// <summary>Towed mass as a fraction of the head mass — the shooting head's whole reason to exist.</summary>
    public double TowedMassFraction => HeadMassG > 0 ? TowedMassG / HeadMassG : double.NaN;
}
