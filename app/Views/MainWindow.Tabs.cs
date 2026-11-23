using System.ComponentModel;
using System.Windows;
using MessageBox = System.Windows.MessageBox;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// What a project view needs to live inside a Chrome-style tab of <see cref="ShellWindow"/>.
/// MainWindow is no longer a Window: it is the whole UI of ONE open .flp, and the shell holds
/// several of them. Everything else in MainWindow is unchanged — this file only adds the hooks
/// the shell talks to.
/// </summary>
public partial class MainWindow
{
    private static readonly List<MainWindow> s_openViews = new();

    private bool _loadedOnce;
    private static bool s_primaryTaken;
    // The first view ever created is the one that auto-connects and opens the command-line file.
    private readonly bool _isPrimaryTab = TakePrimary();
    private static bool TakePrimary() { bool first = !s_primaryTaken; s_primaryTaken = true; return first; }

    private string _tabHeader = "Untitled";

    /// <summary>File to load as soon as the view is set up (tab opened with "+").</summary>
    public string? PendingOpenPath { get; set; }

    /// <summary>"Name *" — what the tab and the window title show.</summary>
    public string TabHeader
    {
        get => _tabHeader;
        private set { _tabHeader = value; OnPropertyChanged(nameof(TabHeader)); }
    }

    public string? ProjectPath => _currentProjectPath ?? PendingOpenPath;

    /// <summary>Raised when this view wants to be the visible tab (e.g. "Open in Profiler").</summary>
    public event Action<MainWindow>? ActivateRequested;
    /// <summary>Raised when a file this view produced (a C file) should be opened in a tab.</summary>
    public event Action<MainWindow, string>? OpenInNewTabRequested;
    /// <summary>Raised by the Exit menu item: closes the whole application.</summary>
    public event Action<MainWindow>? ExitRequested;

    /// <summary>
    /// True for a tab nothing was done in yet: opening a file there replaces it instead of adding
    /// a new tab, as Chrome does with a blank tab.
    /// </summary>
    public bool IsBlank =>
        PendingOpenPath == null && _currentProjectPath == null && !_isDirty
        && ProjectSegments.Count == 0 && _importedSeries.Count == 0 && _vm.Points.Count == 0;

    /// <summary>Registers the view; call once when the shell creates it.</summary>
    public void RegisterTab()
    {
        if (!s_openViews.Contains(this)) s_openViews.Add(this);
        if (!_compactHooked) { _compactHooked = true; SizeChanged += (_, e) => ApplyCompactHeader(e.NewSize.Width); }
        if (!_coreHooked)
        {
            _coreHooked = true;
            // LineCore.Current is one value for the whole process, but every tab has its own core.
            // Before anything in this tab computes (a click, a key, the wheel scrolling the table,
            // the tab coming into view) its own core is put back: without this, side by side or
            // after switching tab, masses and sink speeds were computed with the core of the last
            // tab loaded or edited (found 23/11/2026).
            PreviewMouseDown  += (_, _) => UseOwnCore();
            PreviewMouseWheel += (_, _) => UseOwnCore();
            PreviewKeyDown    += (_, _) => UseOwnCore();
            IsVisibleChanged  += (_, e) => { if (e.NewValue is true) UseOwnCore(); };
        }
    }

    private bool _compactHooked;
    private bool _coreHooked;

    /// <summary>Points the physics at this tab's core. Loading a file is synchronous on the UI
    /// thread, so none of the events above can fire half-way through it.</summary>
    private void UseOwnCore() => Models.LineCore.Current = CurrentCoreModel();

    /// <summary>
    /// Side by side the header's centre buttons (New/Open/…) would slide under the app title.
    /// When the view is narrow, hide the title and the project name (the tab shows it) instead.
    /// At full width nothing changes.
    /// </summary>
    private void ApplyCompactHeader(double width)
    {
        var vis = width < 1250 ? Visibility.Collapsed : Visibility.Visible;
        AppTitlePanel.Visibility = vis;
        ProjectNameText.Visibility = vis;
    }

    /// <summary>
    /// The same questions the window used to ask on close (unsaved project, prototype window).
    /// Returns false when the user cancels. On success the gauge connection, if this tab
    /// holds it, is released so another tab can take it.
    /// </summary>
    public bool RequestClose()
    {
        var e = new CancelEventArgs();
        MainWindow_Closing(this, e);
        if (!e.Cancel) MainWindow_ClosingPrototype(this, e);
        if (e.Cancel) return false;
        s_openViews.Remove(this);
        if (_vm.IsConnected) _ = _vm.DisconnectAsync();
        return true;
    }

    /// <summary>
    /// Reloads this tab's file from disk (a C file just regenerated over the one shown here).
    /// Asks first if this tab has unsaved changes.
    /// </summary>
    public void ReloadFromDisk(string path)
    {
        if (!ConfirmDiscardIfDirty()) return;
        try { LoadProjectFromFile(path); }
        catch (Exception ex)
        {
            MessageBox.Show($"Could not open project:\n{ex.Message}", "Error",
                            MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    /// <summary>One gauge, one WebSocket: refuse to connect while another tab holds it.</summary>
    private bool CanTakeGauge()
    {
        var owner = s_openViews.FirstOrDefault(v => v != this && v._vm.IsConnected);
        if (owner == null) return true;
        MessageBox.Show(
            $"The gauge is already connected in the tab \"{owner.TabHeader}\".\n" +
            "Disconnect it there first.",
            "Gauge in use", MessageBoxButton.OK, MessageBoxImage.Information);
        return false;
    }
}
