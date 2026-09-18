using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using DiametroLineaDesktop.Models;
using DiametroLineaDesktop.Services;
using Microsoft.Win32;
using ScottPlot;
using ScottColor = ScottPlot.Color;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// Builds a prototype line out of real scanned pieces: pick pieces from the library, lay them on the
/// chart, slide them over each other to compare diameters, trim either end, flip end for end.
/// Where to cut is always the user's decision — the window only shows diameters and reports joints.
/// </summary>
public partial class PrototypeWindow : Window
{
    private const double HandleHitPx = 7;     // horizontal grab distance for a trim handle
    private const double BodyHitPadPx = 6;    // vertical slack around a piece's silhouette
    private const double SnapPx       = 10;   // a dragged piece's end snaps to a neighbour's end within this
    private const double MinKeptCm    = 1;

    private readonly Func<string>         _getLibraryFolder;
    private readonly Action<string>       _setLibraryFolder;
    private readonly Action<string>       _openInProfiler;

    private PrototypeProject _project = new();
    private string?          _path;
    private bool             _dirty;
    private AssemblyResult   _result = new();

    private List<LibraryPiece> _library = new();
    private PrototypePiece?    _selected;

    private enum DragKind { None, Move, TrimLeft, TrimRight }
    private DragKind        _drag = DragKind.None;
    private PrototypePiece? _dragPiece;
    private double          _dragStartMouseX;
    private double          _dragStartOffset;

    private readonly Stack<List<PrototypePiece>> _undo = new();
    private bool _fitPending = true;
    private bool _suppressNameChange;
    private ScottPlot.Plottables.VerticalLine? _hoverLine;
    private Point? _lastMouse;   // last position over the chart, for the S (split) key

    public PrototypeWindow(Func<string> getLibraryFolder, Action<string> setLibraryFolder, Action<string> openInProfiler)
    {
        InitializeComponent();
        _getLibraryFolder = getLibraryFolder;
        _setLibraryFolder = setLibraryFolder;
        _openInProfiler   = openInProfiler;

        Chart.PreviewMouseLeftButtonDown  += Chart_LeftDown;
        Chart.PreviewMouseMove            += Chart_MouseMove;
        Chart.PreviewMouseLeftButtonUp    += Chart_LeftUp;
        Chart.PreviewMouseRightButtonDown += Chart_RightDown;
        Chart.MouseLeave += (_, _) => { _lastMouse = null; SetHover(null); };
        PreviewKeyDown += Window_PreviewKeyDown;
        Closing += Window_Closing;

        SetName(_project.Name);
        ShowAllowance();
        Loaded += async (_, _) => { Recompute(); await LoadLibraryAsync(); };
    }

    // ── Library ─────────────────────────────────────────────────────────────

    private string LibraryFolder
    {
        get
        {
            string f = _getLibraryFolder();
            return string.IsNullOrWhiteSpace(f) ? PieceLibrary.DefaultFolder : f;
        }
    }

    private async Task LoadLibraryAsync()
    {
        string folder = LibraryFolder;
        LibraryFolderText.Text = folder;
        LibraryFolderText.ToolTip = folder;
        StatusText.Text = "Scanning library…";
        _library = await Task.Run(() => PieceLibrary.Load(folder));
        ApplyLibraryFilter();
        StatusText.Text = Directory.Exists(folder)
            ? $"{_library.Count} scanned pieces in the library"
            : $"Library folder not found: {folder}";
    }

    private void ApplyLibraryFilter()
    {
        string f = LibraryFilterBox.Text.Trim();
        LibraryList.ItemsSource = f.Length == 0
            ? _library
            : _library.Where(p => p.Name.Contains(f, StringComparison.OrdinalIgnoreCase)
                               || p.Folder.Contains(f, StringComparison.OrdinalIgnoreCase)).ToList();
    }

    private void LibraryFilter_TextChanged(object sender, TextChangedEventArgs e) => ApplyLibraryFilter();

    private async void RefreshLibrary_Click(object sender, RoutedEventArgs e) => await LoadLibraryAsync();

    private async void ChangeLibrary_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "Piece library folder", InitialDirectory = LibraryFolder };
        if (dlg.ShowDialog(this) != true) return;
        _setLibraryFolder(dlg.FolderName);
        await LoadLibraryAsync();
    }

    private void LibraryList_MouseDoubleClick(object sender, MouseButtonEventArgs e) => AddSelectedLibraryPiece();
    private void AddPiece_Click(object sender, RoutedEventArgs e) => AddSelectedLibraryPiece();

    private void AddSelectedLibraryPiece()
    {
        if (LibraryList.SelectedItem is not LibraryPiece lib) return;
        PushUndo();
        var piece = PrototypeAssembler.CreatePiece(lib, _project);
        _project.Pieces.Add(piece);
        _selected = piece;
        _fitPending = true;
        MarkDirty();
        Recompute();
        StatusText.Text = $"Added {lib.Name} ({lib.LengthCm:0} cm)";
    }

    // ── Recompute + render ─────────────────────────────────────────────────

    private void Recompute()
    {
        _result = PrototypeAssembler.Assemble(_project);
        RenderChart();
        RefreshTable();
        CutListBox.Text = _result.Pieces.Count == 0 ? "Add pieces from the library on the left." : PrototypeAssembler.CutList(_result, _project.JointAllowanceCm);
        WarningsText.Text = string.Join("\n", _result.Warnings);
        TotalsText.Text = _result.Pieces.Count == 0 ? string.Empty
            : Inv($"{_result.Pieces.Count} pieces   length {_result.LengthCm / 100.0:0.00} m")
              + (_result.MassG.HasValue ? Inv($"   mass {_result.MassG:0.00} g  ({_result.MassGrains:0} gr)") : "   mass: density missing");
    }

    private void RenderChart()
    {
        var plot = Chart.Plot;
        plot.Clear();
        plot.XLabel("Assembly position (cm)");
        plot.YLabel("Diameter (mm)");
        // The profile is drawn symmetric (±radius) but read as diameters: label the ticks that way.
        plot.Axes.Left.TickGenerator = new ScottPlot.TickGenerators.NumericAutomatic
        {
            LabelFormatter = y => (Math.Abs(y) * 2).ToString("0.0#", CultureInfo.InvariantCulture),
        };

        // Selected piece drawn last so it sits on top and is the one you grab.
        var drawOrder = _project.Pieces.Where(p => p != _selected).ToList();
        if (_selected != null && _project.Pieces.Contains(_selected)) drawOrder.Add(_selected);

        foreach (var p in drawOrder)
            RenderPiece(plot, p, p == _selected, OriginalShapeToggle.IsChecked == true);

        RenderJoints(plot);

        _hoverLine = plot.Add.VerticalLine(0);
        _hoverLine.LineColor = ScottPlot.Colors.Gray.WithAlpha(0.6f);
        _hoverLine.LineWidth = 1;
        _hoverLine.LinePattern = LinePattern.Dotted;
        _hoverLine.EnableAutoscale = false;
        _hoverLine.IsVisible = false;

        var axis = plot.Add.HorizontalLine(0);
        axis.LineColor = ScottPlot.Colors.Gray.WithAlpha(0.35f);
        axis.LineWidth = 0.8f;
        axis.EnableAutoscale = false;

        if (_project.Pieces.Count == 0)
            plot.Axes.SetLimits(0, 1000, -2, 2);
        else if (_fitPending)
        {
            plot.Axes.AutoScale();
            var l = plot.Axes.GetLimits();
            double h = l.Rect.Height;
            plot.Axes.SetLimitsY(l.Bottom - h * 0.15, l.Top + h * 0.25);
            _fitPending = false;
        }
        Chart.Refresh();
    }

    private static void RenderPiece(Plot plot, PrototypePiece p, bool selected, bool showOriginal)
    {
        ChartGeometry.TryParseHexColor(p.ColorHex, out var color);
        int step = Math.Max(1, p.Xs.Length / 1500);

        // Full original piece as a dashed outline, for reference (toolbar "Original shape"): shows what
        // was cut off — and can be dragged back — and, for a split part, the whole piece it came from.
        if (showOriginal) RenderGhost(plot, p, color);

        RenderKept(plot, p, color, step, selected);
    }

    private static void RenderGhost(Plot plot, PrototypePiece p, ScottColor color)
    {
        // Coarser than the kept part: on 1 cm scan noise a dash pattern breaks up into specks.
        int step = Math.Max(1, p.Xs.Length / 300);
        var ghostXs = new List<double>();
        var ghostYs = new List<double>();
        for (int i = 0; i < p.Xs.Length; i += step) { ghostXs.Add(p.ToAssemblyX(p.Xs[i])); ghostYs.Add(p.Ds[i] / 2); }
        ghostXs.Add(p.ToAssemblyX(p.Xs[^1])); ghostYs.Add(p.Ds[^1] / 2);
        var ghostTop = plot.Add.Scatter(ghostXs.ToArray(), ghostYs.ToArray());
        ghostTop.MarkerSize = 0; ghostTop.LineWidth = 1.2f; ghostTop.LinePattern = LinePattern.Dashed;
        ghostTop.Color = Ink(color).WithAlpha(0.6f);
        var ghostBot = plot.Add.Scatter(ghostXs.ToArray(), ghostYs.Select(y => -y).ToArray());
        ghostBot.MarkerSize = 0; ghostBot.LineWidth = 1.2f; ghostBot.LinePattern = LinePattern.Dashed;
        ghostBot.Color = Ink(color).WithAlpha(0.6f);
    }

    private static void RenderKept(Plot plot, PrototypePiece p, ScottColor color, int step, bool selected)
    {
        double s = p.VisibleStart, e = p.VisibleEnd;
        var xs = new List<double> { s };
        var srcXs = p.Xs.Select(p.ToAssemblyX).Where(x => x > s && x < e).OrderBy(x => x).ToList();
        for (int i = 0; i < srcXs.Count; i += step) xs.Add(srcXs[i]);
        xs.Add(e);
        double[] ax  = xs.ToArray();
        double[] top = ax.Select(x => p.DiameterAtSource(p.ToSourceX(x)) / 2).ToArray();
        double[] bot = top.Select(y => -y).ToArray();

        ChartGeometry.DrawLineFill(plot, ax, top, bot, color);
        var ink = Ink(color);   // lines and text: readable even for a white or yellow piece
        var outlineTop = plot.Add.Scatter(ax, top);
        outlineTop.MarkerSize = 0; outlineTop.LineWidth = selected ? 2.5f : 1.5f; outlineTop.Color = ink;
        var outlineBot = plot.Add.Scatter(ax, bot);
        outlineBot.MarkerSize = 0; outlineBot.LineWidth = selected ? 2.5f : 1.5f; outlineBot.Color = ink;

        // Trim handles: a bar a bit taller than the line at each kept end.
        foreach (double hx in new[] { s, e })
        {
            double r = p.DiameterAtSource(p.ToSourceX(hx)) / 2 * 1.35 + 0.05;
            var bar = plot.Add.Scatter(new[] { hx, hx }, new[] { -r, r });
            bar.MarkerSize = 0;
            bar.LineWidth  = selected ? 4 : 2.5f;
            bar.Color      = selected ? ScottPlot.Colors.Black : ink.WithAlpha(0.9f);
        }

        // Label: which piece, and which way round.
        double maxR = top.Length > 0 ? top.Max() : 0.5;
        var label = plot.Add.Text(p.DisplayName + (p.Flipped ? " (flipped)" : ""), (s + e) / 2, maxR * 1.35 + 0.1);
        label.LabelFontSize = 11;
        label.LabelBold = selected;
        label.LabelFontColor = ink;
        label.LabelBackgroundColor = ScottPlot.Colors.White.WithAlpha(0.75f);
        label.LabelAlignment = Alignment.LowerCenter;
    }

    /// <summary>The piece colour for lines and text, darkened when it's too light to see on the white chart.</summary>
    private static ScottColor Ink(ScottColor c)
    {
        double luma = (0.299 * c.Red + 0.587 * c.Green + 0.114 * c.Blue) / 255;
        if (luma < 0.75) return c;
        return new ScottColor((byte)(c.Red * 0.55), (byte)(c.Green * 0.55), (byte)(c.Blue * 0.55));
    }

    private void RenderJoints(Plot plot)
    {
        foreach (var j in _result.Joints)
        {
            var a = _result.Pieces[j.LeftIndex].Piece;
            var b = _result.Pieces[j.RightIndex].Piece;

            if (j.OverlapCm > PrototypeAssembler.TouchToleranceCm)
            {
                // Still overlapping: shade the shared span — this is where you compare and pick a cut.
                double x0 = b.VisibleStart, x1 = a.VisibleEnd;
                double r = Math.Max(a.Ds.Max(), b.Ds.Max()) / 2 * 1.2;
                var shade = plot.Add.Polygon(new Coordinates[] { new(x0, -r), new(x1, -r), new(x1, r), new(x0, r) });
                shade.FillColor = new ScottColor(245, 166, 35).WithAlpha(0.10f);
                shade.LineColor = new ScottColor(245, 166, 35).WithAlpha(0.6f);
                shade.LineWidth = 1;
                shade.LinePattern = LinePattern.Dashed;
                var t = plot.Add.Text(Inv($"overlap {j.OverlapCm:0} cm"), (x0 + x1) / 2, -r);
                t.LabelFontSize = 10; t.LabelFontColor = new ScottColor(190, 120, 10);
                t.LabelBackgroundColor = ScottPlot.Colors.White.WithAlpha(0.75f);
                t.LabelAlignment = Alignment.UpperCenter;
                continue;
            }

            double step = Math.Abs(j.StepMm);
            var col = step <= 0.03 ? new ScottColor(30, 150, 60)
                    : step <= 0.08 ? new ScottColor(215, 140, 0)
                    : new ScottColor(210, 40, 40);
            double rr = Math.Max(j.DLeftMm, j.DRightMm) / 2 * 1.35 + 0.05;
            var txt = plot.Add.Text(Inv($"Ø {j.DLeftMm:0.00}|{j.DRightMm:0.00}\nΔ {j.StepMm:+0.00;-0.00;0.00}") +
                                    (j.OverlapCm < -PrototypeAssembler.TouchToleranceCm ? Inv($"\ngap {-j.OverlapCm:0} cm") : ""),
                                    j.X, -rr);
            txt.LabelFontSize = 10; txt.LabelBold = true; txt.LabelFontColor = col;
            txt.LabelBackgroundColor = ScottPlot.Colors.White.WithAlpha(0.8f);
            txt.LabelBorderColor = col; txt.LabelBorderWidth = 1;
            txt.LabelAlignment = Alignment.UpperCenter;
        }
    }

    private void RefreshTable()
    {
        var rows = _result.Pieces.Select(r => new PieceRow(r)).ToList();
        // Pieces with nothing kept aren't in the result, but must stay editable in the table.
        rows.AddRange(_project.Pieces.Where(p => _result.Pieces.All(r => r.Piece != p))
                                     .Select(p => new PieceRow(p)));
        PiecesGrid.ItemsSource = rows;
        PiecesGrid.SelectedItem = rows.FirstOrDefault(r => r.Piece == _selected);
    }

    // ── Mouse ──────────────────────────────────────────────────────────────

    private Coordinates ToData(Point pos) => Chart.Plot.GetCoordinates(new Pixel((float)pos.X, (float)pos.Y));
    private double PxToCm(double px)
    {
        var a = Chart.Plot.GetCoordinates(new Pixel(0, 0));
        var b = Chart.Plot.GetCoordinates(new Pixel((float)px, 0));
        return Math.Abs(b.X - a.X);
    }

    /// <summary>Topmost piece under the mouse and which part of it: a trim handle or the body.</summary>
    private (PrototypePiece Piece, DragKind Kind)? HitPiece(Point pos)
    {
        var d = ToData(pos);
        double handleCm = PxToCm(HandleHitPx);
        double padCm    = Math.Abs(ToData(new Point(pos.X, pos.Y + BodyHitPadPx)).Y - d.Y);

        // Reverse draw order: selected first, then the rest from last drawn.
        var order = new List<PrototypePiece>();
        if (_selected != null && _project.Pieces.Contains(_selected)) order.Add(_selected);
        order.AddRange(_project.Pieces.Where(p => p != _selected).Reverse());

        foreach (var p in order)
        {
            foreach (var (x, kind) in new[] { (p.VisibleStart, DragKind.TrimLeft), (p.VisibleEnd, DragKind.TrimRight) })
            {
                double r = p.DiameterAtSource(p.ToSourceX(x)) / 2 * 1.35 + 0.05;
                if (Math.Abs(d.X - x) <= handleCm && Math.Abs(d.Y) <= r + padCm) return (p, kind);
            }
        }
        foreach (var p in order)
        {
            var dia = p.DiameterAt(d.X);
            if (dia.HasValue && Math.Abs(d.Y) <= dia.Value / 2 + padCm) return (p, DragKind.Move);
        }
        return null;
    }

    private void Chart_LeftDown(object sender, MouseButtonEventArgs e)
    {
        var pos = e.GetPosition(Chart);
        var hit = HitPiece(pos);
        if (hit == null)
        {
            if (_selected != null) { _selected = null; RenderChart(); RefreshTable(); }
            return;   // let ScottPlot pan
        }

        PushUndo();
        _selected        = hit.Value.Piece;
        _drag            = hit.Value.Kind;
        _dragPiece       = hit.Value.Piece;
        _dragStartMouseX = ToData(pos).X;
        _dragStartOffset = _dragPiece.OffsetCm;
        Chart.CaptureMouse();
        RenderChart();
        RefreshTable();
        e.Handled = true;
    }

    private void Chart_MouseMove(object sender, MouseEventArgs e)
    {
        var pos = e.GetPosition(Chart);
        var d = ToData(pos);
        _lastMouse = pos;

        if (_drag == DragKind.None || _dragPiece == null)
        {
            SetHover(d.X);
            var hit = HitPiece(pos);
            Chart.Cursor = hit?.Kind switch
            {
                DragKind.Move => Cursors.SizeWE,
                DragKind.TrimLeft or DragKind.TrimRight => Cursors.ScrollWE,
                _ => null,
            };
            return;
        }

        var p = _dragPiece;
        bool noSnap = Keyboard.Modifiers.HasFlag(ModifierKeys.Shift);
        switch (_drag)
        {
            case DragKind.Move:
                p.OffsetCm = Math.Round(_dragStartOffset + (d.X - _dragStartMouseX), 1);
                if (!noSnap) SnapMove(p);
                StatusText.Text = Inv($"{p.DisplayName}: {p.VisibleStart:0.#} → {p.VisibleEnd:0.#} cm   (Shift = no snap)");
                break;

            case DragKind.TrimLeft:
            {
                double x = Math.Round(Math.Clamp(d.X, p.OffsetCm, p.VisibleEnd - MinKeptCm));
                p.SetLeftTrim(Math.Max(0, x - p.OffsetCm));
                StatusText.Text = Inv($"{p.DisplayName}: cut {p.LeftTrimCm:0} cm at the {(p.Flipped ? "scan-end" : "scan-start")} end   Ø {p.DiameterAtSource(p.ToSourceX(p.VisibleStart)):0.00} mm");
                break;
            }
            case DragKind.TrimRight:
            {
                double x = Math.Round(Math.Clamp(d.X, p.VisibleStart + MinKeptCm, p.OffsetCm + p.LengthCm));
                p.SetRightTrim(Math.Max(0, p.OffsetCm + p.LengthCm - x));
                StatusText.Text = Inv($"{p.DisplayName}: cut {p.RightTrimCm:0} cm at the {(p.Flipped ? "scan-start" : "scan-end")} end   Ø {p.DiameterAtSource(p.ToSourceX(p.VisibleEnd)):0.00} mm");
                break;
            }
        }

        _result = PrototypeAssembler.Assemble(_project);
        RenderChart();
        e.Handled = true;
    }

    /// <summary>Butts the dragged piece against a neighbour's end when it comes within <see cref="SnapPx"/>.</summary>
    private void SnapMove(PrototypePiece p)
    {
        double tol = PxToCm(SnapPx);
        double best = double.MaxValue, shift = 0;
        foreach (var o in _project.Pieces.Where(o => o != p))
        {
            foreach (double delta in new[] { o.VisibleEnd - p.VisibleStart, o.VisibleStart - p.VisibleEnd })
                if (Math.Abs(delta) < tol && Math.Abs(delta) < best) { best = Math.Abs(delta); shift = delta; }
        }
        if (best < double.MaxValue) p.OffsetCm += shift;
    }

    private void Chart_LeftUp(object sender, MouseButtonEventArgs e)
    {
        if (_drag == DragKind.None) return;
        bool changed = _dragPiece != null &&
                       (_undo.Count == 0 || !SameState(_undo.Peek(), _project.Pieces));
        if (!changed && _undo.Count > 0) _undo.Pop();   // a click, not a drag: no undo step
        _drag = DragKind.None;
        _dragPiece = null;
        Chart.ReleaseMouseCapture();
        if (changed) MarkDirty();
        Recompute();
        e.Handled = true;
    }

    private void Chart_RightDown(object sender, MouseButtonEventArgs e)
    {
        var pos = e.GetPosition(Chart);
        var d = ToData(pos);
        var hit = HitPiece(pos);
        var under = _project.Pieces.Where(p => p.DiameterAt(d.X).HasValue).ToList();
        if (hit == null && under.Count < 2) return;   // ScottPlot's own menu

        var menu = new ContextMenu();
        double x = Math.Round(d.X);

        if (under.Count >= 2)
        {
            // Two pieces share this X: one click trims the left one's tail and the right one's head here.
            var left  = under.OrderBy(p => p.VisibleStart).First();
            var right = under.OrderBy(p => p.VisibleStart).Last();
            string dl = Inv($"{left.DiameterAt(x):0.00}"), dr = Inv($"{right.DiameterAt(x):0.00}");
            AddItem(menu, Inv($"✂ Cut both here ({x:0} cm):  {left.DisplayName} Ø {dl}  |  {right.DisplayName} Ø {dr}"), () => CutBoth(left, right, x));
            menu.Items.Add(new Separator());
        }

        if (hit != null)
        {
            var p = hit.Value.Piece;
            _selected = p;
            var dia = p.DiameterAt(x);
            if (dia.HasValue && x > p.VisibleStart + MinKeptCm && x < p.VisibleEnd - MinKeptCm)
            {
                AddItem(menu, Inv($"✂ Split {p.DisplayName} here into two parts (Ø {dia:0.00})  [S]"), () => SplitAt(p, x));
                AddItem(menu, Inv($"✂ Cut {p.DisplayName} here, keep the left part (Ø {dia:0.00})"),  () => CutKeep(p, x, keepLeft: true));
                AddItem(menu, Inv($"✂ Cut {p.DisplayName} here, keep the right part (Ø {dia:0.00})"), () => CutKeep(p, x, keepLeft: false));
                menu.Items.Add(new Separator());
            }
            menu.Items.Add(BuildColorMenu(p));
            AddItem(menu, "⇄ Flip 180°", () => FlipSelected());
            AddItem(menu, "Reset cuts", () => ResetCutsSelected());
            AddItem(menu, "Remove piece", () => RemoveSelected());
        }

        menu.PlacementTarget = Chart;
        menu.IsOpen = true;
        RenderChart();
        RefreshTable();
        e.Handled = true;
    }

    /// <summary>Swatches offered for a piece: the auto palette plus the usual fly-line colours.</summary>
    private static readonly (string Hex, string Name)[] ColorChoices =
    {
        ("3296FF", "Blue"),   ("DC3232", "Red"),    ("28A428", "Green"),  ("F0A020", "Amber"),
        ("9B59B6", "Purple"), ("17BECF", "Cyan"),   ("E377C2", "Pink"),   ("8C564B", "Brown"),
        ("FFD700", "Yellow"), ("FF6B35", "Orange"), ("F5F5F5", "White"),  ("AAAAAA", "Grey"),
        ("222222", "Black"),
    };

    /// <summary>"Color" submenu for one piece — each part of a split piece has its own colour.</summary>
    private MenuItem BuildColorMenu(PrototypePiece p)
    {
        var root = new MenuItem { Header = "🎨 Color" };
        foreach (var (hex, name) in ColorChoices)
        {
            var item = new MenuItem
            {
                Header = name,
                Icon = new System.Windows.Shapes.Rectangle
                {
                    Width = 14, Height = 14, Stroke = System.Windows.Media.Brushes.Gray, StrokeThickness = 0.5,
                    Fill = (System.Windows.Media.Brush)new HexToBrushConverter().Convert(hex, typeof(System.Windows.Media.Brush), null!, CultureInfo.InvariantCulture),
                },
                IsChecked = string.Equals(p.ColorHex, hex, StringComparison.OrdinalIgnoreCase),
            };
            item.Click += (_, _) => SetColor(p, hex);
            root.Items.Add(item);
        }
        root.Items.Add(new Separator());
        var custom = new MenuItem { Header = "Custom…" };
        custom.Click += (_, _) =>
        {
            string? hex = ShowColorDialog(p.ColorHex);
            if (hex != null) SetColor(p, hex);
        };
        root.Items.Add(custom);
        return root;
    }

    private void SetColor(PrototypePiece p, string hex)
    {
        if (string.Equals(p.ColorHex, hex, StringComparison.OrdinalIgnoreCase)) return;
        PushUndo();
        p.ColorHex = hex.ToUpperInvariant();
        MarkDirty();
        Recompute();
    }

    /// <summary>Full Windows colour dialog; returns 6-char hex or null if cancelled.</summary>
    private static string? ShowColorDialog(string currentHex)
    {
        var dlg = new System.Windows.Forms.ColorDialog { FullOpen = true, AnyColor = true };
        try
        {
            string h = currentHex.TrimStart('#');
            if (h.Length == 6)
                dlg.Color = System.Drawing.Color.FromArgb(
                    Convert.ToByte(h[0..2], 16), Convert.ToByte(h[2..4], 16), Convert.ToByte(h[4..6], 16));
        }
        catch { }
        return dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK
            ? $"{dlg.Color.R:X2}{dlg.Color.G:X2}{dlg.Color.B:X2}"
            : null;
    }

    /// <summary>Table swatch clicked: same colour menu as on the chart.</summary>
    private void Swatch_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement { DataContext: PieceRow row } fe) return;
        _selected = row.Piece;
        var menu = new ContextMenu { PlacementTarget = fe, Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom };
        foreach (var item in BuildColorMenu(row.Piece).Items.Cast<object>().ToList())
        {
            // Lift the swatches out of the "Color" submenu: here the whole menu is about colour.
            ((ItemsControl)((FrameworkElement)item).Parent).Items.Remove(item);
            menu.Items.Add(item);
        }
        menu.IsOpen = true;
        RenderChart();
    }

    private static void AddItem(ContextMenu menu, string header, Action action)
    {
        var item = new MenuItem { Header = header };
        item.Click += (_, _) => action();
        menu.Items.Add(item);
    }

    private void CutBoth(PrototypePiece left, PrototypePiece right, double x)
    {
        PushUndo();
        left.SetRightTrim(Math.Max(0, left.OffsetCm + left.LengthCm - x));
        right.SetLeftTrim(Math.Max(0, x - right.OffsetCm));
        MarkDirty();
        Recompute();
    }

    /// <summary>Splits a piece into two independent parts at x (see <see cref="PrototypeAssembler.Split"/>).</summary>
    private void SplitAt(PrototypePiece p, double x)
    {
        PushUndo();
        var part = PrototypeAssembler.Split(_project, p, Math.Round(x), MinKeptCm);
        if (part == null)
        {
            _undo.Pop();
            StatusText.Text = "Split point must be inside the kept part of the piece.";
            return;
        }
        _selected = part;
        MarkDirty();
        Recompute();
        StatusText.Text = Inv($"Split at {x:0} cm → {p.DisplayName} + {part.DisplayName}. Drag the parts apart to use them separately.");
    }

    /// <summary>Toolbar: split the selected piece into N equal parts (for "at this point", use the chart).</summary>
    private void SplitSelected_Click(object sender, RoutedEventArgs e)
    {
        if (!RequireSelection()) return;
        var p = _selected!;
        var menu = new ContextMenu { PlacementTarget = (UIElement)sender, Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom };
        foreach (int n in new[] { 2, 3, 4, 5 })
        {
            double len = (p.VisibleEnd - p.VisibleStart) / n;
            AddItem(menu, Inv($"{n} equal parts of {len:0} cm"), () => SplitEqual(p, n));
        }
        menu.IsOpen = true;
    }

    private void SplitEqual(PrototypePiece p, int n)
    {
        PushUndo();
        double start = p.VisibleStart, len = (p.VisibleEnd - start) / n;
        var current = p;
        for (int i = 1; i < n; i++)
            current = PrototypeAssembler.Split(_project, current, Math.Round(start + i * len, 1), MinKeptCm) ?? current;
        _selected = current;
        MarkDirty();
        Recompute();
        StatusText.Text = Inv($"{p.Name} split into {n} parts of {len:0} cm.");
    }

    /// <summary>Keyboard/toolbar split: the piece under the mouse (else the selected one), at the mouse X.</summary>
    private void SplitUnderMouse()
    {
        if (_lastMouse == null) { StatusText.Text = "Point at the split position on the chart, then press S."; return; }
        var d = ToData(_lastMouse.Value);
        var p = HitPiece(_lastMouse.Value)?.Piece
             ?? (_selected != null && _selected.DiameterAt(d.X).HasValue ? _selected : null);
        if (p == null) { StatusText.Text = "Point at a piece on the chart, then press S to split it there."; return; }
        SplitAt(p, d.X);
    }

    private void CutKeep(PrototypePiece p, double x, bool keepLeft)
    {
        PushUndo();
        if (keepLeft) p.SetRightTrim(Math.Max(0, p.OffsetCm + p.LengthCm - x));
        else          p.SetLeftTrim(Math.Max(0, x - p.OffsetCm));
        MarkDirty();
        Recompute();
    }

    /// <summary>Hover readout: the diameter of every piece under the cursor, and their difference.</summary>
    private void SetHover(double? x)
    {
        if (_hoverLine == null) return;
        if (x == null)
        {
            _hoverLine.IsVisible = false;
            Chart.Refresh();
            return;
        }
        _hoverLine.X = x.Value;
        _hoverLine.IsVisible = true;
        Chart.Refresh();

        var under = _project.Pieces.Select(p => (p, d: p.DiameterAt(x.Value))).Where(t => t.d.HasValue).ToList();
        string text = Inv($"x {x:0} cm");
        foreach (var (p, dia) in under)
            text += Inv($"   {p.DisplayName}: Ø {dia:0.00}");
        if (under.Count == 2)
            text += Inv($"   Δ {Math.Abs(under[0].d!.Value - under[1].d!.Value):0.00} mm");
        StatusText.Text = text;
    }

    // ── Piece commands ─────────────────────────────────────────────────────

    private void Flip_Click(object sender, RoutedEventArgs e) => FlipSelected();
    private void ResetCuts_Click(object sender, RoutedEventArgs e) => ResetCutsSelected();
    private void Remove_Click(object sender, RoutedEventArgs e) => RemoveSelected();

    private bool RequireSelection()
    {
        if (_selected != null && _project.Pieces.Contains(_selected)) return true;
        StatusText.Text = "Select a piece first (click it on the chart or in the table).";
        return false;
    }

    private void FlipSelected()
    {
        if (!RequireSelection()) return;
        PushUndo();
        _selected!.Flip();
        MarkDirty();
        Recompute();
    }

    private void ResetCutsSelected()
    {
        if (!RequireSelection()) return;
        PushUndo();
        var p = _selected!;
        double visStart = p.VisibleStart;
        p.TrimStartCm = 0;
        p.TrimEndCm = 0;
        p.OffsetCm = visStart;   // grow to the right from where it was, rather than jumping
        MarkDirty();
        Recompute();
    }

    private void RemoveSelected()
    {
        if (!RequireSelection()) return;
        PushUndo();
        _project.Pieces.Remove(_selected!);
        _selected = null;
        MarkDirty();
        Recompute();
    }

    private void CloseGaps_Click(object sender, RoutedEventArgs e)
    {
        if (_project.Pieces.Count == 0) return;
        PushUndo();
        double cursor = 0;
        foreach (var p in _project.Pieces.OrderBy(p => p.VisibleStart).ThenBy(p => p.VisibleEnd))
        {
            p.OffsetCm += cursor - p.VisibleStart;
            cursor = p.VisibleEnd;
        }
        _fitPending = true;
        MarkDirty();
        Recompute();
    }

    private void OriginalShape_Click(object sender, RoutedEventArgs e) => RenderChart();

    private void Fit_Click(object sender, RoutedEventArgs e) { _fitPending = true; RenderChart(); }

    private void Undo_Click(object sender, RoutedEventArgs e) => Undo();

    private void PushUndo()
    {
        _undo.Push(_project.Pieces.Select(Clone).ToList());
        if (_undo.Count > 100)
        {
            var keep = _undo.Take(100).Reverse().ToList();
            _undo.Clear();
            foreach (var s in keep) _undo.Push(s);
        }
    }

    private void Undo()
    {
        if (_undo.Count == 0) { StatusText.Text = "Nothing to undo."; return; }
        string? selId = _selected?.Id;
        _project.Pieces = _undo.Pop();
        _selected = _project.Pieces.FirstOrDefault(p => p.Id == selId);
        MarkDirty();
        Recompute();
    }

    private static PrototypePiece Clone(PrototypePiece p) => new()
    {
        Id = p.Id, Name = p.Name, PartNumber = p.PartNumber, SourcePath = p.SourcePath, ColorHex = p.ColorHex, DensityGCm3 = p.DensityGCm3,
        Xs = p.Xs, Ds = p.Ds,   // scan arrays are never mutated — share them
        Flipped = p.Flipped, TrimStartCm = p.TrimStartCm, TrimEndCm = p.TrimEndCm, OffsetCm = p.OffsetCm,
    };

    private static bool SameState(List<PrototypePiece> a, List<PrototypePiece> b) =>
        a.Count == b.Count && a.Zip(b).All(t =>
            t.First.Id == t.Second.Id && t.First.Flipped == t.Second.Flipped &&
            t.First.TrimStartCm == t.Second.TrimStartCm && t.First.TrimEndCm == t.Second.TrimEndCm &&
            t.First.OffsetCm == t.Second.OffsetCm && t.First.DensityGCm3 == t.Second.DensityGCm3);

    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.OriginalSource is TextBox) return;
        if (e.Key == Key.Z && Keyboard.Modifiers == ModifierKeys.Control) { Undo(); e.Handled = true; }
        else if (e.Key == Key.Delete) { RemoveSelected(); e.Handled = true; }
        else if (e.Key == Key.F && Keyboard.Modifiers == ModifierKeys.None) { FlipSelected(); e.Handled = true; }
        else if (e.Key == Key.S && Keyboard.Modifiers == ModifierKeys.None) { SplitUnderMouse(); e.Handled = true; }
    }

    // ── Table ──────────────────────────────────────────────────────────────

    private void PiecesGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (PiecesGrid.SelectedItem is not PieceRow row || row.Piece == _selected) return;
        _selected = row.Piece;
        RenderChart();
    }

    private void PiecesGrid_CellEditEnding(object sender, DataGridCellEditEndingEventArgs e)
    {
        if (e.EditAction != DataGridEditAction.Commit) return;
        if (e.Row.Item is not PieceRow row || e.EditingElement is not TextBox tb) return;

        // Read the typed text directly: the binding hasn't pushed it into the row yet at this point.
        const NumberStyles styles = NumberStyles.Float;
        if (!double.TryParse(tb.Text, styles, CultureInfo.CurrentCulture, out double v) &&
            !double.TryParse(tb.Text, styles, CultureInfo.InvariantCulture, out v)) return;

        var p = row.Piece;
        string header = e.Column.Header?.ToString() ?? string.Empty;
        PushUndo();
        switch (header)
        {
            case "Trim scan-start":
                p.TrimStartCm = Math.Clamp(v, 0, Math.Max(0, p.LengthCm - p.TrimEndCm - MinKeptCm));
                break;
            case "Trim scan-end":
                p.TrimEndCm = Math.Clamp(v, 0, Math.Max(0, p.LengthCm - p.TrimStartCm - MinKeptCm));
                break;
            case "ρ g/cm³":
                p.DensityGCm3 = Math.Max(0, v);
                break;
            default:
                _undo.Pop();
                return;
        }
        MarkDirty();
        // Rebuilding ItemsSource inside CellEditEnding throws — do it once the edit has closed.
        Dispatcher.InvokeAsync(Recompute);
    }

    // ── File ───────────────────────────────────────────────────────────────

    private void NameBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (_suppressNameChange) return;
        _project.Name = NameBox.Text.Trim().Length > 0 ? NameBox.Text.Trim() : "Prototype";
        MarkDirty();
    }

    private void ShowAllowance() =>
        AllowanceBox.Text = _project.JointAllowanceCm.ToString("0.#", CultureInfo.CurrentCulture);

    private void AllowanceBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) { AllowanceBox_Commit(sender, e); e.Handled = true; }
    }

    private void AllowanceBox_Commit(object sender, RoutedEventArgs e)
    {
        const NumberStyles styles = NumberStyles.Float;
        if ((double.TryParse(AllowanceBox.Text, styles, CultureInfo.CurrentCulture, out double v) ||
             double.TryParse(AllowanceBox.Text, styles, CultureInfo.InvariantCulture, out v)) && v >= 0 && v <= 100)
        {
            if (Math.Abs(v - _project.JointAllowanceCm) > 1e-9)
            {
                _project.JointAllowanceCm = v;
                MarkDirty();
                Recompute();
            }
        }
        ShowAllowance();
    }

    private void SetName(string name)
    {
        _suppressNameChange = true;
        NameBox.Text = name;
        _suppressNameChange = false;
    }

    private void MarkDirty()
    {
        _dirty = true;
        UpdateTitle();
    }

    private void UpdateTitle() =>
        Title = $"Prototype — {(_path != null ? Path.GetFileName(_path) : _project.Name)}{(_dirty ? " *" : "")}";

    private bool ConfirmDiscard()
    {
        if (!_dirty || _project.Pieces.Count == 0) return true;
        var r = MessageBox.Show(this, "Save changes to this prototype?", "Prototype",
                                MessageBoxButton.YesNoCancel, MessageBoxImage.Question);
        if (r == MessageBoxResult.Cancel) return false;
        if (r == MessageBoxResult.Yes) return SaveTo(_path ?? AskSavePath());
        return true;
    }

    private void Window_Closing(object? sender, CancelEventArgs e)
    {
        if (!ConfirmDiscard()) e.Cancel = true;
    }

    private void New_Click(object sender, RoutedEventArgs e)
    {
        if (!ConfirmDiscard()) return;
        _project = new PrototypeProject();
        _path = null;
        _selected = null;
        _undo.Clear();
        _dirty = false;
        SetName(_project.Name);
        ShowAllowance();
        UpdateTitle();
        Recompute();
    }

    private void Open_Click(object sender, RoutedEventArgs e)
    {
        if (!ConfirmDiscard()) return;
        Directory.CreateDirectory(PrototypeAssembler.DefaultFolder);
        var dlg = new OpenFileDialog
        {
            Filter = PrototypeAssembler.FileFilter,
            InitialDirectory = _path != null ? Path.GetDirectoryName(_path) : PrototypeAssembler.DefaultFolder,
        };
        if (dlg.ShowDialog(this) != true) return;
        try
        {
            _project = PrototypeAssembler.Load(dlg.FileName);
            _path = dlg.FileName;
            _selected = null;
            _undo.Clear();
            _dirty = false;
            _fitPending = true;
            SetName(_project.Name);
            ShowAllowance();
            UpdateTitle();
            Recompute();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Could not open the prototype:\n{ex.Message}", "Prototype", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void Save_Click(object sender, RoutedEventArgs e) => SaveTo(_path ?? AskSavePath());
    private void SaveAs_Click(object sender, RoutedEventArgs e) => SaveTo(AskSavePath());

    private string? AskSavePath()
    {
        Directory.CreateDirectory(PrototypeAssembler.DefaultFolder);
        var dlg = new SaveFileDialog
        {
            Filter = PrototypeAssembler.FileFilter,
            InitialDirectory = _path != null ? Path.GetDirectoryName(_path) : PrototypeAssembler.DefaultFolder,
            FileName = Sanitize(_project.Name) + PrototypeAssembler.FileExtension,
        };
        return dlg.ShowDialog(this) == true ? dlg.FileName : null;
    }

    private bool SaveTo(string? path)
    {
        if (path == null) return false;
        try
        {
            PrototypeAssembler.Save(_project, path);
            _path = path;
            _dirty = false;
            UpdateTitle();
            StatusText.Text = $"Saved {path}";
            return true;
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Could not save:\n{ex.Message}", "Prototype", MessageBoxButton.OK, MessageBoxImage.Error);
            return false;
        }
    }

    private void CopyCutList_Click(object sender, RoutedEventArgs e)
    {
        if (_result.Pieces.Count == 0) return;
        Clipboard.SetText(PrototypeAssembler.CutList(_result, _project.JointAllowanceCm));
        StatusText.Text = "Cut list copied to the clipboard.";
    }

    private string? ExportFlp()
    {
        if (_result.Pieces.Count == 0)
        {
            StatusText.Text = "Nothing to export — add pieces first.";
            return null;
        }
        if (_result.Joints.Any(j => j.OverlapCm > PrototypeAssembler.TouchToleranceCm))
        {
            var r = MessageBox.Show(this,
                "Some pieces still overlap on the chart. The finished line joins every piece end to end " +
                "exactly as trimmed, so the overlapping parts will be in the line twice.\n\nExport anyway?",
                "Prototype", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (r != MessageBoxResult.Yes) return null;
        }

        var dlg = new SaveFileDialog
        {
            Filter = ProjectService.FileFilter,
            InitialDirectory = ProjectService.DefaultProjectFolder,
            FileName = Sanitize(_project.Name) + ProjectService.FileExtension,
        };
        if (dlg.ShowDialog(this) != true) return null;

        ProjectService.Save(PrototypeAssembler.ToFlyLineProject(_project, _result), dlg.FileName);
        StatusText.Text = $"Exported {dlg.FileName}";
        return dlg.FileName;
    }

    private void ExportFlp_Click(object sender, RoutedEventArgs e) => ExportFlp();

    private void OpenInProfiler_Click(object sender, RoutedEventArgs e)
    {
        string? path = ExportFlp();
        if (path != null) _openInProfiler(path);
    }

    private static string Sanitize(string name)
    {
        foreach (char c in Path.GetInvalidFileNameChars()) name = name.Replace(c, '_');
        return name.Trim().Length > 0 ? name.Trim() : "Prototype";
    }

    private static string Inv(FormattableString s) => s.ToString(CultureInfo.InvariantCulture);

    /// <summary>One row of the pieces table (public: WPF bindings can't reach a private type's properties).</summary>
    public sealed class PieceRow
    {
        public PrototypePiece Piece { get; }
        public int     Number    { get; }
        public double  KeptCm    { get; }
        public double  CutLengthCm { get; }
        public double  DLeft     { get; }
        public double  DRight    { get; }
        public string  MassText  { get; }

        public PieceRow(PrototypePieceResult r)
        {
            Piece = r.Piece; Number = r.Number; KeptCm = r.KeptCm; CutLengthCm = r.CutLengthCm; DLeft = r.DLeftMm; DRight = r.DRightMm;
            MassText = r.MassG.HasValue ? r.MassG.Value.ToString("0.00", CultureInfo.InvariantCulture) : "—";
        }

        public PieceRow(PrototypePiece p)
        {
            Piece = p; Number = 0; KeptCm = 0; MassText = "—";
        }

        public string ColorHex  => Piece.ColorHex;
        public string Name      => Piece.DisplayName;
        public string Direction => Piece.Flipped ? "← flipped" : "→";
        public double FullCm    => Piece.LengthCm;
        // Setters exist only so the columns are editable; the edit is applied in CellEditEnding.
        public double CutStart  { get => Piece.TrimStartCm; set { } }
        public double CutEnd    { get => Piece.TrimEndCm;   set { } }
        public double Density   { get => Piece.DensityGCm3; set { } }
    }
}
