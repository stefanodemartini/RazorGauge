using SkiaSharp;

namespace DiametroLineaDesktop.Services;

/// <summary>
/// How a nozzle is told apart on the design sheet: a grey shade plus a hatch, never its colour.
/// Four nozzles used for four densities share one pigment ("4 ugelli = 4 densità ⇒ colore unico"),
/// so colour cannot carry nozzle identity — the line's real colour is shown separately. Used by
/// the chart strips (on screen and in the PDF image) and by the PDF's own swatches, so the same
/// nozzle looks the same everywhere.
/// </summary>
public static class NozzlePattern
{
    /// <summary>Pseudo-index for a nozzle-to-nozzle transition: diagonal lines on white.</summary>
    public const int Transition = -1;

    private static readonly SKColor[] Shades =
    {
        new(0xEE, 0xF0, 0xF3), new(0xDF, 0xE3, 0xE8), new(0xCD, 0xD3, 0xDA), new(0xB9, 0xC1, 0xCA),
    };
    private static readonly SKColor Ink   = new(0x1F, 0x23, 0x29);
    private static readonly SKColor Muted = new(0x6B, 0x72, 0x80);

    /// <summary>A repeating shader for one nozzle; <paramref name="tile"/> is the hatch pitch in pixels.</summary>
    public static SKShader Shader(int nozzle, float tile)
    {
        int s = Math.Max(4, (int)Math.Round(tile));
        using var bmp = new SKBitmap(s, s);
        using (var c = new SKCanvas(bmp)) DrawTile(c, nozzle, s);
        using var img = SKImage.FromBitmap(bmp);
        return img.ToShader(SKShaderTileMode.Repeat, SKShaderTileMode.Repeat);
    }

    private static void DrawTile(SKCanvas c, int nozzle, float s)
    {
        c.Clear(nozzle < 0 ? SKColors.White : Shades[nozzle % Shades.Length]);
        using var p = new SKPaint
        {
            IsAntialias = true, Style = SKPaintStyle.Stroke,
            Color = nozzle < 0 ? Muted : Ink, StrokeWidth = Math.Max(1f, s * 0.13f),
        };
        // Each diagonal is drawn three times (shifted by one tile) so it runs on seamlessly into
        // the neighbouring tiles instead of leaving a gap at the corners.
        void Diag(bool rising)
        {
            for (int k = -1; k <= 1; k++)
            {
                float o = k * s;
                if (rising) c.DrawLine(o, s, o + s, 0, p);
                else        c.DrawLine(o, 0, o + s, s, p);
            }
        }
        switch (nozzle)
        {
            case Transition: Diag(rising: false); break;
            case 0: break;                                   // M1: plain shade
            case 1: Diag(rising: true); break;               // M2: ///
            case 2: Diag(rising: true); Diag(rising: false); break; // M3: xxx
            default:                                         // M4: dots
                p.Style = SKPaintStyle.Fill;
                c.DrawCircle(s / 2f, s / 2f, s * 0.17f, p);
                break;
        }
    }

    /// <summary>A small framed PNG swatch of the pattern, for the PDF's cards and table rows.</summary>
    public static byte[] SwatchPng(int nozzle, int width, int height, float tile)
    {
        using var bmp = new SKBitmap(width, height);
        using (var c = new SKCanvas(bmp))
        {
            using var fill = new SKPaint { Shader = Shader(nozzle, tile) };
            c.DrawRect(0, 0, width, height, fill);
            using var frame = new SKPaint { Style = SKPaintStyle.Stroke, Color = Ink, StrokeWidth = 2 };
            c.DrawRect(1, 1, width - 2, height - 2, frame);
        }
        using var img = SKImage.FromBitmap(bmp);
        using var data = img.Encode(SKEncodedImageFormat.Png, 100);
        return data.ToArray();
    }

    /// <summary>The same pattern as a ScottPlot fill, for the chart's NOZZLE strip.</summary>
    public sealed class Hatch(int nozzle, float tile) : ScottPlot.IHatch
    {
        public SKShader GetShader(ScottPlot.Color backgroundColor, ScottPlot.Color hatchColor, ScottPlot.PixelRect rect)
            => Shader(nozzle, tile);
    }
}
