using DiametroLineaDesktop.Models;
using ScottColor = ScottPlot.Color;

namespace DiametroLineaDesktop.Services;

/// <summary>
/// The Sink Map for the PDF: the profile coloured by the local sink speed of each section (blue =
/// slowest, red = fastest on this line), with a colour bar of its in/s scale under it. Same model as
/// the app's Sink Map toggle — every slice as an isolated cylinder of its own diameter and density
/// (<see cref="SinkingSpeedCalc.CylinderSinkSpeed"/>) — so the sheet shows what the screen shows.
/// A separate image, never painted over the materials chart: the two colourings must not mix.
/// </summary>
public static class SinkMapRenderer
{
    public sealed record Result(byte[] Png, double MinIns, double MaxIns);

    /// <summary>Blue → cyan → green → yellow → red, t ∈ [0, 1] — the app's Sink Map ramp.</summary>
    public static ScottColor SpeedColor(double t)
    {
        t = Math.Clamp(t, 0.0, 1.0);
        byte r, g, b;
        if (t < 0.25)      { double s = t / 0.25;          r = 0;               g = (byte)(s * 255);       b = 255; }
        else if (t < 0.50) { double s = (t - 0.25) / 0.25; r = 0;               g = 255;                   b = (byte)((1 - s) * 255); }
        else if (t < 0.75) { double s = (t - 0.50) / 0.25; r = (byte)(s * 255); g = 255;                   b = 0; }
        else               { double s = (t - 0.75) / 0.25; r = 255;             g = (byte)((1 - s) * 255); b = 0; }
        return new ScottColor(r, g, b);
    }

    /// <summary>Slices of the line with their local sink speed (m/s): a segment's own compensation
    /// slices when it has them (C file, zoned design), else the drawn taper sampled every ~12 cm.</summary>
    public static List<(double X0, double X1, double D0, double D1, double V)> Slices(
        IEnumerable<ProjectSegment> segments, bool isSalt, double tempC)
    {
        var slices = new List<(double, double, double, double, double)>();
        foreach (var seg in segments.OrderBy(s => s.StartCm))
        {
            int ns = seg.CompSliceXsCm.Length;
            if (seg.HasCompensation && ns > 0)
            {
                double half = ns > 1 ? (seg.CompSliceXsCm[1] - seg.CompSliceXsCm[0]) / 2.0 : seg.LengthCm / 2.0;
                for (int i = 0; i < ns; i++)
                {
                    double x  = seg.StartCm + seg.CompSliceXsCm[i];
                    double d0 = i > 0      ? (seg.CompSliceDiamsMm[i - 1] + seg.CompSliceDiamsMm[i]) / 2.0 : seg.CompSliceDiamsMm[i];
                    double d1 = i < ns - 1 ? (seg.CompSliceDiamsMm[i] + seg.CompSliceDiamsMm[i + 1]) / 2.0 : seg.CompSliceDiamsMm[i];
                    double v  = SinkingSpeedCalc.CylinderSinkSpeed(isSalt, tempC, seg.CompSliceDiamsMm[i], seg.CompSliceDensities[i]);
                    if (!double.IsNaN(v))
                        slices.Add((Math.Max(seg.StartCm, x - half), Math.Min(seg.EndCm, x + half), d0, d1, Math.Max(0, v)));
                }
                continue;
            }

            double rho = seg.EffectiveSpecWeightGCm3;
            if (seg.LengthCm <= 0 || rho <= 0) continue;
            int n = Math.Max(1, (int)Math.Ceiling(seg.LengthCm / 12.0));
            for (int i = 0; i < n; i++)
            {
                double t0 = (double)i / n, t1 = (i + 1.0) / n, tm = (t0 + t1) / 2.0;
                double dd = seg.EndDiameterMm - seg.StartDiameterMm;
                double v  = SinkingSpeedCalc.CylinderSinkSpeed(isSalt, tempC, seg.StartDiameterMm + tm * dd, rho);
                if (!double.IsNaN(v))
                    slices.Add((seg.StartCm + t0 * seg.LengthCm, seg.StartCm + t1 * seg.LengthCm,
                                seg.StartDiameterMm + t0 * dd, seg.StartDiameterMm + t1 * dd, Math.Max(0, v)));
            }
        }
        return slices;
    }

    /// <summary>Renders the map, or null when no section has a density to compute a speed from.</summary>
    public static Result? Render(IEnumerable<ProjectSegment> segments, bool isSalt, double tempC, SheetLanguage language)
    {
        var slices = Slices(segments, isSalt, tempC);
        if (slices.Count == 0) return null;

        double minV = slices.Min(s => s.V), maxV = slices.Max(s => s.V);
        double range = maxV - minV;
        bool uniform = range * 39.3701 < 0.0005;
        double T(double v) => uniform ? 0.0 : (v - minV) / range;

        var plot = new ScottPlot.Plot();
        plot.FigureBackground.Color = ScottPlot.Colors.White;
        plot.DataBackground.Color   = ScottPlot.Colors.White;
        plot.Axes.Color(new ScottColor(80, 80, 80));

        foreach (var (x0, x1, d0, d1, v) in slices)
        {
            var poly = plot.Add.Polygon(new ScottPlot.Coordinates[]
            {
                new(x0, d0 / 2.0), new(x1, d1 / 2.0), new(x1, -d1 / 2.0), new(x0, -d0 / 2.0),
            });
            poly.FillColor = SpeedColor(T(v));
            // A hairline in the fill's own colour closes the anti-alias seams between slices.
            poly.LineColor = SpeedColor(T(v));
            poly.LineWidth = 0.6f;
        }

        // Outline of the profile
        var outline = new ScottColor(60, 60, 60);
        var xsTop = new List<double>(); var ysTop = new List<double>();
        foreach (var s in slices) { xsTop.Add(s.X0); ysTop.Add(s.D0 / 2.0); xsTop.Add(s.X1); ysTop.Add(s.D1 / 2.0); }
        var top = plot.Add.Scatter(xsTop.ToArray(), ysTop.ToArray());               top.Color = outline; top.LineWidth = 1f; top.MarkerSize = 0;
        var bot = plot.Add.Scatter(xsTop.ToArray(), ysTop.Select(y => -y).ToArray()); bot.Color = outline; bot.LineWidth = 1f; bot.MarkerSize = 0;

        // Colour bar under the profile, as wide as the line, with its in/s scale.
        double lineX0 = slices.Min(s => s.X0), lineX1 = slices.Max(s => s.X1);
        double maxD   = slices.Max(s => Math.Max(s.D0, s.D1));
        double barTop = -maxD / 2.0 - maxD * 0.45, barH = maxD * 0.22;
        const int steps = 120;
        for (int i = 0; i < steps; i++)
        {
            double a = lineX0 + (lineX1 - lineX0) * i / steps, b = lineX0 + (lineX1 - lineX0) * (i + 1) / steps;
            var cell = plot.Add.Rectangle(a, b, barTop - barH, barTop);
            var c = SpeedColor(uniform ? 0 : (i + 0.5) / steps);
            cell.FillColor = c; cell.LineColor = c; cell.LineWidth = 0.6f;
        }
        var frame = plot.Add.Rectangle(lineX0, lineX1, barTop - barH, barTop);
        frame.FillColor = ScottPlot.Colors.Transparent; frame.LineColor = outline; frame.LineWidth = 1f;

        double minIns = minV * 39.3701, maxIns = maxV * 39.3701;
        void Tick(double x, string text, ScottPlot.Alignment align)
        {
            var t = plot.Add.Text(text, x, barTop - barH - maxD * 0.06);
            t.LabelFontSize = 20; t.LabelBold = true; t.LabelFontColor = new ScottColor(40, 40, 40);
            t.LabelAlignment = align;
            if (language != SheetLanguage.English) t.LabelFontName = "Microsoft YaHei";
        }
        if (uniform)
            Tick((lineX0 + lineX1) / 2, maxIns < 0.0005 ? SheetText.Ti(language, "floating") : $"{maxIns:0.000} in/s — " + SheetText.Ti(language, "uniform"), ScottPlot.Alignment.UpperCenter);
        else
        {
            Tick(lineX0, $"{minIns:0.000} in/s", ScottPlot.Alignment.UpperLeft);
            Tick((lineX0 + lineX1) / 2, $"{(minIns + maxIns) / 2:0.000} in/s", ScottPlot.Alignment.UpperCenter);
            Tick(lineX1, $"{maxIns:0.000} in/s", ScottPlot.Alignment.UpperRight);
        }

        plot.XLabel(SheetText.Ti(language, "Length (cm)"));
        plot.YLabel(SheetText.Ti(language, "Diameter (mm)"));
        if (language != SheetLanguage.English) plot.Font.Set("Microsoft YaHei");
        plot.Axes.Bottom.TickLabelStyle.FontSize = 15;
        plot.Axes.Left.TickLabelStyle.FontSize   = 15;
        plot.Axes.Bottom.Label.FontSize          = 16;
        plot.Axes.Left.Label.FontSize            = 16;
        double pad = (lineX1 - lineX0) * 0.02;
        plot.Axes.SetLimits(lineX0 - pad, lineX1 + pad, barTop - barH - maxD * 0.45, maxD / 2.0 + maxD * 0.25);

        return new Result(plot.GetImage(3200, 520).GetImageBytes(ScottPlot.ImageFormat.Png), minIns, maxIns);
    }
}
