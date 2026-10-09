namespace FlyLinePhysics.Model;

/// <summary>
/// Serializable model for a FlyLine Profiler project (.flp file) — a twin of
/// DiametroLineaDesktop.Models.FlyLineProject kept in this library so FlyLinePhysics can read/
/// write the same file format without depending on the WPF assembly (that would create a
/// reference cycle, since the WPF app depends on this library, not the other way round).
/// Field names and JSON shape must stay in lockstep with the WPF-side model by hand.
/// </summary>
public class FlyLineProject
{
    /// <summary>
    /// Schema version. Default stays 1 — matching every existing .flp file, which either has no
    /// "Version" key at all (pre-dating the field) or "Version": 1 — so a file missing the key
    /// deserializes as what it actually is, schema v1, not silently promoted to v2. Code that
    /// explicitly populates <see cref="CoreDiameterMm"/>/<see cref="CoreDensityGCm3"/> should set
    /// this to 2 itself when saving.
    /// </summary>
    public int Version { get; set; } = 1;

    public string   Name       { get; set; } = "Untitled";
    public DateTime CreatedAt  { get; set; } = DateTime.UtcNow;
    public DateTime ModifiedAt { get; set; } = DateTime.UtcNow;
    public string   Notes      { get; set; } = string.Empty;

    public bool   UseSharedDensity  { get; set; } = true;
    public double SharedDensityGCm3 { get; set; } = 0.0;

    public bool IsSinking  { get; set; } = false;
    /// <summary>"Floating", "Neutral" or "Sinking"; empty in files written before it existed, which
    /// are read from <see cref="IsSinking"/>. Carried so a round-trip through Save does not drop it
    /// — this library only reads the geometry, but it rewrites whole files.</summary>
    public string LineType { get; set; } = string.Empty;
    public bool IsFullLine { get; set; } = false;

    public string WaterType   { get; set; } = "fresh";
    public double WaterTempC  { get; set; } = 20.0;

    public List<ScanPoint>       ScanPoints       { get; set; } = new();
    public List<ImportedSeries>  ImportedSeries   { get; set; } = new();
    public List<DesignNode>      DesignNodes      { get; set; } = new();
    public List<SegmentMetadata> SegmentMetadata  { get; set; } = new();
    public List<NodeLabelOffset> NodeLabelOffsets { get; set; } = new();
    public string DesignLineColorHex { get; set; } = "DC3232";
    public string ColorNote          { get; set; } = string.Empty;
    public string CoreType           { get; set; } = string.Empty;
    public string LaserMark          { get; set; } = string.Empty;
    public string LaserMarkFromTipMm { get; set; } = string.Empty;
    public string LaserMarkFromEndMm { get; set; } = string.Empty;
    public List<LineColorSection> ColorSections { get; set; } = new();

    public List<NozzleDefinition> NozzleDefinitions { get; set; } = new();
    public List<NozzleZone>       NozzleZones       { get; set; } = new();

    public double CompTargetSpeedMs         { get; set; } = 0.0;
    public bool   ShowCompProfile           { get; set; } = false;
    public bool   IsCompensatedDerivative   { get; set; } = false;
    public bool   ZoneDensityAdaptDiameters { get; set; } = true;

    /// <summary>
    /// Core (anima) diameter in mm, shared by the whole line — a braided core normally runs a
    /// fixed diameter under a coating whose thickness is what actually shapes the taper. Null when
    /// unset: files saved before this field existed, or a design that hasn't modelled a core yet.
    /// Only meaningful together with <see cref="CoreDensityGCm3"/>.
    /// </summary>
    public double? CoreDiameterMm { get; set; }

    /// <summary>Core (anima) density in g/cm³ — see <see cref="CoreDiameterMm"/>.</summary>
    public double? CoreDensityGCm3 { get; set; }
}

/// <summary>One nozzle = one material: a fixed (colour, density) compound.</summary>
public class NozzleDefinition
{
    public string ColorHex    { get; set; } = "DC3232";
    public double DensityGCm3 { get; set; } = 0.0;
    public string Label       { get; set; } = string.Empty;
}

/// <summary>A zone on the line that is extruded by a single nozzle.</summary>
public class NozzleZone
{
    public double StartCm     { get; set; }
    public double EndCm       { get; set; }
    public int    NozzleIndex { get; set; }
}

/// <summary>A raw acquired point: X in cm, RawY/FilteredY (diameter) in mm.</summary>
public class ScanPoint
{
    public double X         { get; set; }
    public double RawY      { get; set; }
    public double FilteredY { get; set; }
}

public class ImportedSeries
{
    public string   Name     { get; set; } = string.Empty;
    public double[] Xs       { get; set; } = Array.Empty<double>();
    public double[] Ys       { get; set; } = Array.Empty<double>();
    public string   ColorHex { get; set; } = "#28C996";
}

/// <summary>A drawn taper node: X = position in cm, Y = full diameter in mm.</summary>
public class DesignNode
{
    public double X { get; set; }
    public double Y { get; set; }
}

public class NodeLabelOffset
{
    public double NodeX { get; set; }
    public double LX    { get; set; }
    public double LY    { get; set; }
}

public class LineColorSection
{
    public double StartCm  { get; set; }
    public double EndCm    { get; set; }
    public string ColorHex { get; set; } = "DC3232";
    public string Label    { get; set; } = string.Empty;
}

/// <summary>User-edited segment name, specific weight and head flag, persisted across saves.</summary>
public class SegmentMetadata
{
    public double StartCm    { get; set; }
    public double EndCm      { get; set; }
    public string Name       { get; set; } = string.Empty;
    public double SpecWeight { get; set; } = 0.0;
    public bool   IsHead     { get; set; } = false;
}
