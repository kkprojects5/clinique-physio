namespace CliniquePhysio.Desktop.Core.Services;

/// <summary>Kinds of failure the screens need to explain differently.</summary>
public enum ApiErrorKind
{
    Offline,
    Unauthorized,
    Forbidden,
    Validation,
    TooManyRequests,
    Server,
    Other,
}

public sealed class ApiException : Exception
{
    public ApiException(ApiErrorKind kind, int statusCode)
        : base($"API error {statusCode} ({kind})")
    {
        Kind = kind;
        StatusCode = statusCode;
    }

    public ApiErrorKind Kind { get; }

    public int StatusCode { get; }

    public static ApiErrorKind KindFor(int statusCode) => statusCode switch
    {
        401 => ApiErrorKind.Unauthorized,
        403 => ApiErrorKind.Forbidden,
        422 => ApiErrorKind.Validation,
        429 => ApiErrorKind.TooManyRequests,
        >= 500 => ApiErrorKind.Server,
        _ => ApiErrorKind.Other,
    };
}
