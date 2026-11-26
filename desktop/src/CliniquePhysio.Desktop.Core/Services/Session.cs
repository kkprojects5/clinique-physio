namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>
/// The logged-in staff member. The access token is kept in memory only: it is never
/// written to disk, so closing the app ends the session.
/// </summary>
public sealed class Session
{
    public string? AccessToken { get; private set; }

    public string? Email { get; private set; }

    public bool IsActive => AccessToken is not null;

    /// <summary>
    /// Check-ins and no-shows waiting for the connection (B-C5). Not cleared when the session
    /// ends: if the 10-minute token expired while offline, they are sent after the next login.
    /// </summary>
    public OfflineQueue Pending { get; } = new();

    public void Start(string accessToken, string email)
    {
        AccessToken = accessToken;
        Email = email;
    }

    public void Clear()
    {
        AccessToken = null;
        Email = null;
    }
}
