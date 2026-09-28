using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using DiametroLineaDesktop.Services;

namespace DiametroLineaDesktop.Views;

public partial class GenerateDensityFamilyDialog : Window
{
    private readonly List<double> _densities = new();          // g/cm³
    private readonly IReadOnlyList<double> _nozzleDensities;   // the project's own M1–M4

    public List<double> SelectedDensities { get; private set; } = new();

    /// <summary>True when the variants should rescale to hold the source's line-weight class.</summary>
    public bool KeepClassMass { get; private set; } = true;

    public GenerateDensityFamilyDialog(IEnumerable<double>? nozzleDensities = null)
    {
        InitializeComponent();
        _nozzleDensities = (nozzleDensities ?? Enumerable.Empty<double>())
            .Where(d => d > 0)
            .Distinct()
            .OrderBy(d => d)
            .ToList();
        AddNozzlesBtn.IsEnabled = _nozzleDensities.Count > 0;
        UpdateDensityLabel();
    }

    private void DensitySlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        => UpdateDensityLabel();

    private void UpdateDensityLabel()
    {
        if (DensityValueLabel == null) return; // ValueChanged can fire mid-InitializeComponent
        double v = DensitySlider.Value;
        DensityValueLabel.Text = $"{v:0.00} g/cm³";

        // Below water it cannot sink at any diameter, which is worth saying before the variant is
        // generated rather than as a note afterwards.
        HintLabel.Text = v <= 1.00
            ? "lighter than water — this variant will float"
            : string.Empty;
    }

    private void AddBtn_Click(object sender, RoutedEventArgs e)
        => Add(Math.Round(DensitySlider.Value, 2));

    private void AddNozzlesBtn_Click(object sender, RoutedEventArgs e)
    {
        foreach (double d in _nozzleDensities) Add(Math.Round(d, 2));
    }

    private void Add(double v)
    {
        if (v <= 0 || _densities.Contains(v)) return;
        _densities.Add(v);
        _densities.Sort();
        RefreshList();
    }

    private void RemoveBtn_Click(object sender, RoutedEventArgs e)
    {
        if (DensitiesListBox.SelectedIndex < 0) return;
        _densities.RemoveAt(DensitiesListBox.SelectedIndex);
        RefreshList();
    }

    private void RefreshList()
    {
        DensitiesListBox.ItemsSource = _densities
            .Select(v => v <= 1.00
                ? $"{v:0.00} g/cm³   (floating)"
                : v <= SinkingSpeedCalc.RhoFloor + 1e-9
                    ? $"{v:0.00} g/cm³   (practical minimum)"
                    : $"{v:0.00} g/cm³")
            .ToList();
    }

    private void OkBtn_Click(object sender, RoutedEventArgs e)
    {
        SelectedDensities = new List<double>(_densities);
        KeepClassMass     = KeepClassRadio.IsChecked == true;
        DialogResult      = true;
    }

    private void CancelBtn_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
