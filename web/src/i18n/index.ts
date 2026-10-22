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

const savedLanguage =
  typeof window !== 'undefined'
    ? localStorage.getItem('language') || localStorage.getItem('i18nextLng')
    : null;

i18n
  // Detect user language
  .use(LanguageDetector)
  // Pass to react-i18next
  .use(initReactI18next)
  .init({
    resources,
    // Fallback language
    fallbackLng: 'en',
    // Default language: use saved preference from localStorage if present, otherwise 'en'
    lng: savedLanguage ? savedLanguage.split('-')[0] : 'en',
    supportedLngs: ['en', 'vi'],
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

// Persist language choice to both storage keys and update <html lang="...">
i18n.on('languageChanged', (lng) => {
  if (typeof window !== 'undefined') {
    const cleanLng = lng.split('-')[0];
    localStorage.setItem('language', cleanLng);
    localStorage.setItem('i18nextLng', cleanLng);
    document.documentElement.lang = cleanLng;
  }
});

export default i18n;
