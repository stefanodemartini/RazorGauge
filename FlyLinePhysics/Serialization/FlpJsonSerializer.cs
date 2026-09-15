using System.Text;
using System.Text.Json;
using FlyLinePhysics.Model;

namespace FlyLinePhysics.Serialization;

/// <summary>
/// Reads/writes the .flp JSON format — same options as
/// DiametroLineaDesktop.Services.ProjectService (plain System.Text.Json, WriteIndented, no naming
/// policy: file keys are already PascalCase, matching the C# property names 1:1). Pure
/// (de)serialization only — unlike ProjectService.Save, this never touches ModifiedAt or creates
/// directories, since it isn't a project-save workflow.
/// </summary>
public static class FlpJsonSerializer
{
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };

    public static string Serialize(FlyLineProject project) =>
        JsonSerializer.Serialize(project, Options);

    public static FlyLineProject Deserialize(string json) =>
        JsonSerializer.Deserialize<FlyLineProject>(json, Options)
            ?? throw new InvalidDataException("Invalid or empty .flp content.");

    public static FlyLineProject Load(string path) =>
        Deserialize(File.ReadAllText(path, Encoding.UTF8));

    public static void Save(FlyLineProject project, string path) =>
        File.WriteAllText(path, Serialize(project), Encoding.UTF8);
}
