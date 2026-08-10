import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { Language } from "@/types"
import {
	buildPreferredLanguageCookie,
	readPreferredLanguage,
	resolveRequestedLanguage,
	takeLanguageFromQuery,
} from "@/utils/language"
import { createResource } from "frappe-ui"
import { type ComputedRef, computed, watch } from "vue"

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
	window.location.reload()
}

/**
 * Honour `?lang=xx` on boot, so a link can be shared in a specific language.
 *
 * Reading and stripping happen synchronously — the router is about to run, and
 * a redirect would carry the parameter away. Applying it has to wait for the
 * enabled languages, which is what the requested code is validated against.
 */
export function applyLanguageFromQuery() {
	const { cleanedUrl, requestedLanguage } = takeLanguageFromQuery(
		window.location.href,
	)

	if (!requestedLanguage) return

	if (cleanedUrl) {
		window.history.replaceState(window.history.state, "", cleanedUrl)
	}

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
