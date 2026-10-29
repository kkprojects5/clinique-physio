using System.Text.RegularExpressions;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Step 2 of 2: the 6-digit code. The first time, show the QR code to scan.</summary>
public sealed partial class MfaViewModel : ObservableObject
{
    private readonly IApiClient _api;
    private readonly Session _session;
    private readonly INavigator _navigator;
    private readonly string _mfaToken;
    private readonly string _email;
    private string? _secret;
    private string? _otpauthUri;
    private string _code = "";
    private string? _error;
    private bool _isBusy;

    public MfaViewModel(
        IApiClient api, Session session, INavigator navigator, string mfaToken, bool setupRequired, string email)
    {
        _api = api;
        _session = session;
        _navigator = navigator;
        _mfaToken = mfaToken;
        _email = email;
        SetupRequired = setupRequired;
        LoadCommand = new AsyncRelayCommand(LoadAsync);
        VerifyCommand = new AsyncRelayCommand(VerifyAsync);
        BackCommand = new RelayCommand(() => _navigator.GoToLogin());
    }

    public bool SetupRequired { get; }

    /// <summary>Key for manual entry in the authenticator app (first login only).</summary>
    public string? Secret
    {
        get => _secret;
        private set => SetProperty(ref _secret, value);
    }

    /// <summary>otpauth:// link, shown as a QR code by the view.</summary>
    public string? OtpauthUri
    {
        get => _otpauthUri;
        private set => SetProperty(ref _otpauthUri, value);
    }

    public string Code
    {
        get => _code;
        set => SetProperty(ref _code, value);
    }

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

    public IAsyncRelayCommand LoadCommand { get; }

    public IAsyncRelayCommand VerifyCommand { get; }

    public IRelayCommand BackCommand { get; }

    [GeneratedRegex(@"^\d{6}$")]
    private static partial Regex SixDigits();

    private async Task LoadAsync()
    {
        if (!SetupRequired || Secret is not null)
        {
            return;
        }

        IsBusy = true;
        try
        {
            var setup = await _api.SetupMfaAsync(_mfaToken);
            Secret = setup.Secret;
            OtpauthUri = setup.OtpauthUri;
        }
        catch (ApiException error)
        {
            Error = error.Kind == ApiErrorKind.Unauthorized
                ? Localizer.Instance["error.expired"]
                : ErrorMessages.For(error);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task VerifyAsync()
    {
        Error = null;
        var code = Code.Trim();
        if (!SixDigits().IsMatch(code))
        {
            Error = Localizer.Instance["mfa.enterCode"];
            return;
        }

        IsBusy = true;
        try
        {
            var tokens = await _api.VerifyMfaAsync(_mfaToken, code);
            _session.Start(tokens.AccessToken, _email);
            _navigator.GoToSchedule();
        }
        catch (ApiException error)
        {
            Error = error.Kind == ApiErrorKind.Unauthorized
                ? Localizer.Instance["error.code"]
                : ErrorMessages.For(error);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
