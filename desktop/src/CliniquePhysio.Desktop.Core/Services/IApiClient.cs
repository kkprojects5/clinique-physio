using CliniquePhysio.Desktop.Core.Models;

namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Everything the desktop app asks the API. An interface, so tests can use a fake.</summary>
public interface IApiClient
{
    Task<LoginResponse> LoginAsync(string email, string password, CancellationToken ct = default);

    Task<MfaSetupResponse> SetupMfaAsync(string mfaToken, CancellationToken ct = default);

    Task<TokenResponse> VerifyMfaAsync(string mfaToken, string code, CancellationToken ct = default);

    Task<DaySchedule> GetDayScheduleAsync(DateOnly day, CancellationToken ct = default);

    /// <summary>Find a patient by name, phone digits or date of birth (B-FRD-02).</summary>
    Task<List<PatientFound>> SearchPatientsAsync(string query, CancellationToken ct = default);

    Task<List<ServiceInfo>> GetServicesAsync(CancellationToken ct = default);

    Task<List<TherapistInfo>> GetTherapistsAsync(CancellationToken ct = default);

    /// <summary>Free times of one day. No therapist: first available across the team.</summary>
    Task<List<FreeSlot>> GetFreeSlotsAsync(Guid serviceId, Guid? therapistId, DateOnly day, CancellationToken ct = default);

    /// <summary>Book for a patient on the phone: confirmed at once, paid at the clinic.</summary>
    Task<DeskAppointment> BookByPhoneAsync(
        Guid patientId, Guid serviceId, Guid? therapistId, DateTimeOffset start, CancellationToken ct = default);

    Task<DeskAppointment> RescheduleByPhoneAsync(
        Guid appointmentId, DateTimeOffset start, Guid? therapistId, CancellationToken ct = default);

    Task<CancelResult> CancelByPhoneAsync(Guid appointmentId, CancellationToken ct = default);

    /// <summary>The patient has arrived (B-FRD-03).</summary>
    Task<DeskAppointment> CheckInAsync(Guid appointmentId, CancellationToken ct = default);

    /// <summary>The patient did not come (15 minutes after the start at the earliest).</summary>
    Task<DeskAppointment> MarkNoShowAsync(Guid appointmentId, CancellationToken ct = default);

    Task LogoutAsync(CancellationToken ct = default);

    Task<bool> IsOnlineAsync(CancellationToken ct = default);
}
