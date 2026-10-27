// Translations (NFR-10): French is the default, as the Charter of the French language requires.
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import fr from './fr.json';
import en from './en.json';

export const LANGUAGES = ['fr', 'en'];
const STORAGE_KEY = 'language';

function savedLanguage() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return LANGUAGES.includes(value) ? value : 'fr';
  } catch {
    return 'fr'; // storage can be blocked (private mode); French is the default
  }
}

i18n.use(initReactI18next).init({
  resources: { fr: { translation: fr }, en: { translation: en } },
  lng: savedLanguage(),
  fallbackLng: 'fr',
  interpolation: { escapeValue: false }, // React already escapes text (XSS protection)
});

i18n.on('languageChanged', (language) => {
  document.documentElement.lang = language; // screen readers use the right voice
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // ignore: the choice just won't be remembered
  }
});
document.documentElement.lang = i18n.language;

export default i18n;
