using System.Windows;
using DiametroLineaDesktop.Models;

namespace DiametroLineaDesktop.Views;

public partial class SettingsWindow : Window
{
    public AppSettings EditableSettings { get; }

    public SettingsWindow(AppSettings settingsCopy)
    {
        InitializeComponent();
        EditableSettings = settingsCopy;
        DataContext = EditableSettings;
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = true;
        Close();
    }

    private void BrowseLibrary_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFolderDialog
        {
            Title = "Cartella libreria pezzi",
            InitialDirectory = string.IsNullOrWhiteSpace(EditableSettings.Prototype.LibraryFolder)
                ? Services.PieceLibrary.DefaultFolder
                : EditableSettings.Prototype.LibraryFolder,
        };
        if (dlg.ShowDialog(this) != true) return;

        EditableSettings.Prototype.LibraryFolder = dlg.FolderName;
        // The model isn't observable — rebind so the TextBox shows the picked folder.
        DataContext = null;
        DataContext = EditableSettings;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}