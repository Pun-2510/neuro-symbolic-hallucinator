/**
 * i18n Configuration
 * Setup for internationalization with react-i18next
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import vi from './locales/vi.json';

// ============================================================
// i18next Configuration
// ============================================================

const resources = {
  en: { translation: en },
  vi: { translation: vi },
};

i18n
  // Detect user language
  .use(LanguageDetector)
  // Pass to react-i18next
  .use(initReactI18next)
  .init({
    resources,
    // Fallback language
    fallbackLng: 'en',
    // Default language
    lng: localStorage.getItem('i18nextLng') || 'vi', // Default to Vietnamese
    // Interpolation
    interpolation: {
      escapeValue: false, // React already escapes
    },
    // Detection options
    detection: {
      // Language storage key
      order: ['localStorage', 'navigator'],
      // Lookup from localStorage
      lookupLocalStorage: 'language',
      // Cache user language choice
      caches: ['localStorage'],
    },
  });

export default i18n;
