using System.Globalization;
using System.Net;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;
using Xunit;

namespace CliniquePhysio.Desktop.Tests;

// Front desk: booking by phone (B-FRD-02), check-in and no-show (B-FRD-03).

public class FrontDeskApiClientTests
{
    private static (ApiClient Api, FakeHttpHandler Handler) Make(Func<HttpRequestMessage, HttpResponseMessage> respond)
    {
        var handler = new FakeHttpHandler(respond);
        var http = new HttpClient(handler) { BaseAddress = new Uri("https://api.test/") };
        return (new ApiClient(http, new Session()), handler);
    }

    [Fact]
    public async Task Patient_search_escapes_the_text_and_reads_the_date_of_birth()
    {
        var (api, handler) = Make(_ => FakeHttpHandler.Json(new[]
        {
            new { id = Guid.NewGuid(), first_name = "Mei", last_name = "Boucher", date_of_birth = "1990-04-02", phone = "514-555-0024" },
        }));

        var found = await api.SearchPatientsAsync("Mei Boucher");

        var patient = Assert.Single(found);
        Assert.Equal(new DateOnly(1990, 4, 2), patient.DateOfBirth);
        Assert.Equal("Mei Boucher — 1990-04-02 — 514-555-0024", patient.Display);
        var (request, _) = handler.Calls.Single();
        Assert.Equal(HttpMethod.Get, request.Method);
        Assert.Equal("/api/v1/desk/patients?q=Mei%20Boucher", request.RequestUri!.PathAndQuery);
    }

    [Fact]
    public async Task Free_slots_ask_one_day_and_the_therapist_only_when_chosen()
    {
        var (api, handler) = Make(_ => FakeHttpHandler.Json(Array.Empty<object>()));
        var service = Guid.NewGuid();
        var therapist = Guid.NewGuid();

        await api.GetFreeSlotsAsync(service, null, new DateOnly(2026, 11, 12));
        await api.GetFreeSlotsAsync(service, therapist, new DateOnly(2026, 11, 12));

        var first = handler.Calls[0].Request.RequestUri!.PathAndQuery;
        var second = handler.Calls[1].Request.RequestUri!.PathAndQuery;
        Assert.Equal($"/api/v1/availability?service_id={service}&date_from=2026-11-12&date_to=2026-11-12", first);
        Assert.EndsWith($"&therapist_id={therapist}", second);
    }

    [Fact]
    public async Task Phone_booking_sends_the_patient_service_and_time_in_snake_case()
    {
        var (api, handler) = Make(_ => FakeHttpHandler.Json(new { id = Guid.NewGuid(), status = "confirmed" }, HttpStatusCode.Created));
        var patient = Guid.NewGuid();
        var service = Guid.NewGuid();
        var start = new DateTimeOffset(2026, 11, 12, 15, 0, 0, TimeSpan.Zero);

        var booked = await api.BookByPhoneAsync(patient, service, null, start);

        Assert.Equal("confirmed", booked.Status);
        var (request, body) = handler.Calls.Single();
        Assert.Equal(HttpMethod.Post, request.Method);
        Assert.Equal("/api/v1/desk/appointments", request.RequestUri!.PathAndQuery);
        Assert.Contains($"\"patient_id\":\"{patient}\"", body);
        Assert.Contains($"\"service_id\":\"{service}\"", body);
        Assert.Contains("\"therapist_id\":null", body);
        Assert.Contains("\"start\":\"2026-11-12T15:00:00+00:00\"", body);
    }

    [Fact]
    public async Task Desk_actions_post_to_the_appointment_and_cancel_reads_the_refund()
    {
        var id = Guid.NewGuid();
        var (api, handler) = Make(request => request.RequestUri!.AbsolutePath.EndsWith("/cancel")
            ? FakeHttpHandler.Json(new { deposit_refunded = true })
            : FakeHttpHandler.Json(new { id, status = "checked_in" }));

        await api.CheckInAsync(id);
        await api.MarkNoShowAsync(id);
        var cancelled = await api.CancelByPhoneAsync(id);
        await api.RescheduleByPhoneAsync(id, DateTimeOffset.UnixEpoch, null);

        Assert.True(cancelled.DepositRefunded);
        Assert.Equal(
            new[] { "check-in", "no-show", "cancel", "reschedule" }
                .Select(action => $"/api/v1/desk/appointments/{id}/{action}"),
            handler.Calls.Select(c => c.Request.RequestUri!.AbsolutePath));
        Assert.All(handler.Calls, c => Assert.Equal(HttpMethod.Post, c.Request.Method));
    }

    [Theory]
    [InlineData(409, ApiErrorKind.Conflict)]
    [InlineData(404, ApiErrorKind.NotFound)]
    [InlineData(422, ApiErrorKind.Validation)]
    public async Task Refusals_become_clear_error_kinds(int status, ApiErrorKind kind)
    {
        var (api, _) = Make(_ => FakeHttpHandler.Json(new { detail = "refused" }, (HttpStatusCode)status));

        var error = await Assert.ThrowsAsync<ApiException>(() => api.CheckInAsync(Guid.NewGuid()));

        Assert.Equal(kind, error.Kind);
    }
}

public class ScheduleActionTests
{
    private static readonly Guid Anne = Guid.NewGuid();
    private static readonly DateTime Day = new(2026, 11, 12);

    private static DeskAppointment Appointment(string status) => new()
    {
        Id = Guid.NewGuid(),
        TherapistId = Anne,
        Start = DateTimeOffset.Parse("2026-11-12T15:00:00Z", CultureInfo.InvariantCulture),
        End = DateTimeOffset.Parse("2026-11-12T15:30:00Z", CultureInfo.InvariantCulture),
        StartLocal = "2026-11-12T10:00:00-05:00",
        Status = status,
        Service = new ServiceRef { Id = Guid.NewGuid(), NameFr = "Suivi", NameEn = "Follow-up" },
        Patient = new PatientRef { Id = Guid.NewGuid(), FirstName = "Marie", LastName = "Gagnon", Phone = "514-555-0001" },
    };

    private static DaySchedule Schedule(params DeskAppointment[] appointments) => new()
    {
        Date = DateOnly.FromDateTime(Day),
        Therapists = new() { new TherapistRef { Id = Anne, FirstName = "Anne", LastName = "Lefebvre" } },
        Appointments = appointments.ToList(),
    };

    private static string Text(string key, params object[] values) =>
        string.Format(CultureInfo.CurrentCulture, Localizer.Instance[key], values);

    private static async Task<(ScheduleViewModel Vm, FakeApi Api, FakeNavigator Nav, FakeDialogs Dialogs, AppointmentItem Item)>
        Loaded(string status = "confirmed")
    {
        var appointment = Appointment(status);
        var api = new FakeApi { Schedule = _ => Task.FromResult(Schedule(appointment)) };
        var nav = new FakeNavigator();
        var dialogs = new FakeDialogs();
        var vm = new ScheduleViewModel(api, new Session(), nav, Day, dialogs: dialogs);
        await vm.LoadCommand.ExecuteAsync(null);
        return (vm, api, nav, dialogs, vm.Columns[0].Appointments[0]);
    }

    [Fact]
    public void Cards_carry_the_ids_and_only_confirmed_appointments_offer_actions()
    {
        var confirmed = Appointment("confirmed");
        var arrived = Appointment("checked_in");

        var items = ScheduleViewModel.BuildColumns(Schedule(confirmed, arrived), "fr")[0].Appointments;

        var first = items.Single(i => i.Id == confirmed.Id);
        Assert.Equal(confirmed.Patient.Id, first.PatientId);
        Assert.Equal(confirmed.Service.Id, first.ServiceId);
        Assert.Equal(Anne, first.TherapistId);
        Assert.True(first.IsConfirmed);
        Assert.False(items.Single(i => i.Id == arrived.Id).IsConfirmed);
    }

    [Fact]
    public async Task Check_in_sends_the_appointment_reloads_the_day_and_says_it()
    {
        var (vm, api, _, dialogs, item) = await Loaded();

        await vm.CheckInCommand.ExecuteAsync(item);

        Assert.Equal(new[] { $"check-in {item.Id}" }, api.Actions);
        Assert.Equal(2, api.ScheduleCalls); // the new status is shown
        Assert.Equal(Text("schedule.checkedIn", "Marie Gagnon"), vm.Info);
        Assert.Null(vm.Error);
        Assert.Empty(dialogs.Questions); // arriving needs no confirmation
    }

    [Fact]
    public async Task Refused_check_in_explains_the_rule_and_shows_no_success()
    {
        var (vm, api, _, _, item) = await Loaded();
        api.CheckIn = _ => throw new ApiException(ApiErrorKind.Conflict, 409);

        await vm.CheckInCommand.ExecuteAsync(item);

        Assert.Equal(Localizer.Instance["schedule.checkInRefused"], vm.Error);
        Assert.Null(vm.Info);
    }

    [Fact]
    public async Task Refused_no_show_explains_the_15_minute_rule()
    {
        var (vm, api, _, dialogs, item) = await Loaded();
        api.NoShow = _ => throw new ApiException(ApiErrorKind.Conflict, 409);

        await vm.NoShowCommand.ExecuteAsync(item);

        Assert.Single(dialogs.Questions);
        Assert.Equal(Localizer.Instance["schedule.noShowRefused"], vm.Error);
    }

    [Fact]
    public async Task No_show_asks_first_then_marks_and_says_the_deposit_is_kept()
    {
        var (vm, api, _, dialogs, item) = await Loaded();

        await vm.NoShowCommand.ExecuteAsync(item);

        Assert.Equal(Text("schedule.confirmNoShow", "Marie Gagnon", "10:00–10:30"), dialogs.Questions.Single());
        Assert.Equal(new[] { $"no-show {item.Id}" }, api.Actions);
        Assert.Equal(Text("schedule.markedNoShow", "Marie Gagnon"), vm.Info);
    }

    [Fact]
    public async Task Answering_no_to_the_cancel_question_sends_nothing()
    {
        var (vm, api, _, dialogs, item) = await Loaded();
        dialogs.Answer = false;

        await vm.CancelCommand.ExecuteAsync(item);

        Assert.Single(dialogs.Questions);
        Assert.Empty(api.Actions);
        Assert.Null(vm.Info);
    }

    [Theory]
    [InlineData(true, "schedule.cancelledRefunded")]
    [InlineData(false, "schedule.cancelledKept")]
    public async Task Cancel_says_whether_the_deposit_is_refunded(bool refunded, string key)
    {
        var (vm, api, _, _, item) = await Loaded();
        api.Cancel = _ => Task.FromResult(new CancelResult { DepositRefunded = refunded });

        await vm.CancelCommand.ExecuteAsync(item);

        Assert.Equal(new[] { $"cancel {item.Id}" }, api.Actions);
        Assert.Equal(Text(key, "Marie Gagnon"), vm.Info);
    }

    [Fact]
    public async Task Expired_session_during_an_action_goes_back_to_login()
    {
        var (vm, api, nav, _, item) = await Loaded();
        api.CheckIn = _ => throw new ApiException(ApiErrorKind.Unauthorized, 401);

        await vm.CheckInCommand.ExecuteAsync(item);

        Assert.Equal("login", nav.Screen);
        Assert.Equal(Localizer.Instance["error.expired"], nav.LoginMessage);
    }

    [Fact]
    public async Task New_booking_and_move_open_the_booking_screen_for_the_day_shown()
    {
        var (vm, _, nav, _, item) = await Loaded();

        vm.NewBookingCommand.Execute(null);
        Assert.Equal("booking", nav.Screen);
        Assert.Equal(Day, nav.BookingDay);
        Assert.Null(nav.Moving);

        vm.MoveCommand.Execute(item);
        Assert.Same(item, nav.Moving);
    }

    [Fact]
    public async Task A_message_from_the_booking_screen_is_shown_until_the_day_changes()
    {
        var api = new FakeApi();
        var vm = new ScheduleViewModel(api, new Session(), new FakeNavigator(), Day, Day.AddDays(3), info: "Booked");

        await vm.LoadCommand.ExecuteAsync(null);
        Assert.Equal(Day.AddDays(3), vm.SelectedDate);
        Assert.Equal("Booked", vm.Info);

        vm.SelectedDate = Day.AddDays(4);
        Assert.Null(vm.Info);
    }
}

public class PhoneBookingViewModelTests
{
    private static readonly Guid Anne = Guid.NewGuid();
    private static readonly Guid Sophie = Guid.NewGuid();
    private static readonly Guid Marc = Guid.NewGuid();
    private static readonly Guid FollowUp = Guid.NewGuid();
    private static readonly DateTime Day = new(2026, 11, 12);

    private static readonly PatientFound Mei = new()
    {
        Id = Guid.NewGuid(),
        FirstName = "Mei",
        LastName = "Boucher",
        DateOfBirth = new DateOnly(1990, 4, 2),
        Phone = "514-555-0024",
    };

    private static FreeSlot Slot(Guid therapist, string startLocal)
    {
        var start = DateTimeOffset.Parse(startLocal, CultureInfo.InvariantCulture);
        return new FreeSlot
        {
            TherapistId = therapist,
            Start = start.ToUniversalTime(),
            End = start.AddMinutes(30).ToUniversalTime(),
            StartLocal = startLocal,
        };
    }

    private static FakeApi Api() => new()
    {
        Services = () => Task.FromResult(new List<ServiceInfo>
        {
            new() { Id = FollowUp, NameFr = "Suivi 30 min", NameEn = "Follow-up 30 min", TherapistIds = new() { Anne, Sophie } },
            new() { Id = Guid.NewGuid(), NameFr = "Évaluation initiale", NameEn = "Initial evaluation", TherapistIds = new() { Marc } },
        }),
        Team = () => Task.FromResult(new List<TherapistInfo>
        {
            new() { Id = Anne, FirstName = "Anne", LastName = "Lefebvre" },
            new() { Id = Sophie, FirstName = "Sophie", LastName = "Nguyen" },
            new() { Id = Marc, FirstName = "Marc", LastName = "Tremblay" },
        }),
        Search = _ => Task.FromResult(new List<PatientFound> { Mei }),
        Slots = (_, _, _) => Task.FromResult(new List<FreeSlot>
        {
            Slot(Sophie, "2026-11-12T11:00:00-05:00"),
            Slot(Anne, "2026-11-12T10:00:00-05:00"),
        }),
    };

    private static async Task<(PhoneBookingViewModel Vm, FakeApi Api, FakeNavigator Nav)> Ready(
        AppointmentItem? moving = null)
    {
        var api = Api();
        var nav = new FakeNavigator();
        var vm = new PhoneBookingViewModel(api, new Session(), nav, Day, moving);
        await vm.LoadCommand.ExecuteAsync(null);
        return (vm, api, nav);
    }

    [Fact]
    public async Task Choosing_a_service_lists_only_its_therapists_after_first_available()
    {
        var (vm, _, _) = await Ready();

        Assert.Equal(new[] { "Suivi 30 min", "Évaluation initiale" }, vm.Services.Select(s => s.Name));
        vm.SelectedService = vm.Services[0];

        Assert.Equal(
            new[] { Localizer.Instance["booking.firstAvailable"], "Anne Lefebvre", "Sophie Nguyen" },
            vm.Therapists.Select(t => t.Name));
        Assert.Null(vm.SelectedTherapist!.Id); // first available by default
    }

    [Fact]
    public async Task Search_needs_two_characters_and_selects_a_single_result()
    {
        var (vm, api, _) = await Ready();
        var searched = new List<string>();
        api.Search = text => { searched.Add(text); return Task.FromResult(new List<PatientFound> { Mei }); };

        vm.SearchText = " M ";
        await vm.SearchCommand.ExecuteAsync(null);
        Assert.Empty(searched);
        Assert.Equal(Localizer.Instance["booking.searchTooShort"], vm.SearchMessage);

        vm.SearchText = " 514-555-0024 ";
        await vm.SearchCommand.ExecuteAsync(null);
        Assert.Equal(new[] { "514-555-0024" }, searched);
        Assert.Same(Mei, vm.SelectedPatient);
        Assert.Null(vm.SearchMessage);
    }

    [Fact]
    public async Task No_patient_found_says_so()
    {
        var (vm, api, _) = await Ready();
        api.Search = _ => Task.FromResult(new List<PatientFound>());

        vm.SearchText = "Zzz";
        await vm.SearchCommand.ExecuteAsync(null);

        Assert.Empty(vm.Patients);
        Assert.Null(vm.SelectedPatient);
        Assert.Equal(Localizer.Instance["booking.noPatient"], vm.SearchMessage);
    }

    [Fact]
    public async Task Free_times_are_asked_for_the_day_and_shown_in_montreal_time_in_order()
    {
        var (vm, api, _) = await Ready();
        (Guid Service, Guid? Therapist, DateOnly Day)? asked = null;
        var slots = api.Slots;
        api.Slots = (s, t, d) => { asked = (s, t, d); return slots(s, t, d); };
        vm.SelectedService = vm.Services[0];

        await vm.FindSlotsCommand.ExecuteAsync(null);

        Assert.NotNull(asked);
        Assert.Equal(FollowUp, asked.Value.Service);
        Assert.Null(asked.Value.Therapist); // first available
        Assert.Equal(new DateOnly(2026, 11, 12), asked.Value.Day);
        Assert.Equal(new[] { "10:00 — Anne Lefebvre", "11:00 — Sophie Nguyen" }, vm.Slots.Select(s => s.Label));
        Assert.Null(vm.SlotsMessage);
    }

    [Fact]
    public async Task A_day_without_free_time_says_so_and_changing_the_day_clears_the_times()
    {
        var (vm, api, _) = await Ready();
        vm.SelectedService = vm.Services[0];
        await vm.FindSlotsCommand.ExecuteAsync(null);
        Assert.Equal(2, vm.Slots.Count);

        vm.Date = Day.AddDays(1);
        Assert.Empty(vm.Slots);

        api.Slots = (_, _, _) => Task.FromResult(new List<FreeSlot>());
        await vm.FindSlotsCommand.ExecuteAsync(null);
        Assert.Equal(Localizer.Instance["booking.noSlot"], vm.SlotsMessage);
    }

    [Fact]
    public async Task Booking_without_a_patient_or_a_time_is_stopped_before_the_api()
    {
        var (vm, api, _) = await Ready();
        vm.SelectedService = vm.Services[0];

        await vm.BookCommand.ExecuteAsync(null);
        Assert.Equal(Localizer.Instance["booking.choosePatient"], vm.Error);

        vm.SelectedPatient = Mei;
        await vm.BookCommand.ExecuteAsync(null);
        Assert.Equal(Localizer.Instance["booking.chooseSlot"], vm.Error);
        Assert.Empty(api.Actions);
    }

    [Fact]
    public async Task Booking_sends_the_chosen_time_and_returns_to_that_day_with_a_message()
    {
        var (vm, api, nav) = await Ready();
        (Guid Patient, Guid Service, Guid? Therapist, DateTimeOffset Start)? sent = null;
        api.Book = (p, s, t, start) => { sent = (p, s, t, start); return Task.FromResult(new DeskAppointment()); };
        vm.SelectedPatient = Mei;
        vm.SelectedService = vm.Services[0];
        await vm.FindSlotsCommand.ExecuteAsync(null);
        vm.SelectedSlot = vm.Slots[0];

        await vm.BookCommand.ExecuteAsync(null);

        Assert.NotNull(sent);
        Assert.Equal(Mei.Id, sent.Value.Patient);
        Assert.Equal(FollowUp, sent.Value.Service);
        Assert.Null(sent.Value.Therapist);
        Assert.Equal(vm.Slots[0].Slot.Start, sent.Value.Start);
        Assert.Equal("schedule", nav.Screen);
        Assert.Equal(Day, nav.ScheduleDay);
        Assert.Contains("Mei Boucher", nav.ScheduleInfo);
        Assert.Contains("10:00 — Anne Lefebvre", nav.ScheduleInfo);
    }

    [Fact]
    public async Task A_time_taken_meanwhile_is_refused_and_the_free_times_are_reloaded()
    {
        var (vm, api, nav) = await Ready();
        api.Book = (_, _, _, _) => throw new ApiException(ApiErrorKind.Conflict, 409);
        vm.SelectedPatient = Mei;
        vm.SelectedService = vm.Services[0];
        await vm.FindSlotsCommand.ExecuteAsync(null);
        vm.SelectedSlot = vm.Slots[0];
        var reloads = 0;
        api.Slots = (_, _, _) =>
        {
            reloads++;
            return Task.FromResult(new List<FreeSlot> { Slot(Sophie, "2026-11-12T11:00:00-05:00") });
        };

        await vm.BookCommand.ExecuteAsync(null);

        Assert.Equal(Localizer.Instance["booking.refused"], vm.Error);
        Assert.Equal(1, reloads);
        Assert.Equal(new[] { "11:00 — Sophie Nguyen" }, vm.Slots.Select(s => s.Label));
        Assert.Null(vm.SelectedSlot);
        Assert.Null(nav.Screen); // stays on the booking screen
    }

    [Fact]
    public async Task Moving_keeps_the_service_proposes_the_same_therapist_and_reschedules()
    {
        var moving = new AppointmentItem(
            Guid.NewGuid(), "09:00–09:30", "Marie Gagnon", "514-555-0001", "Suivi 30 min", "confirmed", "Confirmé")
        {
            ServiceId = FollowUp,
            TherapistId = Sophie,
        };
        var (vm, api, nav) = await Ready(moving);
        (Guid Id, DateTimeOffset Start, Guid? Therapist)? sent = null;
        api.Reschedule = (id, start, t) => { sent = (id, start, t); return Task.FromResult(new DeskAppointment()); };

        Assert.True(vm.IsMoving);
        Assert.Equal(FollowUp, vm.SelectedService!.Id);
        Assert.Equal(Sophie, vm.SelectedTherapist!.Id);
        Assert.Contains("Marie Gagnon", vm.Heading);

        await vm.FindSlotsCommand.ExecuteAsync(null);
        vm.SelectedSlot = vm.Slots[1]; // 11:00 with Sophie
        await vm.BookCommand.ExecuteAsync(null);

        Assert.NotNull(sent);
        Assert.Equal(moving.Id, sent.Value.Id);
        Assert.Equal(vm.Slots[1].Slot.Start, sent.Value.Start);
        Assert.Equal(Sophie, sent.Value.Therapist);
        Assert.DoesNotContain(api.Actions, a => a.StartsWith("book", StringComparison.Ordinal));
        Assert.Equal("schedule", nav.Screen);
    }

    [Fact]
    public async Task Expired_session_during_search_goes_back_to_login()
    {
        var (vm, api, nav) = await Ready();
        api.Search = _ => throw new ApiException(ApiErrorKind.Unauthorized, 401);

        vm.SearchText = "Mei";
        await vm.SearchCommand.ExecuteAsync(null);

        Assert.Equal("login", nav.Screen);
    }

    [Fact]
    public void Back_returns_to_the_schedule_of_the_same_day()
    {
        var nav = new FakeNavigator();
        var vm = new PhoneBookingViewModel(Api(), new Session(), nav, Day);

        vm.BackCommand.Execute(null);

        Assert.Equal("schedule", nav.Screen);
        Assert.Equal(Day, nav.ScheduleDay);
    }
}
