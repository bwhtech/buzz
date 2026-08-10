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
import { createResource } from "frappe-ui"
import { type ComputedRef, computed, watch } from "vue"
import type { Router } from "vue-router"

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

// One resource for every caller: the list cannot change within a page load, and
// applyLanguageFromQuery needs the same data the switcher renders. Created on
// first use rather than at import — `auto: true` fetches straight away, and
// main.ts has to install frappe-ui's resource fetcher first.
let languagesResource: LanguagesResource | null = null

function availableLanguages(): LanguagesResource {
	if (!languagesResource) {
		languagesResource = createResource({
			url: "buzz.api.account.get_enabled_languages",
			auto: true,
			cache: "enabled_languages",
		}) as LanguagesResource
	}
	return languagesResource
}

const switchLanguage = createResource({
	url: "buzz.api.account.update_user_language",
	onSuccess() {
		// Reload the page to apply new translations
		window.location.reload()
	},
})

// The server resolves this for both kinds of visitor — a logged-in user's User
// document, a guest's cookie — so there is one source of truth either way.
const currentLanguage = computed(() => userResource.data?.language || "en")

function changeLanguage(languageCode: string) {
	if (session.isLoggedIn) {
		switchLanguage.submit({ language_code: languageCode })
		return
	}

	// Guests all share the `Guest` User, so persisting there would hand this
	// language to every other visitor. The cookie is per browser.
	document.cookie = buildPreferredLanguageCookie(languageCode)
	window.location.reload()
}

function persistRequestedLanguage(
	requestedLanguage: string,
	languages: Language[],
) {
	const languageToApply = resolveRequestedLanguage({
		requestedLanguage,
		isLoggedIn: session.isLoggedIn,
		enabledLanguageCodes: languages.map((language) => language.language_code),
		currentLanguage: readPreferredLanguage(document.cookie),
	})

	if (!languageToApply) return

	document.cookie = buildPreferredLanguageCookie(languageToApply)

	// Navigating to the cleaned URL both drops the parameter and reloads for the
	// new translations. The page is torn down either way, so writing the address
	// bar directly is safe here.
	const { cleanedUrl } = takeLanguageFromQuery(window.location.href)
	window.location.replace(cleanedUrl ?? window.location.href)
}

/**
 * Drop `?lang` through the router rather than history.replaceState.
 *
 * The router captures the location when it is created and writes it back on its
 * first navigation, so a replaceState before that gets undone; going through
 * the router also keeps its `currentRoute.query` in step with the address bar,
 * so a later push that spreads the existing query cannot resurrect the value.
 */
function stripLanguageQueryParam(router: Router) {
	const route = router.currentRoute.value

	if (!(LANGUAGE_QUERY_PARAM in route.query)) return

	const { [LANGUAGE_QUERY_PARAM]: _applied, ...query } = route.query
	router.replace({ path: route.path, query, hash: route.hash })
}

/**
 * Honour `?lang=xx` on boot, so a link can be shared in a specific language.
 *
 * The parameter is read synchronously — the router is about to run and may
 * redirect — but applying it has to wait for the enabled languages, which is
 * what the requested code is validated against.
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
			if (loadedLanguages)
				persistRequestedLanguage(requestedLanguage, loadedLanguages)
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
