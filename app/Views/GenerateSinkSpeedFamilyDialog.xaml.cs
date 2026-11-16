using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Windows;

namespace DiametroLineaDesktop.Views;

public partial class GenerateSinkSpeedFamilyDialog : Window
{
    private readonly List<double> _speeds = new(); // in/s; 0 = floating

    public List<double> SelectedSpeedsIns { get; private set; } = new();

    public GenerateSinkSpeedFamilyDialog()
    {
        InitializeComponent();
        UpdateSpeedLabel();
    }

    // The speed that will be added: the slider's value (0.05 steps) or the exact one typed in the box.
    private double _value = 1.5;
    private bool _fromBox;

    private void SpeedSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (_fromBox) return;          // the box set the slider: keep the typed value, not the snapped one
        _value = Math.Round(SpeedSlider.Value, 2);
        UpdateSpeedLabel();
    }

    private void UpdateSpeedLabel()
    {
        if (SpeedValueLabel == null || SpeedBox == null) return; // ValueChanged can fire mid-InitializeComponent, before these fields are assigned
        bool floating = _value < 0.05;
        SpeedBox.Text = floating ? "0" : _value.ToString("0.00", CultureInfo.InvariantCulture);
        SpeedValueLabel.Text = floating ? "in/s  (Floating)" : "in/s";
    }

    /// <summary>Reads the typed speed (dot or comma, 0 = Floating), clamped to the slider's range.</summary>
    private void CommitSpeedBox()
    {
        string t = SpeedBox.Text.Trim().Replace(',', '.');
        if (double.TryParse(t, NumberStyles.Float, CultureInfo.InvariantCulture, out double v))
        {
            _value = Math.Round(Math.Clamp(v, SpeedSlider.Minimum, SpeedSlider.Maximum), 2);
            _fromBox = true;
            SpeedSlider.Value = _value;
            _fromBox = false;
        }
        UpdateSpeedLabel();   // a bad entry falls back to the last good value
    }

    private void SpeedBox_LostKeyboardFocus(object sender, System.Windows.Input.KeyboardFocusChangedEventArgs e)
        => CommitSpeedBox();

    private void AddBtn_Click(object sender, RoutedEventArgs e)
    {
        CommitSpeedBox();   // Enter in the box presses Add (default button) before the box loses focus
        double v = _value < 0.05 ? 0.0 : _value;
        if (_speeds.Contains(v)) return;
        _speeds.Add(v);
        _speeds.Sort();
        RefreshList();
    }

    private void RemoveBtn_Click(object sender, RoutedEventArgs e)
    {
        if (SpeedsListBox.SelectedIndex < 0) return;
        _speeds.RemoveAt(SpeedsListBox.SelectedIndex);
        RefreshList();
    }

    private void RefreshList()
    {
        SpeedsListBox.ItemsSource = _speeds
            .Select(v => v <= 0 ? "Floating" : $"{v:0.00} in/s")
            .ToList();
    }

    private void OkBtn_Click(object sender, RoutedEventArgs e)
    {
        SelectedSpeedsIns = new List<double>(_speeds);
        DialogResult = true;
    }

    private void CancelBtn_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
