// French and English texts (NFR-10). French is the default.
export type Language = 'fr' | 'en';

const texts = {
  fr: {
    appTitle: 'Clinique Physio Mont-Royal',
    switchLanguage: 'English',
    switchLanguageLabel: 'Switch to English',
    loginTitle: 'Connexion patient',
    email: 'Courriel',
    password: 'Mot de passe',
    login: 'Se connecter',
    missing: 'Entrez votre courriel et votre mot de passe.',
    staffAccount: 'Ce compte est un compte du personnel. Utilisez l’application de bureau ou le site web.',
    myAppointments: 'Mes rendez-vous',
    noAppointments: 'Aucun rendez-vous à venir.',
    with: 'avec {name}',
    logout: 'Se déconnecter',
    loading: 'Chargement…',
    timezone: 'Heures de Montréal.',
    'status.held': 'Réservé (paiement en cours)',
    'status.pending_payment': 'Paiement en attente',
    'status.confirmed': 'Confirmé',
    'status.checked_in': 'Arrivé',
    'status.completed': 'Terminé',
    'status.cancelled_by_patient': 'Annulé',
    'status.cancelled_by_clinic': 'Annulé par la clinique',
    'status.no_show': 'Absent',
    'error.offline': 'Impossible de joindre le serveur. Vérifiez votre connexion et réessayez.',
    'error.credentials': 'Courriel ou mot de passe incorrect.',
    'error.unverified': 'Confirmez d’abord votre adresse courriel.',
    'error.tooMany': 'Trop de tentatives. Attendez une minute.',
    'error.expired': 'Votre session a expiré. Veuillez vous reconnecter.',
    'error.generic': 'Une erreur est survenue. Réessayez.',
  },
  en: {
    appTitle: 'Clinique Physio Mont-Royal',
    switchLanguage: 'Français',
    switchLanguageLabel: 'Passer en français',
    loginTitle: 'Patient login',
    email: 'Email',
    password: 'Password',
    login: 'Log in',
    missing: 'Enter your email and password.',
    staffAccount: 'This is a staff account. Use the desktop app or the website.',
    myAppointments: 'My appointments',
    noAppointments: 'No upcoming appointments.',
    with: 'with {name}',
    logout: 'Log out',
    loading: 'Loading…',
    timezone: 'Montréal time.',
    'status.held': 'Held (payment in progress)',
    'status.pending_payment': 'Payment pending',
    'status.confirmed': 'Confirmed',
    'status.checked_in': 'Checked in',
    'status.completed': 'Completed',
    'status.cancelled_by_patient': 'Cancelled',
    'status.cancelled_by_clinic': 'Cancelled by the clinic',
    'status.no_show': 'No-show',
    'error.offline': 'Cannot reach the server. Check your connection and try again.',
    'error.credentials': 'Incorrect email or password.',
    'error.unverified': 'Please confirm your email address first.',
    'error.tooMany': 'Too many attempts. Wait a minute.',
    'error.expired': 'Your session has expired. Please log in again.',
    'error.generic': 'Something went wrong. Please try again.',
  },
} as const;

export type TextKey = keyof (typeof texts)['fr'];

export function translate(
  language: Language,
  key: TextKey | string,
  params: Record<string, string> = {},
): string {
  const table = texts[language] as Record<string, string>;
  const text = table[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name: string) => params[name] ?? '');
}

export const keysFor = (language: Language) => Object.keys(texts[language]).sort();
