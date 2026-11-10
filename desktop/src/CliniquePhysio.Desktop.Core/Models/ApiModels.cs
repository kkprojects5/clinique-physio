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

/// <summary>A patient found by the front desk (B-FRD-02): enough to recognize the caller.</summary>
public sealed class PatientFound
{
    public Guid Id { get; set; }
    public string FirstName { get; set; } = "";
    public string LastName { get; set; } = "";
    public DateOnly DateOfBirth { get; set; }
    public string Phone { get; set; } = "";

    public string FullName => $"{FirstName} {LastName}";

    /// <summary>"Marie Gagnon — 1985-03-14 — 514-555-0001", to tell two homonyms apart.</summary>
    public string Display => $"{FullName} — {DateOfBirth:yyyy-MM-dd} — {Phone}";
}

/// <summary>A service of GET /services, with the therapists who provide it.</summary>
public sealed class ServiceInfo
{
    public Guid Id { get; set; }
    public string NameFr { get; set; } = "";
    public string NameEn { get; set; } = "";
    public int DurationMin { get; set; }
    public bool IsInitialEvaluation { get; set; }
    public List<Guid> TherapistIds { get; set; } = new();
}

/// <summary>A therapist of GET /therapists (public information only).</summary>
public sealed class TherapistInfo
{
    public Guid Id { get; set; }
    public string FirstName { get; set; } = "";
    public string LastName { get; set; } = "";

    public string FullName => $"{FirstName} {LastName}";
}

/// <summary>A free time of GET /availability.</summary>
public sealed class FreeSlot
{
    public Guid TherapistId { get; set; }
    public DateTimeOffset Start { get; set; }
    public DateTimeOffset End { get; set; }

    /// <summary>Start in Montréal time with its offset, e.g. "2026-11-02T10:00:00-05:00".</summary>
    public string StartLocal { get; set; } = "";
}

/// <summary>Answer of a cancellation: was the online deposit refunded (more than 24 h before)?</summary>
public sealed class CancelResult
{
    public bool DepositRefunded { get; set; }
}
