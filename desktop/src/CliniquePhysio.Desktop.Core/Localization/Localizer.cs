using System.ComponentModel;

namespace CliniquePhysio.Desktop.Core.Localization;

/// <summary>
/// French and English texts (NFR-10). French is the default. Screens bind to
/// Localizer.Instance["key"], so switching language updates every screen at once.
/// </summary>
public sealed class Localizer : INotifyPropertyChanged
{
    private static readonly Dictionary<string, Dictionary<string, string>> Texts = new()
    {
        ["fr"] = new()
        {
            ["app.title"] = "Clinique Physio Mont-Royal — Accueil",
            ["lang.switch"] = "English",
            ["conn.online"] = "En ligne",
            ["conn.offline"] = "Hors ligne",
            ["login.title"] = "Connexion du personnel",
            ["login.email"] = "Courriel",
            ["login.password"] = "Mot de passe",
            ["login.submit"] = "Se connecter",
            ["login.missing"] = "Entrez votre courriel et votre mot de passe.",
            ["login.staffOnly"] = "Cette application est réservée au personnel de la clinique.",
            ["mfa.title"] = "Vérification en deux étapes",
            ["mfa.setupIntro"] = "Première connexion : scannez ce code avec une application d’authentification (Google Authenticator, Microsoft Authenticator), puis entrez le code à 6 chiffres.",
            ["mfa.secret"] = "Ou entrez cette clé manuellement :",
            ["mfa.code"] = "Code à 6 chiffres",
            ["mfa.submit"] = "Vérifier",
            ["mfa.back"] = "Retour",
            ["mfa.enterCode"] = "Entrez les 6 chiffres affichés dans votre application.",
            ["schedule.title"] = "Horaire du jour",
            ["schedule.previous"] = "◀ Jour précédent",
            ["schedule.next"] = "Jour suivant ▶",
            ["schedule.today"] = "Aujourd’hui",
            ["schedule.refresh"] = "Actualiser",
            ["schedule.logout"] = "Se déconnecter",
            ["schedule.empty"] = "Aucun rendez-vous",
            ["schedule.loading"] = "Chargement…",
            ["status.held"] = "Réservé (paiement en cours)",
            ["status.pending_payment"] = "Paiement en attente",
            ["status.confirmed"] = "Confirmé",
            ["status.checked_in"] = "Arrivé",
            ["status.completed"] = "Terminé",
            ["status.cancelled_by_patient"] = "Annulé (patient)",
            ["status.cancelled_by_clinic"] = "Annulé (clinique)",
            ["status.no_show"] = "Absent",
            ["error.offline"] = "Impossible de joindre le serveur. Vérifiez la connexion et réessayez.",
            ["error.credentials"] = "Courriel ou mot de passe incorrect.",
            ["error.forbidden"] = "Accès refusé pour ce compte.",
            ["error.tooMany"] = "Trop de tentatives. Attendez une minute avant de réessayer.",
            ["error.code"] = "Code invalide ou étape expirée. Réessayez ou reconnectez-vous.",
            ["error.expired"] = "Votre session a expiré. Veuillez vous reconnecter.",
            ["error.generic"] = "Une erreur est survenue. Réessayez.",
        },
        ["en"] = new()
        {
            ["app.title"] = "Clinique Physio Mont-Royal — Front desk",
            ["lang.switch"] = "Français",
            ["conn.online"] = "Online",
            ["conn.offline"] = "Offline",
            ["login.title"] = "Staff login",
            ["login.email"] = "Email",
            ["login.password"] = "Password",
            ["login.submit"] = "Log in",
            ["login.missing"] = "Enter your email and password.",
            ["login.staffOnly"] = "This application is for clinic staff only.",
            ["mfa.title"] = "Two-step verification",
            ["mfa.setupIntro"] = "First login: scan this code with an authenticator app (Google Authenticator, Microsoft Authenticator), then enter the 6-digit code.",
            ["mfa.secret"] = "Or enter this key manually:",
            ["mfa.code"] = "6-digit code",
            ["mfa.submit"] = "Verify",
            ["mfa.back"] = "Back",
            ["mfa.enterCode"] = "Enter the 6 digits shown in your app.",
            ["schedule.title"] = "Today's schedule",
            ["schedule.previous"] = "◀ Previous day",
            ["schedule.next"] = "Next day ▶",
            ["schedule.today"] = "Today",
            ["schedule.refresh"] = "Refresh",
            ["schedule.logout"] = "Log out",
            ["schedule.empty"] = "No appointments",
            ["schedule.loading"] = "Loading…",
            ["status.held"] = "Held (payment in progress)",
            ["status.pending_payment"] = "Payment pending",
            ["status.confirmed"] = "Confirmed",
            ["status.checked_in"] = "Checked in",
            ["status.completed"] = "Completed",
            ["status.cancelled_by_patient"] = "Cancelled (patient)",
            ["status.cancelled_by_clinic"] = "Cancelled (clinic)",
            ["status.no_show"] = "No-show",
            ["error.offline"] = "Cannot reach the server. Check the connection and try again.",
            ["error.credentials"] = "Incorrect email or password.",
            ["error.forbidden"] = "Access denied for this account.",
            ["error.tooMany"] = "Too many attempts. Wait a minute before trying again.",
            ["error.code"] = "Invalid code or expired step. Try again or log in again.",
            ["error.expired"] = "Your session has expired. Please log in again.",
            ["error.generic"] = "Something went wrong. Please try again.",
        },
    };

    private string _language = "fr";

    public static Localizer Instance { get; } = new();

    public event PropertyChangedEventHandler? PropertyChanged;

    public string Language
    {
        get => _language;
        set
        {
            if (!Texts.ContainsKey(value) || value == _language)
            {
                return;
            }

            _language = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Language)));
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("Item[]")); // refresh every text
        }
    }

    public string this[string key] =>
        Texts[_language].TryGetValue(key, out var text) ? text : key;

    /// <summary>Every key exists in both languages (checked by a test).</summary>
    public static IReadOnlyCollection<string> KeysFor(string language) => Texts[language].Keys;
}
