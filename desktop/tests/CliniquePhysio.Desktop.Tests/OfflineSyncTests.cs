using System.Globalization;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;
using Xunit;

namespace CliniquePhysio.Desktop.Tests;

// Challenge B-C5: the desk checks a patient in while offline; the patient cancels online.
// The action waits in memory, is sent when the connection returns, and a conflict is shown.

public class OfflineSyncTests
{
    private static readonly DateTime Day = new(2026, 11, 12);
    private static readonly Guid Anne = Guid.NewGuid();

    private static DeskAppointment Appointment(Guid id, string status) => new()
    {
        Id = id,
        TherapistId = Anne,
        Start = DateTimeOffset.Parse("2026-11-12T15:00:00Z", CultureInfo.InvariantCulture),
        End = DateTimeOffset.Parse("2026-11-12T15:30:00Z", CultureInfo.InvariantCulture),
        StartLocal = "2026-11-12T10:00:00-05:00",
        Status = status,
        Service = new ServiceRef { Id = Guid.NewGuid(), NameFr = "Suivi", NameEn = "Follow-up" },
        Patient = new PatientRef { Id = Guid.NewGuid(), FirstName = "Marie", LastName = "Gagnon", Phone = "514-555-0001" },
    };

    private static DaySchedule Schedule(DeskAppointment appointment) => new()
    {
        Date = DateOnly.FromDateTime(Day),
        Therapists = new() { new TherapistRef { Id = Anne, FirstName = "Anne", LastName = "Lefebvre" } },
        Appointments = new() { appointment },
    };

    private static string Text(string key, params object[] values) =>
        string.Format(CultureInfo.CurrentCulture, Localizer.Instance[key], values);

    /// <summary>A loaded day with one confirmed appointment; the server's status can be changed.</summary>
    private sealed class World
    {
        public Guid Id { get; } = Guid.NewGuid();
        public string ServerStatus { get; set; } = "confirmed";
        public bool Online { get; set; } = true;
        public Session Session { get; } = new();
        public FakeApi Api { get; }
        public FakeDialogs Dialogs { get; } = new();
        public ScheduleViewModel Vm { get; }

        public World()
        {
            Api = new FakeApi();
            Api.Schedule = _ => Online
                ? Task.FromResult(Schedule(Appointment(Id, ServerStatus)))
                : throw new ApiException(ApiErrorKind.Offline, 0);
            Api.CheckIn = _ => Online
                ? Task.FromResult(new DeskAppointment())
                : throw new ApiException(ApiErrorKind.Offline, 0);
            Vm = new ScheduleViewModel(Api, Session, new FakeNavigator(), Day, dialogs: Dialogs);
        }

        public AppointmentItem Card => Vm.Columns[0].Appointments[0];
    }

    [Fact]
    public async Task Offline_check_in_is_kept_in_memory_and_shown_as_waiting()
    {
        var w = new World();
        await w.Vm.LoadCommand.ExecuteAsync(null);
        w.Online = false;

        await w.Vm.CheckInCommand.ExecuteAsync(w.Card);

        var pending = Assert.Single(w.Session.Pending.Items);
        Assert.Equal(("check_in", "confirmed", w.Id), (pending.Action, pending.SeenStatus, pending.AppointmentId));
        Assert.True(w.Vm.HasPending);
        Assert.Equal(Text("schedule.pending", 1), w.Vm.PendingText);
        Assert.Equal(Text("schedule.savedOffline", "Marie Gagnon"), w.Vm.Info);
        Assert.True(w.Card.IsPendingSync);
        Assert.False(w.Card.IsConfirmed); // no second click on Check-in
        Assert.Equal(Localizer.Instance["status.pending_sync"], w.Card.StatusLabel);
    }

    [Fact]
    public async Task Patient_cancelled_online_the_conflict_is_reported_and_the_server_wins()
    {
        var w = new World();
        await w.Vm.LoadCommand.ExecuteAsync(null);
        w.Online = false;
        await w.Vm.CheckInCommand.ExecuteAsync(w.Card);

        // Meanwhile the patient cancels online; then the connection returns.
        w.ServerStatus = "cancelled_by_patient";
        w.Online = true;
        w.Api.Sync = actions => Task.FromResult(actions.Select(a => new SyncResult
        {
            Id = a.Id, AppointmentId = a.AppointmentId, Result = "conflict", Status = "cancelled_by_patient",
        }).ToList());
        await w.Vm.SyncCommand.ExecuteAsync(null);

        Assert.Empty(w.Session.Pending.Items);
        Assert.False(w.Vm.HasPending);
        var sent = Assert.Single(Assert.Single(w.Api.Synced));
        Assert.Equal("confirmed", sent.SeenStatus);
        Assert.Equal(
            Text("schedule.syncConflict", "Marie Gagnon", Localizer.Instance["status.cancelled_by_patient"]),
            w.Vm.Error);
        Assert.Equal("cancelled_by_patient", w.Card.Status); // the day shows the server's state
        Assert.False(w.Card.IsPendingSync);
    }

    [Fact]
    public async Task Waiting_actions_are_sent_before_the_day_is_reloaded()
    {
        var w = new World();
        await w.Vm.LoadCommand.ExecuteAsync(null);
        w.Online = false;
        await w.Vm.CheckInCommand.ExecuteAsync(w.Card);
        w.Online = true;
        w.ServerStatus = "checked_in";

        await w.Vm.LoadCommand.ExecuteAsync(null);

        Assert.Single(w.Api.Synced);
        Assert.Empty(w.Session.Pending.Items);
        Assert.Equal(Text("schedule.synced", 1), w.Vm.Info);
        Assert.Null(w.Vm.Error);
        Assert.Equal("checked_in", w.Card.Status);
    }

    [Fact]
    public async Task Still_offline_keeps_the_actions_and_says_so()
    {
        var w = new World();
        await w.Vm.LoadCommand.ExecuteAsync(null);
        w.Online = false;
        await w.Vm.CheckInCommand.ExecuteAsync(w.Card);
        w.Api.Sync = _ => throw new ApiException(ApiErrorKind.Offline, 0);

        await w.Vm.SyncCommand.ExecuteAsync(null);

        Assert.Single(w.Session.Pending.Items);
        Assert.Equal(Localizer.Instance["schedule.stillOffline"], w.Vm.Error);
    }

    [Fact]
    public async Task Logging_out_with_waiting_actions_asks_first()
    {
        var w = new World();
        await w.Vm.LoadCommand.ExecuteAsync(null);
        w.Online = false;
        await w.Vm.CheckInCommand.ExecuteAsync(w.Card);
        w.Dialogs.Answer = false;

        await w.Vm.LogoutCommand.ExecuteAsync(null);

        Assert.Equal(Text("schedule.confirmLogoutPending", 1), Assert.Single(w.Dialogs.Questions));
        Assert.Single(w.Session.Pending.Items); // nothing lost
    }

    [Fact]
    public void Describe_sync_counts_successes_and_lists_problems_by_patient()
    {
        var a = new PendingAction(Guid.NewGuid(), Guid.NewGuid(), "Marie Gagnon", "check_in", "confirmed", DateTimeOffset.Now);
        var b = new PendingAction(Guid.NewGuid(), Guid.NewGuid(), "Paul Martin", "no_show", "confirmed", DateTimeOffset.Now);
        var results = new List<SyncResult>
        {
            new() { Id = a.Id, Result = "applied", Status = "checked_in" },
            new() { Id = b.Id, Result = "refused", Status = "confirmed" },
        };

        var (info, problems) = ScheduleViewModel.DescribeSync(new[] { a, b }, results);

        Assert.Equal(Text("schedule.synced", 1), info);
        Assert.Equal(Text("schedule.syncRefused", "Paul Martin", Localizer.Instance["status.confirmed"]), problems);
    }

    [Fact]
    public async Task Only_ids_status_and_time_are_sent_never_the_patient_name()
    {
        var handler = new FakeHttpHandler(_ => FakeHttpHandler.Json(Array.Empty<object>()));
        var api = new ApiClient(new HttpClient(handler) { BaseAddress = new Uri("https://api.test/") }, new Session());
        var action = new PendingAction(
            Guid.NewGuid(), Guid.NewGuid(), "Marie Gagnon", "check_in", "confirmed",
            new DateTimeOffset(2026, 11, 12, 10, 2, 0, TimeSpan.FromHours(-5)));

        await api.SyncAsync(new[] { action });

        var (request, body) = handler.Calls.Single();
        Assert.Equal("/api/v1/desk/sync", request.RequestUri!.AbsolutePath);
        Assert.Contains($"\"appointment_id\":\"{action.AppointmentId}\"", body);
        Assert.Contains("\"seen_status\":\"confirmed\"", body);
        Assert.Contains("\"done_at\":\"2026-11-12T10:02:00-05:00\"", body);
        Assert.DoesNotContain("Marie", body);
    }
}
