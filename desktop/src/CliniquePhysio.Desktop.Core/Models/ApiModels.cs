namespace CliniquePhysio.Desktop.Core.Models;

// Shapes of the API's JSON answers. Property names are converted from snake_case
// (e.g. "access_token" -> AccessToken) by the JSON options in ApiClient.

/// <summary>Answer of POST /auth/login: tokens (patients) or an MFA challenge (staff).</summary>
public sealed class LoginResponse
{
    public string? AccessToken { get; set; }
    public bool MfaRequired { get; set; }
    public bool MfaSetupRequired { get; set; }
    public string? MfaToken { get; set; }
    public int ExpiresIn { get; set; }
}

public sealed class MfaSetupResponse
{
    public string Secret { get; set; } = "";
    public string OtpauthUri { get; set; } = "";
}

public sealed class TokenResponse
{
    public string AccessToken { get; set; } = "";
    public int ExpiresIn { get; set; }
}

public sealed class TherapistRef
{
    public Guid Id { get; set; }
    public string FirstName { get; set; } = "";
    public string LastName { get; set; } = "";

    public string FullName => $"{FirstName} {LastName}";
}

/// <summary>What the front desk sees about a patient: no clinical data (B-CLN-05).</summary>
public sealed class PatientRef
{
    public Guid Id { get; set; }
    public string FirstName { get; set; } = "";
    public string LastName { get; set; } = "";
    public string Phone { get; set; } = "";
}

public sealed class ServiceRef
{
    public Guid Id { get; set; }
    public string NameFr { get; set; } = "";
    public string NameEn { get; set; } = "";
    public int DurationMin { get; set; }
}

public sealed class DeskAppointment
{
    public Guid Id { get; set; }
    public Guid TherapistId { get; set; }
    public DateTimeOffset Start { get; set; }
    public DateTimeOffset End { get; set; }

    /// <summary>Start in Montréal time with its offset, e.g. "2026-11-02T10:00:00-05:00".</summary>
    public string StartLocal { get; set; } = "";
    public string Status { get; set; } = "";
    public ServiceRef Service { get; set; } = new();
    public PatientRef Patient { get; set; } = new();
}

public sealed class DaySchedule
{
    public DateOnly Date { get; set; }
    public List<TherapistRef> Therapists { get; set; } = new();
    public List<DeskAppointment> Appointments { get; set; } = new();
}
