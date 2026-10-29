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

    public Task<DaySchedule> GetDayScheduleAsync(DateOnly day, CancellationToken ct = default) => Schedule(day);

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

    public void GoToSchedule() => Screen = "schedule";
}
