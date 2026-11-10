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
            ["schedule.newBooking"] = "+ Rendez-vous par téléphone",
            ["schedule.checkIn"] = "Arrivé",
            ["schedule.noShow"] = "Absent",
            ["schedule.move"] = "Déplacer",
            ["schedule.cancel"] = "Annuler",
            ["schedule.checkedIn"] = "{0} est arrivé(e).",
            ["schedule.markedNoShow"] = "{0} est marqué(e) absent(e). L’acompte est conservé.",
            ["schedule.cancelledRefunded"] = "Rendez-vous de {0} annulé. L’acompte payé en ligne sera remboursé.",
            ["schedule.cancelledKept"] = "Rendez-vous de {0} annulé. Aucun remboursement (moins de 24 h avant, ou rien de payé en ligne).",
            ["schedule.confirmCancel"] = "Annuler le rendez-vous de {0} ({1}) ?",
            ["schedule.confirmNoShow"] = "Marquer {0} ({1}) comme absent(e) ? L’acompte sera conservé.",
            ["schedule.checkInRefused"] = "Arrivée impossible : seulement pour un rendez-vous confirmé, le jour même.",
            ["schedule.noShowRefused"] = "Absence impossible : seulement pour un rendez-vous confirmé, 15 minutes après le début.",
            ["schedule.cancelRefused"] = "Ce rendez-vous ne peut plus être annulé (déjà commencé ou déjà annulé).",
            ["booking.title"] = "Rendez-vous par téléphone",
            ["booking.moveTitle"] = "Déplacer le rendez-vous de {0} ({1})",
            ["booking.back"] = "◀ Retour à l’horaire",
            ["booking.patient"] = "1. Patient",
            ["booking.searchHint"] = "Nom, téléphone ou date de naissance (AAAA-MM-JJ)",
            ["booking.search"] = "Chercher",
            ["booking.searchTooShort"] = "Entrez au moins 2 caractères.",
            ["booking.noPatient"] = "Aucun patient trouvé. Vérifiez l’orthographe ou cherchez par téléphone.",
            ["booking.service"] = "2. Service et physiothérapeute",
            ["booking.firstAvailable"] = "Premier disponible",
            ["booking.day"] = "3. Jour et heure",
            ["booking.findSlots"] = "Voir les heures libres",
            ["booking.noSlot"] = "Aucune heure libre ce jour-là. Essayez un autre jour ou un autre physiothérapeute.",
            ["booking.book"] = "Réserver",
            ["booking.moveButton"] = "Déplacer ici",
            ["booking.paidAtClinic"] = "Le rendez-vous est confirmé tout de suite ; le patient paie à la clinique.",
            ["booking.choosePatient"] = "Choisissez d’abord le patient.",
            ["booking.chooseServiceAndDay"] = "Choisissez un service et un jour.",
            ["booking.chooseSlot"] = "Choisissez une heure libre.",
            ["booking.refused"] = "Réservation refusée : cette heure vient d’être prise, ou ce patient doit d’abord avoir une évaluation initiale. Les heures libres ont été mises à jour.",
            ["booking.booked"] = "Rendez-vous réservé pour {0} : {1}.",
            ["booking.moved"] = "Rendez-vous de {0} déplacé : {1}.",
            ["error.conflict"] = "Cette action n’est plus possible. Actualisez l’horaire.",
            ["error.notFound"] = "Introuvable : ce rendez-vous ou ce patient n’existe plus. Actualisez l’horaire.",
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
            ["schedule.newBooking"] = "+ Phone booking",
            ["schedule.checkIn"] = "Arrived",
            ["schedule.noShow"] = "No-show",
            ["schedule.move"] = "Move",
            ["schedule.cancel"] = "Cancel",
            ["schedule.checkedIn"] = "{0} has arrived.",
            ["schedule.markedNoShow"] = "{0} is marked as a no-show. The deposit is kept.",
            ["schedule.cancelledRefunded"] = "{0}'s appointment is cancelled. The deposit paid online will be refunded.",
            ["schedule.cancelledKept"] = "{0}'s appointment is cancelled. No refund (less than 24 h before, or nothing paid online).",
            ["schedule.confirmCancel"] = "Cancel {0}'s appointment ({1})?",
            ["schedule.confirmNoShow"] = "Mark {0} ({1}) as a no-show? The deposit will be kept.",
            ["schedule.checkInRefused"] = "Check-in not possible: only for a confirmed appointment, on the same day.",
            ["schedule.noShowRefused"] = "No-show not possible: only for a confirmed appointment, 15 minutes after the start.",
            ["schedule.cancelRefused"] = "This appointment can no longer be cancelled (already started or cancelled).",
            ["booking.title"] = "Phone booking",
            ["booking.moveTitle"] = "Move {0}'s appointment ({1})",
            ["booking.back"] = "◀ Back to the schedule",
            ["booking.patient"] = "1. Patient",
            ["booking.searchHint"] = "Name, phone or date of birth (YYYY-MM-DD)",
            ["booking.search"] = "Search",
            ["booking.searchTooShort"] = "Type at least 2 characters.",
            ["booking.noPatient"] = "No patient found. Check the spelling or search by phone.",
            ["booking.service"] = "2. Service and physiotherapist",
            ["booking.firstAvailable"] = "First available",
            ["booking.day"] = "3. Day and time",
            ["booking.findSlots"] = "Show free times",
            ["booking.noSlot"] = "No free time that day. Try another day or another physiotherapist.",
            ["booking.book"] = "Book",
            ["booking.moveButton"] = "Move here",
            ["booking.paidAtClinic"] = "The appointment is confirmed at once; the patient pays at the clinic.",
            ["booking.choosePatient"] = "Choose the patient first.",
            ["booking.chooseServiceAndDay"] = "Choose a service and a day.",
            ["booking.chooseSlot"] = "Choose a free time.",
            ["booking.refused"] = "Booking refused: this time was just taken, or this patient needs an initial evaluation first. The free times have been updated.",
            ["booking.booked"] = "Appointment booked for {0}: {1}.",
            ["booking.moved"] = "{0}'s appointment moved: {1}.",
            ["error.conflict"] = "This action is no longer possible. Refresh the schedule.",
            ["error.notFound"] = "Not found: this appointment or patient no longer exists. Refresh the schedule.",
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
