namespace DiametroLineaDesktop.Models;

/// <summary>
/// How a line — or one section of it — behaves in the water.
///
/// Physics only has two states: below the water's density a line floats, above it the line sinks.
/// <see cref="Neutral"/> is not a third state but a band of very slow sinking, wide enough that the
/// line is fished as if it suspended. Where that band ends is a product convention, not a measured
/// boundary, which is why it lives in one named constant
/// (<see cref="Services.SinkingSpeedCalc.NeutralMaxIns"/>) instead of being spread through the code.
/// </summary>
public enum LineDensityClass
{
    Floating,
    Neutral,
    Sinking,
}

public static class LineDensityClassExtensions
{
    public static string ToLabel(this LineDensityClass c) => c switch
    {
        LineDensityClass.Floating => "Floating",
        LineDensityClass.Neutral  => "Neutral",
        _                         => "Sinking",
    };

    /// <summary>
    /// Parses what was stored in the .flp. Unknown or missing text falls back to the caller's
    /// value, which is how a file written before LineType existed is read: from its IsSinking flag.
    /// </summary>
    public static LineDensityClass ParseOr(string? text, LineDensityClass fallback) => text?.Trim().ToLowerInvariant() switch
    {
        "floating" => LineDensityClass.Floating,
        "neutral"  => LineDensityClass.Neutral,
        "sinking"  => LineDensityClass.Sinking,
        _          => fallback,
    };
}
