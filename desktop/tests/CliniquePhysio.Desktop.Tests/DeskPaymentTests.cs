using System.Globalization;
using System.Net;
using System.Text;
using CliniquePhysio.Desktop.Core.Localization;
using CliniquePhysio.Desktop.Core.Models;
using CliniquePhysio.Desktop.Core.Services;
using CliniquePhysio.Desktop.Core.ViewModels;
using Xunit;

namespace CliniquePhysio.Desktop.Tests;

// Balance paid at the desk and receipt to print (B-FRD-05, B-BKG-10).

public class DeskPaymentApiClientTests
{
    private static (ApiClient Api, FakeHttpHandler Handler) Make(Func<HttpRequestMessage, HttpResponseMessage> respond)
    {
        var handler = new FakeHttpHandler(respond);
        var http = new HttpClient(handler) { BaseAddress = new Uri("https://api.test/") };
        return (new ApiClient(http, new Session()), handler);
    }

    [Fact]
    public async Task Payment_sends_only_the_method_and_reads_the_new_balance()
    {
        var id = Guid.NewGuid();
        var (api, handler) = Make(_ => FakeHttpHandler.Json(
            new { appointment_id = id, price_cents = 8000, paid_cents = 8000, due_cents = 0, can_pay = false, receipt_available = true, receipt_number = "R-12345678" },
            HttpStatusCode.Created));

        var billing = await api.RecordPaymentAsync(id, "debit");

        Assert.Equal($"/api/v1/desk/appointments/{id}/payments", handler.Calls[0].Request.RequestUri!.AbsolutePath);
        Assert.Equal("{\"method\":\"debit\"}", handler.Calls[0].Body);
        Assert.Equal(0, billing.DueCents);
        Assert.True(billing.ReceiptAvailable);
        Assert.Equal("R-12345678", billing.ReceiptNumber);
    }

    [Fact]
    public async Task Receipt_is_downloaded_as_bytes_in_the_chosen_language()
    {
        var id = Guid.NewGuid();
        var (api, handler) = Make(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new ByteArrayContent(Encoding.ASCII.GetBytes("%PDF-1.4")),
        });

        var pdf = await api.GetReceiptAsync(id, "en");

        Assert.Equal("%PDF-1.4", Encoding.ASCII.GetString(pdf));
        Assert.Equal($"/api/v1/desk/appointments/{id}/receipt", handler.Calls[0].Request.RequestUri!.AbsolutePath);
        Assert.Equal("?lang=en", handler.Calls[0].Request.RequestUri!.Query);
    }

    [Fact]
    public async Task Refused_receipt_becomes_a_conflict()
    {
        var (api, _) = Make(_ => FakeHttpHandler.Json(new { detail = "no receipt" }, HttpStatusCode.Conflict));

        var error = await Assert.ThrowsAsync<ApiException>(() => api.GetReceiptAsync(Guid.NewGuid(), "fr"));

        Assert.Equal(ApiErrorKind.Conflict, error.Kind);
    }
}

public class DeskPaymentViewModelTests
{
    private static readonly Guid Anne = Guid.NewGuid();
    private static readonly DateTime Day = new(2026, 11, 12);

    private static async Task<(ScheduleViewModel Vm, FakeApi Api, FakeDialogs Dialogs, AppointmentItem Item)> Loaded(
        string status = "checked_in")
    {
        Localizer.Instance.Language = "fr";
        var appointment = new DeskAppointment
        {
            Id = Guid.NewGuid(),
            TherapistId = Anne,
            Start = DateTimeOffset.Parse("2026-11-12T15:00:00Z", CultureInfo.InvariantCulture),
            End = DateTimeOffset.Parse("2026-11-12T15:30:00Z", CultureInfo.InvariantCulture),
            StartLocal = "2026-11-12T10:00:00-05:00",
            Status = status,
            Service = new ServiceRef { Id = Guid.NewGuid(), NameFr = "Suivi", NameEn = "Follow-up" },
            Patient = new PatientRef { Id = Guid.NewGuid(), FirstName = "Marie", LastName = "Gagnon", Phone = "514-555-0001" },
        };
        var api = new FakeApi
        {
            Schedule = _ => Task.FromResult(new DaySchedule
            {
                Date = DateOnly.FromDateTime(Day),
                Therapists = new() { new TherapistRef { Id = Anne, FirstName = "Anne", LastName = "Lefebvre" } },
                Appointments = new() { appointment },
            }),
        };
        var dialogs = new FakeDialogs();
        var vm = new ScheduleViewModel(api, new Session(), new FakeNavigator(), Day, dialogs: dialogs);
        await vm.LoadCommand.ExecuteAsync(null);
        return (vm, api, dialogs, vm.Columns[0].Appointments[0]);
    }

    private static string Text(string key, params object[] values) =>
        string.Format(CultureInfo.CurrentCulture, Localizer.Instance[key], values);

    [Fact]
    public void Only_a_patient_who_came_can_pay_or_get_a_receipt()
    {
        var item = new AppointmentItem(Guid.NewGuid(), "", "", "", "", "checked_in", "");

        Assert.True(item.HasCome);
        Assert.True((item with { Status = "completed" }).HasCome);
        Assert.False((item with { Status = "confirmed" }).HasCome);
        Assert.False((item with { Status = "no_show" }).HasCome);
    }

    [Fact]
    public async Task Paying_confirms_the_amount_and_method_then_records_it()
    {
        var (vm, api, dialogs, item) = await Loaded();
        vm.PaymentMethod = vm.PaymentMethods.Single(m => m.Code == "cash");
        var amount = ScheduleViewModel.Money(6000, "fr");

        await vm.PayCommand.ExecuteAsync(item);

        Assert.Equal(Text("schedule.confirmPay", amount, "Comptant", "Marie Gagnon"), dialogs.Questions.Single());
        Assert.Equal(new[] { $"pay {item.Id} cash" }, api.Actions);
        Assert.Equal(Text("schedule.paid", amount, "Comptant", "Marie Gagnon"), vm.Info);
        Assert.Null(vm.Error);
    }

    [Fact]
    public async Task Saying_no_records_nothing()
    {
        var (vm, api, dialogs, item) = await Loaded();
        dialogs.Answer = false;

        await vm.PayCommand.ExecuteAsync(item);

        Assert.Empty(api.Actions);
    }

    [Fact]
    public async Task Nothing_due_says_so_without_asking()
    {
        var (vm, api, dialogs, item) = await Loaded();
        api.GetBilling = id => Task.FromResult(new Billing { AppointmentId = id, PriceCents = 8000, PaidCents = 8000 });

        await vm.PayCommand.ExecuteAsync(item);

        Assert.Empty(dialogs.Questions);
        Assert.Empty(api.Actions);
        Assert.Equal(Text("schedule.nothingDue", "Marie Gagnon"), vm.Info);
    }

    [Fact]
    public async Task Refused_payment_explains_the_rule()
    {
        var (vm, api, _, item) = await Loaded();
        api.Pay = (_, _) => throw new ApiException(ApiErrorKind.Conflict, 409);

        await vm.PayCommand.ExecuteAsync(item);

        Assert.Equal(Localizer.Instance["schedule.payRefused"], vm.Error);
        Assert.Null(vm.Info);
    }

    [Fact]
    public async Task Receipt_opens_the_pdf_named_after_the_receipt_number()
    {
        var (vm, api, dialogs, item) = await Loaded("completed");

        await vm.ReceiptCommand.ExecuteAsync(item);

        Assert.Equal(new[] { $"receipt {item.Id} fr" }, api.Actions);
        var opened = dialogs.Opened.Single();
        Assert.Equal("R-" + item.Id.ToString("N")[..8].ToUpperInvariant() + ".pdf", opened.Name);
        Assert.Equal(4, opened.Size);
        Assert.Equal(Text("schedule.receiptOpened", "Marie Gagnon"), vm.Info);
    }

    [Fact]
    public async Task No_receipt_yet_explains_why()
    {
        var (vm, api, dialogs, item) = await Loaded();
        api.Receipt = (_, _) => throw new ApiException(ApiErrorKind.Conflict, 409);

        await vm.ReceiptCommand.ExecuteAsync(item);

        Assert.Empty(dialogs.Opened);
        Assert.Equal(Localizer.Instance["schedule.receiptRefused"], vm.Error);
    }

    [Fact]
    public void Money_is_written_for_each_language()
    {
        Assert.Equal("$60.00", ScheduleViewModel.Money(6000, "en"));
        Assert.Contains("60,00", ScheduleViewModel.Money(6000, "fr"));
    }
}
