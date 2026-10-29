using System.Windows;
using System.Windows.Controls;
using CliniquePhysio.Desktop.Core.ViewModels;

namespace CliniquePhysio.Desktop.Views;

public partial class LoginView : UserControl
{
    public LoginView()
    {
        InitializeComponent();
        Loaded += (_, _) => EmailBox.Focus();
    }

    // WPF does not allow binding a PasswordBox (on purpose, for security), so we pass it here.
    private void OnPasswordChanged(object sender, RoutedEventArgs e)
    {
        if (DataContext is LoginViewModel vm)
        {
            vm.Password = PasswordInput.Password;
        }
    }
}
