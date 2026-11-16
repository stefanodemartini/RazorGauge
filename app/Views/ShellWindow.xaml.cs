using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Button = System.Windows.Controls.Button;
using Cursors = System.Windows.Input.Cursors;
using KeyEventArgs = System.Windows.Input.KeyEventArgs;
using MouseEventArgs = System.Windows.Input.MouseEventArgs;
using Orientation = System.Windows.Controls.Orientation;
using Point = System.Windows.Point;

namespace DiametroLineaDesktop.Views;

/// <summary>
/// Chrome-style tabs around the project views. Each tab is a complete, independent
/// <see cref="MainWindow"/> (one .flp). Tabs can be reordered by dragging, dragged out into a
/// window of their own, dropped onto another window's tab strip, or shown two side by side.
/// </summary>
public partial class ShellWindow : Window
{
    private sealed class Tab
    {
        public required MainWindow View;
        public required Border Header;
        public required TextBlock Text;
    }

    private readonly List<Tab> _tabs = new();
    private MainWindow? _left;          // view in the left (or only) pane
    private MainWindow? _right;         // view in the right pane; null = single view
    private bool _focusRight;           // which pane the tab strip currently drives

    private static readonly SolidColorBrush ActiveBg   = Brush("#1C2030");
    private static readonly SolidColorBrush ShownBg    = Brush("#171A25");
    private static readonly SolidColorBrush HoverBg    = Brush("#191C27");
    private static readonly SolidColorBrush Accent     = Brush("#2D7DD2");
    private static readonly SolidColorBrush AccentDim  = Brush("#1A4F8A");
    private static readonly SolidColorBrush TextOn     = Brush("#E2E8F4");
    private static readonly SolidColorBrush TextOff    = Brush("#7A8499");

    private static SolidColorBrush Brush(string hex)
    {
        var b = new SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(hex));
        b.Freeze();
        return b;
    }

    /// <summary>Startup window: one tab with a fresh project view.</summary>
    public ShellWindow() : this(new MainWindow()) { }

    /// <summary>A window that starts with an existing view (a tab dragged out of another window).</summary>
    public ShellWindow(MainWindow view)
    {
        InitializeComponent();
        AddTab(view, -1);
        Show(view);
        Closing += ShellWindow_Closing;
        PreviewKeyDown += ShellWindow_PreviewKeyDown;
    }

    // ── Tabs ─────────────────────────────────────────────────────────────────

    private void AddTab(MainWindow view, int index)
    {
        view.RegisterTab();
        var text = new TextBlock
        {
            Text = view.TabHeader, FontSize = 12, VerticalAlignment = VerticalAlignment.Center,
            TextTrimming = TextTrimming.CharacterEllipsis, MaxWidth = 190, Foreground = TextOff,
        };
        var close = new Button
        {
            Content = "×", FontSize = 13, Padding = new Thickness(5, 0, 5, 1), Margin = new Thickness(8, 0, 0, 0),
            Style = (Style)FindResource("StripBtn"), ToolTip = "Close tab (Ctrl+W)", Focusable = false,
        };
        var panel = new StackPanel { Orientation = Orientation.Horizontal };
        panel.Children.Add(text);
        panel.Children.Add(close);
        var header = new Border
        {
            Child = panel, Padding = new Thickness(12, 0, 4, 0), Margin = new Thickness(0, 4, 2, 0),
            CornerRadius = new CornerRadius(6, 6, 0, 0), BorderThickness = new Thickness(0, 2, 0, 0),
            Background = System.Windows.Media.Brushes.Transparent, BorderBrush = System.Windows.Media.Brushes.Transparent,
            MinWidth = 110, ToolTip = view.ProjectPath ?? view.TabHeader, Cursor = Cursors.Arrow,
        };
        var tab = new Tab { View = view, Header = header, Text = text };

        close.Click += (_, _) => CloseTab(tab);
        header.MouseEnter += (_, _) => StyleHeaders();
        header.MouseLeave += (_, _) => StyleHeaders();
        header.MouseDown += (_, e) => { if (e.ChangedButton == MouseButton.Middle) { CloseTab(tab); e.Handled = true; } };
        header.PreviewMouseLeftButtonDown += (s, e) => Header_MouseDown(tab, e);
        header.MouseMove += (s, e) => Header_MouseMove(tab, e);
        header.MouseLeftButtonUp += (s, e) => Header_MouseUp(tab, e);
        header.LostMouseCapture += (_, _) => EndDragVisuals(tab);
        header.ContextMenu = BuildContextMenu(tab);

        view.PropertyChanged += View_PropertyChanged;
        view.ActivateRequested += View_ActivateRequested;
        view.ExitRequested += View_ExitRequested;
        view.PreviewMouseDown += View_FocusGained;
        view.PreviewGotKeyboardFocus += View_FocusGained;

        if (index < 0 || index > _tabs.Count) index = _tabs.Count;
        _tabs.Insert(index, tab);
        TabStrip.Children.Insert(index, header);
        view.Visibility = Visibility.Collapsed;
        ContentHost.Children.Add(view);
    }

    /// <summary>Takes a tab out of this window without closing its project.</summary>
    private void DetachTab(Tab tab)
    {
        var view = tab.View;
        view.PropertyChanged -= View_PropertyChanged;
        view.ActivateRequested -= View_ActivateRequested;
        view.ExitRequested -= View_ExitRequested;
        view.PreviewMouseDown -= View_FocusGained;
        view.PreviewGotKeyboardFocus -= View_FocusGained;

        int idx = _tabs.IndexOf(tab);
        _tabs.Remove(tab);
        TabStrip.Children.Remove(tab.Header);
        ContentHost.Children.Remove(view);

        if (view == _right) { _right = null; _focusRight = false; }
        else if (view == _left)
        {
            if (_right != null) { _left = _right; _right = null; _focusRight = false; }
            else _left = _tabs.Count > 0 ? _tabs[Math.Min(idx, _tabs.Count - 1)].View : null;
        }

        if (_tabs.Count == 0) { Close(); return; }
        Layout();
    }

    private void CloseTab(Tab tab)
    {
        Show(tab.View);
        if (!tab.View.RequestClose()) return;
        DetachTab(tab);
    }

    private Tab? TabOf(MainWindow view) => _tabs.FirstOrDefault(t => t.View == view);

    /// <summary>Shows a view in the pane the strip currently drives (Chrome: click a tab).</summary>
    private void Show(MainWindow view)
    {
        if (_right == null) _left = view;
        else if (view == _left || view == _right) _focusRight = view == _right;   // already shown: just focus its pane
        else if (_focusRight)
        {
            _right = view;
        }
        else
        {
            _left = view;
        }
        Layout();
    }

    private void Layout()
    {
        bool split = _right != null && _right != _left;
        if (!split) { _right = null; _focusRight = false; }

        foreach (var t in _tabs)
        {
            var v = t.View;
            if (v == _left)       { Grid.SetColumn(v, 0); v.Visibility = Visibility.Visible; }
            else if (v == _right) { Grid.SetColumn(v, 2); v.Visibility = Visibility.Visible; }
            else v.Visibility = Visibility.Collapsed;
        }

        var cols = ContentHost.ColumnDefinitions;
        if (split)
        {
            if (cols[2].Width.Value == 0) { cols[0].Width = new GridLength(1, GridUnitType.Star); cols[2].Width = new GridLength(1, GridUnitType.Star); }
            cols[1].Width = new GridLength(6);
            PaneSplitter.Visibility = Visibility.Visible;
            SplitBtn.Content = "▭  Single view";
        }
        else
        {
            cols[0].Width = new GridLength(1, GridUnitType.Star);
            cols[1].Width = new GridLength(0);
            cols[2].Width = new GridLength(0);
            PaneSplitter.Visibility = Visibility.Collapsed;
            SplitBtn.Content = "◫  Side by side";
        }
        StyleHeaders();
        UpdateTitle();
    }

    private MainWindow? FocusedView => _focusRight && _right != null ? _right : _left;

    private void StyleHeaders()
    {
        var focused = FocusedView;
        foreach (var t in _tabs)
        {
            bool isFocused = t.View == focused;
            bool isShown = t.View == _left || t.View == _right;
            t.Header.Background = isFocused ? ActiveBg : isShown ? ShownBg
                                : t.Header.IsMouseOver ? HoverBg : System.Windows.Media.Brushes.Transparent;
            t.Header.BorderBrush = isFocused ? Accent : isShown ? AccentDim : System.Windows.Media.Brushes.Transparent;
            t.Text.Foreground = isShown ? TextOn : TextOff;
            t.Text.FontWeight = isFocused ? FontWeights.SemiBold : FontWeights.Normal;
        }
    }

    private void UpdateTitle()
    {
        var v = FocusedView;
        Title = v == null ? "RazorGauge" : $"RazorGauge — {v.TabHeader}";
    }

    // ── View events ──────────────────────────────────────────────────────────

    private void View_PropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(MainWindow.TabHeader) || sender is not MainWindow v) return;
        if (TabOf(v) is { } t)
        {
            t.Text.Text = v.TabHeader;
            t.Header.ToolTip = v.ProjectPath ?? v.TabHeader;
        }
        UpdateTitle();
    }

    private void View_FocusGained(object sender, RoutedEventArgs e)
    {
        if (_right == null || sender is not MainWindow v) return;
        bool right = v == _right;
        if (right == _focusRight) return;
        _focusRight = right;
        StyleHeaders();
        UpdateTitle();
    }

    private void View_ActivateRequested(MainWindow v)
    {
        if (v != _left && v != _right) Show(v);
        if (WindowState == WindowState.Minimized) WindowState = WindowState.Normal;
        Activate();
    }

    private static void View_ExitRequested(MainWindow v)
    {
        foreach (var w in System.Windows.Application.Current.Windows.OfType<ShellWindow>().ToList())
        {
            w.Close();
            if (w.IsVisible) return;   // the user cancelled on an unsaved project
        }
    }

    // ── Commands ─────────────────────────────────────────────────────────────

    private void NewTab()
    {
        var v = new MainWindow();
        AddTab(v, _tabs.Count);
        Show(v);
    }

    private void NewTab_Click(object sender, RoutedEventArgs e) => NewTab();

    private void SplitBtn_Click(object sender, RoutedEventArgs e)
    {
        if (_right != null) { _right = null; _focusRight = false; Layout(); return; }
        // Right pane: the tab after the current one, or a new blank tab if there is only one.
        if (_tabs.Count < 2) { var v = new MainWindow(); AddTab(v, _tabs.Count); }
        int i = _tabs.FindIndex(t => t.View == _left);
        var other = _tabs[(i + 1) % _tabs.Count].View;
        ShowSideBySide(other);
    }

    private void ShowSideBySide(MainWindow rightView)
    {
        if (rightView == _left)
        {
            var other = _tabs.FirstOrDefault(t => t.View != rightView)?.View;
            if (other == null) return;
            _left = other;
        }
        _right = rightView;
        _focusRight = true;
        Layout();
    }

    private void MoveToNewWindow(Tab tab, Point? screenDip = null)
    {
        if (_tabs.Count < 2) return;   // the only tab already is a window
        DetachTab(tab);
        var w = new ShellWindow(tab.View) { Width = ActualWidth, Height = ActualHeight };
        if (screenDip is { } p)
        {
            w.WindowStartupLocation = WindowStartupLocation.Manual;
            w.Left = p.X - 80;
            w.Top = p.Y - 16;
        }
        else
        {
            w.WindowStartupLocation = WindowStartupLocation.Manual;
            w.Left = Left + 40;
            w.Top = Top + 40;
        }
        w.Show();
        w.Activate();
    }

    private ContextMenu BuildContextMenu(Tab tab)
    {
        var m = new ContextMenu();
        void Add(string header, Action a, Func<bool>? enabled = null)
        {
            var it = new MenuItem { Header = header };
            it.Click += (_, _) => a();
            if (enabled != null) m.Opened += (_, _) => it.IsEnabled = enabled();
            m.Items.Add(it);
        }
        Add("New tab", NewTab);
        Add("Show on the right (side by side)", () => ShowSideBySide(tab.View), () => _tabs.Count > 1);
        Add("Move to new window", () => MoveToNewWindow(tab), () => _tabs.Count > 1);
        m.Items.Add(new Separator());
        Add("Close tab", () => CloseTab(tab));
        Add("Close other tabs", () =>
        {
            foreach (var t in _tabs.Where(t => t != tab).ToList())
            {
                Show(t.View);
                if (!t.View.RequestClose()) break;
                DetachTab(t);
            }
            Show(tab.View);
        }, () => _tabs.Count > 1);
        return m;
    }

    private void ShellWindow_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (Keyboard.Modifiers.HasFlag(ModifierKeys.Control))
        {
            if (e.Key == Key.T && Keyboard.Modifiers == ModifierKeys.Control) { NewTab(); e.Handled = true; }
            else if (e.Key == Key.W && Keyboard.Modifiers == ModifierKeys.Control)
            {
                if (FocusedView is { } v && TabOf(v) is { } t) CloseTab(t);
                e.Handled = true;
            }
            else if (e.Key == Key.Tab && _tabs.Count > 1)
            {
                int dir = Keyboard.Modifiers.HasFlag(ModifierKeys.Shift) ? -1 : 1;
                int i = _tabs.FindIndex(t => t.View == FocusedView);
                Show(_tabs[(i + dir + _tabs.Count) % _tabs.Count].View);
                e.Handled = true;
            }
        }
    }

    private void TabScroll_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
    {
        TabScroll.ScrollToHorizontalOffset(TabScroll.HorizontalOffset - e.Delta / 3.0);
        e.Handled = true;
    }

    private void ShellWindow_Closing(object? sender, CancelEventArgs e)
    {
        // Same questions as before, one tab at a time; Cancel on any of them keeps the window.
        foreach (var t in _tabs.ToList())
        {
            if (t.View.Visibility != Visibility.Visible) Show(t.View);
            if (!t.View.RequestClose())
            {
                e.Cancel = true;
                if (_left == null || !_tabs.Any(x => x.View == _left)) _left = _tabs[0].View;
                Layout();
                return;
            }
            _tabs.Remove(t);
            TabStrip.Children.Remove(t.Header);
            ContentHost.Children.Remove(t.View);
            if (t.View == _left) _left = null;
            if (t.View == _right) _right = null;
        }
    }

    // ── Dragging a tab ───────────────────────────────────────────────────────

    private Tab? _pressTab;
    private Point _pressPoint;
    private bool _dragging;

    private void Header_MouseDown(Tab tab, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is DependencyObject d && FindAncestor<Button>(d) != null) return;   // the ×
        Show(tab.View);
        _pressTab = tab;
        _pressPoint = e.GetPosition(this);
        _dragging = false;
    }

    private void Header_MouseMove(Tab tab, MouseEventArgs e)
    {
        if (_pressTab != tab || e.LeftButton != MouseButtonState.Pressed) return;
        var p = e.GetPosition(this);
        if (!_dragging)
        {
            if (Math.Abs(p.X - _pressPoint.X) < 8 && Math.Abs(p.Y - _pressPoint.Y) < 8) return;
            _dragging = true;
            tab.Header.CaptureMouse();
            tab.Header.Opacity = 0.75;
        }

        // Reorder while the pointer is over the strip.
        var ps = e.GetPosition(TabStrip);
        if (ps.Y >= -10 && ps.Y <= StripBorder.ActualHeight + 10)
        {
            int target = 0;
            for (int i = 0; i < _tabs.Count; i++)
            {
                var h = _tabs[i].Header;
                if (h == tab.Header) continue;
                var x = h.TranslatePoint(new Point(h.ActualWidth / 2, 0), TabStrip).X;
                if (ps.X > x) target++;
            }
            int cur = _tabs.IndexOf(tab);
            if (target != cur)
            {
                _tabs.RemoveAt(cur); _tabs.Insert(target, tab);
                TabStrip.Children.Remove(tab.Header); TabStrip.Children.Insert(target, tab.Header);
                tab.Header.CaptureMouse();
            }
            Mouse.OverrideCursor = null;
            DropHint.Visibility = Visibility.Collapsed;
            return;
        }

        // Over the content's right half: hint "side by side".
        var pc = e.GetPosition(ContentHost);
        bool inContent = pc.X >= 0 && pc.Y >= 0 && pc.X <= ContentHost.ActualWidth && pc.Y <= ContentHost.ActualHeight;
        if (inContent && pc.X > ContentHost.ActualWidth / 2 && _tabs.Count > 1)
        {
            DropHint.Width = ContentHost.ActualWidth / 2;
            DropHint.Visibility = Visibility.Visible;
        }
        else DropHint.Visibility = Visibility.Collapsed;
        Mouse.OverrideCursor = inContent ? Cursors.Arrow : Cursors.SizeAll;
    }

    private void Header_MouseUp(Tab tab, MouseButtonEventArgs e)
    {
        bool wasDragging = _dragging && _pressTab == tab;
        _pressTab = null;
        _dragging = false;
        if (tab.Header.IsMouseCaptured) tab.Header.ReleaseMouseCapture();
        EndDragVisuals(tab);
        if (!wasDragging) return;

        var ps = e.GetPosition(TabStrip);
        if (ps.Y >= -10 && ps.Y <= StripBorder.ActualHeight + 10) return;   // reorder only

        var screen = PointToScreen(e.GetPosition(this));

        // Onto another window's tab strip: move the tab there.
        foreach (var w in System.Windows.Application.Current.Windows.OfType<ShellWindow>())
        {
            if (w == this || !w.IsVisible) continue;
            var pw = w.StripBorder.PointFromScreen(screen);
            if (pw.X >= 0 && pw.Y >= 0 && pw.X <= w.StripBorder.ActualWidth && pw.Y <= w.StripBorder.ActualHeight)
            {
                DetachTab(tab);
                w.AdoptTab(tab.View, w.InsertIndexAt(w.TabStrip.PointFromScreen(screen).X));
                return;
            }
        }

        var pc = e.GetPosition(ContentHost);
        bool inContent = pc.X >= 0 && pc.Y >= 0 && pc.X <= ContentHost.ActualWidth && pc.Y <= ContentHost.ActualHeight;
        if (inContent)
        {
            if (pc.X > ContentHost.ActualWidth / 2 && _tabs.Count > 1) ShowSideBySide(tab.View);
            return;
        }

        // Outside the window: a window of its own, where it was dropped.
        var src = PresentationSource.FromVisual(this);
        var dip = src?.CompositionTarget is { } ct ? ct.TransformFromDevice.Transform(screen) : screen;
        MoveToNewWindow(tab, dip);
    }

    private void EndDragVisuals(Tab tab)
    {
        tab.Header.Opacity = 1;
        Mouse.OverrideCursor = null;
        DropHint.Visibility = Visibility.Collapsed;
    }

    private int InsertIndexAt(double x)
    {
        int idx = 0;
        foreach (var t in _tabs)
            if (x > t.Header.TranslatePoint(new Point(t.Header.ActualWidth / 2, 0), TabStrip).X) idx++;
        return idx;
    }

    /// <summary>Receives a tab dragged from another window.</summary>
    private void AdoptTab(MainWindow view, int index)
    {
        AddTab(view, index);
        _focusRight = false;
        Show(view);
        Activate();
    }

    private static T? FindAncestor<T>(DependencyObject d) where T : DependencyObject
    {
        while (d != null)
        {
            if (d is T t) return t;
            d = d is Visual or System.Windows.Media.Media3D.Visual3D ? VisualTreeHelper.GetParent(d) : LogicalTreeHelper.GetParent(d);
        }
        return null;
    }
}
