using System.Collections.ObjectModel;
using System.Globalization;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>A service in the list, with its name in the current language.</summary>
public sealed record ServiceChoice(Guid Id, string Name, IReadOnlyList<Guid> TherapistIds);

/// <summary>A therapist in the list. Id empty: "first available".</summary>
public sealed record TherapistChoice(Guid? Id, string Name);

/// <summary>A free time in the list: "10:00 — Anne Lefebvre".</summary>
public sealed record SlotChoice(FreeSlot Slot, string Label);

/// <summary>
/// Booking by phone (B-FRD-02): find the caller, choose a service, a therapist (or the first
/// available), a day and a free time, then book. The appointment is confirmed at once and paid
/// at the clinic. With an existing appointment, the same screen moves it to another time.
/// The server checks every rule again (free time, initial evaluation first, 60 days ahead).
/// </summary>
public sealed class PhoneBookingViewModel : ObservableObject
{
    private readonly IApiClient _api;
    private readonly Session _session;
    private readonly INavigator _navigator;
    private readonly DateTime _returnDay;
    private readonly List<TherapistInfo> _team = new();
    private string _searchText = "";
    private PatientFound? _selectedPatient;
    private ServiceChoice? _selectedService;
    private TherapistChoice? _selectedTherapist;
    private DateTime? _date;
    private SlotChoice? _selectedSlot;
    private string? _error;
    private string? _searchMessage;
    private string? _slotsMessage;
    private bool _isBusy;

    public PhoneBookingViewModel(
        IApiClient api, Session session, INavigator navigator, DateTime day, AppointmentItem? moving = null)
    {
        _api = api;
        _session = session;
        _navigator = navigator;
        _returnDay = day.Date;
        _date = day.Date;
        Moving = moving;
        LoadCommand = new AsyncRelayCommand(LoadAsync);
        SearchCommand = new AsyncRelayCommand(SearchAsync);
        FindSlotsCommand = new AsyncRelayCommand(FindSlotsAsync);
        BookCommand = new AsyncRelayCommand(BookAsync);
        BackCommand = new RelayCommand(() => _navigator.GoToSchedule(_returnDay));
    }

    /// <summary>The appointment being moved, or null for a new booking.</summary>
    public AppointmentItem? Moving { get; }

    public bool IsMoving => Moving is not null;

    public bool IsNewBooking => Moving is null;

    /// <summary>"Move Marie Gagnon's appointment (10:00–10:30)" or "Book by phone".</summary>
    public string Heading => Moving is null
        ? Localizer.Instance["booking.title"]
        : string.Format(
            CultureInfo.CurrentCulture, Localizer.Instance["booking.moveTitle"], Moving.PatientName, Moving.TimeRange);

    public ObservableCollection<PatientFound> Patients { get; } = new();

    public ObservableCollection<ServiceChoice> Services { get; } = new();

    public ObservableCollection<TherapistChoice> Therapists { get; } = new();

    public ObservableCollection<SlotChoice> Slots { get; } = new();

    public string SearchText
    {
        get => _searchText;
        set => SetProperty(ref _searchText, value);
    }

    public PatientFound? SelectedPatient
    {
        get => _selectedPatient;
        set => SetProperty(ref _selectedPatient, value);
    }

    /// <summary>Choosing a service lists only the therapists who provide it.</summary>
    public ServiceChoice? SelectedService
    {
        get => _selectedService;
        set
        {
            if (SetProperty(ref _selectedService, value))
            {
                FillTherapists();
                ClearSlots();
            }
        }
    }

    public TherapistChoice? SelectedTherapist
    {
        get => _selectedTherapist;
        set
        {
            if (SetProperty(ref _selectedTherapist, value))
            {
                ClearSlots();
            }
        }
    }

    public DateTime? Date
    {
        get => _date;
        set
        {
            if (SetProperty(ref _date, value?.Date))
            {
                ClearSlots();
            }
        }
    }

    public SlotChoice? SelectedSlot
    {
        get => _selectedSlot;
        set => SetProperty(ref _selectedSlot, value);
    }

    public string? Error
    {
        get => _error;
        private set => SetProperty(ref _error, value);
    }

    /// <summary>"No patient found" under the search box.</summary>
    public string? SearchMessage
    {
        get => _searchMessage;
        private set => SetProperty(ref _searchMessage, value);
    }

    /// <summary>"No free time this day" under the list of times.</summary>
    public string? SlotsMessage
    {
        get => _slotsMessage;
        private set => SetProperty(ref _slotsMessage, value);
    }

    public bool IsBusy
    {
        get => _isBusy;
        private set => SetProperty(ref _isBusy, value);
    }

    public IAsyncRelayCommand LoadCommand { get; }

    public IAsyncRelayCommand SearchCommand { get; }

    public IAsyncRelayCommand FindSlotsCommand { get; }

    public IAsyncRelayCommand BookCommand { get; }

    public IRelayCommand BackCommand { get; }

    /// <summary>"10:00 — Anne Lefebvre": the time in Montréal time and who gives it.</summary>
    public static string SlotLabel(FreeSlot slot, IEnumerable<TherapistInfo> team)
    {
        var start = DateTimeOffset.Parse(slot.StartLocal, CultureInfo.InvariantCulture);
        var name = team.FirstOrDefault(t => t.Id == slot.TherapistId)?.FullName ?? "";
        return $"{start:HH\\:mm} — {name}";
    }

    /// <summary>Loads the services and the team (once, when the screen opens).</summary>
    private async Task LoadAsync()
    {
        await RunAsync(async () =>
        {
            var services = await _api.GetServicesAsync();
            var team = await _api.GetTherapistsAsync();
            _team.Clear();
            _team.AddRange(team);
            var english = Localizer.Instance.Language == "en";
            Services.Clear();
            foreach (var s in services)
            {
                Services.Add(new ServiceChoice(s.Id, english ? s.NameEn : s.NameFr, s.TherapistIds));
            }

            if (Moving is AppointmentItem moving)
            {
                // A move keeps the service; the same therapist is proposed first.
                SelectedService = Services.FirstOrDefault(s => s.Id == moving.ServiceId);
                SelectedTherapist = Therapists.FirstOrDefault(t => t.Id == moving.TherapistId) ?? SelectedTherapist;
            }
        });
    }

    private async Task SearchAsync()
    {
        var text = SearchText.Trim();
        SearchMessage = null;
        if (text.Length < 2)
        {
            SearchMessage = Localizer.Instance["booking.searchTooShort"];
            return;
        }

        await RunAsync(async () =>
        {
            var found = await _api.SearchPatientsAsync(text);
            Patients.Clear();
            foreach (var p in found)
            {
                Patients.Add(p);
            }

            SelectedPatient = Patients.Count == 1 ? Patients[0] : null;
            SearchMessage = Patients.Count == 0 ? Localizer.Instance["booking.noPatient"] : null;
        });
    }

    private async Task FindSlotsAsync()
    {
        var service = SelectedService;
        if (service is null || Date is not DateTime day)
        {
            Error = Localizer.Instance["booking.chooseServiceAndDay"];
            return;
        }

        await RunAsync(() => LoadSlotsAsync(service.Id, SelectedTherapist?.Id, day));
    }

    private async Task LoadSlotsAsync(Guid serviceId, Guid? therapistId, DateTime day)
    {
        var slots = await _api.GetFreeSlotsAsync(serviceId, therapistId, DateOnly.FromDateTime(day));
        ClearSlots();
        foreach (var slot in slots.OrderBy(s => s.Start))
        {
            Slots.Add(new SlotChoice(slot, SlotLabel(slot, _team)));
        }

        SlotsMessage = Slots.Count == 0 ? Localizer.Instance["booking.noSlot"] : null;
    }

    private async Task BookAsync()
    {
        var l = Localizer.Instance;
        if (Moving is null && SelectedPatient is null)
        {
            Error = l["booking.choosePatient"];
            return;
        }

        if (SelectedService is null || SelectedSlot is null)
        {
            Error = l["booking.chooseSlot"];
            return;
        }

        var slot = SelectedSlot.Slot;
        var label = SelectedSlot.Label;
        var service = SelectedService;
        var moving = Moving;
        var start = DateTimeOffset.Parse(slot.StartLocal, CultureInfo.InvariantCulture);
        Error = null;
        IsBusy = true;
        try
        {
            string done;
            if (moving is not null)
            {
                await _api.RescheduleByPhoneAsync(moving.Id, slot.Start, slot.TherapistId);
                done = string.Format(CultureInfo.CurrentCulture, l["booking.moved"], moving.PatientName, label);
            }
            else
            {
                var patient = SelectedPatient!;
                await _api.BookByPhoneAsync(patient.Id, service.Id, SelectedTherapist?.Id, slot.Start);
                done = string.Format(CultureInfo.CurrentCulture, l["booking.booked"], patient.FullName, label);
            }

            _navigator.GoToSchedule(start.Date, done);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
            _session.Clear();
            _navigator.GoToLogin(l["error.expired"]);
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Conflict)
        {
            // Taken in the meantime (or a first visit must be an evaluation): show the times again.
            Error = l["booking.refused"];
            await ReloadSlotsQuietlyAsync(service.Id);
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

    private async Task ReloadSlotsQuietlyAsync(Guid serviceId)
    {
        if (Date is not DateTime day)
        {
            return;
        }

        try
        {
            await LoadSlotsAsync(serviceId, SelectedTherapist?.Id, day);
        }
        catch (ApiException)
        {
            ClearSlots(); // the refusal message already explains what to do
        }
    }

    private void FillTherapists()
    {
        Therapists.Clear();
        var service = SelectedService;
        if (service is null)
        {
            SelectedTherapist = null;
            return;
        }

        var first = new TherapistChoice(null, Localizer.Instance["booking.firstAvailable"]);
        Therapists.Add(first);
        foreach (var t in _team.Where(t => service.TherapistIds.Contains(t.Id)))
        {
            Therapists.Add(new TherapistChoice(t.Id, t.FullName));
        }

        SelectedTherapist = first;
    }

    private void ClearSlots()
    {
        Slots.Clear();
        SelectedSlot = null;
        SlotsMessage = null;
    }

    /// <summary>Runs an API call with the busy bar and turns failures into messages.</summary>
    private async Task RunAsync(Func<Task> work)
    {
        Error = null;
        IsBusy = true;
        try
        {
            await work();
        }
        catch (ApiException error) when (error.Kind == ApiErrorKind.Unauthorized)
        {
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
}
