using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using DiametroLineaDesktop.Models;
using MessageBox = System.Windows.MessageBox;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// Right-click menu of the Zones table. On a zone: change nozzle, edit start/end, extend to a
/// neighbour or a line end, split, merge with the next zone, show on chart, remove. On an M1 row
/// (base material between zones): make it a zone, show on chart. A C file is locked: only "show".
/// </summary>
public partial class MainWindow
{
    private void NozzleZonesGrid_ContextMenuOpening(object sender, ContextMenuEventArgs e)
    {
        // The row under the mouse becomes the selection — the menu acts on what was right-clicked.
        DependencyObject? d = e.OriginalSource as DependencyObject;
        while (d != null && d is not DataGridRow) d = VisualTreeHelper.GetParent(d);
        if (d is not DataGridRow { Item: NozzleZoneVm zone } row) { e.Handled = true; return; }
        NozzleZonesGrid.SelectedItem = zone;
        row.Focus();

        var menu = NozzleZonesGrid.ContextMenu!;
        menu.Items.Clear();
        bool locked = _isCompensatedDerivative;

        MenuItem Item(string header, Action act, bool enabled = true)
        {
            var mi = new MenuItem { Header = header, IsEnabled = enabled && !locked };
            mi.Click += (_, _) => act();
            return mi;
        }
        MenuItem NozzleMenu(string header, Action<int> pick, int skip)
        {
            var parent = new MenuItem { Header = header, IsEnabled = !locked };
            for (int i = 0; i < Nozzles.Count && i < 4; i++)
            {
                int idx = i;
                var n = Nozzles[i];
                if (idx == skip) continue;
                var swatch = new System.Windows.Shapes.Rectangle
                {
                    Width = 14, Height = 10, Stroke = Brushes.Gray, StrokeThickness = 0.5,
                    Fill = new SolidColorBrush(ParseWpfColor(n.ColorHex)),
                };
                var mi = new MenuItem
                {
                    Header = n.DensityGCm3 > 0 ? $"{n.DisplayName}  ·  ρ {n.DensityGCm3:0.00}" : $"{n.DisplayName}  ·  (no density)",
                    Icon = swatch,
                };
                mi.Click += (_, _) => pick(idx);
                parent.Items.Add(mi);
            }
            return parent;
        }

        if (zone.IsImplicit)
        {
            menu.Items.Add(NozzleMenu("Make zone", idx => MakeZoneFromM1(zone, idx), skip: 0));
            menu.Items.Add(new Separator());
            menu.Items.Add(new MenuItem { Header = "Show on chart" }.With(mi => mi.Click += (_, _) => ShowZoneOnChart(zone)));
            return;
        }

        var (prev, next) = ZoneNeighbours(zone);
        var (lineStart, lineEnd) = LineSpan();

        menu.Items.Add(NozzleMenu("Change nozzle", idx => ChangeZoneNozzle(zone, idx), skip: zone.NozzleIndex));
        menu.Items.Add(Item("Edit start", () => BeginZoneCellEdit(zone, "Start (cm)")));
        menu.Items.Add(Item("Edit end",   () => BeginZoneCellEdit(zone, "End (cm)")));
        menu.Items.Add(new Separator());

        var extend = new MenuItem { Header = "Extend", IsEnabled = !locked };
        double prevEnd   = prev?.EndCm   ?? lineStart;
        double nextStart = next?.StartCm ?? lineEnd;
        extend.Items.Add(Item(prev != null ? $"To previous zone ({prevEnd:0.0} cm)" : $"To line start ({prevEnd:0.0} cm)",
                              () => ApplyZoneEdit(() => zone.StartCm = prevEnd), zone.StartCm - prevEnd > 0.05));
        extend.Items.Add(Item(next != null ? $"To next zone ({nextStart:0.0} cm)" : $"To line end ({nextStart:0.0} cm)",
                              () => ApplyZoneEdit(() => zone.EndCm = nextStart), nextStart - zone.EndCm > 0.05));
        if (prev != null)
            extend.Items.Add(Item($"To line start ({lineStart:0.0} cm) — over the zones before",
                                  () => ExtendOverZones(zone, lineStart, zone.EndCm)));
        if (next != null)
            extend.Items.Add(Item($"To line end ({lineEnd:0.0} cm) — over the zones after",
                                  () => ExtendOverZones(zone, zone.StartCm, lineEnd)));
        menu.Items.Add(extend);

        menu.Items.Add(Item("Split at…", () => SplitZone(zone), zone.EndCm - zone.StartCm > 0.2));
        bool canMerge = next != null && next.NozzleIndex == zone.NozzleIndex && Math.Abs(next.StartCm - zone.EndCm) < 0.05;
        menu.Items.Add(Item(canMerge ? $"Merge with next ({next!.StartCm:0.0}–{next.EndCm:0.0} cm)" : "Merge with next (same nozzle, touching)",
                            () => MergeWithNext(zone, next!), canMerge));
        menu.Items.Add(new Separator());
        menu.Items.Add(new MenuItem { Header = "Show on chart" }.With(mi => mi.Click += (_, _) => ShowZoneOnChart(zone)));
        menu.Items.Add(new Separator());
        menu.Items.Add(Item("Remove zone", RemoveSelectedZone));
    }

    private (NozzleZoneVm? Prev, NozzleZoneVm? Next) ZoneNeighbours(NozzleZoneVm zone)
    {
        var others = NozzleZones.Where(z => !ReferenceEquals(z, zone)).ToList();
        var prev = others.Where(z => z.EndCm <= zone.StartCm + 0.05).OrderByDescending(z => z.EndCm).FirstOrDefault();
        var next = others.Where(z => z.StartCm >= zone.EndCm - 0.05).OrderBy(z => z.StartCm).FirstOrDefault();
        return (prev, next);
    }

    private (double Start, double End) LineSpan() => _segmentNodes.Count > 0
        ? (_segmentNodes.Min(n => n.X), _segmentNodes.Max(n => n.X))
        : (0, NozzleZones.Count > 0 ? NozzleZones.Max(z => z.EndCm) : 0);

    /// <summary>Every zone change ends the same way as a typed edit in the table.</summary>
    private void ApplyZoneEdit(Action change, bool forcePrompt = false)
    {
        change();
        UpdateNozzleBadge();
        RefreshPlot();
        MarkDirty();
        MaybeApplyZoneDensityChange(forcePrompt);
        WarnIfZonesOverlap();
        QueueZoneSequence();
    }

    /// <summary>A new material where there was another: ask about the diameters, as Add Zone does.</summary>
    private bool DensityChanges(double fromRho, int toIdx) =>
        toIdx < Nozzles.Count && Nozzles[toIdx].DensityGCm3 > 0
        && Math.Abs(Nozzles[toIdx].DensityGCm3 - fromRho) > DensityMergeThreshold;

    private void ChangeZoneNozzle(NozzleZoneVm zone, int idx)
    {
        bool prompt = DensityChanges(zone.DensityGCm3, idx);
        ApplyZoneEdit(() => zone.NozzleIndex = idx, prompt);
        UiStatus = $"Zone {zone.StartCm:0.0}–{zone.EndCm:0.0} cm now uses {zone.NozzleLabel}";
    }

    private void MakeZoneFromM1(NozzleZoneVm m1Row, int idx)
    {
        var z = new NozzleZoneVm(Nozzles) { StartCm = m1Row.StartCm, EndCm = m1Row.EndCm, NozzleIndex = idx };
        bool prompt = DensityChanges(Nozzles[0].DensityGCm3, idx);
        ApplyZoneEdit(() => NozzleZones.Add(z), prompt);
        NozzleZonesGrid.SelectedItem = z;
        UiStatus = $"Zone {z.NozzleLabel} {z.StartCm:0.0}–{z.EndCm:0.0} cm created";
    }

    /// <summary>Extends a zone over its neighbours up to a line end: the zones it now covers
    /// entirely are removed, one it only partly covers is shortened — never an overlap.</summary>
    private void ExtendOverZones(NozzleZoneVm zone, double newStart, double newEnd)
    {
        var covered = NozzleZones.Where(z => !ReferenceEquals(z, zone) && z.StartCm >= newStart - 0.05 && z.EndCm <= newEnd + 0.05).ToList();
        string list = string.Join("\n", covered.Select(z => $"  • {z.NozzleLabel} {z.StartCm:0.0}–{z.EndCm:0.0} cm"));
        if (covered.Count > 0 && MessageBox.Show(
                $"Extending {zone.NozzleLabel} to {newStart:0.0}–{newEnd:0.0} cm covers these zones, which will be removed:\n{list}\n\nContinue?",
                "Extend zone", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes)
            return;
        ApplyZoneEdit(() =>
        {
            foreach (var z in covered) NozzleZones.Remove(z);
            foreach (var z in NozzleZones.Where(z => !ReferenceEquals(z, zone)))
            {
                if (z.StartCm < newStart && z.EndCm > newStart) z.EndCm = newStart;
                if (z.StartCm < newEnd && z.EndCm > newEnd) z.StartCm = newEnd;
            }
            zone.StartCm = newStart; zone.EndCm = newEnd;
        });
    }

    private void SplitZone(NozzleZoneVm zone)
    {
        double mid = Math.Round((zone.StartCm + zone.EndCm) / 2.0, 1);
        double? at = AskNumber("Split zone",
            $"Split {zone.NozzleLabel} {zone.StartCm:0.0}–{zone.EndCm:0.0} cm at (cm):", mid);
        if (at is not double x) return;
        x = Math.Round(x, 1);
        if (x <= zone.StartCm + 0.05 || x >= zone.EndCm - 0.05)
        {
            MessageBox.Show($"The split point must lie inside the zone ({zone.StartCm:0.0}–{zone.EndCm:0.0} cm).",
                            "Split zone", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        var second = new NozzleZoneVm(Nozzles) { StartCm = x, EndCm = zone.EndCm, NozzleIndex = zone.NozzleIndex };
        ApplyZoneEdit(() => { zone.EndCm = x; NozzleZones.Add(second); });
        NozzleZonesGrid.SelectedItem = second;
        UiStatus = $"Zone split at {x:0.0} cm — right-click the second part to give it another nozzle";
    }

    private void MergeWithNext(NozzleZoneVm zone, NozzleZoneVm next)
    {
        ApplyZoneEdit(() => { zone.EndCm = next.EndCm; NozzleZones.Remove(next); });
        UiStatus = $"Zones merged: {zone.NozzleLabel} {zone.StartCm:0.0}–{zone.EndCm:0.0} cm";
    }

    private void BeginZoneCellEdit(NozzleZoneVm zone, string header)
    {
        var col = NozzleZonesGrid.Columns.FirstOrDefault(c => c.Header?.ToString() == header);
        if (col == null) return;
        NozzleZonesGrid.SelectedItem = zone;
        NozzleZonesGrid.ScrollIntoView(zone, col);
        NozzleZonesGrid.CurrentCell = new DataGridCellInfo(zone, col);
        NozzleZonesGrid.Focus();
        NozzleZonesGrid.BeginEdit();
    }

    private void ShowZoneOnChart(NozzleZoneVm zone)
    {
        double len = Math.Max(zone.EndCm - zone.StartCm, 1.0);
        double pad = Math.Max(len * 0.15, 10.0);
        var lim = PlotControl.Plot.Axes.GetLimits();
        PlotControl.Plot.Axes.SetLimits(zone.StartCm - pad, zone.EndCm + pad, lim.Bottom, lim.Top);
        PlotControl.Refresh();
        UiStatus = $"Chart: {zone.NozzleLabel} {zone.StartCm:0.0}–{zone.EndCm:0.0} cm";
    }

    private static System.Windows.Media.Color ParseWpfColor(string hex)
    {
        try { return (System.Windows.Media.Color)ColorConverter.ConvertFromString("#" + hex.TrimStart('#')); }
        catch { return Colors.Gray; }
    }

    /// <summary>A one-number prompt (cm), invariant or local decimal separator.</summary>
    private double? AskNumber(string title, string label, double initial)
    {
        var win = new Window
        {
            Title = title, SizeToContent = SizeToContent.WidthAndHeight, ResizeMode = ResizeMode.NoResize,
            WindowStartupLocation = WindowStartupLocation.CenterOwner, Owner = Window.GetWindow(this),
            Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(0x1A, 0x1E, 0x2A)),
        };
        var panel = new StackPanel { Margin = new Thickness(16) };
        panel.Children.Add(new TextBlock { Text = label, Foreground = Brushes.Gainsboro, Margin = new Thickness(0, 0, 0, 6) });
        var box = new TextBox { Text = initial.ToString("0.0"), Width = 120, HorizontalAlignment = HorizontalAlignment.Left };
        panel.Children.Add(box);
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 12, 0, 0) };
        var ok = new Button { Content = "OK", Width = 70, IsDefault = true, Margin = new Thickness(0, 0, 6, 0) };
        var cancel = new Button { Content = "Cancel", Width = 70, IsCancel = true };
        ok.Click += (_, _) => win.DialogResult = true;
        buttons.Children.Add(ok); buttons.Children.Add(cancel);
        panel.Children.Add(buttons);
        win.Content = panel;
        win.Loaded += (_, _) => { box.Focus(); box.SelectAll(); };
        if (win.ShowDialog() != true) return null;
        return TryParseDouble(box.Text, out double v) ? v : null;
    }
}

internal static class FrameworkElementWithExtensions
{
    /// <summary>Configure an element inline: <c>new MenuItem { … }.With(mi => …)</c>.</summary>
    public static T With<T>(this T item, Action<T> configure) { configure(item); return item; }
}
