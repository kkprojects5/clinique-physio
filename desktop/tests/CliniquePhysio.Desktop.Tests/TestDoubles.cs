using System.Net;
using System.Text;
using System.Text.Json;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;
using Xunit;

// The Localizer is shared by all tests: run them one at a time so language changes don't collide.
[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace CliniquePhysio.Desktop.Tests;

/// <summary>A fake network: answers each request with a prepared response, and records it.</summary>
public sealed class FakeHttpHandler : HttpMessageHandler
{
    private readonly Func<HttpRequestMessage, HttpResponseMessage> _respond;

    public FakeHttpHandler(Func<HttpRequestMessage, HttpResponseMessage> respond) => _respond = respond;

    public List<(HttpRequestMessage Request, string Body)> Calls { get; } = new();

    public static HttpResponseMessage Json(object body, HttpStatusCode status = HttpStatusCode.OK) =>
        new(status)
        {
            Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json"),
        };

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        var body = request.Content is null ? "" : await request.Content.ReadAsStringAsync(ct);
        Calls.Add((request, body));
        return _respond(request);
    }
}

/// <summary>A fake API for view model tests: each method can be replaced.</summary>
public sealed class FakeApi : IApiClient
{
    public Func<string, string, Task<LoginResponse>> Login { get; set; } =
        (_, _) => Task.FromResult(new LoginResponse());

    public Func<string, Task<MfaSetupResponse>> Setup { get; set; } =
        _ => Task.FromResult(new MfaSetupResponse { Secret = "SECRET", OtpauthUri = "otpauth://totp/x" });

    public Func<string, string, Task<TokenResponse>> Verify { get; set; } =
        (_, _) => Task.FromResult(new TokenResponse { AccessToken = "access-token", ExpiresIn = 600 });

    public Func<DateOnly, Task<DaySchedule>> Schedule { get; set; } = _ => Task.FromResult(new DaySchedule());

    public Func<string, Task<List<PatientFound>>> Search { get; set; } =
        _ => Task.FromResult(new List<PatientFound>());

    public Func<Task<List<ServiceInfo>>> Services { get; set; } = () => Task.FromResult(new List<ServiceInfo>());

    public Func<Task<List<TherapistInfo>>> Team { get; set; } = () => Task.FromResult(new List<TherapistInfo>());

    public Func<Guid, Guid?, DateOnly, Task<List<FreeSlot>>> Slots { get; set; } =
        (_, _, _) => Task.FromResult(new List<FreeSlot>());

    public Func<Guid, Guid, Guid?, DateTimeOffset, Task<DeskAppointment>> Book { get; set; } =
        (_, _, _, _) => Task.FromResult(new DeskAppointment());

    public Func<Guid, DateTimeOffset, Guid?, Task<DeskAppointment>> Reschedule { get; set; } =
        (_, _, _) => Task.FromResult(new DeskAppointment());

    public Func<Guid, Task<CancelResult>> Cancel { get; set; } = _ => Task.FromResult(new CancelResult());

    public Func<Guid, Task<DeskAppointment>> CheckIn { get; set; } = _ => Task.FromResult(new DeskAppointment());

    public Func<Guid, Task<DeskAppointment>> NoShow { get; set; } = _ => Task.FromResult(new DeskAppointment());

    /// <summary>Every desk action, in order, e.g. "check-in 3f2a…" (to check what was sent).</summary>
    public List<string> Actions { get; } = new();

    public int ScheduleCalls { get; private set; }

    public int LoginCalls { get; private set; }

    public int SetupCalls { get; private set; }

    public int VerifyCalls { get; private set; }

    public int LogoutCalls { get; private set; }

    public Task<LoginResponse> LoginAsync(string email, string password, CancellationToken ct = default)
    {
        LoginCalls++;
        return Login(email, password);
    }

    public Task<MfaSetupResponse> SetupMfaAsync(string mfaToken, CancellationToken ct = default)
    {
        SetupCalls++;
        return Setup(mfaToken);
    }

    public Task<TokenResponse> VerifyMfaAsync(string mfaToken, string code, CancellationToken ct = default)
    {
        VerifyCalls++;
        return Verify(mfaToken, code);
    }

    public Task<DaySchedule> GetDayScheduleAsync(DateOnly day, CancellationToken ct = default)
    {
        ScheduleCalls++;
        return Schedule(day);
    }

    public Task<List<PatientFound>> SearchPatientsAsync(string query, CancellationToken ct = default) => Search(query);

    public Task<List<ServiceInfo>> GetServicesAsync(CancellationToken ct = default) => Services();

    public Task<List<TherapistInfo>> GetTherapistsAsync(CancellationToken ct = default) => Team();

    public Task<List<FreeSlot>> GetFreeSlotsAsync(
        Guid serviceId, Guid? therapistId, DateOnly day, CancellationToken ct = default) =>
        Slots(serviceId, therapistId, day);

    public Task<DeskAppointment> BookByPhoneAsync(
        Guid patientId, Guid serviceId, Guid? therapistId, DateTimeOffset start, CancellationToken ct = default)
    {
        Actions.Add($"book {patientId}");
        return Book(patientId, serviceId, therapistId, start);
    }

    public Task<DeskAppointment> RescheduleByPhoneAsync(
        Guid appointmentId, DateTimeOffset start, Guid? therapistId, CancellationToken ct = default)
    {
        Actions.Add($"reschedule {appointmentId}");
        return Reschedule(appointmentId, start, therapistId);
    }

    public Task<CancelResult> CancelByPhoneAsync(Guid appointmentId, CancellationToken ct = default)
    {
        Actions.Add($"cancel {appointmentId}");
        return Cancel(appointmentId);
    }

    public Task<DeskAppointment> CheckInAsync(Guid appointmentId, CancellationToken ct = default)
    {
        Actions.Add($"check-in {appointmentId}");
        return CheckIn(appointmentId);
    }

    public Task<DeskAppointment> MarkNoShowAsync(Guid appointmentId, CancellationToken ct = default)
    {
        Actions.Add($"no-show {appointmentId}");
        return NoShow(appointmentId);
    }

    public Task LogoutAsync(CancellationToken ct = default)
    {
        LogoutCalls++;
        return Task.CompletedTask;
    }

    public Task<bool> IsOnlineAsync(CancellationToken ct = default) => Task.FromResult(true);
}

/// <summary>Records which screen the app asked to show.</summary>
public sealed class FakeNavigator : INavigator
{
    public string? Screen { get; private set; }

    public string? LoginMessage { get; private set; }

    public string? MfaToken { get; private set; }

    public bool MfaSetupRequired { get; private set; }

    public void GoToLogin(string? message = null)
    {
        Screen = "login";
        LoginMessage = message;
    }

    public void GoToMfa(string mfaToken, bool setupRequired, string email)
    {
        Screen = "mfa";
        MfaToken = mfaToken;
        MfaSetupRequired = setupRequired;
    }

    public DateTime? ScheduleDay { get; private set; }

    public string? ScheduleInfo { get; private set; }

    public DateTime? BookingDay { get; private set; }

    public AppointmentItem? Moving { get; private set; }

    public void GoToSchedule(DateTime? day = null, string? info = null)
    {
        Screen = "schedule";
        ScheduleDay = day;
        ScheduleInfo = info;
    }

    public void GoToBooking(DateTime day, AppointmentItem? moving = null)
    {
        Screen = "booking";
        BookingDay = day;
        Moving = moving;
    }
}

/// <summary>Answers the confirmation questions with a prepared answer, and records them.</summary>
public sealed class FakeDialogs : IDialogService
{
    public bool Answer { get; set; } = true;

    public List<string> Questions { get; } = new();

    public bool Confirm(string message)
    {
        Questions.Add(message);
        return Answer;
    }
}
