// Guests have no User document to hold a language preference — every visitor
// shares the one `Guest` user — so their choice lives in the
// `preferred_language` cookie that frappe.translate.get_language() reads on
// each request. A cookie is per browser, so one visitor's choice cannot leak
// into another's session.
//
// Everything here is pure so it can be unit tested; useLanguage owns the
// document/window side effects.

export const PREFERRED_LANGUAGE_COOKIE = "preferred_language"
export const LANGUAGE_QUERY_PARAM = "lang"

// A year, so a returning visitor keeps the language they picked.
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365

export function readPreferredLanguage(cookieString: string): string | null {
	const cookies = new URLSearchParams(cookieString.split("; ").join("&"))
	return cookies.get(PREFERRED_LANGUAGE_COOKIE)
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
 * Pull `?lang=xx` off a URL.
 *
 * The parameter is a one-shot instruction carried by a shared link, so it is
 * always removed — leaving it in place would re-pin the language on every
 * later reload, and the router is free to drop the query on its next redirect.
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

	// Never hand an unvalidated value to the cookie: whatever lands there is
	// what the server resolves translations against.
	if (!enabledLanguageCodes.includes(requestedLanguage)) return null

	// Already in effect — nothing to write, and no reason to reload.
	if (requestedLanguage === currentLanguage) return null

	return requestedLanguage
}
