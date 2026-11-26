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

    /// <summary>A check-in or no-show was clicked offline and waits to be sent (B-C5).</summary>
    public bool IsPendingSync { get; init; }

    /// <summary>Check-in, no-show, move and cancel are offered only for a confirmed appointment.</summary>
    public bool IsConfirmed => Status == "confirmed" && !IsPendingSync;

    /// <summary>The patient came: the balance can be paid and a receipt printed (B-FRD-05).</summary>
    public bool HasCome => Status is "checked_in" or "completed";
}

/// <summary>A way to pay at the desk, as shown in the list.</summary>
public sealed record PaymentMethodOption(string Code, string Label);

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
    private PaymentMethodOption _paymentMethod;
    private DaySchedule? _shown;

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
        PayCommand = new AsyncRelayCommand<AppointmentItem>(PayAsync);
        ReceiptCommand = new AsyncRelayCommand<AppointmentItem>(ReceiptAsync);
        SyncCommand = new AsyncRelayCommand(() => SyncAsync(reload: true));
        PaymentMethods = new[] { "debit", "credit", "cash" }
            .Select(code => new PaymentMethodOption(code, Localizer.Instance[$"method.{code}"]))
            .ToList();
        _paymentMethod = PaymentMethods[0];
    }

    /// <summary>Cash, debit or credit (the clinic's own terminal; no card data reaches the app).</summary>
    public IReadOnlyList<PaymentMethodOption> PaymentMethods { get; }

    public PaymentMethodOption PaymentMethod
    {
        get => _paymentMethod;
        set => SetProperty(ref _paymentMethod, value ?? PaymentMethods[0]);
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

    /// <summary>The patient pays the balance at the desk (B-FRD-05). The server computes the amount.</summary>
    public IAsyncRelayCommand<AppointmentItem> PayCommand { get; }

    /// <summary>Open the receipt in the PDF reader, to print it (B-FRD-05, B-BKG-10).</summary>
    public IAsyncRelayCommand<AppointmentItem> ReceiptCommand { get; }

    /// <summary>Send the actions recorded offline now (also done before each reload).</summary>
    public IAsyncRelayCommand SyncCommand { get; }

    public bool HasPending => _session.Pending.Count > 0;

    /// <summary>"2 actions waiting to be sent (offline)."</summary>
    public string PendingText => Format("schedule.pending", _session.Pending.Count);

    /// <summary>"60,00 $" or "$60.00".</summary>
    public static string Money(int cents, string language) =>
        (cents / 100m).ToString("C", CultureInfo.GetCultureInfo(language == "en" ? "en-CA" : "fr-CA"));

    /// <summary>Builds the columns from the API answer. Pure function: easy to test.</summary>
    public static IReadOnlyList<TherapistColumn> BuildColumns(
        DaySchedule schedule, string language, OfflineQueue? pending = null)
    {
        return schedule.Therapists
            .Select(t => new TherapistColumn(
                t.FullName,
                schedule.Appointments
                    .Where(a => a.TherapistId == t.Id)
                    .OrderBy(a => a.Start)
                    .Select(a => ToItem(a, language, pending?.Contains(a.Id) == true))
                    .ToList()))
            .ToList();
    }

    private static AppointmentItem ToItem(DeskAppointment a, string language, bool pendingSync)
    {
        var item = new AppointmentItem(
            a.Id,
            TimeRange(a),
            $"{a.Patient.FirstName} {a.Patient.LastName}",
            a.Patient.Phone,
            language == "en" ? a.Service.NameEn : a.Service.NameFr,
            a.Status,
            Localizer.Instance[pendingSync ? "status.pending_sync" : $"status.{a.Status}"]);
        return item with
        {
            PatientId = a.Patient.Id,
            ServiceId = a.Service.Id,
            TherapistId = a.TherapistId,
            IsPendingSync = pendingSync,
        };
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
        }, offlineAction: "check_in");

    private Task NoShowAsync(AppointmentItem? item) =>
        RunAsync(item, "schedule.confirmNoShow", "schedule.noShowRefused", async a =>
        {
            await _api.MarkNoShowAsync(a.Id);
            return Format("schedule.markedNoShow", a.PatientName);
        }, offlineAction: "no_show");

    /// <summary>
    /// Offline (challenge B-C5): the check-in or no-show is kept in memory and shown as waiting.
    /// It is sent before the next reload or with "Send now". The server's state wins: if the
    /// appointment changed meanwhile (e.g. the patient cancelled online), the action is not
    /// applied and the desk sees the conflict.
    /// </summary>
    private void KeepOffline(AppointmentItem item, string action)
    {
        _session.Pending.Add(new PendingAction(
            Guid.NewGuid(), item.Id, item.PatientName, action, item.Status, DateTimeOffset.Now));
        if (_shown is not null)
        {
            ShowColumns(_shown);
        }

        Error = null;
        Info = Format("schedule.savedOffline", item.PatientName);
        OnPropertyChanged(nameof(HasPending));
        OnPropertyChanged(nameof(PendingText));
    }

    /// <summary>Sends the waiting actions. Returns false if the server still cannot be reached.</summary>
    private async Task<bool> SyncAsync(bool reload)
    {
        var waiting = _session.Pending.Items.ToList();
        if (waiting.Count == 0)
        {
            if (reload)
            {
                await LoadAsync();
            }

            return true;
        }

        Error = null;
        Info = null;
        IsBusy = true;
        List<SyncResult> results;
        try
        {
            results = await _api.SyncAsync(waiting);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            // The actions stay in memory and are sent after the next login.
            _session.Clear();
            _navigator.GoToLogin(Localizer.Instance["error.expired"]);
            return false;
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Offline)
        {
            Error = Localizer.Instance["schedule.stillOffline"];
            return false;
        }
        catch (ApiException error)
        {
            Error = ErrorMessages.For(error);
            return false;
        }
        finally
        {
            IsBusy = false;
        }

        _session.Pending.Remove(results.Select(r => r.Id));
        OnPropertyChanged(nameof(HasPending));
        OnPropertyChanged(nameof(PendingText));
        var messages = DescribeSync(waiting, results);
        if (reload)
        {
            await LoadAsync();
        }

        Info = messages.Info;
        Error = messages.Problems;
        return true;
    }

    /// <summary>What to tell the desk after a synchronization. Pure function: easy to test.</summary>
    public static (string? Info, string? Problems) DescribeSync(
        IReadOnlyList<PendingAction> sent, IReadOnlyList<SyncResult> results)
    {
        var names = sent.ToDictionary(a => a.Id, a => a.PatientName);
        var applied = results.Count(r => r.Result is "applied" or "already_done");
        var problems = results
            .Where(r => r.Result is "conflict" or "refused")
            .Select(r =>
            {
                var name = names.GetValueOrDefault(r.Id, "?");
                var status = r.Status is null ? "?" : Localizer.Instance[$"status.{r.Status}"];
                return r.Result == "conflict"
                    ? Format("schedule.syncConflict", name, status)
                    : Format("schedule.syncRefused", name, status);
            })
            .ToList();
        return (
            applied > 0 ? Format("schedule.synced", applied) : null,
            problems.Count > 0 ? string.Join(Environment.NewLine, problems) : null);
    }

    private Task CancelAsync(AppointmentItem? item) =>
        RunAsync(item, "schedule.confirmCancel", "schedule.cancelRefused", async a =>
        {
            var result = await _api.CancelByPhoneAsync(a.Id);
            return Format(result.DepositRefunded ? "schedule.cancelledRefunded" : "schedule.cancelledKept", a.PatientName);
        });

    private async Task PayAsync(AppointmentItem? item)
    {
        if (item is null)
        {
            return;
        }

        var method = PaymentMethod;
        Billing billing;
        try
        {
            billing = await _api.GetBillingAsync(item.Id);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            _session.Clear();
            _navigator.GoToLogin(Localizer.Instance["error.expired"]);
            return;
        }
        catch (ApiException error)
        {
            Info = null;
            Error = ErrorMessages.For(error);
            return;
        }

        var language = Localizer.Instance.Language;
        if (billing.DueCents == 0)
        {
            Error = null;
            Info = Format("schedule.nothingDue", item.PatientName);
            return;
        }

        var amount = Money(billing.DueCents, language);
        if (_dialogs is not null && !_dialogs.Confirm(Format("schedule.confirmPay", amount, method.Label, item.PatientName)))
        {
            return;
        }

        await RunAsync(item, null, "schedule.payRefused", async a =>
        {
            await _api.RecordPaymentAsync(a.Id, method.Code);
            return Format("schedule.paid", amount, method.Label, a.PatientName);
        });
    }

    private async Task ReceiptAsync(AppointmentItem? item)
    {
        if (item is null)
        {
            return;
        }

        Error = null;
        Info = null;
        IsBusy = true;
        try
        {
            var pdf = await _api.GetReceiptAsync(item.Id, Localizer.Instance.Language);
            var number = "R-" + item.Id.ToString("N")[..8].ToUpperInvariant();
            _dialogs?.OpenPdf(pdf, $"{number}.pdf");
            Info = Format("schedule.receiptOpened", item.PatientName);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            _session.Clear();
            _navigator.GoToLogin(Localizer.Instance["error.expired"]);
        }
        catch (ApiException error)
        {
            Error = ErrorMessages.For(error, "schedule.receiptRefused");
        }
        finally
        {
            IsBusy = false;
        }
    }

    /// <summary>Asks for confirmation if needed, runs the action, reloads the day and shows the result.</summary>
    private async Task RunAsync(
        AppointmentItem? item,
        string? confirmKey,
        string conflictKey,
        Func<AppointmentItem, Task<string>> action,
        string? offlineAction = null)
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
        catch (ApiException error) when (error.Kind == ApiErrorKind.Offline && offlineAction is not null)
        {
            KeepOffline(item, offlineAction);
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

        // Offline actions first, so the day shows the server's real state afterwards (B-C5).
        string? syncInfo = null, syncProblems = null;
        if (_session.Pending.Count > 0)
        {
            if (!await SyncAsync(reload: false))
            {
                return; // still offline (message shown) or logged out
            }

            (syncInfo, syncProblems) = (Info, Error);
        }

        var language = Localizer.Instance.Language;
        Title = day.ToString("dddd d MMMM yyyy", CultureInfo.GetCultureInfo(language == "en" ? "en-CA" : "fr-CA"));
        Error = null;
        IsBusy = true;
        try
        {
            var schedule = await _api.GetDayScheduleAsync(DateOnly.FromDateTime(day));
            ShowColumns(schedule);
            Info = syncInfo ?? Info;
            Error = syncProblems;
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

    private void ShowColumns(DaySchedule schedule)
    {
        _shown = schedule;
        Columns.Clear();
        foreach (var column in BuildColumns(schedule, Localizer.Instance.Language, _session.Pending))
        {
            Columns.Add(column);
        }
    }

    private async Task LogoutAsync()
    {
        if (_session.Pending.Count > 0 && _dialogs is not null
            && !_dialogs.Confirm(Format("schedule.confirmLogoutPending", _session.Pending.Count)))
        {
            return;
        }

        await _api.LogoutAsync();
        _session.Clear();
        _navigator.GoToLogin();
    }
}
