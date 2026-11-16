using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// Asks for the target sink speed of a physical compensation and how many nozzles (real
/// materials, 2–4) it may use. The main window never shows a compensated preview — "Create C
/// file" solves the profile and writes it straight to its own sibling file, leaving this design
/// untouched. The only preview is the speed deviation each nozzle count would give.
/// </summary>
public partial class CompensateDialog : Window
{
    private readonly Func<double, int, string> _fileNameFor;
    private readonly Func<double, (double WorstIns, double MeanIns)[]>? _previewErrors;
    private readonly DispatcherTimer _previewTimer;
    private bool _ready;

    /// <summary>Chosen target sink speed, in inches per second.</summary>
    public double SelectedSpeedIns { get; private set; }

    /// <summary>Chosen number of nozzles (materials), 2–4.</summary>
    public int SelectedNozzleCount { get; private set; } = 4;

    /// <param name="minIns">Slowest sink speed among the current sections (in/s).</param>
    /// <param name="maxIns">Fastest sink speed among the current sections (in/s).</param>
    /// <param name="defaultIns">Initial slider position (in/s).</param>
    /// <param name="defaultNozzles">Initially selected nozzle count (2–4).</param>
    /// <param name="fileNameFor">Maps (target speed, nozzle count) to the file name that would be written.</param>
    /// <param name="previewErrors">Maps a target speed to the (worst, mean) deviation in in/s for 2, 3, 4 nozzles.</param>
    public CompensateDialog(double minIns, double maxIns, double defaultIns, int defaultNozzles,
                            Func<double, int, string> fileNameFor,
                            Func<double, (double WorstIns, double MeanIns)[]>? previewErrors = null)
    {
        _fileNameFor   = fileNameFor;
        _previewErrors = previewErrors;
        InitializeComponent();

        // The solve runs on every slider stop, not on every pixel of a drag.
        _previewTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(150) };
        _previewTimer.Tick += (_, _) => { _previewTimer.Stop(); UpdatePreview(); };

        // A single-section line (or one whose sections happen to match) has a degenerate range;
        // open it up slightly so the slider is still usable rather than locked to one value.
        if (maxIns - minIns < 0.01)
        {
            minIns = Math.Max(0.01, minIns - 0.25);
            maxIns += 0.25;
        }

        SpeedSlider.Minimum = minIns;
        SpeedSlider.Maximum = maxIns;
        SpeedSlider.Value   = Math.Clamp(defaultIns, minIns, maxIns);
        MinLabel.Text = $"{minIns:0.00}";
        MaxLabel.Text = $"{maxIns:0.00}";

        SelectedNozzleCount = Math.Clamp(defaultNozzles, 2, 4);
        (SelectedNozzleCount switch { 2 => Noz2, 3 => Noz3, _ => Noz4 }).IsChecked = true;

        _ready = true;
        UpdateLabels();
        UpdatePreview();
    }

    private void SpeedSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        UpdateLabels();
        if (_ready) { _previewTimer.Stop(); _previewTimer.Start(); }
    }

    private void NozzleRadio_Checked(object sender, RoutedEventArgs e)
    {
        if (sender is RadioButton rb && int.TryParse(rb.Tag?.ToString(), out int n))
            SelectedNozzleCount = n;
        UpdateLabels();
    }

    private void UpdateLabels()
    {
        if (!_ready) return; // fires mid-InitializeComponent, before the fields exist
        SpeedValueLabel.Text = $"{SpeedSlider.Value:0.000} in/s";
        FileNameLabel.Text   = _fileNameFor(SpeedSlider.Value, SelectedNozzleCount);
    }

    private void UpdatePreview()
    {
        if (_previewErrors == null) return;
        (double WorstIns, double MeanIns)[] e;
        try { e = _previewErrors(SpeedSlider.Value); }
        catch { return; } // a preview must never block the dialog
        var worst = new[] { Worst2, Worst3, Worst4 };
        var mean  = new[] { Mean2,  Mean3,  Mean4  };
        for (int i = 0; i < 3 && i < e.Length; i++)
        {
            worst[i].Text = $"±{e[i].WorstIns:0.000}";
            mean[i].Text  = $"{e[i].MeanIns:0.000}";
        }
    }

    private void OkBtn_Click(object sender, RoutedEventArgs e)
    {
        SelectedSpeedIns = SpeedSlider.Value;
        DialogResult = true;
    }

    private void CancelBtn_Click(object sender, RoutedEventArgs e) => DialogResult = false;
}
