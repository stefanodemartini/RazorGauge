using System.Text.Json.Nodes;
using FlyLinePhysics.Model;
using FlyLinePhysics.Serialization;
using Xunit;

namespace FlyLinePhysics.Tests;

public class RoundTripTests
{
    private static string FixturePath => Path.Combine(AppContext.BaseDirectory, "TestData", "sample_full.flp");

    [Fact]
    public void RealFile_RoundTrips_Losslessly()
    {
        string originalJson = File.ReadAllText(FixturePath);

        var project = FlpJsonSerializer.Deserialize(originalJson);
        string roundTrippedJson = FlpJsonSerializer.Serialize(project);

        var originalObj = JsonNode.Parse(originalJson)!.AsObject();
        var roundTrippedObj = JsonNode.Parse(roundTrippedJson)!.AsObject();

        // Every field the source file actually had must survive unchanged. The round-tripped JSON
        // is allowed to gain extra keys (CoreDiameterMm/CoreDensityGCm3: null) that this schema
        // adds but the fixture predates — that's expected forward evolution, not data loss.
        foreach (var (key, originalValue) in originalObj)
        {
            Assert.True(roundTrippedObj.ContainsKey(key), $"Round-tripped JSON is missing key '{key}'.");
            Assert.True(JsonNode.DeepEquals(originalValue, roundTrippedObj[key]),
                $"Key '{key}' differs after round-trip.\n--- original ---\n{originalValue}\n--- round-tripped ---\n{roundTrippedObj[key]}");
        }

        // The fixture predates the core-model fields — they must stay unset, not default to 0.
        Assert.Null(project.CoreDiameterMm);
        Assert.Null(project.CoreDensityGCm3);
    }

    [Fact]
    public void LegacyFile_WithoutVersionKey_DefaultsToVersion1()
    {
        // Reproduces the shape of Stefano's older real .flp files (e.g. DT.flp), which predate the
        // "Version" field entirely and so never wrote that key at all.
        const string legacyJson = """
        {
          "Name": "Legacy",
          "CreatedAt": "2026-06-12T13:17:13.1015074Z",
          "ModifiedAt": "2026-06-12T13:48:21.1407076Z",
          "Notes": "",
          "UseSharedDensity": true,
          "SharedDensityGCm3": 0.95,
          "IsSinking": false,
          "IsFullLine": false,
          "WaterType": "fresh",
          "WaterTempC": 20,
          "ScanPoints": []
        }
        """;

        var project = FlpJsonSerializer.Deserialize(legacyJson);

        Assert.Equal(1, project.Version);
        Assert.Null(project.CoreDiameterMm);
        Assert.Null(project.CoreDensityGCm3);
    }

    [Fact]
    public void CoreFields_RoundTrip_Correctly()
    {
        var project = new FlyLineProject
        {
            Version = 2,
            Name = "Core test",
            CoreDiameterMm = 0.35,
            CoreDensityGCm3 = 1.38,
        };

        string json = FlpJsonSerializer.Serialize(project);
        var reloaded = FlpJsonSerializer.Deserialize(json);

        Assert.Equal(2, reloaded.Version);
        Assert.Equal(0.35, reloaded.CoreDiameterMm);
        Assert.Equal(1.38, reloaded.CoreDensityGCm3);
    }

    [Fact]
    public void LineType_SurvivesARoundTrip_AndIsAbsentFromOlderFiles()
    {
        // This library rewrites whole files, so a key it does not model is a key it silently
        // deletes. LineType is read by the app and nothing here, which is exactly the shape of
        // field most easily lost.
        var project = FlpJsonSerializer.Deserialize(File.ReadAllText(FixturePath));
        project.LineType = "Neutral";

        var again = FlpJsonSerializer.Deserialize(FlpJsonSerializer.Serialize(project));

        Assert.Equal("Neutral", again.LineType);
    }

    [Fact]
    public void FileWithoutLineType_ReadsAsEmpty_SoTheAppCanFallBackToIsSinking()
    {
        var project = FlpJsonSerializer.Deserialize(File.ReadAllText(FixturePath));

        Assert.Equal(string.Empty, project.LineType);
    }

    [Fact]
    public void CoreDiameter_SurvivesARoundTrip()
    {
        // Same trap as LineType: this library rewrites whole files, and the app is the only thing
        // that sets the core, so a field it does not model is a field it deletes.
        var project = FlpJsonSerializer.Deserialize(File.ReadAllText(FixturePath));
        project.CoreDiameterMm = 0.845;

        var again = FlpJsonSerializer.Deserialize(FlpJsonSerializer.Serialize(project));

        Assert.Equal(0.845, again.CoreDiameterMm);
    }
}
