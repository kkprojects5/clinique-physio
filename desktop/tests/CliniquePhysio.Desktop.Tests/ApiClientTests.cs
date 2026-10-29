using System.Net;
using CliniquePhysio.Desktop.Core.Services;
using Xunit;

namespace CliniquePhysio.Desktop.Tests;

public class ApiClientTests
{
    private static (ApiClient Api, FakeHttpHandler Handler, Session Session) Make(
        Func<HttpRequestMessage, HttpResponseMessage> respond)
    {
        var handler = new FakeHttpHandler(respond);
        var session = new Session();
        var http = new HttpClient(handler) { BaseAddress = new Uri("https://api.test/") };
        return (new ApiClient(http, session), handler, session);
    }

    [Fact]
    public async Task Staff_login_returns_an_mfa_challenge_read_from_snake_case_json()
    {
        var (api, handler, _) = Make(_ => FakeHttpHandler.Json(new
        {
            mfa_required = true,
            mfa_setup_required = false,
            mfa_token = "ticket",
            expires_in = 300,
        }));

        var result = await api.LoginAsync("accueil1@clinique.example.com", "secret-password");

        Assert.True(result.MfaRequired);
        Assert.Equal("ticket", result.MfaToken);
        Assert.Null(result.AccessToken);
        var (request, body) = handler.Calls.Single();
        Assert.Equal("https://api.test/api/v1/auth/login", request.RequestUri!.ToString());
        Assert.Contains("\"email\":\"accueil1@clinique.example.com\"", body);
    }

    [Fact]
    public async Task Mfa_verify_sends_the_ticket_and_code_in_snake_case()
    {
        var (api, handler, _) = Make(_ => FakeHttpHandler.Json(new { access_token = "tok", expires_in = 600 }));

        var tokens = await api.VerifyMfaAsync("ticket", "123456");

        Assert.Equal("tok", tokens.AccessToken);
        Assert.Contains("\"mfa_token\":\"ticket\"", handler.Calls.Single().Body);
        Assert.Contains("\"code\":\"123456\"", handler.Calls.Single().Body);
    }

    [Theory]
    [InlineData(HttpStatusCode.Unauthorized, ApiErrorKind.Unauthorized)]
    [InlineData(HttpStatusCode.Forbidden, ApiErrorKind.Forbidden)]
    [InlineData(HttpStatusCode.TooManyRequests, ApiErrorKind.TooManyRequests)]
    [InlineData(HttpStatusCode.ServiceUnavailable, ApiErrorKind.Server)]
    public async Task Http_errors_become_clear_error_kinds(HttpStatusCode status, ApiErrorKind expected)
    {
        var (api, _, _) = Make(_ => FakeHttpHandler.Json(new { detail = "x" }, status));

        var error = await Assert.ThrowsAsync<ApiException>(() => api.LoginAsync("a@b.c", "password"));

        Assert.Equal(expected, error.Kind);
    }

    [Fact]
    public async Task No_network_is_reported_as_offline()
    {
        var (api, _, _) = Make(_ => throw new HttpRequestException("no route"));

        var error = await Assert.ThrowsAsync<ApiException>(() => api.LoginAsync("a@b.c", "password"));

        Assert.Equal(ApiErrorKind.Offline, error.Kind);
    }

    [Fact]
    public async Task Day_schedule_sends_the_date_and_the_bearer_token()
    {
        var (api, handler, session) = Make(_ => FakeHttpHandler.Json(new
        {
            date = "2026-11-02",
            therapists = new[] { new { id = Guid.NewGuid(), first_name = "Anne", last_name = "Lefebvre" } },
            appointments = Array.Empty<object>(),
        }));
        session.Start("my-access-token", "accueil1@clinique.example.com");

        var schedule = await api.GetDayScheduleAsync(new DateOnly(2026, 11, 2));

        var request = handler.Calls.Single().Request;
        Assert.Equal("https://api.test/api/v1/desk/schedule?date=2026-11-02", request.RequestUri!.ToString());
        Assert.Equal("Bearer", request.Headers.Authorization!.Scheme);
        Assert.Equal("my-access-token", request.Headers.Authorization.Parameter);
        Assert.Equal(new DateOnly(2026, 11, 2), schedule.Date);
        Assert.Equal("Anne Lefebvre", schedule.Therapists.Single().FullName);
    }

    [Fact]
    public async Task No_token_is_sent_before_login()
    {
        var (api, handler, _) = Make(_ => FakeHttpHandler.Json(new { mfa_required = true, mfa_token = "t" }));

        await api.LoginAsync("a@b.c", "password");

        Assert.Null(handler.Calls.Single().Request.Headers.Authorization);
    }

    [Fact]
    public async Task Health_check_reports_offline_without_throwing()
    {
        var (api, _, _) = Make(_ => throw new HttpRequestException("down"));

        Assert.False(await api.IsOnlineAsync());
    }
}
