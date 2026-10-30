import { computed, h } from "vue"

import { useLanguage } from "@/composables/useLanguage"
import type { Language } from "@/types"

// Dropdown options for every enabled language, shared by the header's switcher and its mobile menu.
export function useLanguageMenu() {
	const { availableLanguages, currentLanguage, changeLanguage, isSwitching } = useLanguage()

	const currentLanguageName = computed(() => {
		const match = (availableLanguages.data || []).find(
			(lang: Language) => lang.language_code === currentLanguage.value,
		)
		return match?.language_name || currentLanguage.value
	})

	const options = computed(() =>
		(availableLanguages.data || []).map((lang: Language) => {
			const label = lang.language_name || lang.name
			const isActive = currentLanguage.value === lang.language_code
			return {
				label,
				// The row shell's `label` slot, not the whole-row `item` slot: that one
				// remounts its element on every re-render, so mousedown and mouseup land
				// on different nodes and the browser never fires a click.
				slots: {
					label: () =>
						h(
							"span",
							{
								class: "whitespace-nowrap",
								lang: lang.language_code,
								"data-testid": `language-option-${lang.language_code}`,
							},
							label,
						),
				},
				// One icon in the group makes every row reserve the space, so the list
				// stays aligned with a tick on only the active one.
				icon: isActive ? "lucide-check" : undefined,
				selected: isActive,
				onClick: () => changeLanguage(lang.language_code),
			}
		}),
	)

	return { options, currentLanguage, currentLanguageName, isSwitching }
}
