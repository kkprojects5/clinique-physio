using System.Diagnostics;
using System.IO;
using System.Windows;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;

namespace CliniquePhysio.Desktop;

/// <summary>Asks Yes / No in a message box before an action that cannot be undone; opens receipts.</summary>
public sealed class MessageBoxDialogs : IDialogService
{
    public bool Confirm(string message) =>
        MessageBox.Show(
            Application.Current.MainWindow!,
            message,
            Localizer.Instance["app.title"],
            MessageBoxButton.YesNo,
            MessageBoxImage.Question,
            MessageBoxResult.No) == MessageBoxResult.Yes;

    /// <summary>Saves the PDF in the user's temporary folder and opens it with the PDF reader, to print.
    /// The file holds a patient's name: it stays in the user's own profile, never in a shared folder.</summary>
    public void OpenPdf(byte[] content, string fileName)
    {
        var folder = Path.Combine(Path.GetTempPath(), "CliniquePhysio", "receipts");
        Directory.CreateDirectory(folder);
        var path = Path.Combine(folder, Path.GetFileName(fileName));
        File.WriteAllBytes(path, content);
        Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    }
}
