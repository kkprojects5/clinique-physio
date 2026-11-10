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
    Guid Id, string TimeRange, string PatientName, string Phone, string ServiceName, string Status, string StatusLabel)
{
    public Guid PatientId { get; init; }

    public Guid ServiceId { get; init; }

    public Guid TherapistId { get; init; }

    /// <summary>Check-in, no-show, move and cancel are offered only for a confirmed appointment.</summary>
    public bool IsConfirmed => Status == "confirmed";
}

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
    private readonly IDialogService? _dialogs;
    private DateTime? _selectedDate;
    private string _title = "";
    private string? _error;
    private string? _info;
    private bool _isBusy;

    /// <param name="api">The API.</param>
    /// <param name="session">The logged-in staff member.</param>
    /// <param name="navigator">Screen changes.</param>
    /// <param name="today">Today's date (the "Today" button).</param>
    /// <param name="day">The day to show first; today if empty.</param>
    /// <param name="dialogs">Confirmation before cancel and no-show; without it, actions are not confirmed.</param>
    /// <param name="info">A message to show at the top (e.g. "appointment booked").</param>
    public ScheduleViewModel(
        IApiClient api,
        Session session,
        INavigator navigator,
        DateTime today,
        DateTime? day = null,
        IDialogService? dialogs = null,
        string? info = null)
    {
        _api = api;
        _session = session;
        _navigator = navigator;
        _dialogs = dialogs;
        _selectedDate = (day ?? today).Date;
        _info = info;
        LoadCommand = new AsyncRelayCommand(LoadAsync);
        PreviousCommand = new AsyncRelayCommand(() => MoveAsync(-1));
        NextCommand = new AsyncRelayCommand(() => MoveAsync(1));
        TodayCommand = new AsyncRelayCommand(() => GoToAsync(today.Date));
        LogoutCommand = new AsyncRelayCommand(LogoutAsync);
        NewBookingCommand = new RelayCommand(() => _navigator.GoToBooking(SelectedDate ?? today.Date));
        MoveCommand = new RelayCommand<AppointmentItem>(item =>
        {
            if (item is not null)
            {
                _navigator.GoToBooking(SelectedDate ?? today.Date, item);
            }
        });
        CheckInCommand = new AsyncRelayCommand<AppointmentItem>(CheckInAsync);
        NoShowCommand = new AsyncRelayCommand<AppointmentItem>(NoShowAsync);
        CancelCommand = new AsyncRelayCommand<AppointmentItem>(CancelAsync);
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
                Info = null; // the message was about the day shown before
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

    /// <summary>Result of the last action (e.g. "Marie Gagnon has arrived").</summary>
    public string? Info
    {
        get => _info;
        private set => SetProperty(ref _info, value);
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

    /// <summary>Book for a patient on the phone (B-FRD-02).</summary>
    public IRelayCommand NewBookingCommand { get; }

    public IRelayCommand<AppointmentItem> MoveCommand { get; }

    /// <summary>The patient has arrived (B-FRD-03).</summary>
    public IAsyncRelayCommand<AppointmentItem> CheckInCommand { get; }

    /// <summary>The patient did not come; the deposit is kept (B-FRD-03).</summary>
    public IAsyncRelayCommand<AppointmentItem> NoShowCommand { get; }

    /// <summary>Cancel for a patient who calls; deposit refunded only more than 24 hours before.</summary>
    public IAsyncRelayCommand<AppointmentItem> CancelCommand { get; }

    /// <summary>Builds the columns from the API answer. Pure function: easy to test.</summary>
    public static IReadOnlyList<TherapistColumn> BuildColumns(DaySchedule schedule, string language)
    {
        return schedule.Therapists
            .Select(t => new TherapistColumn(
                t.FullName,
                schedule.Appointments
                    .Where(a => a.TherapistId == t.Id)
                    .OrderBy(a => a.Start)
                    .Select(a => ToItem(a, language))
                    .ToList()))
            .ToList();
    }

    private static AppointmentItem ToItem(DeskAppointment a, string language)
    {
        var item = new AppointmentItem(
            a.Id,
            TimeRange(a),
            $"{a.Patient.FirstName} {a.Patient.LastName}",
            a.Patient.Phone,
            language == "en" ? a.Service.NameEn : a.Service.NameFr,
            a.Status,
            Localizer.Instance[$"status.{a.Status}"]);
        return item with { PatientId = a.Patient.Id, ServiceId = a.Service.Id, TherapistId = a.TherapistId };
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
        Info = null;
        if (SelectedDate == day.Date)
        {
            return LoadAsync();
        }

        SelectedDate = day; // the setter loads the day
        return Task.CompletedTask;
    }

    private Task CheckInAsync(AppointmentItem? item) =>
        RunAsync(item, null, "schedule.checkInRefused", async a =>
        {
            await _api.CheckInAsync(a.Id);
            return Format("schedule.checkedIn", a.PatientName);
        });

    private Task NoShowAsync(AppointmentItem? item) =>
        RunAsync(item, "schedule.confirmNoShow", "schedule.noShowRefused", async a =>
        {
            await _api.MarkNoShowAsync(a.Id);
            return Format("schedule.markedNoShow", a.PatientName);
        });

    private Task CancelAsync(AppointmentItem? item) =>
        RunAsync(item, "schedule.confirmCancel", "schedule.cancelRefused", async a =>
        {
            var result = await _api.CancelByPhoneAsync(a.Id);
            return Format(result.DepositRefunded ? "schedule.cancelledRefunded" : "schedule.cancelledKept", a.PatientName);
        });

    /// <summary>Asks for confirmation if needed, runs the action, reloads the day and shows the result.</summary>
    private async Task RunAsync(
        AppointmentItem? item, string? confirmKey, string conflictKey, Func<AppointmentItem, Task<string>> action)
    {
        if (item is null)
        {
            return;
        }

        if (confirmKey is not null && _dialogs is not null
            && !_dialogs.Confirm(Format(confirmKey, item.PatientName, item.TimeRange)))
        {
            return;
        }

        Error = null;
        Info = null;
        IsBusy = true;
        string done;
        try
        {
            done = await action(item);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            _session.Clear();
            _navigator.GoToLogin(Localizer.Instance["error.expired"]);
            return;
        }
        catch (ApiException error)
        {
            Error = ErrorMessages.For(error, conflictKey);
            return;
        }
        finally
        {
            IsBusy = false;
        }

        await LoadAsync(); // show the new status
        if (Error is null)
        {
            Info = done;
        }
    }

    private static string Format(string key, params object[] values) =>
        string.Format(CultureInfo.CurrentCulture, Localizer.Instance[key], values);

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
