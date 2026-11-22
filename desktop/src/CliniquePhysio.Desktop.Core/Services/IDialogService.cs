namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Asks the user to confirm an action that cannot be undone, and opens files to print.
/// The WPF app shows a message box and opens the PDF reader.</summary>
public interface IDialogService
{
    bool Confirm(string message);

    /// <summary>Open a PDF (a receipt) in the computer's PDF reader, where it can be printed.</summary>
    void OpenPdf(byte[] content, string fileName);
}
