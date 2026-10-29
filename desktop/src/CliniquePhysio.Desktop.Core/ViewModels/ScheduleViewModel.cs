using System.Collections.ObjectModel;
using System.Globalization;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>One appointment as shown in a therapist's column.</summary>
public sealed record AppointmentItem(
    string TimeRange, string PatientName, string Phone, string ServiceName, string Status, string StatusLabel);

/// <summary>One column of the day grid: a therapist and their appointments (B-FRD-01).</summary>
public sealed record TherapistColumn(string Name, IReadOnlyList<AppointmentItem> Appointments)
{
    public bool IsEmpty => Appointments.Count == 0;
}

/// <summary>The front desk's day view: one column per therapist, status colours.</summary>
public sealed class ScheduleViewModel : ObservableObject
{
    private readonly IApiClient _api;
    private readonly Session _session;
    private readonly INavigator _navigator;
    private DateTime? _selectedDate;
    private string _title = "";
    private string? _error;
    private bool _isBusy;

    public ScheduleViewModel(IApiClient api, Session session, INavigator navigator, DateTime today)
    {
        _api = api;
        _session = session;
        _navigator = navigator;
        _selectedDate = today.Date;
        LoadCommand = new AsyncRelayCommand(LoadAsync);
        PreviousCommand = new AsyncRelayCommand(() => MoveAsync(-1));
        NextCommand = new AsyncRelayCommand(() => MoveAsync(1));
        TodayCommand = new AsyncRelayCommand(() => GoToAsync(today.Date));
        LogoutCommand = new AsyncRelayCommand(LogoutAsync);
    }

    public ObservableCollection<TherapistColumn> Columns { get; } = new();

    /// <summary>Bound to the DatePicker. Changing it loads that day.</summary>
    public DateTime? SelectedDate
    {
        get => _selectedDate;
        set
        {
            if (SetProperty(ref _selectedDate, value?.Date) && value is not null)
            {
                _ = LoadCommand.ExecuteAsync(null);
            }
        }
    }

    public string Title
    {
        get => _title;
        private set => SetProperty(ref _title, value);
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

    public string? StaffEmail => _session.Email;

    public IAsyncRelayCommand LoadCommand { get; }

    public IAsyncRelayCommand PreviousCommand { get; }

    public IAsyncRelayCommand NextCommand { get; }

    public IAsyncRelayCommand TodayCommand { get; }

    public IAsyncRelayCommand LogoutCommand { get; }

    /// <summary>Builds the columns from the API answer. Pure function: easy to test.</summary>
    public static IReadOnlyList<TherapistColumn> BuildColumns(DaySchedule schedule, string language)
    {
        var l = Localizer.Instance;
        return schedule.Therapists
            .Select(t => new TherapistColumn(
                t.FullName,
                schedule.Appointments
                    .Where(a => a.TherapistId == t.Id)
                    .OrderBy(a => a.Start)
                    .Select(a => new AppointmentItem(
                        TimeRange(a),
                        $"{a.Patient.FirstName} {a.Patient.LastName}",
                        a.Patient.Phone,
                        language == "en" ? a.Service.NameEn : a.Service.NameFr,
                        a.Status,
                        l[$"status.{a.Status}"]))
                    .ToList()))
            .ToList();
    }

    /// <summary>"09:00–09:30" in Montréal time, using the offset the API gives.</summary>
    public static string TimeRange(DeskAppointment appointment)
    {
        var start = DateTimeOffset.Parse(appointment.StartLocal, CultureInfo.InvariantCulture);
        var end = appointment.End.ToOffset(start.Offset);
        return $"{start:HH\\:mm}–{end:HH\\:mm}";
    }

    private Task MoveAsync(int days) => GoToAsync((SelectedDate ?? DateTime.Today).AddDays(days));

    private Task GoToAsync(DateTime day)
    {
        if (SelectedDate == day.Date)
        {
            return LoadAsync();
        }

        SelectedDate = day; // the setter loads the day
        return Task.CompletedTask;
    }

    private async Task LoadAsync()
    {
        if (SelectedDate is not DateTime day)
        {
            return;
        }

        var language = Localizer.Instance.Language;
        Title = day.ToString("dddd d MMMM yyyy", CultureInfo.GetCultureInfo(language == "en" ? "en-CA" : "fr-CA"));
        Error = null;
        IsBusy = true;
        try
        {
            var schedule = await _api.GetDayScheduleAsync(DateOnly.FromDateTime(day));
            Columns.Clear();
            foreach (var column in BuildColumns(schedule, language))
            {
                Columns.Add(column);
            }
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            // The 10-minute access token expired: log in again.
            _session.Clear();
            _navigator.GoToLogin(Localizer.Instance["error.expired"]);
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

    private async Task LogoutAsync()
    {
        await _api.LogoutAsync();
        _session.Clear();
        _navigator.GoToLogin();
    }
}
