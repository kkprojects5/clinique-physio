namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Moves between screens. MainViewModel implements it; tests use a fake.</summary>
public interface INavigator
{
    void GoToLogin(string? message = null);

    void GoToMfa(string mfaToken, bool setupRequired, string email);

    /// <summary>The day schedule. Without a day: today. The info message is shown at the top.</summary>
    void GoToSchedule(DateTime? day = null, string? info = null);

    /// <summary>Phone booking for that day; with an appointment, moves it instead (B-FRD-02).</summary>
    void GoToBooking(DateTime day, AppointmentItem? moving = null);
}
