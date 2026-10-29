using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using QRCoder;

namespace CliniquePhysio.Desktop.Converters;

/// <summary>Hides an element when its value is null or empty (e.g. no error message).</summary>
public sealed class NullToCollapsedConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        value is null || (value is string s && s.Length == 0) ? Visibility.Collapsed : Visibility.Visible;

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

/// <summary>Background colour for an appointment status (B-FRD-01). The status is also written in words.</summary>
public sealed class StatusToBrushConverter : IValueConverter
{
    private static readonly Dictionary<string, Brush> StatusBrushes = new()
    {
        ["held"] = Make("#FCEFD2"),
        ["pending_payment"] = Make("#FCEFD2"),
        ["confirmed"] = Make("#DCEDEA"),
        ["checked_in"] = Make("#D3ECD6"),
        ["completed"] = Make("#E3E7EE"),
        ["cancelled_by_patient"] = Make("#EEEAE4"),
        ["cancelled_by_clinic"] = Make("#EEEAE4"),
        ["no_show"] = Make("#F8DCD3"),
    };

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        value is string status && StatusBrushes.TryGetValue(status, out var brush) ? brush : Make("#FFFFFF");

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();

    private static Brush Make(string hex)
    {
        var brush = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
        brush.Freeze();
        return brush;
    }
}

/// <summary>Draws the otpauth:// link as a QR code for the authenticator app (first staff login).</summary>
public sealed class QrCodeConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is not string text || text.Length == 0)
        {
            return null;
        }

        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(text, QRCodeGenerator.ECCLevel.Q);
        var png = new PngByteQRCode(data).GetGraphic(8);

        var image = new BitmapImage();
        using (var stream = new MemoryStream(png))
        {
            image.BeginInit();
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.StreamSource = stream;
            image.EndInit();
        }

        image.Freeze();
        return image;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
