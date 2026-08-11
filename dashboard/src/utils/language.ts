// Every visitor shares the one `Guest` user, so a guest's language lives in the
// `preferred_language` cookie that frappe.translate.get_language() reads per
// request — a cookie is per browser, so one choice cannot leak into another
// visitor's session. Kept pure for unit testing; useLanguage owns the side
// effects.

export const PREFERRED_LANGUAGE_COOKIE = "preferred_language"
export const LANGUAGE_QUERY_PARAM = "lang"

const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365

export function readPreferredLanguage(cookieString: string): string | null {
	// Split on the separator rather than reusing URLSearchParams: another
	// cookie's value is free to contain an `&`, and would be read as ours.
	for (const cookie of cookieString.split(";")) {
		const [name, ...value] = cookie.split("=")
		if (name.trim() === PREFERRED_LANGUAGE_COOKIE) {
			return decodeURIComponent(value.join("="))
		}
	}

	return null
}

export function buildPreferredLanguageCookie(languageCode: string): string {
	const value = encodeURIComponent(languageCode)
	return `${PREFERRED_LANGUAGE_COOKIE}=${value}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax`
}

export interface LanguageQueryRequest {
	/** The URL with `?lang` removed, or null when there was nothing to remove. */
	cleanedUrl: string | null
	/** The requested language code, or null when the URL carried none. */
	requestedLanguage: string | null
}

/**
 * Pull `?lang=xx` off a URL. Always removed: left in place it would re-pin the
 * language on every later reload.
 */
export function takeLanguageFromQuery(url: string): LanguageQueryRequest {
	const parsedUrl = new URL(url)
	const requestedLanguage = parsedUrl.searchParams.get(LANGUAGE_QUERY_PARAM)

	if (!requestedLanguage) {
		return { cleanedUrl: null, requestedLanguage: null }
	}

	parsedUrl.searchParams.delete(LANGUAGE_QUERY_PARAM)

	return { cleanedUrl: parsedUrl.toString(), requestedLanguage }
}

export interface RequestedLanguageInput {
	requestedLanguage: string
	isLoggedIn: boolean
	/** Codes of the languages enabled on the site, from get_enabled_languages. */
	enabledLanguageCodes: string[]
	/** The language already in effect for this browser, if any. */
	currentLanguage: string | null
}

/**
 * Decide whether a requested language should be persisted for this visitor.
 * Returns the code to write, or null when nothing should change.
 */
export function resolveRequestedLanguage({
	requestedLanguage,
	isLoggedIn,
	enabledLanguageCodes,
	currentLanguage,
}: RequestedLanguageInput): string | null {
	// A shared link must not silently rewrite someone's saved preference.
	if (isLoggedIn) return null

	// Whatever lands in the cookie is what the server resolves translations
	// against, so it is never written unvalidated.
	if (!enabledLanguageCodes.includes(requestedLanguage)) return null

	// Already in effect — nothing to write, and no reason to reload.
	if (requestedLanguage === currentLanguage) return null

	return requestedLanguage
}
