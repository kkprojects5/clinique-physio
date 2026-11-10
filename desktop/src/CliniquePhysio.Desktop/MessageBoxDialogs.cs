using System.Windows;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;

namespace CliniquePhysio.Desktop;

/// <summary>Asks Yes / No in a message box before an action that cannot be undone.</summary>
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
}
