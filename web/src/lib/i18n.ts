import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import bn from '../locales/bn.json'
import en from '../locales/en.json'

export const LANGUAGE_KEY = 'medimatch-language'

function initialLanguage(): string {
  try {
    return localStorage.getItem(LANGUAGE_KEY) === 'bn' ? 'bn' : 'en'
  } catch {
    return 'en'
  }
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, bn: { translation: bn } },
  lng: initialLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

function syncDocumentLanguage(language: string) {
  document.documentElement.lang = language
}

syncDocumentLanguage(i18n.language)
i18n.on('languageChanged', syncDocumentLanguage)

export default i18n
