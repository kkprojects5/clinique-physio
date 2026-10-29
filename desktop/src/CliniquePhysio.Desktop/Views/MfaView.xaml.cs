using System.Windows.Controls;

namespace CliniquePhysio.Desktop.Views;

public partial class MfaView : UserControl
{
    public MfaView()
    {
        InitializeComponent();
        Loaded += (_, _) => CodeBox.Focus();
    }
}
