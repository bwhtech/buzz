import { createResource } from "frappe-ui"
import { type ComputedRef, computed, watch } from "vue"
import type { Router } from "vue-router"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { Language } from "@/types"
import {
	LANGUAGE_QUERY_PARAM,
	buildPreferredLanguageCookie,
	readPreferredLanguage,
	resolveRequestedLanguage,
	takeLanguageFromQuery,
} from "@/utils/language"

// frappe-ui types `data` as `{}`; this endpoint returns Language rows.
type LanguagesResource = Omit<ReturnType<typeof createResource>, "data"> & {
	data?: Language[]
}

interface LanguageComposable {
	availableLanguages: LanguagesResource
	currentLanguage: ComputedRef<string>
	changeLanguage: (languageCode: string) => void
	isSwitching: ComputedRef<boolean>
}

// The cache key hands every caller the same resource. Built on call rather than
// at import: `auto: true` fetches straight away, and main.ts has to install
// frappe-ui's resource fetcher first.
function availableLanguages(): LanguagesResource {
	return createResource({
		url: "buzz.api.account.get_enabled_languages",
		auto: true,
		cache: "enabled_languages",
	}) as LanguagesResource
}

const switchLanguage = createResource({
	url: "buzz.api.account.update_user_language",
	onSuccess() {
		// Reload the page to apply new translations
		window.location.reload()
	},
})

// Resolved server-side for both kinds of visitor, so there is one source of truth.
const currentLanguage = computed(() => userResource.data?.language || "en")

function changeLanguage(languageCode: string) {
	if (session.isLoggedIn) {
		switchLanguage.submit({ language_code: languageCode })
		return
	}

	// Guests share the one `Guest` User; the cookie is per browser.
	document.cookie = buildPreferredLanguageCookie(languageCode)
	window.location.reload()
}

function persistRequestedLanguage(requestedLanguage: string, languages: Language[]) {
	const languageToApply = resolveRequestedLanguage({
		requestedLanguage,
		isLoggedIn: session.isLoggedIn,
		enabledLanguageCodes: languages.map((language) => language.language_code),
		currentLanguage: readPreferredLanguage(document.cookie),
	})

	if (!languageToApply) return

	document.cookie = buildPreferredLanguageCookie(languageToApply)

	// Navigating to the cleaned URL drops the parameter and reloads for the new
	// translations in one go.
	const { cleanedUrl } = takeLanguageFromQuery(window.location.href)
	window.location.replace(cleanedUrl ?? window.location.href)
}

/**
 * Drop `?lang` through the router, not history.replaceState: the router captures
 * the location when it is created and writes it back on its first navigation,
 * undoing anything done before that. It also keeps `currentRoute.query` in step,
 * so a later push spreading the query cannot resurrect the value.
 */
function stripLanguageQueryParam(router: Router) {
	const route = router.currentRoute.value

	if (!(LANGUAGE_QUERY_PARAM in route.query)) return

	const { [LANGUAGE_QUERY_PARAM]: _applied, ...query } = route.query
	router.replace({ path: route.path, query, hash: route.hash })
}

/**
 * Honour `?lang=xx` on boot, so a link can be shared in a specific language. The
 * parameter is read synchronously — the router is about to run and may redirect
 * — but applying it waits for the enabled languages it is validated against.
 */
export function applyLanguageFromQuery(router: Router) {
	const { requestedLanguage } = takeLanguageFromQuery(window.location.href)

	if (!requestedLanguage) return

	router.isReady().then(() => stripLanguageQueryParam(router))

	const languages = availableLanguages()

	if (languages.data) {
		persistRequestedLanguage(requestedLanguage, languages.data)
		return
	}

	watch(
		() => languages.data,
		(loadedLanguages: Language[] | undefined) => {
			if (loadedLanguages) persistRequestedLanguage(requestedLanguage, loadedLanguages)
		},
		{ once: true },
	)
}

export function useLanguage(): LanguageComposable {
	return {
		availableLanguages: availableLanguages(),
		currentLanguage,
		changeLanguage,
		isSwitching: computed(() => switchLanguage.loading),
	}
}
