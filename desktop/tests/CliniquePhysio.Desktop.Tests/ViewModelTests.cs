using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;
using Xunit;

namespace CliniquePhysio.Desktop.Tests;

public class LoginViewModelTests
{
    private static string T(string key) => Localizer.Instance[key];

    [Fact]
    public async Task Empty_fields_show_a_message_without_calling_the_api()
    {
        var api = new FakeApi();
        var vm = new LoginViewModel(api, new FakeNavigator());

        await vm.LoginCommand.ExecuteAsync(null);

        Assert.Equal(T("login.missing"), vm.Error);
        Assert.Equal(0, api.LoginCalls);
    }

    [Fact]
    public async Task Staff_login_goes_to_the_mfa_step()
    {
        var api = new FakeApi
        {
            Login = (_, _) => Task.FromResult(new LoginResponse
            {
                MfaRequired = true,
                MfaSetupRequired = true,
                MfaToken = "ticket",
            }),
        };
        var nav = new FakeNavigator();
        var vm = new LoginViewModel(api, nav) { Email = " accueil1@clinique.example.com ", Password = "pw" };

        await vm.LoginCommand.ExecuteAsync(null);

        Assert.Equal("mfa", nav.Screen);
        Assert.Equal("ticket", nav.MfaToken);
        Assert.True(nav.MfaSetupRequired);
        Assert.Equal("", vm.Password); // not kept in memory longer than needed
    }

    [Fact]
    public async Task Patients_are_refused_and_their_session_is_closed()
    {
        var api = new FakeApi
        {
            Login = (_, _) => Task.FromResult(new LoginResponse { AccessToken = "patient-token" }),
        };
        var nav = new FakeNavigator();
        var vm = new LoginViewModel(api, nav) { Email = "patient01@example.com", Password = "pw" };

        await vm.LoginCommand.ExecuteAsync(null);

        Assert.Equal(T("login.staffOnly"), vm.Error);
        Assert.Null(nav.Screen);
        Assert.Equal(1, api.LogoutCalls);
    }

    [Fact]
    public async Task Wrong_password_shows_the_generic_message()
    {
        var api = new FakeApi
        {
            Login = (_, _) => throw new ApiException(ApiErrorKind.Unauthorized, 401),
        };
        var vm = new LoginViewModel(api, new FakeNavigator()) { Email = "a@b.c", Password = "pw" };

        await vm.LoginCommand.ExecuteAsync(null);

        Assert.Equal(T("error.credentials"), vm.Error);
        Assert.False(vm.IsBusy);
    }
}

public class MfaViewModelTests
{
    private static string T(string key) => Localizer.Instance[key];

    [Fact]
    public async Task First_login_loads_the_secret_and_qr_link()
    {
        var api = new FakeApi();
        var vm = new MfaViewModel(api, new Session(), new FakeNavigator(), "ticket", setupRequired: true, "e@x.c");

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.Equal("SECRET", vm.Secret);
        Assert.StartsWith("otpauth://", vm.OtpauthUri);
    }

    [Fact]
    public async Task Enrolled_staff_do_not_get_a_new_secret()
    {
        var api = new FakeApi();
        var vm = new MfaViewModel(api, new Session(), new FakeNavigator(), "ticket", setupRequired: false, "e@x.c");

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.Equal(0, api.SetupCalls);
        Assert.Null(vm.Secret);
    }

    [Theory]
    [InlineData("")]
    [InlineData("12345")]
    [InlineData("12a456")]
    public async Task Code_must_be_six_digits(string code)
    {
        var api = new FakeApi();
        var vm = new MfaViewModel(api, new Session(), new FakeNavigator(), "ticket", false, "e@x.c") { Code = code };

        await vm.VerifyCommand.ExecuteAsync(null);

        Assert.Equal(T("mfa.enterCode"), vm.Error);
        Assert.Equal(0, api.VerifyCalls);
    }

    [Fact]
    public async Task Correct_code_starts_the_session_and_opens_the_schedule()
    {
        var session = new Session();
        var nav = new FakeNavigator();
        var vm = new MfaViewModel(new FakeApi(), session, nav, "ticket", false, "accueil1@clinique.example.com")
        {
            Code = "123456",
        };

        await vm.VerifyCommand.ExecuteAsync(null);

        Assert.True(session.IsActive);
        Assert.Equal("access-token", session.AccessToken);
        Assert.Equal("schedule", nav.Screen);
    }

    [Fact]
    public async Task Wrong_code_shows_a_message_and_keeps_the_user_on_the_mfa_step()
    {
        var api = new FakeApi { Verify = (_, _) => throw new ApiException(ApiErrorKind.Unauthorized, 401) };
        var session = new Session();
        var nav = new FakeNavigator();
        var vm = new MfaViewModel(api, session, nav, "ticket", false, "e@x.c") { Code = "000000" };

        await vm.VerifyCommand.ExecuteAsync(null);

        Assert.Equal(T("error.code"), vm.Error);
        Assert.False(session.IsActive);
        Assert.Null(nav.Screen);
    }
}

public class ScheduleViewModelTests
{
    private static readonly Guid Anne = Guid.NewGuid();
    private static readonly Guid Sophie = Guid.NewGuid();

    private static DeskAppointment Appointment(Guid therapist, string startLocal, string status = "confirmed")
    {
        var start = DateTimeOffset.Parse(startLocal);
        return new DeskAppointment
        {
            Id = Guid.NewGuid(),
            TherapistId = therapist,
            Start = start.ToUniversalTime(),
            End = start.AddMinutes(30).ToUniversalTime(),
            StartLocal = startLocal,
            Status = status,
            Service = new ServiceRef { NameFr = "Suivi 30 min", NameEn = "Follow-up 30 min", DurationMin = 30 },
            Patient = new PatientRef { FirstName = "Marie", LastName = "Gagnon", Phone = "514-555-0001" },
        };
    }

    private static DaySchedule Day() => new()
    {
        Date = new DateOnly(2026, 11, 2),
        Therapists = new()
        {
            new TherapistRef { Id = Anne, FirstName = "Anne", LastName = "Lefebvre" },
            new TherapistRef { Id = Sophie, FirstName = "Sophie", LastName = "Nguyen" },
        },
        Appointments = new()
        {
            Appointment(Anne, "2026-11-02T11:00:00-05:00"),
            Appointment(Anne, "2026-11-02T09:00:00-05:00", "checked_in"),
        },
    };

    [Fact]
    public void One_column_per_therapist_with_their_appointments_in_time_order()
    {
        var columns = ScheduleViewModel.BuildColumns(Day(), "fr");

        Assert.Equal(new[] { "Anne Lefebvre", "Sophie Nguyen" }, columns.Select(c => c.Name));
        Assert.Equal(new[] { "09:00–09:30", "11:00–11:30" }, columns[0].Appointments.Select(a => a.TimeRange));
        Assert.True(columns[1].IsEmpty);
    }

    [Fact]
    public void Times_are_shown_in_montreal_time_before_and_after_the_dst_change()
    {
        var before = Appointment(Anne, "2026-10-26T10:00:00-04:00");
        var after = Appointment(Anne, "2026-11-02T10:00:00-05:00");

        Assert.Equal("10:00–10:30", ScheduleViewModel.TimeRange(before));
        Assert.Equal("10:00–10:30", ScheduleViewModel.TimeRange(after));
    }

    [Fact]
    public void Status_is_written_in_words_and_service_name_follows_the_language()
    {
        var french = ScheduleViewModel.BuildColumns(Day(), "fr")[0].Appointments[0];
        var english = ScheduleViewModel.BuildColumns(Day(), "en")[0].Appointments[0];

        Assert.Equal("checked_in", french.Status);
        Assert.Equal(Localizer.Instance["status.checked_in"], french.StatusLabel);
        Assert.Equal("Suivi 30 min", french.ServiceName);
        Assert.Equal("Follow-up 30 min", english.ServiceName);
        Assert.Equal("Marie Gagnon", french.PatientName);
    }

    [Fact]
    public async Task Loading_a_day_fills_the_columns()
    {
        DateOnly? asked = null;
        var api = new FakeApi { Schedule = day => { asked = day; return Task.FromResult(Day()); } };
        var vm = new ScheduleViewModel(api, new Session(), new FakeNavigator(), new DateTime(2026, 11, 2));

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.Equal(new DateOnly(2026, 11, 2), asked);
        Assert.Equal(2, vm.Columns.Count);
        Assert.Null(vm.Error);
    }

    [Fact]
    public async Task Expired_session_goes_back_to_login_with_a_message()
    {
        var api = new FakeApi { Schedule = _ => throw new ApiException(ApiErrorKind.Unauthorized, 401) };
        var session = new Session();
        session.Start("old-token", "e@x.c");
        var nav = new FakeNavigator();
        var vm = new ScheduleViewModel(api, session, nav, new DateTime(2026, 11, 2));

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.False(session.IsActive);
        Assert.Equal("login", nav.Screen);
        Assert.Equal(Localizer.Instance["error.expired"], nav.LoginMessage);
    }

    [Fact]
    public async Task Offline_shows_a_message_and_keeps_the_screen()
    {
        var api = new FakeApi { Schedule = _ => throw new ApiException(ApiErrorKind.Offline, 0) };
        var nav = new FakeNavigator();
        var vm = new ScheduleViewModel(api, new Session(), nav, new DateTime(2026, 11, 2));

        await vm.LoadCommand.ExecuteAsync(null);

        Assert.Equal(Localizer.Instance["error.offline"], vm.Error);
        Assert.Null(nav.Screen);
    }

    [Fact]
    public async Task Logout_clears_the_session_and_returns_to_login()
    {
        var api = new FakeApi();
        var session = new Session();
        session.Start("token", "e@x.c");
        var nav = new FakeNavigator();
        var vm = new ScheduleViewModel(api, session, nav, new DateTime(2026, 11, 2));

        await vm.LogoutCommand.ExecuteAsync(null);

        Assert.False(session.IsActive);
        Assert.Equal(1, api.LogoutCalls);
        Assert.Equal("login", nav.Screen);
    }
}

public class LocalizerTests
{
    [Fact]
    public void French_is_the_default_language()
    {
        Assert.Equal("fr", Localizer.Instance.Language);
    }

    [Fact]
    public void Every_text_exists_in_both_languages()
    {
        Assert.Equal(
            Localizer.KeysFor("fr").OrderBy(k => k),
            Localizer.KeysFor("en").OrderBy(k => k));
    }

    [Fact]
    public void Switching_language_changes_the_texts_and_notifies_the_screens()
    {
        var localizer = Localizer.Instance;
        var changed = new List<string?>();
        localizer.PropertyChanged += (_, e) => changed.Add(e.PropertyName);
        try
        {
            localizer.Language = "en";

            Assert.Equal("Log in", localizer["login.submit"]);
            Assert.Contains("Item[]", changed);
        }
        finally
        {
            localizer.Language = "fr";
        }

        Assert.Equal("Se connecter", localizer["login.submit"]);
    }
}
