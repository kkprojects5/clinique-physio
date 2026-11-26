namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>A check-in or no-show clicked while the API could not be reached (challenge B-C5).</summary>
/// <param name="Id">Made here, to match the server's answer to the action.</param>
/// <param name="AppointmentId">The appointment.</param>
/// <param name="PatientName">Shown in the conflict message only; never sent, never saved.</param>
/// <param name="Action">"check_in" or "no_show".</param>
/// <param name="SeenStatus">The status shown on screen when the desk clicked.</param>
/// <param name="DoneAt">When the desk clicked.</param>
public sealed record PendingAction(
    Guid Id, Guid AppointmentId, string PatientName, string Action, string SeenStatus, DateTimeOffset DoneAt);

/// <summary>
/// The desk's offline actions, waiting to be sent to POST /desk/sync. Kept in memory only, for
/// the life of the app: no patient information is ever written to the computer's disk. Closing
/// the app with actions waiting loses them, so the app asks first.
/// </summary>
public sealed class OfflineQueue
{
    private readonly List<PendingAction> _items = new();

    public IReadOnlyList<PendingAction> Items => _items;

    public int Count => _items.Count;

    public bool Contains(Guid appointmentId) => _items.Any(a => a.AppointmentId == appointmentId);

    public void Add(PendingAction action) => _items.Add(action);

    public void Remove(IEnumerable<Guid> ids)
    {
        var done = ids.ToHashSet();
        _items.RemoveAll(a => done.Contains(a.Id));
    }
}
