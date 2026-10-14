using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using DiametroLineaDesktop.Models;
using DiametroLineaDesktop.Services;
using FlyLinePhysics.Analysis;
using FlyLinePhysics.Physics;
using FlyLinePhysics.Serialization;

// Headless front end for the design engine: spec in, .flp out — same builder, same physics and
// same file format the GUI uses. Meant to be driven by a script or an agent.

Console.OutputEncoding = System.Text.Encoding.UTF8;   // Ø, ρ and → in the report

var json = new JsonSerializerOptions
{
    WriteIndented          = true,
    PropertyNamingPolicy   = JsonNamingPolicy.CamelCase,
    PropertyNameCaseInsensitive = true,
    ReadCommentHandling    = JsonCommentHandling.Skip,
    AllowTrailingCommas    = true,
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
};

try
{
    return (args.Length == 0 ? "help" : args[0].ToLowerInvariant()) switch
    {
        "build"   => Build(args),
        "inspect" => Inspect(args),
        "report"  => ReportOnly(args),
        "pdf"     => Pdf(args),
        "analyze" => Analyze(args),
        "assemble" => Assemble(args),
        _         => Help(),
    };
}
catch (DesignSpecException ex)
{
    Console.Error.WriteLine($"Spec error: {ex.Message}");
    return 2;
}
catch (Exception ex)
{
    Console.Error.WriteLine($"{ex.GetType().Name}: {ex.Message}");
    return 1;
}

int Help()
{
    Console.WriteLine("""
        flyline — headless fly line designer

          flyline build   <spec.json> [-o <out.flp>]   build a design and save it
          flyline inspect <in.flp>    [-o <spec.json>] recover the spec of an existing design
          flyline report  <in.flp>                     mass, AFFTA class and sink speeds
          flyline pdf     <in.flp>    [-o <out.pdf>]   the spec sheet a producer would receive
          flyline analyze <in.flp>    -a <accel m/s2>  Level-2 physics: ρ·d, per-segment taper rate,
                                                       m, M, Re, drag, Π, C
                                      [--csv <out.csv>]       per-segment rows (appends)
                                      [--csv-line <out.csv>]  one row per project (appends)
                                      [--csv-slices <out.csv>] every 1 cm slice (overwrites)
                                      [--tail-d <mm>] [--tail-rho <g/cm3>] [--tail-len <cm>]
                                      [--kind auto|shootinghead|fullline]

        A shooting head is analyzed together with the shooting line it tows (default 0.40 mm nylon,
        40 m); a full line already carries its running line in the profile. Which one a file is, is
        detected from the trailing constant-diameter run unless --kind says otherwise.

        -a only scales Π's level, never the shape of ρ·d or the taper rates, so it does not need
        to be right for the per-segment readout to be.
          flyline assemble <in.flproto> [-o <out.flp>] prototype from scanned pieces: cut list (+ .flp)

        Without -o, build/pdf write next to the input file and inspect prints to stdout.
        """);
    return 0;
}

int Build(string[] a)
{
    string specPath = Arg(a, 1) ?? throw new ArgumentException("build needs a spec file: flyline build <spec.json>");
    var spec = JsonSerializer.Deserialize<LineDesignSpec>(File.ReadAllText(specPath), json)
               ?? throw new InvalidDataException("The spec file is empty or not valid JSON.");

    var project = LineDesignBuilder.Build(spec, out var notes);

    string outPath = Opt(a, "-o")
        ?? Path.Combine(Path.GetDirectoryName(Path.GetFullPath(specPath)) ?? ".",
                        Sanitize(spec.Name) + ProjectService.FileExtension);
    ProjectService.Save(project, outPath);

    foreach (var n in notes) Console.WriteLine($"  · {n}");
    Console.WriteLine($"\nSaved: {outPath}\n");
    PrintReport(LineDesignBuilder.Report(project));
    return 0;
}

int Inspect(string[] a)
{
    string path = Arg(a, 1) ?? throw new ArgumentException("inspect needs a project file: flyline inspect <in.flp>");
    var project = ProjectService.Load(path);
    string text = JsonSerializer.Serialize(LineDesignBuilder.ToSpec(project), json);

    string? outPath = Opt(a, "-o");
    if (outPath is null) Console.WriteLine(text);
    else { File.WriteAllText(outPath, text); Console.WriteLine($"Saved: {outPath}"); }
    return 0;
}

int ReportOnly(string[] a)
{
    string path = Arg(a, 1) ?? throw new ArgumentException("report needs a project file: flyline report <in.flp>");
    PrintReport(LineDesignBuilder.Report(ProjectService.Load(path)));
    return 0;
}

int Pdf(string[] a)
{
    string path = Arg(a, 1) ?? throw new ArgumentException("pdf needs a project file: flyline pdf <in.flp>");
    var project = ProjectService.Load(path);
    var segments = LineDesignBuilder.ToProjectSegments(project);
    if (segments.Count == 0)
        throw new InvalidDataException("This project has no design segments to export.");

    // Same trigger the GUI uses (_inCompMode || _zoneDerivedComp): a live zone-derived design or a
    // baked C snapshot renders the per-slice coloured profile; a plain single-material design does
    // not, even though ToProjectSegments bakes trivial per-segment compensation into every segment
    // either way (RenderPdfChart is gated on this flag, not on HasCompensation alone).
    bool useComp = project.NozzleZones.Any(z => z.EndCm > z.StartCm) || project.IsCompensatedDerivative;

    var nozzleDefs  = project.NozzleDefinitions;
    var nozzleZones = project.NozzleZones;

    var chartInput = new ChartRenderInput
    {
        ScanPoints         = project.ScanPoints,
        DesignNodes         = project.DesignNodes.Select(n => (n.X, n.Y)).ToList(),
        Segments            = segments,
        NozzleZones         = nozzleZones,
        Nozzles             = nozzleDefs,
        UseCompensatedView  = useComp,
    };
    byte[] chartBytes = ChartRenderer.RenderPdfChart(chartInput);

    var (lw, grains) = LineWeightFamilyCalc.ClassifyAffta(segments);
    string afftaBadge = lw == 0 ? "AFFTA: —"
        : $"AFFTA  LW {lw}   {grains:0.0} gr   " +
          (Math.Abs(LineWeightFamilyCalc.Targets.First(t => t.Lw == lw).Gr - grains) <= 6.0 ? "✓" : "✗");

    var segSpeedsIns = segments.Where(s => s.HasCompensation)
        .Select(s => s.CompensatedTargetSpeedMs * 39.3701).Where(v => v > 0).ToList();
    bool uniformSegSpeed = segSpeedsIns.Count > 0 && (segSpeedsIns.Max() - segSpeedsIns.Min()) < 0.001;
    string compNote = !useComp ? ""
        : uniformSegSpeed
            ? $"Compensated profile — target sink {segSpeedsIns[0]:0.00} in/s. " +
              "Diameters are mass-preserving compensated values. Manufacture each section at the exact density shown."
            : "Multi-material design — each zone uses its own material. " +
              "Diameters are mass-preserving values. Manufacture each section at the exact density shown.";

    string outPath = Opt(a, "-o")
        ?? Path.Combine(Path.GetDirectoryName(Path.GetFullPath(path)) ?? ".",
                        Sanitize(project.Name) + (useComp ? "_C" : "_NC") + ".pdf");

    FlyLinePdfExporter.Export(outPath, project.Name, chartBytes, segments,
        // Older files carry no LineType, so fall back to the flag they do have.
        LineDensityClassExtensions.ParseOr(project.LineType,
            project.IsSinking ? LineDensityClass.Sinking : LineDensityClass.Floating),
        project.IsFullLine, project.WaterType == "salt", project.WaterTempC,
        afftaBadge, project.ColorNote, nozzleDefs, nozzleZones, project.DesignLineColorHex,
        // Same switch the GUI honours, so a headless export matches what the window would print.
        project.ShowCore ? project.CoreType : string.Empty,
        project.ShowCore ? project.CoreDiameterMm : null,
        project.LaserMark, useComp, compNote);

    Console.WriteLine($"Saved: {outPath}");
    return 0;
}

int Analyze(string[] a)
{
    string path = Arg(a, 1) ?? throw new ArgumentException("analyze needs a project file: flyline analyze <in.flp>");
    string? accelText = Opt(a, "-a");
    if (accelText is null || !double.TryParse(accelText, System.Globalization.CultureInfo.InvariantCulture, out double accel))
        throw new ArgumentException("analyze needs a reference acceleration: flyline analyze <in.flp> -a <accel m/s2>");

    // FlyLinePhysics reads the .flp file directly — it can't depend on DiametroLineaDesktop.Models
    // (that would be a reference cycle), so it carries its own twin model/serializer for the same
    // JSON format instead of going through ProjectService.
    var project = FlpJsonSerializer.Load(path);
    var scenario = new CastScenario { AccelerationRefMs2 = accel };

    // The shooting line is a property of how the head is fished, not of the file, so it is a global
    // default here rather than a stored field. These overrides exist to try alternatives — notably
    // fluorocarbon (--tail-rho 1.78), which lands at nearly the same ρ·d as a coated running line.
    if (double.TryParse(Opt(a, "--tail-d"), System.Globalization.CultureInfo.InvariantCulture, out double td))
        scenario.ShootingLine.DiameterMm = td;
    if (double.TryParse(Opt(a, "--tail-rho"), System.Globalization.CultureInfo.InvariantCulture, out double tr))
        scenario.ShootingLine.DensityGCm3 = tr;
    if (double.TryParse(Opt(a, "--tail-len"), System.Globalization.CultureInfo.InvariantCulture, out double tl))
        scenario.ShootingLine.LengthCm = tl;
    if (Opt(a, "--kind") is string k && Enum.TryParse<LineKind>(k, ignoreCase: true, out var kind))
        scenario.Kind = kind;

    var report = ProfileAnalyzer.Analyze(project, scenario);

    PrintAnalysis(project.Name, report);

    // Full precision, machine-readable: the printed table rounds Π to two decimals and hides the
    // coefficient of variation entirely, which is too coarse to calibrate the score weights against.
    string? sliceCsv = Opt(a, "--csv-slices");
    if (sliceCsv != null)
    {
        var inv = System.Globalization.CultureInfo.InvariantCulture;
        var sb = new System.Text.StringBuilder("xCm,diameterMm,linearMassKgM,cumulativeMassG,inertialTaper,region\n");
        for (int i = 0; i < report.XsCm.Length; i++)
            sb.Append(report.XsCm[i].ToString("R", inv)).Append(',')
              .Append(report.Diameter[i].ToString("R", inv)).Append(',')
              .Append(report.LinearMassKgM[i].ToString("R", inv)).Append(',')
              .Append(report.CumulativeMassG[i].ToString("R", inv)).Append(',')
              .Append(report.InertialTaper[i].ToString("R", inv)).Append(',')
              .Append(i < report.DesignSliceCount ? "design" : "shootingline").Append('\n');
        File.WriteAllText(sliceCsv, sb.ToString());
        Console.WriteLine($"\nCSV (slices): {sliceCsv}");
    }

    string? lineCsv = Opt(a, "--csv-line");
    if (lineCsv != null)
    {
        WriteLineCsv(lineCsv, path, project.Name, report);
        Console.WriteLine($"\nCSV (line): {lineCsv}");
    }

    string? csvPath = Opt(a, "--csv");
    if (csvPath != null)
    {
        WriteAnalysisCsv(csvPath, path, project.Name, report);
        Console.WriteLine($"\nCSV: {csvPath}");
    }
    return 0;
}

// One row per project: the shape of rho*d plus the junction. This is the table the index scales are
// meant to be read off, so it is separate from the per-segment one.
void WriteLineCsv(string csvPath, string sourcePath, string name, AnalysisReport r)
{
    var inv = System.Globalization.CultureInfo.InvariantCulture;
    var sb = new System.Text.StringBuilder();
    if (!File.Exists(csvPath))
        sb.AppendLine("file,project,kind,designCm,designMassG,peakCm,peakTaper,frontBackup," +
                      "medianC,p99C,spikiness,junctionStep,towedG,towedFrac");

    string N(double v) => double.IsNaN(v) ? "" : v.ToString("R", inv);
    int nd = r.DesignSliceCount;
    var sh = r.Shape; var j = r.Junction;

    sb.AppendLine(string.Join(',',
        Csv(sourcePath), Csv(name), r.Kind.ToString(),
        N(nd > 0 ? r.XsCm[nd - 1] - r.XsCm[0] : double.NaN),
        N(nd > 0 ? r.CumulativeMassG[nd - 1] : double.NaN),
        N(sh?.PeakPositionCm      ?? double.NaN),
        N(sh?.PeakInertialTaper   ?? double.NaN),
        N(sh?.FrontBackupFraction ?? double.NaN),
        N(sh?.MedianContinuity    ?? double.NaN),
        N(sh?.P99Continuity       ?? double.NaN),
        N(sh?.ContinuitySpikiness ?? double.NaN),
        N(j?.StepRatio          ?? double.NaN),
        N(j?.TowedMassG         ?? double.NaN),
        N(j?.TowedMassFraction  ?? double.NaN)));
    File.AppendAllText(csvPath, sb.ToString());
}

// Appends when the file already exists, so a batch run over many projects builds one table.
void WriteAnalysisCsv(string csvPath, string sourcePath, string name, AnalysisReport r)
{
    var inv = System.Globalization.CultureInfo.InvariantCulture;
    var sb = new System.Text.StringBuilder();
    if (!File.Exists(csvPath))
        sb.AppendLine("file,project,seg,name,startCm,endCm,lengthCm,taperIn,taperOut,kPer100Cm,massG");

    foreach (var (s, i) in r.SegmentTapers.Select((s, i) => (s, i + 1)))
        sb.AppendLine(string.Join(',',
            Csv(sourcePath), Csv(name), i.ToString(inv), Csv(s.Name),
            s.StartCm.ToString("R", inv), s.EndCm.ToString("R", inv),
            s.LengthCm.ToString("R", inv),
            s.InertialTaperStart.ToString("R", inv), s.InertialTaperEnd.ToString("R", inv),
            s.TaperRatePer100Cm.ToString("R", inv), s.MassG.ToString("R", inv)));
    File.AppendAllText(csvPath, sb.ToString());
}

static string Csv(string v) => $"\"{v.Replace("\"", "\"\"")}\"";

int Assemble(string[] a)
{
    string path = Arg(a, 1) ?? throw new ArgumentException("assemble needs a prototype file: flyline assemble <in.flproto>");
    // Same loader as the Prototype window: pieces without an embedded scan are filled from SourcePath,
    // so a hand-written spec only needs source, flip, trims and offset.
    var proto  = PrototypeAssembler.Load(path);
    var result = PrototypeAssembler.Assemble(proto);

    Console.WriteLine(proto.Name);
    Console.Write(PrototypeAssembler.CutList(result, proto.JointAllowanceCm));
    foreach (var w in result.Warnings) Console.WriteLine($"  ! {w}");

    string? outPath = Opt(a, "-o");
    if (outPath != null)
    {
        ProjectService.Save(PrototypeAssembler.ToFlyLineProject(proto, result), outPath);
        Console.WriteLine($"\nSaved: {outPath}");
    }
    return 0;
}

void PrintReport(LineDesignBuilder.DesignReport r)
{
    Console.WriteLine($"{r.Name}");
    Console.WriteLine($"  length {r.TotalLengthCm:0.#} cm ({r.TotalLengthCm / 30.48:0.#} ft)   " +
                      $"head {r.HeadLengthCm:0.#} cm   mass {r.TotalMassGrains:0.0} gr   head {r.HeadMassGrains:0.0} gr");
    Console.WriteLine(r.AfftaClass > 0
        ? $"  AFFTA #{r.AfftaClass}  (first 30 ft = {r.Affta30FtGrains:0.0} gr)"
        : "  AFFTA — not classifiable (no density set)");
    Console.WriteLine();
    Console.WriteLine($"  {"#",-3}{"name",-16}{"start",8}{"end",8}{"Ø start",9}{"Ø end",9}{"ρ",8}{"mass g",9}  sink");
    int i = 1;
    foreach (var s in r.Sections)
        Console.WriteLine($"  {i++,-3}{Trim(s.Name, 15),-16}{s.StartCm,8:0.#}{s.EndCm,8:0.#}" +
                          $"{s.StartDiamMm,9:0.000}{s.EndDiamMm,9:0.000}{s.DensityGCm3,8:0.00}{s.MassG,9:0.000}  {s.SinkText}");
}

void PrintAnalysis(string name, AnalysisReport r)
{
    Console.WriteLine($"{name}");
    if (r.XsCm.Length == 0) { Console.WriteLine("  no design nodes to analyze."); return; }
    if (!r.HasDensityData)
    {
        Console.WriteLine("  no density set anywhere in this project — every mass and ρ·d would be " +
                          "zero. Set a density before reading anything into it.");
        return;
    }

    int nd = r.DesignSliceCount;
    double designLen = r.XsCm[nd - 1] - r.XsCm[0];
    double designMass = r.CumulativeMassG[nd - 1];
    // Only over the design: the appended shooting line is NaN there, nothing was scanned out past
    // the head.
    var scanDeltas = r.ScanDesignDeltaMm?.Take(nd).Where(d => !double.IsNaN(d)).ToList();

    Console.WriteLine($"  {(r.Kind == LineKind.FullLine ? "full line" : "shooting head")}   " +
        $"{(r.Kind == LineKind.FullLine ? "length" : "head")} {designLen:0.#} cm   mass {designMass:0.0} g" +
        (scanDeltas is { Count: > 0 } ? $"   mean scan↔design delta {scanDeltas.Average():0.00} mm" : ""));

    if (r.Shape is { } sh)
    {
        Console.WriteLine($"  ρ·d peak {sh.PeakInertialTaper:0.000} at {sh.PeakPositionCm:0.#} cm   " +
            $"front backup {sh.FrontBackupFraction * 100:0.0}%   spikiness {sh.ContinuitySpikiness:0.0}x " +
            $"(median C {sh.MedianContinuity:0.0000}, p99 {sh.P99Continuity:0.0000})");
    }

    if (r.Shape is { BackupSpots.Count: > 0 } bs)
    {
        // Where the line ahead is inertially heavier than the line behind it — a hinge. Reported by
        // position because these sit on density-zone edges, where the diameter taper looks smooth.
        var worst = bs.BackupSpots.OrderByDescending(t => t.Fraction).Take(3);
        Console.WriteLine("  ! front backup at " +
            string.Join(", ", worst.Select(t => $"{t.PositionCm:0.#} cm ({t.Fraction * 100:0.0}%)")));
    }

    if (r.Junction is { } j)
    {
        Console.WriteLine($"  + shooting line from {j.PositionCm:0.#} cm: " +
            $"ρ·d {j.InertialTaperBefore:0.000} → {j.InertialTaperAfter:0.000}  " +
            $"step {j.StepRatio:0.00}x   tows {j.TowedMassG:0.0} g ({j.TowedMassFraction * 100:0.#}% of head)");
    }
    Console.WriteLine();

    foreach (var series in r.ByVelocity)
    {
        var validPi = series.Pi.Where(p => !StabilityMetrics.IsDegenerate(p)).ToList();
        string piRange = validPi.Count > 0 ? $"{validPi.Min():0.00} .. {validPi.Max():0.00}" : "n/a";
        int warnCount = series.Warning.Count(w => w);
        Console.WriteLine($"  v={series.VelocityMs,4:0} m/s   Re {series.Reynolds.Min(),7:0} - {series.Reynolds.Max(),-7:0}   " +
                          $"Π {piRange,-16}   warnings {warnCount}");
    }
    Console.WriteLine();

    if (r.SegmentTapers.Count == 0) return;
    Console.WriteLine($"  {"#",-3}{"name",-14}{"start",7}{"end",7}{"len",6}{"ρ·d in",9}{"ρ·d out",9}{"k/100cm",9}{"mass g",8}  vs archive");
    int si = 1;
    foreach (var s in r.SegmentTapers)
        Console.WriteLine($"  {si++,-3}{Trim(s.Name, 13),-14}{s.StartCm,7:0.#}{s.EndCm,7:0.#}{s.LengthCm,6:0}" +
                          $"{s.InertialTaperStart,9:0.000}{s.InertialTaperEnd,9:0.000}{s.TaperRatePer100Cm,9:0.000}" +
                          $"{s.MassG,8:0.00}  {Band(s)}");
}

// Where this segment's rate sits against the archive. Reference, never a verdict: a front taper
// outside the commercial band may be exactly what was wanted.
static string Band(SegmentTaper s)
{
    if (double.IsNaN(s.TaperRatePer100Cm)) return "";
    if (s.IsCylindrical) return "cylindrical";

    double k = Math.Abs(s.TaperRatePer100Cm);
    string where =
        k < TaperReference.RisingP10    ? "very gentle" :
        k < TaperReference.RisingP25    ? "gentle" :
        k < TaperReference.RisingP75    ? "typical" :
        k < TaperReference.RisingP90    ? "steep" : "very steep";

    bool rising = s.TaperRatePer100Cm > 0;
    bool inCommercial = rising
        && k >= TaperReference.CommercialRisingLo && k <= TaperReference.CommercialRisingHi;
    return where + (inCommercial ? "  · commercial band" : "");
}

static string Trim(string s, int n) => s.Length <= n ? s : s[..n];

static string? Arg(string[] a, int i) => i < a.Length && !a[i].StartsWith('-') ? a[i] : null;

static string? Opt(string[] a, string name)
{
    int i = Array.FindIndex(a, x => string.Equals(x, name, StringComparison.OrdinalIgnoreCase));
    return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
}

static string Sanitize(string name)
{
    foreach (char c in Path.GetInvalidFileNameChars()) name = name.Replace(c, '_');
    return name;
}
