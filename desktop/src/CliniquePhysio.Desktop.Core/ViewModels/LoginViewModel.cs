using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Step 1 of 2: email and password. Staff then need an MFA code (B-AUTH-04).</summary>
public sealed class LoginViewModel : ObservableObject
{
    private readonly IApiClient _api;
    private readonly INavigator _navigator;
    private string _email = "";
    private string? _error;
    private bool _isBusy;

    public LoginViewModel(IApiClient api, INavigator navigator, string? message = null)
    {
        _api = api;
        _navigator = navigator;
        _error = message;
        LoginCommand = new AsyncRelayCommand(LoginAsync);
    }

    public string Email
    {
        get => _email;
        set => SetProperty(ref _email, value);
    }

    /// <summary>Set by the view's PasswordBox (a password cannot be data-bound in WPF).</summary>
    public string Password { get; set; } = "";

    public string? Error
    {
        get => _error;
        private set => SetProperty(ref _error, value);
    }

    public bool IsBusy
    {
        get => _isBusy;
        private set => SetProperty(ref _isBusy, value);
    }

    public IAsyncRelayCommand LoginCommand { get; }

    private async Task LoginAsync()
    {
        Error = null;
        var email = Email.Trim();
        if (email.Length == 0 || Password.Length == 0)
        {
            Error = Localizer.Instance["login.missing"];
            return;
        }

        IsBusy = true;
        try
        {
            var result = await _api.LoginAsync(email, Password);
            if (!result.MfaRequired || result.MfaToken is null)
            {
                // A patient account: it got tokens directly. This app is for staff only.
                await _api.LogoutAsync();
                Error = Localizer.Instance["login.staffOnly"];
                return;
            }

            Password = "";
            _navigator.GoToMfa(result.MfaToken, result.MfaSetupRequired, email);
        }
        catch (ApiException error)
        {
            Error = ErrorMessages.For(error);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
