using System.IO;
using System.Text;
using System.Text.Json;
using DiametroLineaDesktop.Models;

namespace DiametroLineaDesktop.Services;

public static class ProjectService
{
    public static string DefaultProjectFolder =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                     "FlyLineProfiler", "Projects");

    public const string FileFilter    = "RazorGauge project (*.flp)|*.flp";
    /// <summary>
    /// Resta ".flp" anche dopo che il prodotto si chiama RazorGauge: cambiarla renderebbe
    /// invisibili tutti i progetti gia salvati e romperebbe le associazioni di sistema, in cambio
    /// di nulla. L'estensione identifica il formato, non il nome commerciale.
    /// </summary>
    public const string FileExtension = ".flp";

    private static readonly JsonSerializerOptions _opts = new() { WriteIndented = true };

    public static void Save(FlyLineProject project, string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        project.ModifiedAt = DateTime.UtcNow;
        File.WriteAllText(path, JsonSerializer.Serialize(project, _opts), Encoding.UTF8);
    }

    public static FlyLineProject Load(string path)
    {
        var json = File.ReadAllText(path, Encoding.UTF8);
        return JsonSerializer.Deserialize<FlyLineProject>(json, _opts)
               ?? throw new InvalidDataException("Invalid or empty project file.");
    }

    public static FlyLineProject New(string name = "Untitled") =>
        new() { Name = name, CreatedAt = DateTime.UtcNow, ModifiedAt = DateTime.UtcNow };
}
