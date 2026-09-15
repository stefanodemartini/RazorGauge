using FlyLinePhysics.Model;

namespace FlyLinePhysics.Analysis;

/// <summary>Result of <see cref="ProfileAnalyzer.Analyze"/>: per-slice arrays plus per-segment scores.</summary>
public class AnalysisReport
{
    /// <summary>Slice centres, cm from the tip — the common grid every array below is sampled on.</summary>
    public double[] XsCm { get; set; } = Array.Empty<double>();
    public double[] LinearMassKgM { get; set; } = Array.Empty<double>();
    public double[] CumulativeMassG { get; set; } = Array.Empty<double>();

    /// <summary>|scan − design| diameter per slice, in mm. Null when the project has no scan points.</summary>
    public double[]? ScanDesignDeltaMm { get; set; }

    /// <summary>One series per <see cref="CastScenario.VelocitiesMs"/> entry, same order.</summary>
    public List<VelocitySeries> ByVelocity { get; set; } = new();

    public List<SegmentScore> SegmentScores { get; set; } = new();
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

/// <summary>The 0-100 synthetic score for one SegmentMetadata entry, and the components behind it.</summary>
public class SegmentScore
{
    public SegmentMetadata Segment { get; set; } = new();
    public double Score { get; set; }
    public double MeanPi { get; set; }
    public double PiVariance { get; set; }
    public double MaxContinuityAtTransitions { get; set; }
    public double MeanScanDesignDeltaMm { get; set; }
}
