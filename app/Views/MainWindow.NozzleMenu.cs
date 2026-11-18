using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using DiametroLineaDesktop.Models;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// Removing a nozzle the line doesn't use. M1 (the base material) and any nozzle a zone uses stay.
/// The slots are fixed (M1–M4), so a hole is closed: the nozzles above move down one place and
/// their zones follow — M3 becomes M2, never an empty M2 between M1 and M3.
/// </summary>
public partial class MainWindow
{
    /// <summary>Why this nozzle can't be removed, or null when it can.</summary>
    private string? WhyNozzleNotRemovable(int index)
    {
        if (_isCompensatedDerivative) return "a C file is locked";
        if (index <= 0) return "M1 is the base material of the line";
        if (index >= Nozzles.Count) return "no such nozzle";
        int zones = NozzleZones.Count(z => z.NozzleIndex == index);
        if (zones > 0) return $"{zones} zone{(zones > 1 ? "s use" : " uses")} it — remove or change {(zones > 1 ? "them" : "it")} first";
        return null;
    }

    private void RemoveNozzleMaterial_Click(object sender, RoutedEventArgs e)
    {
        if (NozzleDefsGrid.SelectedItem is not NozzleDefinitionVm n)
        {
            UiStatus = "Select a nozzle row first";
            return;
        }
        RemoveNozzle(n.Number - 1);
    }

    private void RemoveNozzle(int index)
    {
        string name = $"M{index + 1}";
        if (WhyNozzleNotRemovable(index) is { } why) { UiStatus = $"{name} can't be removed: {why}"; return; }

        // Close the hole: every slot above moves down one place, the last one is emptied.
        for (int i = index; i < Nozzles.Count - 1; i++)
        {
            Nozzles[i].ColorHex    = Nozzles[i + 1].ColorHex;
            Nozzles[i].DensityGCm3 = Nozzles[i + 1].DensityGCm3;
            Nozzles[i].Label       = Nozzles[i + 1].Label;
        }
        var last = Nozzles[^1];
        last.DensityGCm3 = 0;
        last.Label       = string.Empty;
        foreach (var z in NozzleZones.Where(z => z.NozzleIndex > index))
            z.NozzleIndex--;

        if (_activeNozzleIndex == index) SetActiveNozzle(0);
        else if (_activeNozzleIndex > index) SetActiveNozzle(_activeNozzleIndex - 1);

        UpdateNozzleUsageLabels();
        UpdateNozzleBadge();
        NozzleDefsGrid.Items.Refresh();
        QueueZoneSequence();
        RefreshPlot();
        MarkDirty();
        UiStatus = index < Nozzles.Count - 1 && Nozzles[index].DensityGCm3 > 0
            ? $"{name} removed — the nozzles above moved down one place (zones renumbered)"
            : $"{name} removed";
    }

    private void NozzleDefsGrid_ContextMenuOpening(object sender, ContextMenuEventArgs e)
    {
        DependencyObject? d = e.OriginalSource as DependencyObject;
        while (d != null && d is not DataGridRow) d = VisualTreeHelper.GetParent(d);
        if (d is not DataGridRow { Item: NozzleDefinitionVm n }) { e.Handled = true; return; }
        NozzleDefsGrid.SelectedItem = n;

        int idx = n.Number - 1;
        var menu = NozzleDefsGrid.ContextMenu!;
        menu.Items.Clear();

        var use = new MenuItem { Header = $"Use {n.DisplayName} for new zones", IsEnabled = !_isCompensatedDerivative };
        use.Click += (_, _) => SetActiveNozzle(idx);
        menu.Items.Add(use);
        menu.Items.Add(new Separator());

        string? why = WhyNozzleNotRemovable(idx);
        var remove = new MenuItem
        {
            Header    = why == null ? $"Remove {n.DisplayName}" : $"Remove {n.DisplayName} — {why}",
            IsEnabled = why == null,
        };
        remove.Click += (_, _) => RemoveNozzle(idx);
        menu.Items.Add(remove);
    }
}
