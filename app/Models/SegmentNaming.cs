using System.Text.RegularExpressions;

namespace DiametroLineaDesktop.Models;

/// <summary>
/// Taper names. A segment's name is keyed by its start X, so inserting a node used to give the new
/// segment "S{index}" while every other segment kept its old name — leaving gaps (no S6, no S9)
/// and duplicates (two different slopes both "S10"). Two adjacent tapers with one name are one
/// taper as far as a C file is concerned (its shape boundaries are Name changes), so the slope
/// change between them vanished from the design sheet. Automatic names are therefore always
/// renumbered by position; a name the user typed is theirs and is kept.
/// </summary>
public static class SegmentNaming
{
    private static readonly Regex Auto = new(@"^S\d+$", RegexOptions.Compiled);

    /// <summary>Empty, or "S" + number — a name the program gave, not one the user chose.</summary>
    public static bool IsAuto(string? name) => string.IsNullOrWhiteSpace(name) || Auto.IsMatch(name.Trim());

    /// <summary>The name for the segment at 0-based position <paramref name="index"/>.</summary>
    public static string For(string? saved, int index) => IsAuto(saved) ? $"S{index + 1}" : saved!;
}
