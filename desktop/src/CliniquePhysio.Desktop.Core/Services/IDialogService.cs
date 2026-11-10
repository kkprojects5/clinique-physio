namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Asks the user to confirm an action that cannot be undone. The WPF app shows a message box.</summary>
public interface IDialogService
{
    bool Confirm(string message);
}
