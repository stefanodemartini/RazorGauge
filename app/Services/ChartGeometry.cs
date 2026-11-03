using DiametroLineaDesktop.Models;
using SkiaSharp;
using ScottColor = ScottPlot.Color;

namespace DiametroLineaDesktop.Services;

/// <summary>
/// Geometry and colour lookups shared by every chart renderer — the on-screen chart
/// (MainWindow.RenderSegmentOverlay), the PDF chart image (ChartRenderer, used by both the GUI's
/// PDF export and the headless CLI) — so a fix here is a fix everywhere at once, instead of the
/// same bug needing to be found and fixed separately in each renderer (which happened more than
/// once before this was pulled out: see the display-consistency skill).
///
/// Everything here is a pure function of the segments/zones/nozzles passed in — no UI state, no
/// mutation — which is what makes it safe to call from a console app with no window at all.
/// </summary>
public static class ChartGeometry
{
    /// <summary>
    /// Builds a node list from compensated segment start/end diameters so the compensated profile
    /// can be rendered in the same style as the design profile. A tiny epsilon is added when two
    /// consecutive nodes share the same X to avoid division-by-zero in piecewise interpolation.
    /// </summary>
    public static List<(double X, double Y)> GetCompNodes(IReadOnlyList<ProjectSegment> segments)
    {
        var nodes = new List<(double X, double Y)>();
        foreach (var seg in segments.OrderBy(s => s.StartCm).Where(s => s.HasCompensation))
        {
            double xs = seg.StartCm;
            if (nodes.Count > 0 && Math.Abs(nodes[^1].X - xs) < 1e-6)
                xs += 1e-4;
            nodes.Add((xs, seg.EffectiveBoundaryStartDiamMm));
            nodes.Add((seg.EndCm, seg.EffectiveBoundaryEndDiamMm));
        }
        return nodes;
    }

    /// <summary>
    /// The real material zones as (start, end, density) spans, found from each segment's own
    /// compensated slices — not from a segment's top-level SpecWeightGCm3, which for a LIVE
    /// (not-yet-baked) zone design stays at the shared base density regardless of its zones
    /// (ApplyZoneDensities only ever writes the real per-slice material into CompSliceDensities). A
    /// material can also start or end mid-segment — "il cambio di colore può avvenire in un punto
    /// qualsiasi dei tapers senza che coincida con il cambio di pendenza" — so this flattens every
    /// HasCompensation segment's own slices into one continuous sequence and walks that, which finds
    /// a transition wherever it really is, whether that's at a segment boundary (a loaded/baked
    /// snapshot, effectively one slice per segment) or partway through one (a live zone design).
    /// Kept as the one place that computes these spans so material boundaries and the "M{n}" tag
    /// rendering can't drift apart into two different ideas of where a zone starts and ends.
    /// </summary>
    public static List<(double StartX, double EndX, double Density)> GetMaterialZoneSpans(
        IReadOnlyList<ProjectSegment> segments, List<(double X, double Y)> sorted,
        Func<double, bool>? isTransition = null)
    {
        var flat = new List<(double X, double Density)>();
        foreach (var seg in segments.OrderBy(s => s.StartCm).Where(s => s.HasCompensation))
        {
            int ns = seg.CompSliceXsCm.Length;
            for (int i = 0; i < ns; i++)
                flat.Add((seg.StartCm + seg.CompSliceXsCm[i], seg.CompSliceDensities[i]));
        }
        if (flat.Count == 0) return new();
        flat = flat.OrderBy(f => f.X).ToList();

        // A nozzle-to-nozzle transition is a ramp — a different density every slice. Grouped
        // as-is it would be one "material zone" per cm; it is one span instead, Density = NaN.
        bool T(double d) => isTransition != null && isTransition(d);
        bool SameSpan(double a, double b) => T(a) ? T(b) : !T(b) && Math.Abs(a - b) <= 1e-6;

        var spans = new List<(double StartX, double EndX, double Density)>();
        double spanStart = sorted[0].X;
        for (int i = 0; i < flat.Count; i++)
        {
            bool last = i == flat.Count - 1;
            if (!last && SameSpan(flat[i].Density, flat[i + 1].Density)) continue;
            double x = last ? sorted[^1].X : (flat[i].X + flat[i + 1].X) / 2.0;
            spans.Add((spanStart, x, T(flat[i].Density) ? double.NaN : flat[i].Density));
            spanStart = x;
        }
        return spans;
    }

    /// <summary>
    /// Whether a density is a nozzle-to-nozzle transition (the ramp a physics compensation lays
    /// between two materials) rather than a material itself: strictly between two nozzles and equal
    /// to none. The nozzles hold the exact material densities of a C file, so this is exact.
    /// Older C files stored them rounded (2 or 3 decimals) — no slice matches a nozzle exactly
    /// there, and every slice would read as a transition — so when not every nozzle density is
    /// found among the slices, nothing is a transition (those files have no ramps anyway).
    /// </summary>
    public static Func<double, bool> TransitionTest(
        IEnumerable<double> sliceDensities, IReadOnlyList<NozzleDefinition> nozzles)
    {
        var mats = nozzles.Select(n => n.DensityGCm3).Where(d => d > 0).Distinct().OrderBy(d => d).ToArray();
        if (mats.Length < 2) return _ => false;
        var present = sliceDensities.Distinct().ToArray();
        if (!mats.All(m => present.Any(d => Math.Abs(d - m) < 1e-9))) return _ => false;
        return d => d > mats[0] && d < mats[^1] && !mats.Any(m => Math.Abs(d - m) < 1e-9);
    }

    /// <summary>
    /// Colour of a transition slice: the two real nozzle colours on either side of its density,
    /// mixed in proportion — the gradient a producer actually sees as one material gives way to
    /// the next.
    /// </summary>
    public static ScottColor TransitionColor(double density, IReadOnlyList<NozzleDefinition> nozzles)
    {
        var mats = nozzles.Where(n => n.DensityGCm3 > 0).OrderBy(n => n.DensityGCm3).ToList();
        var lo = mats.LastOrDefault(n => n.DensityGCm3 <= density) ?? mats[0];
        var hi = mats.FirstOrDefault(n => n.DensityGCm3 >= density) ?? mats[^1];
        TryParseHexColor(lo.ColorHex, out var cl);
        TryParseHexColor(hi.ColorHex, out var ch);
        double t = hi.DensityGCm3 > lo.DensityGCm3
            ? Math.Clamp((density - lo.DensityGCm3) / (hi.DensityGCm3 - lo.DensityGCm3), 0, 1) : 0;
        t = Math.Round(t * 10) / 10; // ten steps: runs of a few cm, drawn as one fill each
        byte Mix(byte a, byte b) => (byte)Math.Round(a + (b - a) * t);
        return new ScottColor(Mix(cl.R, ch.R), Mix(cl.G, ch.G), Mix(cl.B, ch.B));
    }

    /// <summary>
    /// Where the ORIGINAL taper's own shape changes — every fine slice inherits the Name of the
    /// real NC segment it was cut from (see BuildCompensatedSnapshotProject), so a Name change here
    /// marks a true taper transition (e.g. a straight taper ending into a level run), independent of
    /// whether the material also changes there. Slope changes and nozzle changes are different
    /// events that don't always land on the same X — the design sheet keeps them apart (solid vs
    /// dashed lines, TAPER vs NOZZLE strip; see <see cref="ProductionSchedule"/>).
    /// Walks <paramref name="segments"/> by its own StartCm/EndCm and interpolates Y from whichever
    /// <paramref name="sorted"/> node list the caller passed — never by indexing into it directly.
    /// </summary>
    public static List<(double X, double Y)> GetTaperShapeBoundaries(
        IReadOnlyList<ProjectSegment> segments, List<(double X, double Y)> sorted)
    {
        var segs = segments.OrderBy(s => s.StartCm).ToList();
        if (segs.Count == 0) return sorted;

        var result = new List<(double X, double Y)> { (segs[0].StartCm, InterpolateProfileY(sorted, segs[0].StartCm)) };
        for (int i = 0; i < segs.Count; i++)
        {
            bool lastSeg = i == segs.Count - 1;
            if (lastSeg || segs[i + 1].Name != segs[i].Name)
                result.Add((segs[i].EndCm, InterpolateProfileY(sorted, segs[i].EndCm)));
        }
        return result;
    }

    /// <summary>
    /// The colour to paint at one slice of a C profile: if a real Nozzle Zone covers this position,
    /// its own user-chosen colour (or M1's, outside any zone) — otherwise (no zones defined at all,
    /// e.g. a plain physics target-speed compensation) the auto density gradient. Used for both the
    /// live preview and a loaded baked snapshot alike.
    /// </summary>
    public static ScottColor GetSliceColor(double xAbsCm, double density, double minDens, double densRng,
        IReadOnlyList<NozzleZone> zones, IReadOnlyList<NozzleDefinition> nozzles,
        Func<double, bool>? isTransition = null)
    {
        if (isTransition != null && isTransition(density))
            return TransitionColor(density, nozzles);
        if (zones.Count > 0)
        {
            var zone = zones.FirstOrDefault(z => xAbsCm >= z.StartCm && xAbsCm < z.EndCm);
            // A NozzleZone itself carries no colour — only which nozzle it uses; the colour is the
            // nozzle's own (matches NozzleZoneVm.ColorHex, which is likewise just nozzles[idx]).
            string hex = zone != null && zone.NozzleIndex >= 0 && zone.NozzleIndex < nozzles.Count
                ? nozzles[zone.NozzleIndex].ColorHex
                : (nozzles.Count > 0 ? nozzles[0].ColorHex : "DC3232");
            if (TryParseHexColor(hex, out var col)) return col;
        }
        return DensityColor(densRng > 0 ? Math.Clamp((density - minDens) / densRng, 0, 1) : 0.5);
    }

    /// <summary>
    /// Which nozzle (0-based) a material span is: the zone covering it, else the nozzle whose
    /// density matches. -1 when there are neither zones nor nozzle densities.
    /// </summary>
    public static int MaterialIndex(double xAbsCm, double density,
        IReadOnlyList<NozzleZone> zones, IReadOnlyList<NozzleDefinition> nozzles)
    {
        int idx = zones.FirstOrDefault(z => xAbsCm >= z.StartCm && xAbsCm < z.EndCm)?.NozzleIndex ?? -1;
        if (idx >= 0) return idx;
        double bestDiff = double.MaxValue;
        for (int i = 0; i < nozzles.Count; i++)
        {
            if (nozzles[i].DensityGCm3 <= 0) continue;
            double diff = Math.Abs(nozzles[i].DensityGCm3 - density);
            if (diff < bestDiff) { bestDiff = diff; idx = i; }
        }
        return idx;
    }

    /// <summary>
    /// The production strips under the profile — TAPER, NOZZLE · DENSITY and COLOR, one above
    /// the other on the chart's own X axis, so every boundary sits exactly under the point of the
    /// line it belongs to. Taper boundaries are solid, nozzle boundaries dashed; a nozzle is told
    /// by its shade and hatch (<see cref="NozzlePattern"/>), never by colour, and a transition by
    /// its diagonal hatch. Returns the Y of the strips' bottom edge, for the axis limits.
    /// </summary>
    /// <param name="yTop">Top of the TAPER strip (data units, below the Ø labels).</param>
    /// <param name="band">Height of one strip (data units).</param>
    public static double DrawProductionStrips(ScottPlot.Plot plot, ProductionSchedule s,
        double yTop, double band, float fontSize, float hatchTile, Func<string, string>? translate = null)
    {
        translate ??= t => t;
        if (s.Tapers.Count == 0) return yTop;
        double x0 = s.StartCm, len = Math.Max(1, s.EndCm - s.StartCm);
        double titleX = x0 - len * 0.012;
        var ink   = new ScottColor(31, 35, 41);

        void Title(string t, double y)
        {
            var l = plot.Add.Text(t, titleX, y);
            l.LabelFontSize = fontSize; l.LabelBold = true; l.LabelFontColor = ink;
            l.LabelAlignment = ScottPlot.Alignment.MiddleRight;
            l.LabelBackgroundColor = ScottPlot.Colors.Transparent; l.LabelBorderWidth = 0;
        }
        void Label(string t, double x, double y, bool bold, float size, bool boxed = false)
        {
            var l = plot.Add.Text(t, x, y);
            l.LabelFontSize = size; l.LabelBold = bold; l.LabelFontColor = ink;
            l.LabelAlignment = ScottPlot.Alignment.MiddleCenter;
            l.LabelBackgroundColor = boxed ? ScottPlot.Colors.White : ScottPlot.Colors.Transparent;
            l.LabelBorderWidth = 0; l.LabelPadding = boxed ? 2 : 0;
        }
        ScottPlot.Plottables.Rectangle Box(double a, double b, double y0, double y1, ScottColor fill, float lineW = 1.2f)
        {
            var r = plot.Add.Rectangle(a, b, y0, y1);
            r.FillColor = fill; r.LineColor = ink; r.LineWidth = lineW;
            return r;
        }
        void VLine(double x, double y0, double y1, bool dashed)
        {
            var l = plot.Add.Scatter(new[] { x, x }, new[] { y0, y1 });
            l.Color = ink; l.LineWidth = 1.2f; l.MarkerSize = 0;
            if (dashed) l.LinePattern = ScottPlot.LinePattern.Dashed;
        }

        // TAPER
        double tTop = yTop, tBot = yTop - band;
        Title(translate("TAPER"), (tTop + tBot) / 2);
        for (int i = 0; i < s.Tapers.Count; i++)
        {
            var t = s.Tapers[i];
            Box(t.StartCm, t.EndCm, tBot, tTop, i % 2 == 0 ? ScottPlot.Colors.White : new ScottColor(243, 244, 246));
            if (t.LengthCm > len * 0.02) Label(t.Name, (t.StartCm + t.EndCm) / 2, (tTop + tBot) / 2, false, fontSize);
        }
        foreach (var t in s.Tapers) VLine(t.StartCm, tBot, tTop, dashed: false);
        VLine(s.Tapers[^1].EndCm, tBot, tTop, dashed: false);

        // NOZZLE · DENSITY — the strip, then a text row (density) and a length row under it
        double nTop = tBot - band * 0.35, nBot = nTop - band;
        double rhoY = nBot - band * 0.45, lenY = nBot - band * 1.05, nTextBot = nBot - band * 1.45;
        Title(translate("NOZZLE"), nTop - band * 0.30);
        Title(translate("DENSITY"), nTop - band * 0.85);
        foreach (var r in s.Nozzles)
        {
            var box = Box(r.StartCm, r.EndCm, nBot, nTop, ScottPlot.Colors.White, 0.8f);
            box.FillHatch = new NozzlePattern.Hatch(r.Nozzle, hatchTile);
            if (r.IsTransition) continue;
            double mid = (r.StartCm + r.EndCm) / 2;
            if (r.LengthCm > len * 0.006)
                Label($"M{r.Nozzle + 1}", mid, (nTop + nBot) / 2, true, fontSize, boxed: true);
            if (r.LengthCm > len * 0.025)
            {
                Label($"ρ {r.StartRho:0.000}", mid, rhoY, false, fontSize * 0.9f);
                Label($"{r.LengthCm:0}", mid, lenY, false, fontSize * 0.85f);
            }
        }
        var chain = plot.Add.Scatter(new[] { x0, s.EndCm }, new[] { lenY - band * 0.25, lenY - band * 0.25 });
        chain.Color = ink; chain.LineWidth = 0.8f; chain.MarkerSize = 0;
        VLine(s.Nozzles[0].StartCm, nTextBot, nTop, dashed: true);
        foreach (var r in s.Nozzles) VLine(r.EndCm, nTextBot, nTop, dashed: true);

        // COLOR — the line's real pigment, labelled with its hex code
        double cTop = nTextBot - band * 0.25, cBot = cTop - band * 0.75;
        Title(translate("COLOR"), (cTop + cBot) / 2);
        foreach (var c in s.Colors)
        {
            TryParseHexColor(c.Hex, out var col);
            Box(c.StartCm, c.EndCm, cBot, cTop, col, 0.8f);
            if (c.EndCm - c.StartCm > len * 0.04)
            {
                double lum = (0.299 * col.R + 0.587 * col.G + 0.114 * col.B) / 255.0;
                var lbl = plot.Add.Text($"#{c.Hex}", (c.StartCm + c.EndCm) / 2, (cTop + cBot) / 2);
                lbl.LabelFontSize = fontSize * 0.85f; lbl.LabelFontColor = lum > 0.55 ? ink : ScottPlot.Colors.White;
                lbl.LabelAlignment = ScottPlot.Alignment.MiddleCenter;
                lbl.LabelBackgroundColor = ScottPlot.Colors.Transparent; lbl.LabelBorderWidth = 0;
            }
        }
        return cBot;
    }

    /// <summary>
    /// A single 45°-diagonal stroke, the classic architectural stand-in for an arrowhead where a
    /// dimension line meets its extension line. Built as a custom <see cref="ScottPlot.IMarker"/> so
    /// the diagonal is computed in PIXEL space (<see cref="Render"/> only ever sees the already-
    /// projected <paramref name="center"/>) — a 45° tick built from data-space coordinates would not
    /// look like 45° on screen here, since the chart's X axis (cm, hundreds) and Y axis (mm ÷ 2,
    /// single digits) never share a common scale.
    /// </summary>
    private sealed class DiagonalTickMarker : ScottPlot.IMarker
    {
        public void Render(SKCanvas canvas, SKPaint paint, ScottPlot.Pixel center, float size, ScottPlot.MarkerStyle markerStyle)
        {
            float offset = size / 2f;
            var path = new SKPath();
            path.MoveTo(center.X - offset, center.Y + offset);
            path.LineTo(center.X + offset, center.Y - offset);
            ScottPlot.Drawing.DrawPath(canvas, paint, path, markerStyle.LineStyle);
        }
    }

    /// <summary>
    /// Draws a continuous chain of length dimension callouts along <paramref name="boundaries"/> —
    /// technical-drawing style: a vertical extension tick from the profile edge up to a shared
    /// dimension row at each boundary, a 45° diagonal tick (<see cref="DiagonalTickMarker"/>) where
    /// the dimension line crosses each extension tick, and the segment length in a plain horizontal
    /// label sitting just above the line (never rotated, never breaking the line itself), unitless
    /// (the row itself is always centimetres, same as the X axis). Drawn ABOVE the profile, well clear
    /// of the S1/S2 taper tags and M{n} material badges that also live up there (those sit right
    /// against the profile edge; this row sits much further out) — the Ø/position node labels are the
    /// only thing below the profile, so the two callout systems never compete for the same band any
    /// more. Extension ticks and their diagonal marks are drawn once per boundary, not once per
    /// adjacent segment, so the chain is continuous with no gap or double line where one segment's end
    /// is the next one's start.
    /// </summary>
    public static void DrawLengthDimensionChain(
        ScottPlot.Plot plot,
        List<(double X, double Y)> boundaries,
        List<(double X, double Y)> profile,
        ScottColor color,
        float fontSize)
    {
        if (boundaries.Count < 2 || profile.Count == 0) return;

        double maxDiam   = profile.Max(n => n.Y);
        double baselineY = maxDiam * 1.55;
        double labelY    = baselineY + maxDiam * 0.05;

        foreach (var b in boundaries)
        {
            double edgeY = InterpolateProfileY(profile, b.X) / 2.0;
            var ext = plot.Add.Scatter(new[] { b.X, b.X }, new[] { edgeY, baselineY });
            ext.Color = color.WithAlpha(0.45f);
            ext.LineWidth = 0.8f;
            ext.MarkerSize = 0;

            var tick = plot.Add.Marker(b.X, baselineY, ScottPlot.MarkerShape.FilledCircle, 11f, color);
            tick.MarkerLineColor = color;
            tick.MarkerLineWidth = 1.6f;
            tick.MarkerStyle.CustomRenderer = new DiagonalTickMarker();
        }

        for (int i = 0; i < boundaries.Count - 1; i++)
        {
            double x0 = boundaries[i].X, x1 = boundaries[i + 1].X;
            double midX = (x0 + x1) / 2.0;
            string text = $"{x1 - x0:0.#}";

            var dim = plot.Add.Scatter(new[] { x0, x1 }, new[] { baselineY, baselineY });
            dim.Color = color;
            dim.LineWidth = 1.0f;
            dim.MarkerSize = 0;

            var lbl = plot.Add.Text(text, midX, labelY);
            lbl.LabelFontSize        = fontSize;
            lbl.LabelBold            = false;
            lbl.LabelFontColor       = color;
            lbl.LabelAlignment       = ScottPlot.Alignment.LowerCenter;
            lbl.LabelBackgroundColor = ScottPlot.Colors.Transparent;
            lbl.LabelBorderWidth     = 0;
            lbl.LabelPadding         = 2;
            lbl.OffsetX = 0; lbl.OffsetY = 0;
        }
    }

    // ── Low-level primitives ────────────────────────────────────────────────
    // Pure functions with no dependency on segments/zones/nozzles at all — moved here from
    // MainWindow (where they were already `private static`) purely so ChartRenderer can call them
    // too, without a WPF reference. MainWindow keeps calling these same ones (it references
    // Services already), so there remains exactly one implementation of each.

    public static double InterpolateProfileY(List<(double X, double Y)> sorted, double x)
    {
        if (x <= sorted[0].X)  return sorted[0].Y;
        if (x >= sorted[^1].X) return sorted[^1].Y;
        for (int i = 0; i < sorted.Count - 1; i++)
        {
            if (x >= sorted[i].X && x <= sorted[i + 1].X)
            {
                double t = (x - sorted[i].X) / (sorted[i + 1].X - sorted[i].X);
                return sorted[i].Y + t * (sorted[i + 1].Y - sorted[i].Y);
            }
        }
        return sorted[^1].Y;
    }

    public static bool TryParseHexColor(string hex6, out ScottColor color)
    {
        color = new ScottColor(200, 200, 200);
        if (string.IsNullOrWhiteSpace(hex6)) return false;
        hex6 = hex6.TrimStart('#');
        if (hex6.Length < 6) return false;
        try
        {
            byte r = Convert.ToByte(hex6[0..2], 16);
            byte g = Convert.ToByte(hex6[2..4], 16);
            byte b = Convert.ToByte(hex6[4..6], 16);
            color = new ScottColor(r, g, b);
            return true;
        }
        catch { return false; }
    }

    /// <summary>Maps t ∈ [0,1] to a blue→cyan→green→yellow→red colour ramp.</summary>
    public static ScottColor DensityColor(double t)
    {
        t = Math.Clamp(t, 0, 1);
        double r, g, b;
        if (t < 0.25)      { double s = t / 0.25;       r = 0;         g = s;         b = 1; }
        else if (t < 0.5)  { double s = (t-0.25)/0.25;  r = 0;         g = 1;         b = 1-s; }
        else if (t < 0.75) { double s = (t-0.5)/0.25;   r = s;         g = 1;         b = 0; }
        else               { double s = (t-0.75)/0.25;  r = 1;         g = 1-s;       b = 0; }
        return new ScottColor((byte)(r*255), (byte)(g*255), (byte)(b*255));
    }

    /// <summary>Draws a filled band between top/bottom Y arrays, either flat-tinted or with Lambert cylindrical shading.</summary>
    /// <summary>
    /// Fills a compensated profile: one shaded body per run of slices sharing a colour, never one
    /// per slice. Per-slice fills (21 translucent layers each, overlapped to hide gaps) stacked
    /// their alpha where neighbours met and drew a dark seam at every slice edge — and cost ~84k
    /// polygons for a C file. A single-colour line is now one fill.
    /// </summary>
    public static void DrawCompensatedProfile(ScottPlot.Plot plot, IEnumerable<ProjectSegment> compSegs,
        Func<double, double, ScottColor> colorAt)
    {
        var xs = new List<double>(); var ds = new List<double>();
        ScottColor? runColor = null;

        void Flush()
        {
            if (xs.Count >= 2 && runColor is ScottColor c)
                DrawLineFill(plot, xs.ToArray(), ds.Select(d => d / 2.0).ToArray(), ds.Select(d => -d / 2.0).ToArray(), c, solid: true);
        }

        foreach (var seg in compSegs.OrderBy(s => s.StartCm))
        {
            int ns = seg.CompSliceXsCm.Length;
            for (int i = 0; i < ns; i++)
            {
                // Slice edges: the segment's own ends, else the midpoint between slice centres
                double x0 = i == 0      ? seg.StartCm : seg.StartCm + (seg.CompSliceXsCm[i - 1] + seg.CompSliceXsCm[i]) / 2.0;
                double x1 = i == ns - 1 ? seg.EndCm   : seg.StartCm + (seg.CompSliceXsCm[i] + seg.CompSliceXsCm[i + 1]) / 2.0;
                double d0 = i == 0      ? seg.EffectiveBoundaryStartDiamMm : (seg.CompSliceDiamsMm[i - 1] + seg.CompSliceDiamsMm[i]) / 2.0;
                double d1 = i == ns - 1 ? seg.EffectiveBoundaryEndDiamMm   : (seg.CompSliceDiamsMm[i] + seg.CompSliceDiamsMm[i + 1]) / 2.0;
                var col = colorAt(seg.StartCm + seg.CompSliceXsCm[i], seg.CompSliceDensities[i]);

                bool sameRun = runColor is ScottColor rc
                               && rc.R == col.R && rc.G == col.G && rc.B == col.B && rc.A == col.A
                               && xs.Count > 0 && Math.Abs(xs[^1] - x0) < 1e-6;
                if (!sameRun)
                {
                    // A new colour starts where the last run ended — sharing that edge, no overlap
                    double? joinX = xs.Count > 0 ? xs[^1] : null, joinD = ds.Count > 0 ? ds[^1] : null;
                    Flush();
                    xs.Clear(); ds.Clear();
                    runColor = col;
                    if (joinX is double jx && Math.Abs(jx - x0) < 1e-6) { xs.Add(jx); ds.Add(joinD!.Value); }
                    else { xs.Add(x0); ds.Add(d0); }
                }
                xs.Add(x1); ds.Add(d1);
            }
        }
        Flush();
    }

    public static void DrawLineFill(ScottPlot.Plot plot,
                                     double[] xs, double[] topYs, double[] botYs,
                                     ScottColor bodyColor,
                                     bool solid = false)
    {
        if (xs.Length < 2) return;

        ScottPlot.Coordinates[] Band(double fraction)
        {
            var top = xs.Select((x, i) => new ScottPlot.Coordinates(x,  topYs[i] * fraction));
            var bot = xs.Select((x, i) => new ScottPlot.Coordinates(x,  botYs[i] * fraction))
                        .Reverse();
            return top.Concat(bot).ToArray();
        }

        if (solid)
        {
            // ── Lambert cylindrical shading ───────────────────────────────
            // Draw 20 concentric bands, outermost (darkest) first.
            // Each inner band is brighter and, at high alpha, nearly replaces
            // the region covered by the previous darker band.
            // v=1 (edge) → b=0 → darkest; v=0 (centre) → b=1 → brightest.
            const int N = 20;
            const float layerAlpha = 0.91f;

            for (int i = 0; i <= N; i++)
            {
                double frac = 1.0 - (double)i / N;        // 1.0 → ~0
                double v    = frac;
                double b    = Math.Sqrt(1.0 - v * v);     // 0 at edge, 1 at centre

                // Shade factor: 0.25 (very dark edge) → 1.0 (full body at centre)
                float shade = (float)(0.25 + 0.75 * b);
                byte  r     = (byte)Math.Min(255, (int)(bodyColor.Red   * shade));
                byte  g     = (byte)Math.Min(255, (int)(bodyColor.Green * shade));
                byte  bl    = (byte)Math.Min(255, (int)(bodyColor.Blue  * shade));

                // Specular glint in the inner 15% of the radius
                if (b > 0.85)
                {
                    float spec = (float)((b - 0.85) / 0.15) * 0.55f;
                    r  = (byte)Math.Min(255, r  + (int)((255 - r)  * spec));
                    g  = (byte)Math.Min(255, g  + (int)((255 - g)  * spec));
                    bl = (byte)Math.Min(255, bl + (int)((255 - bl) * spec));
                }

                var band = plot.Add.Polygon(Band(frac));
                band.FillColor = new ScottColor(r, g, bl).WithAlpha(layerAlpha);
                band.LineWidth = 0;
                band.LineColor = ScottPlot.Colors.Transparent;
            }
        }
        else
        {
            // ── Lightweight 3-layer blend for scan / imported series ──────
            var body = plot.Add.Polygon(Band(1.0));
            body.FillColor = bodyColor.WithAlpha(0.55f);
            body.LineWidth = 0;
            body.LineColor = ScottPlot.Colors.Transparent;

            var mid = plot.Add.Polygon(Band(0.60));
            mid.FillColor = ScottPlot.Colors.White.WithAlpha(0.14f);
            mid.LineWidth = 0;
            mid.LineColor = ScottPlot.Colors.Transparent;

            var hi = plot.Add.Polygon(Band(0.25));
            hi.FillColor = ScottPlot.Colors.White.WithAlpha(0.22f);
            hi.LineWidth = 0;
            hi.LineColor = ScottPlot.Colors.Transparent;
        }
    }
}
