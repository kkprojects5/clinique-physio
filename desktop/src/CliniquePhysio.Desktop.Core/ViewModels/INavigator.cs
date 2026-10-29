namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Moves between screens. MainViewModel implements it; tests use a fake.</summary>
public interface INavigator
{
    void GoToLogin(string? message = null);

    void GoToMfa(string mfaToken, bool setupRequired, string email);

    void GoToSchedule();
}
