using System.Text.Json.Serialization;

namespace DiametroLineaDesktop.Models;

/// <summary>
/// A prototype assembled from real pieces of fly line (.flproto file). Each piece is a cleaned copy
/// of a scan from the piece library, so the prototype stays editable even if the source .flp is
/// moved or rescanned. Nothing here is a design: diameters are never edited, only cut and placed.
/// </summary>
public class PrototypeProject
{
    public int      Version    { get; set; } = 1;
    public string   Name       { get; set; } = "Prototype";
    public DateTime CreatedAt  { get; set; } = DateTime.UtcNow;
    public DateTime ModifiedAt { get; set; } = DateTime.UtcNow;
    public string   Notes      { get; set; } = string.Empty;

    /// <summary>
    /// Extra length each piece needs at every joined end: the coating is stripped back to expose the
    /// core for the needle splice, so that stretch is in the cut piece but not in the finished line.
    /// </summary>
    public double JointAllowanceCm { get; set; } = 4.0;

    public List<PrototypePiece> Pieces { get; set; } = new();
}

/// <summary>
/// One physical piece of line placed in the prototype.
///
/// Coordinates: the piece's own scan runs from X = 0 (the end that entered the sensor first, the
/// "scan-start end") to <see cref="LengthCm"/> (the "scan-end end"). Trims are always expressed in
/// those terms, whatever the orientation, so a cut list reads the same on the bench.
/// On the assembly axis the piece's left edge (untrimmed) sits at <see cref="OffsetCm"/>; when
/// <see cref="Flipped"/> the scan-end end is on the left.
/// </summary>
public class PrototypePiece
{
    public string Id         { get; set; } = Guid.NewGuid().ToString("N");
    public string Name       { get; set; } = string.Empty;
    /// <summary>0 = the whole piece; 1, 2, … = a part obtained by splitting it (see <see cref="DisplayName"/>).</summary>
    public int    PartNumber { get; set; }
    public string SourcePath { get; set; } = string.Empty;
    public string ColorHex   { get; set; } = "3296FF";
    /// <summary>Material density from the source project, g/cm³. 0 = unknown (no weight estimate).</summary>
    public double DensityGCm3 { get; set; }

    /// <summary>Cleaned scan, source orientation, Xs starting at 0 (cm), Ds full diameter (mm).</summary>
    public double[] Xs { get; set; } = Array.Empty<double>();
    public double[] Ds { get; set; } = Array.Empty<double>();

    public bool   Flipped     { get; set; }
    /// <summary>Length cut off at the scan-start end (cm), by hand.</summary>
    public double TrimStartCm { get; set; }
    /// <summary>Length cut off at the scan-end end (cm), by hand.</summary>
    public double TrimEndCm   { get; set; }
    /// <summary>Assembly X of the piece's left edge before any trim.</summary>
    public double OffsetCm    { get; set; }

    [JsonIgnore] public double LengthCm => Xs.Length > 0 ? Xs[^1] : 0;

    [JsonIgnore] public string DisplayName => PartNumber > 0 ? $"{Name} #{PartNumber}" : Name;

    /// <summary>The kept stretch in the piece's own scan coordinates (from the scan-start end).</summary>
    [JsonIgnore] public double SourceFrom => TrimStartCm;
    [JsonIgnore] public double SourceTo   => LengthCm - TrimEndCm;

    /// <summary>Trim at the end currently on the left / right of the assembly.</summary>
    [JsonIgnore] public double LeftTrimCm  => Flipped ? TrimEndCm : TrimStartCm;
    [JsonIgnore] public double RightTrimCm => Flipped ? TrimStartCm : TrimEndCm;

    /// <summary>Visible span on the assembly axis after the hand trims (before automatic joint cuts).</summary>
    [JsonIgnore] public double VisibleStart => OffsetCm + LeftTrimCm;
    [JsonIgnore] public double VisibleEnd   => OffsetCm + LengthCm - RightTrimCm;

    public void SetLeftTrim(double cm)
    {
        if (Flipped) TrimEndCm = cm; else TrimStartCm = cm;
    }

    public void SetRightTrim(double cm)
    {
        if (Flipped) TrimStartCm = cm; else TrimEndCm = cm;
    }

    /// <summary>Converts an assembly X into this piece's own scan X.</summary>
    public double ToSourceX(double assemblyX)
    {
        double u = assemblyX - OffsetCm;
        return Flipped ? LengthCm - u : u;
    }

    /// <summary>Converts a scan X of this piece into assembly X.</summary>
    public double ToAssemblyX(double sourceX) => OffsetCm + (Flipped ? LengthCm - sourceX : sourceX);

    /// <summary>
    /// Flips the piece 180° in place: the visible span stays where it is on the assembly axis, only
    /// the ends swap, so a flip never throws the piece away from its neighbours.
    /// </summary>
    public void Flip()
    {
        double visStart = VisibleStart;
        Flipped = !Flipped;
        OffsetCm = visStart - LeftTrimCm;
    }

    /// <summary>Diameter (mm) at a scan X of this piece, linearly interpolated.</summary>
    public double DiameterAtSource(double sourceX)
    {
        if (Xs.Length == 0) return 0;
        if (sourceX <= Xs[0])  return Ds[0];
        if (sourceX >= Xs[^1]) return Ds[^1];
        int i = Array.BinarySearch(Xs, sourceX);
        if (i >= 0) return Ds[i];
        i = ~i;
        double t = (sourceX - Xs[i - 1]) / (Xs[i] - Xs[i - 1]);
        return Ds[i - 1] + t * (Ds[i] - Ds[i - 1]);
    }

    /// <summary>Diameter (mm) at an assembly X, or null when that X is outside the visible span.</summary>
    public double? DiameterAt(double assemblyX)
    {
        if (assemblyX < VisibleStart - 1e-9 || assemblyX > VisibleEnd + 1e-9) return null;
        return DiameterAtSource(ToSourceX(assemblyX));
    }
}
