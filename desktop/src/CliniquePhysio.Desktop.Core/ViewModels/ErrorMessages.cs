using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Turns API failures into clear messages for the user (never technical details).</summary>
public static class ErrorMessages
{
    /// <param name="error">The failure.</param>
    /// <param name="conflictKey">Text to show for a 409 refusal in this screen (e.g. "slot taken").</param>
    public static string For(ApiException error, string? conflictKey = null)
    {
        var l = Localizer.Instance;
        return error.Kind switch
        {
            ApiErrorKind.Conflict when conflictKey is not null => l[conflictKey],
            ApiErrorKind.Conflict => l["error.conflict"],
            ApiErrorKind.NotFound => l["error.notFound"],
            ApiErrorKind.Offline => l["error.offline"],
            ApiErrorKind.Unauthorized => l["error.credentials"],
            ApiErrorKind.Forbidden => l["error.forbidden"],
            ApiErrorKind.TooManyRequests => l["error.tooMany"],
            _ => l["error.generic"],
        };
    }
}
