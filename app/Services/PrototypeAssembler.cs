using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using DiametroLineaDesktop.Models;

namespace DiametroLineaDesktop.Services;

/// <summary>Minimal clean-up of a raw scan so it can be used as a piece.</summary>
public static class ScanCleaner
{
    /// <summary>Below this the sensor had no line in it (readings of 0.01 mm).</summary>
    public const double MinValidDiameterMm = 0.10;

    /// <summary>
    /// Sorts by X, drops no-line readings, merges repeated X (a back-and-forth during the scan) by
    /// averaging, and shifts X so the piece starts at 0. Ends are left alone: loops, spikes and
    /// frayed tips are for the user to cut, not for us to guess.
    /// </summary>
    public static (double[] Xs, double[] Ds) Clean(IEnumerable<MeasurementPoint> points)
    {
        var groups = points
            .Where(p => p.FilteredY >= MinValidDiameterMm && double.IsFinite(p.X) && double.IsFinite(p.FilteredY))
            .GroupBy(p => p.X)
            .OrderBy(g => g.Key)
            .Select(g => (X: g.Key, D: g.Average(p => p.FilteredY)))
            .ToList();

        if (groups.Count == 0) return (Array.Empty<double>(), Array.Empty<double>());

        double x0 = groups[0].X;
        return (groups.Select(g => g.X - x0).ToArray(), groups.Select(g => g.D).ToArray());
    }
}

/// <summary>A scanned piece available in the library folder.</summary>
public class LibraryPiece
{
    public string   Name          { get; init; } = string.Empty;
    public string   Path          { get; init; } = string.Empty;
    public string   Folder        { get; init; } = string.Empty;   // relative to the library root
    public double[] Xs            { get; init; } = Array.Empty<double>();
    public double[] Ds            { get; init; } = Array.Empty<double>();
    public double   DensityGCm3   { get; init; }

    public double LengthCm => Xs.Length > 0 ? Xs[^1] : 0;
    public double MinD     => Ds.Length > 0 ? Ds.Min() : 0;
    public double MaxD     => Ds.Length > 0 ? Ds.Max() : 0;

    public string Summary =>
        string.Create(CultureInfo.InvariantCulture, $"{LengthCm / 100.0:0.00} m   Ø {MinD:0.00}–{MaxD:0.00} mm")
        + (DensityGCm3 > 0 ? string.Create(CultureInfo.InvariantCulture, $"   ρ {DensityGCm3:0.00}") : "");

    /// <summary>Tiny symmetric silhouette for the library list (frozen, so it can be built off the UI thread).</summary>
    public System.Windows.Media.Geometry? Thumbnail { get; init; }
}

public static class PieceLibrary
{
    /// <summary>Scan files with fewer points than this are not pieces (aborted scans, tests).</summary>
    private const int MinPoints = 20;

    public static string DefaultFolder => ProjectService.DefaultProjectFolder;

    /// <summary>
    /// Every .flp under <paramref name="folder"/> (recursively) that carries a scan. Files that fail
    /// to parse are skipped silently — the library is a browse list, not a validator.
    /// </summary>
    public static List<LibraryPiece> Load(string folder)
    {
        var result = new List<LibraryPiece>();
        if (!Directory.Exists(folder)) return result;

        foreach (var path in Directory.EnumerateFiles(folder, "*" + ProjectService.FileExtension, SearchOption.AllDirectories))
        {
            try
            {
                var p = LoadPiece(path, folder);
                if (p != null) result.Add(p);
            }
            catch { /* not a readable project — skip */ }
        }
        return result.OrderBy(p => p.Folder, StringComparer.OrdinalIgnoreCase)
                     .ThenBy(p => p.Name, StringComparer.OrdinalIgnoreCase)
                     .ToList();
    }

    public static LibraryPiece? LoadPiece(string path, string? libraryRoot = null)
    {
        var project = ProjectService.Load(path);
        if (project.IsCompensatedDerivative || project.ScanPoints.Count < MinPoints) return null;

        var (xs, ds) = ScanCleaner.Clean(project.ScanPoints);
        if (xs.Length < MinPoints) return null;

        double density = project.SharedDensityGCm3 > 0 ? project.SharedDensityGCm3
                       : project.NozzleDefinitions.FirstOrDefault()?.DensityGCm3 ?? 0;

        string folder = libraryRoot == null ? string.Empty
                      : System.IO.Path.GetRelativePath(libraryRoot, System.IO.Path.GetDirectoryName(path) ?? libraryRoot);
        if (folder == ".") folder = string.Empty;

        return new LibraryPiece
        {
            Name        = System.IO.Path.GetFileNameWithoutExtension(path).Trim(),
            Path        = path,
            Folder      = folder,
            Xs          = xs,
            Ds          = ds,
            DensityGCm3 = density,
            Thumbnail   = BuildThumbnail(xs, ds),
        };
    }

    /// <summary>
    /// Silhouette in a 200×28 box. X is scaled to the piece's own length (every thumbnail is full
    /// width); Y uses a fixed 2.5 mm scale so thicknesses compare across pieces at a glance.
    /// </summary>
    private static System.Windows.Media.Geometry BuildThumbnail(double[] xs, double[] ds)
    {
        const double W = 200, H = 28, FullScaleMm = 2.5;
        double len = Math.Max(1, xs[^1]);
        int step = Math.Max(1, xs.Length / 200);

        var top = new List<System.Windows.Point>();
        for (int i = 0; i < xs.Length; i += step)
        {
            double y = Math.Min(1, ds[i] / FullScaleMm) * H / 2;
            top.Add(new System.Windows.Point(xs[i] / len * W, H / 2 - y));
        }

        var geo = new System.Windows.Media.StreamGeometry();
        using (var ctx = geo.Open())
        {
            ctx.BeginFigure(top[0], isFilled: true, isClosed: true);
            ctx.PolyLineTo(top.Skip(1).ToList(), isStroked: true, isSmoothJoin: false);
            var bottom = top.AsEnumerable().Reverse().Select(p => new System.Windows.Point(p.X, H - p.Y)).ToList();
            ctx.PolyLineTo(bottom, isStroked: true, isSmoothJoin: false);
        }
        geo.Freeze();
        return geo;
    }
}

/// <summary>What happens where two consecutive pieces meet.</summary>
public class PrototypeJoint
{
    public int    LeftIndex   { get; init; }   // index into AssemblyResult.Pieces
    public int    RightIndex  { get; init; }
    /// <summary>Assembly X of the left piece's cut end (where the joint is drawn).</summary>
    public double X           { get; init; }
    public double DLeftMm     { get; init; }   // left piece, at its right end
    public double DRightMm    { get; init; }   // right piece, at its left end
    public double StepMm      => DRightMm - DLeftMm;
    /// <summary>&gt; 0: the pieces still overlap by this much (not cut yet). &lt; 0: gap on the chart.</summary>
    public double OverlapCm   { get; init; }
}

/// <summary>One piece as it ends up in the prototype, in assembly order.</summary>
public class PrototypePieceResult
{
    public PrototypePiece Piece        { get; init; } = null!;
    public int            Number       { get; init; }          // 1-based, assembly order
    /// <summary>Length this piece contributes to the finished line.</summary>
    public double         KeptCm       { get; init; }
    public double         CutAtStartCm { get; init; }           // removed at the scan-start end (chart)
    public double         CutAtEndCm   { get; init; }           // removed at the scan-end end (chart)

    // Bench view: every joined end keeps the joint allowance beyond the chart cut (core exposed for
    // the splice), so the physical cut is that much further out and the cut piece that much longer.
    public bool           JoinedAtStart   { get; init; }         // scan-start end joins another piece
    public bool           JoinedAtEnd     { get; init; }
    public double         BenchCutStartCm { get; init; }         // what to actually cut off at the scan-start end
    public double         BenchCutEndCm   { get; init; }
    public double         CutLengthCm     { get; init; }         // physical length of the cut piece
    /// <summary>Allowance missing at each end because the piece runs out of material (0 = fine).</summary>
    public double         ShortAtStartCm  { get; init; }
    public double         ShortAtEndCm    { get; init; }
    public double         DLeftMm      { get; init; }
    public double         DRightMm     { get; init; }
    public double         StartInLineCm { get; init; }          // position in the finished line
    public double?        MassG        { get; init; }

    public string Name        => Piece.DisplayName;
    public string Direction   => Piece.Flipped ? "← flipped" : "→";
    public string ColorHex    => Piece.ColorHex;
}

public class AssemblyResult
{
    public List<PrototypePieceResult> Pieces { get; } = new();
    public List<PrototypeJoint>       Joints { get; } = new();
    /// <summary>The finished line: pieces butted end to end from X = 0, whatever their chart positions.</summary>
    public List<(double X, double D)> Profile { get; } = new();
    public double  LengthCm { get; set; }
    /// <summary>Total mass (g), or null when any piece has no known density.</summary>
    public double? MassG    { get; set; }
    public List<string> Warnings { get; } = new();

    public double? MassGrains => MassG * 15.4323584;
}

public static class PrototypeAssembler
{
    public const string FileExtension = ".flproto";
    public const string FileFilter    = "FlyLine prototype (*.flproto)|*.flproto";

    public static string DefaultFolder =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "FlyLineProfiler", "Prototypes");

    public static readonly string[] Palette =
        { "3296FF", "DC3232", "28A428", "F0A020", "9B59B6", "17BECF", "E377C2", "8C564B" };

    /// <summary>Joints within this are considered touching (no gap, no overlap).</summary>
    public const double TouchToleranceCm = 0.5;

    private static readonly JsonSerializerOptions _json = new() { WriteIndented = true };

    public static void Save(PrototypeProject project, string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        project.ModifiedAt = DateTime.UtcNow;
        File.WriteAllText(path, JsonSerializer.Serialize(project, _json), Encoding.UTF8);
    }

    /// <summary>
    /// Loads a prototype. A piece saved without its own scan copy (e.g. a hand-written spec) is
    /// filled in from its SourcePath.
    /// </summary>
    public static PrototypeProject Load(string path)
    {
        var project = JsonSerializer.Deserialize<PrototypeProject>(File.ReadAllText(path, Encoding.UTF8), _json)
                      ?? throw new InvalidDataException("Invalid or empty prototype file.");
        string baseDir = Path.GetDirectoryName(Path.GetFullPath(path)) ?? ".";
        foreach (var piece in project.Pieces.Where(p => p.Xs.Length == 0))
        {
            string src = Path.IsPathRooted(piece.SourcePath) ? piece.SourcePath : Path.Combine(baseDir, piece.SourcePath);
            var lib = PieceLibrary.LoadPiece(src)
                      ?? throw new InvalidDataException($"'{piece.SourcePath}' has no usable scan.");
            piece.Xs = lib.Xs;
            piece.Ds = lib.Ds;
            if (string.IsNullOrEmpty(piece.Name)) piece.Name = lib.Name;
            if (piece.DensityGCm3 <= 0) piece.DensityGCm3 = lib.DensityGCm3;
        }
        return project;
    }

    /// <summary>A new piece from the library, placed right after the last piece on the chart.</summary>
    public static PrototypePiece CreatePiece(LibraryPiece lib, PrototypeProject project)
    {
        double end = project.Pieces.Count == 0 ? 0 : project.Pieces.Max(p => p.VisibleEnd);
        return new PrototypePiece
        {
            Name        = lib.Name,
            SourcePath  = lib.Path,
            DensityGCm3 = lib.DensityGCm3,
            Xs          = lib.Xs,
            Ds          = lib.Ds,
            ColorHex    = Palette[project.Pieces.Count % Palette.Length],
            OffsetCm    = end,
        };
    }

    /// <summary>
    /// Splits <paramref name="piece"/> at assembly X <paramref name="x"/> into two independent parts:
    /// the original keeps the left side, the returned new part (inserted right after it) the right
    /// side. Both stay where they are on the chart, touching, until moved. Parts are numbered per
    /// source scan (#1, #2, …) so the cut list can say which stretch of the physical piece each one is.
    /// Returns null when <paramref name="x"/> isn't strictly inside the kept span.
    /// </summary>
    public static PrototypePiece? Split(PrototypeProject project, PrototypePiece piece, double x, double minPartCm = 1)
    {
        if (x <= piece.VisibleStart + minPartCm || x >= piece.VisibleEnd - minPartCm) return null;

        if (piece.PartNumber == 0) piece.PartNumber = 1;   // final numbers are assigned below

        var part = new PrototypePiece
        {
            Name        = piece.Name,
            PartNumber  = 1,
            SourcePath  = piece.SourcePath,
            DensityGCm3 = piece.DensityGCm3,
            Xs          = piece.Xs,
            Ds          = piece.Ds,
            ColorHex    = Palette[project.Pieces.Count % Palette.Length],
            Flipped     = piece.Flipped,
            TrimStartCm = piece.TrimStartCm,
            TrimEndCm   = piece.TrimEndCm,
            OffsetCm    = piece.OffsetCm,
        };
        piece.SetRightTrim(piece.OffsetCm + piece.LengthCm - x);
        part.SetLeftTrim(x - part.OffsetCm);

        project.Pieces.Insert(project.Pieces.IndexOf(piece) + 1, part);

        // Renumber so #1, #2, … run along the physical piece from its scan-start end — that's the
        // order you'd mark them on the bench, whatever order they were split in.
        int n = 1;
        foreach (var p in project.Pieces
                     .Where(p => p.PartNumber > 0 && string.Equals(p.SourcePath, piece.SourcePath, StringComparison.OrdinalIgnoreCase))
                     .OrderBy(p => p.SourceFrom))
            p.PartNumber = n++;
        return part;
    }

    /// <summary>
    /// The prototype as it would be built: pieces in chart order (left edge), each kept exactly as
    /// trimmed, butted end to end. Overlaps and gaps on the chart are reported, not resolved — where
    /// to cut is the user's call.
    /// </summary>
    public static AssemblyResult Assemble(PrototypeProject project)
    {
        var result = new AssemblyResult();
        var ordered = project.Pieces
            .Where(p => p.Xs.Length > 1 && p.VisibleEnd - p.VisibleStart > 0)
            .OrderBy(p => p.VisibleStart).ThenBy(p => p.VisibleEnd)
            .ToList();

        double cursor = 0;
        double mass = 0;
        bool massKnown = ordered.Count > 0;
        double allowance = Math.Max(0, project.JointAllowanceCm);
        var allowances = new Dictionary<PrototypePiece, (double Start, double End)>();

        for (int i = 0; i < ordered.Count; i++)
        {
            var p = ordered[i];
            double kept = p.VisibleEnd - p.VisibleStart;
            double? m = p.DensityGCm3 > 0 ? PieceMass(p) : null;
            if (m.HasValue) mass += m.Value; else massKnown = false;

            // Left/right on the chart → scan-start/scan-end on the bench.
            bool joinedLeft = i > 0, joinedRight = i < ordered.Count - 1;
            bool joinedAtStart = p.Flipped ? joinedRight : joinedLeft;
            bool joinedAtEnd   = p.Flipped ? joinedLeft  : joinedRight;
            double wantStart  = joinedAtStart ? allowance : 0;
            double wantEnd    = joinedAtEnd   ? allowance : 0;
            double benchStart = Math.Max(0, p.TrimStartCm - wantStart);
            double benchEnd   = Math.Max(0, p.TrimEndCm   - wantEnd);
            allowances[p] = (p.TrimStartCm - benchStart, p.TrimEndCm - benchEnd);

            result.Pieces.Add(new PrototypePieceResult
            {
                Piece         = p,
                Number        = i + 1,
                KeptCm        = kept,
                CutAtStartCm  = p.TrimStartCm,
                CutAtEndCm    = p.TrimEndCm,
                JoinedAtStart   = joinedAtStart,
                JoinedAtEnd     = joinedAtEnd,
                BenchCutStartCm = benchStart,
                BenchCutEndCm   = benchEnd,
                CutLengthCm     = p.LengthCm - benchStart - benchEnd,
                ShortAtStartCm  = Math.Max(0, wantStart - p.TrimStartCm),
                ShortAtEndCm    = Math.Max(0, wantEnd   - p.TrimEndCm),
                DLeftMm       = p.DiameterAtSource(p.ToSourceX(p.VisibleStart)),
                DRightMm      = p.DiameterAtSource(p.ToSourceX(p.VisibleEnd)),
                StartInLineCm = cursor,
                MassG         = m,
            });

            AppendProfile(result.Profile, p, cursor);
            cursor += kept;
        }

        for (int i = 0; i + 1 < result.Pieces.Count; i++)
        {
            var a = result.Pieces[i];
            var b = result.Pieces[i + 1];
            result.Joints.Add(new PrototypeJoint
            {
                LeftIndex  = i,
                RightIndex = i + 1,
                X          = a.Piece.VisibleEnd,
                DLeftMm    = a.DRightMm,
                DRightMm   = b.DLeftMm,
                OverlapCm  = a.Piece.VisibleEnd - b.Piece.VisibleStart,
            });
        }

        foreach (var j in result.Joints)
        {
            string names = $"{result.Pieces[j.LeftIndex].Name} → {result.Pieces[j.RightIndex].Name}";
            if (j.OverlapCm > TouchToleranceCm)
                result.Warnings.Add(Inv($"{names}: still overlapping by {j.OverlapCm:0} cm — trim one of them."));
            else if (j.OverlapCm < -TouchToleranceCm)
                result.Warnings.Add(Inv($"{names}: {-j.OverlapCm:0} cm gap on the chart (ignored: pieces are joined end to end)."));
        }

        foreach (var r in result.Pieces)
        {
            if (r.ShortAtStartCm > 0.05)
                result.Warnings.Add(Inv($"{r.Name}: only {r.CutAtStartCm:0.#} cm of line beyond the joint at the scan-start end — the splice needs {allowance:0.#} cm (short by {r.ShortAtStartCm:0.#})."));
            if (r.ShortAtEndCm > 0.05)
                result.Warnings.Add(Inv($"{r.Name}: only {r.CutAtEndCm:0.#} cm of line beyond the joint at the scan-end end — the splice needs {allowance:0.#} cm (short by {r.ShortAtEndCm:0.#})."));
        }

        // Parts of one physical piece (same source scan) can't share material — including the joint
        // allowance each one needs at its spliced ends.
        foreach (var group in project.Pieces.Where(p => p.Xs.Length > 1).GroupBy(p => p.SourcePath, StringComparer.OrdinalIgnoreCase))
        {
            var parts = group.OrderBy(p => p.SourceFrom).ToList();
            for (int i = 0; i + 1 < parts.Count; i++)
            for (int k = i + 1; k < parts.Count; k++)
            {
                var a = parts[i]; var b = parts[k];
                double from = Math.Max(a.SourceFrom, b.SourceFrom);
                double to   = Math.Min(a.SourceTo,   b.SourceTo);
                if (to - from > TouchToleranceCm)
                {
                    result.Warnings.Add(Inv($"{a.DisplayName} and {b.DisplayName} both use {from:0}–{to:0} cm of the same scan."));
                    continue;
                }
                var (_, aEnd)   = allowances.GetValueOrDefault(a);
                var (bStart, _) = allowances.GetValueOrDefault(b);
                double gap  = b.SourceFrom - a.SourceTo;   // line between them on the physical piece (a before b)
                double need = aEnd + bStart;
                if (gap >= -TouchToleranceCm && gap + 0.05 < need)
                    result.Warnings.Add(Inv($"{a.DisplayName} and {b.DisplayName}: {Math.Max(0, gap):0.#} cm of line between them, their two splices need {need:0.#} cm."));
            }
        }

        result.LengthCm = cursor;
        result.MassG    = massKnown ? mass : null;
        return result;
    }

    /// <summary>Mass (g) of the kept part: ρ·π/4·D²·dx, trapezoidal over the scan points.</summary>
    public static double PieceMass(PrototypePiece p)
    {
        double a = Math.Min(p.ToSourceX(p.VisibleStart), p.ToSourceX(p.VisibleEnd));
        double b = Math.Max(p.ToSourceX(p.VisibleStart), p.ToSourceX(p.VisibleEnd));
        double volCm3 = 0;
        double prevX = a, prevArea = AreaCm2(p.DiameterAtSource(a));
        foreach (double x in p.Xs.Where(x => x > a && x < b).Append(b))
        {
            double area = AreaCm2(p.DiameterAtSource(x));
            volCm3 += (area + prevArea) / 2 * (x - prevX);
            prevX = x; prevArea = area;
        }
        return volCm3 * p.DensityGCm3;
    }

    private static double AreaCm2(double dMm) => Math.PI / 4 * (dMm / 10) * (dMm / 10);

    /// <summary>Appends the kept part of <paramref name="p"/>, left to right, starting at <paramref name="lineX"/>.</summary>
    private static void AppendProfile(List<(double X, double D)> profile, PrototypePiece p, double lineX)
    {
        double s = p.VisibleStart, e = p.VisibleEnd;
        var xs = new List<double> { s };
        xs.AddRange(p.Xs.Select(p.ToAssemblyX).Where(x => x > s && x < e).OrderBy(x => x));
        xs.Add(e);
        foreach (double x in xs)
        {
            double lx = lineX + (x - s);
            // A joint is a step: both pieces' end values are kept at the same X, left first.
            profile.Add((lx, p.DiameterAtSource(p.ToSourceX(x))));
        }
    }

    /// <summary>Bench instructions, one line per piece, in scan-end terms so they read the same whatever the orientation.</summary>
    public static string CutList(AssemblyResult r, double jointAllowanceCm)
    {
        var sb = new StringBuilder();
        if (r.Joints.Count > 0 && jointAllowanceCm > 0)
            sb.Append(Inv($"Cuts include {jointAllowanceCm:0.#} cm per joined end (core exposed for the splice).\n"));
        foreach (var p in r.Pieces)
        {
            sb.Append(Inv($"{p.Number}. {p.Name}  {(p.Piece.Flipped ? "(flipped)" : "")}\n"));
            sb.Append(Inv($"     cut scan-start {p.BenchCutStartCm:0.#} cm, scan-end {p.BenchCutEndCm:0.#} cm → piece {p.CutLengthCm:0.#} cm"));
            double splice = p.CutLengthCm - p.KeptCm;
            if (splice > 0.05) sb.Append(Inv($" = {p.KeptCm:0.#} in line + {splice:0.#} splice"));
            // For a split part the stretch of the original piece is the clearer instruction.
            if (p.Piece.PartNumber > 0)
                sb.Append(Inv($"  (= {p.BenchCutStartCm:0.#}–{p.Piece.LengthCm - p.BenchCutEndCm:0.#} cm of {p.Piece.Name})"));
            sb.Append('\n');
            sb.Append(Inv($"     Ø {p.DLeftMm:0.00} → {p.DRightMm:0.00} mm   line {p.StartInLineCm:0}–{p.StartInLineCm + p.KeptCm:0} cm"));
            if (p.MassG.HasValue) sb.Append(Inv($"   {p.MassG:0.00} g"));
            sb.Append('\n');
        }
        foreach (var j in r.Joints)
            sb.Append(Inv($"Joint {r.Pieces[j.LeftIndex].Number}→{r.Pieces[j.RightIndex].Number}: Ø {j.DLeftMm:0.00} / {j.DRightMm:0.00} mm  (step {j.StepMm:+0.00;-0.00;0.00})\n"));
        sb.Append(Inv($"Total length {r.LengthCm / 100.0:0.00} m"));
        if (r.MassG.HasValue) sb.Append(Inv($"   mass {r.MassG:0.00} g ({r.MassGrains:0} gr)"));
        sb.Append('\n');
        return sb.ToString();
    }

    /// <summary>
    /// The finished line as an ordinary project: its scan is the assembled profile, so it opens in
    /// the main window like any scanned line (draw a design over it, weigh it, export it).
    /// </summary>
    public static FlyLineProject ToFlyLineProject(PrototypeProject proto, AssemblyResult r)
    {
        var project = ProjectService.New(proto.Name);
        project.Notes = "Prototype assembled from pieces:\n" + CutList(r, proto.JointAllowanceCm);
        foreach (var (x, d) in r.Profile)
            project.ScanPoints.Add(new MeasurementPoint { X = Math.Round(x, 2), RawY = Math.Round(d, 3), FilteredY = Math.Round(d, 3) });

        var densities = r.Pieces.Select(p => p.Piece.DensityGCm3).Distinct().ToList();
        if (densities.Count == 1 && densities[0] > 0)
            project.SharedDensityGCm3 = densities[0];
        return project;
    }

    private static string Inv(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);
}
