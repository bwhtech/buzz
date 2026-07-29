import { userResource } from "@/data/user"
import { createResource } from "frappe-ui"
import { type ComputedRef, computed } from "vue"

interface LanguageComposable {
	availableLanguages: any
	currentLanguage: ComputedRef<string>
	changeLanguage: (languageCode: string) => void
	isSwitching: ComputedRef<boolean>
}

export function useLanguage(): LanguageComposable {
	const availableLanguages = createResource({
		url: "buzz.api.account.get_enabled_languages",
		auto: true,
		cache: "enabled_languages",
	})

	const currentLanguage = computed(() => {
		return userResource.data?.language || "en"
	})

	const switchLanguage = createResource({
		url: "buzz.api.account.update_user_language",
		onSuccess() {
			// Reload the page to apply new translations
			window.location.reload()
		},
	})

	function changeLanguage(languageCode: string) {
		switchLanguage.submit({ language_code: languageCode })
	}

	return {
		availableLanguages,
		currentLanguage,
		changeLanguage,
		isSwitching: computed(() => switchLanguage.loading),
	}
}
