export const locales = ['en', 'pt'] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = 'en'

export const localeNames: Record<Locale, string> = {
  pt: 'Português',
  en: 'English',
}

export const localeFlags: Record<Locale, string> = {
  pt: '🇵🇹',
  en: '🇬🇧',
}

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value)
}
