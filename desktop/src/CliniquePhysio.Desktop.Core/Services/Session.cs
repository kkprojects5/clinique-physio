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
