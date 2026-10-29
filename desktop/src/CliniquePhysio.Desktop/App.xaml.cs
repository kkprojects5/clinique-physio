using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Threading;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;

namespace CliniquePhysio.Desktop;

public partial class App : Application
{
    private const string DefaultApiUrl = "https://clinique-physio-api.onrender.com/";
    private DispatcherTimer? _connectionTimer;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var session = new Session();
        var api = ApiClient.Create(ReadApiUrl(), session);
        var main = new MainViewModel(api, session);

        var window = new MainWindow { DataContext = main };
        window.Show();
        main.GoToLogin();

        // Connection indicator: check the API every 30 seconds.
        _ = main.CheckConnectionCommand.ExecuteAsync(null);
        _connectionTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
        _connectionTimer.Tick += (_, _) => _ = main.CheckConnectionCommand.ExecuteAsync(null);
        _connectionTimer.Start();
    }

    /// <summary>API address from appsettings.json, so it can change without rebuilding.</summary>
    private static Uri ReadApiUrl()
    {
        try
        {
            var path = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            var url = json.RootElement.GetProperty("ApiBaseUrl").GetString() ?? DefaultApiUrl;
            return new Uri(url.EndsWith('/') ? url : url + "/");
        }
        catch (Exception ex) when (ex is IOException or JsonException or KeyNotFoundException or UriFormatException)
        {
            return new Uri(DefaultApiUrl);
        }
    }
}
