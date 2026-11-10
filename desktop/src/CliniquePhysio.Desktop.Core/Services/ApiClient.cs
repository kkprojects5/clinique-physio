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

    public Task<List<PatientFound>> SearchPatientsAsync(string query, CancellationToken ct = default) =>
        GetAsync<List<PatientFound>>($"api/v1/desk/patients?q={Uri.EscapeDataString(query)}", ct);

    public Task<List<ServiceInfo>> GetServicesAsync(CancellationToken ct = default) =>
        GetAsync<List<ServiceInfo>>("api/v1/services", ct);

    public Task<List<TherapistInfo>> GetTherapistsAsync(CancellationToken ct = default) =>
        GetAsync<List<TherapistInfo>>("api/v1/therapists", ct);

    public Task<List<FreeSlot>> GetFreeSlotsAsync(
        Guid serviceId, Guid? therapistId, DateOnly day, CancellationToken ct = default)
    {
        var date = day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        var path = $"api/v1/availability?service_id={serviceId}&date_from={date}&date_to={date}";
        if (therapistId is Guid therapist)
        {
            path += $"&therapist_id={therapist}";
        }

        return GetAsync<List<FreeSlot>>(path, ct);
    }

    public Task<DeskAppointment> BookByPhoneAsync(
        Guid patientId, Guid serviceId, Guid? therapistId, DateTimeOffset start, CancellationToken ct = default) =>
        PostAsync<DeskAppointment>(
            "api/v1/desk/appointments",
            new { patient_id = patientId, service_id = serviceId, therapist_id = therapistId, start },
            ct);

    public Task<DeskAppointment> RescheduleByPhoneAsync(
        Guid appointmentId, DateTimeOffset start, Guid? therapistId, CancellationToken ct = default) =>
        PostAsync<DeskAppointment>(
            $"api/v1/desk/appointments/{appointmentId}/reschedule",
            new { start, therapist_id = therapistId },
            ct);

    public Task<CancelResult> CancelByPhoneAsync(Guid appointmentId, CancellationToken ct = default) =>
        PostAsync<CancelResult>($"api/v1/desk/appointments/{appointmentId}/cancel", new { }, ct);

    public Task<DeskAppointment> CheckInAsync(Guid appointmentId, CancellationToken ct = default) =>
        PostAsync<DeskAppointment>($"api/v1/desk/appointments/{appointmentId}/check-in", new { }, ct);

    public Task<DeskAppointment> MarkNoShowAsync(Guid appointmentId, CancellationToken ct = default) =>
        PostAsync<DeskAppointment>($"api/v1/desk/appointments/{appointmentId}/no-show", new { }, ct);

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

    private Task<T> GetAsync<T>(string path, CancellationToken ct) =>
        SendAsync<T>(new HttpRequestMessage(HttpMethod.Get, path), ct);

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
