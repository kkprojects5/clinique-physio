using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>The window: which screen is shown, the connection indicator and the language switch.</summary>
public sealed class MainViewModel : ObservableObject, INavigator
{
    private readonly IApiClient _api;
    private readonly Session _session;
    private readonly Func<DateTime> _today;
    private object? _currentView;
    private bool _isOnline = true;

    public MainViewModel(IApiClient api, Session session, Func<DateTime>? today = null)
    {
        _api = api;
        _session = session;
        _today = today ?? (() => DateTime.Today);
        CheckConnectionCommand = new AsyncRelayCommand(CheckConnectionAsync);
        SwitchLanguageCommand = new RelayCommand(SwitchLanguage);
    }

    public object? CurrentView
    {
        get => _currentView;
        private set => SetProperty(ref _currentView, value);
    }

    public bool IsOnline
    {
        get => _isOnline;
        private set => SetProperty(ref _isOnline, value);
    }

    public IAsyncRelayCommand CheckConnectionCommand { get; }

    public IRelayCommand SwitchLanguageCommand { get; }

    public void GoToLogin(string? message = null) =>
        CurrentView = new LoginViewModel(_api, this, message);

    public void GoToMfa(string mfaToken, bool setupRequired, string email)
    {
        var mfa = new MfaViewModel(_api, _session, this, mfaToken, setupRequired, email);
        CurrentView = mfa;
        _ = mfa.LoadCommand.ExecuteAsync(null);
    }

    public void GoToSchedule()
    {
        var schedule = new ScheduleViewModel(_api, _session, this, _today());
        CurrentView = schedule;
        _ = schedule.LoadCommand.ExecuteAsync(null);
    }

    private async Task CheckConnectionAsync() => IsOnline = await _api.IsOnlineAsync();

    private void SwitchLanguage()
    {
        var localizer = Localizer.Instance;
        localizer.Language = localizer.Language == "fr" ? "en" : "fr";
        if (CurrentView is ScheduleViewModel schedule)
        {
            _ = schedule.LoadCommand.ExecuteAsync(null); // service names and date in the new language
        }
    }
}
