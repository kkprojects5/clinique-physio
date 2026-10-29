using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using CliniquePhysio.Desktop.Core.Models;

namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Calls the REST API over HTTPS. All business rules stay on the server.</summary>
public sealed class ApiClient : IApiClient
{
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    private readonly HttpClient _http;
    private readonly Session _session;

    public ApiClient(HttpClient http, Session session)
    {
        _http = http;
        _session = session;
    }

    /// <summary>Real client. The cookie container keeps the httpOnly refresh cookie.</summary>
    public static ApiClient Create(Uri baseUrl, Session session)
    {
        var handler = new HttpClientHandler { CookieContainer = new CookieContainer(), UseCookies = true };
        var http = new HttpClient(handler)
        {
            BaseAddress = baseUrl,
            Timeout = TimeSpan.FromSeconds(70), // the free host can take ~50 s to wake up
        };
        return new ApiClient(http, session);
    }

    public Task<LoginResponse> LoginAsync(string email, string password, CancellationToken ct = default) =>
        PostAsync<LoginResponse>("api/v1/auth/login", new { email, password }, ct);

    public Task<MfaSetupResponse> SetupMfaAsync(string mfaToken, CancellationToken ct = default) =>
        PostAsync<MfaSetupResponse>("api/v1/auth/mfa/setup", new { mfa_token = mfaToken }, ct);

    public Task<TokenResponse> VerifyMfaAsync(string mfaToken, string code, CancellationToken ct = default) =>
        PostAsync<TokenResponse>("api/v1/auth/mfa/verify", new { mfa_token = mfaToken, code }, ct);

    public Task<DaySchedule> GetDayScheduleAsync(DateOnly day, CancellationToken ct = default)
    {
        var date = day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        var request = new HttpRequestMessage(HttpMethod.Get, $"api/v1/desk/schedule?date={date}");
        return SendAsync<DaySchedule>(request, ct);
    }

    public async Task LogoutAsync(CancellationToken ct = default)
    {
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, "api/v1/auth/logout");
            using var response = await _http.SendAsync(request, ct);
        }
        catch (HttpRequestException)
        {
            // Offline: the local session is cleared anyway; the server token expires on its own.
        }
        catch (TaskCanceledException)
        {
        }
    }

    public async Task<bool> IsOnlineAsync(CancellationToken ct = default)
    {
        try
        {
            using var response = await _http.GetAsync("health", ct);
            return response.IsSuccessStatusCode;
        }
        catch (HttpRequestException)
        {
            return false;
        }
        catch (TaskCanceledException)
        {
            return false;
        }
    }

    private Task<T> PostAsync<T>(string path, object body, CancellationToken ct)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(body, options: Json),
        };
        return SendAsync<T>(request, ct);
    }

    private async Task<T> SendAsync<T>(HttpRequestMessage request, CancellationToken ct)
    {
        using (request)
        {
            if (_session.AccessToken is not null)
            {
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _session.AccessToken);
            }

            HttpResponseMessage response;
            try
            {
                response = await _http.SendAsync(request, ct);
            }
            catch (HttpRequestException)
            {
                throw new ApiException(ApiErrorKind.Offline, 0);
            }
            catch (TaskCanceledException) when (!ct.IsCancellationRequested)
            {
                throw new ApiException(ApiErrorKind.Offline, 0); // timeout
            }

            using (response)
            {
                if (!response.IsSuccessStatusCode)
                {
                    var status = (int)response.StatusCode;
                    throw new ApiException(ApiException.KindFor(status), status);
                }

                var result = await response.Content.ReadFromJsonAsync<T>(Json, ct);
                return result ?? throw new ApiException(ApiErrorKind.Other, (int)response.StatusCode);
            }
        }
    }
}
