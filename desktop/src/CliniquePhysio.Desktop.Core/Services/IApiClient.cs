using CliniquePhysio.Desktop.Core.Models;

namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Everything the desktop app asks the API. An interface, so tests can use a fake.</summary>
public interface IApiClient
{
    Task<LoginResponse> LoginAsync(string email, string password, CancellationToken ct = default);

    Task<MfaSetupResponse> SetupMfaAsync(string mfaToken, CancellationToken ct = default);

    Task<TokenResponse> VerifyMfaAsync(string mfaToken, string code, CancellationToken ct = default);

    Task<DaySchedule> GetDayScheduleAsync(DateOnly day, CancellationToken ct = default);

    Task LogoutAsync(CancellationToken ct = default);

    Task<bool> IsOnlineAsync(CancellationToken ct = default);
}
