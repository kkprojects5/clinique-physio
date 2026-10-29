using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Services;

namespace CliniquePhysio.Desktop.Core.ViewModels;

/// <summary>Turns API failures into clear messages for the user (never technical details).</summary>
public static class ErrorMessages
{
    public static string For(ApiException error)
    {
        var l = Localizer.Instance;
        return error.Kind switch
        {
            ApiErrorKind.Offline => l["error.offline"],
            ApiErrorKind.Unauthorized => l["error.credentials"],
            ApiErrorKind.Forbidden => l["error.forbidden"],
            ApiErrorKind.TooManyRequests => l["error.tooMany"],
            _ => l["error.generic"],
        };
    }
}
