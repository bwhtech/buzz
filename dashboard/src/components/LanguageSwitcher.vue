<template>
	<Dropdown :options="languageOptions">
		<template #default="{ open }">
			<Button
				variant="ghost"
				size="md"
				:loading="isSwitching"
				:aria-label="triggerLabel"
				data-testid="language-switcher"
			>
				<div class="flex items-center gap-2">
					<Globe class="w-4 h-4" />
					<span :lang="currentLanguage">{{ currentLanguageName }}</span>
					<ChevronDown class="w-3 h-3" :class="{ 'rotate-180': open }" />
				</div>
			</Button>
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import { useLanguage } from "@/composables/useLanguage";
import { Button, Dropdown } from "frappe-ui";
import type { Language } from "@/types";
import { computed, h } from "vue";
import ChevronDown from "~icons/lucide/chevron-down";
import Globe from "~icons/lucide/globe";

const { availableLanguages, currentLanguage, changeLanguage, isSwitching } = useLanguage();

const currentLanguageName = computed(() => {
	const match = (availableLanguages.data || []).find(
		(lang: Language) => lang.language_code === currentLanguage.value
	);
	return match?.language_name || currentLanguage.value;
});

const triggerLabel = computed(() =>
	__("Change language, current: {0}", [currentLanguageName.value])
);

const languageOptions = computed(() => {
	if (!availableLanguages.data || availableLanguages.data.length === 0) {
		return [];
	}

	return availableLanguages.data.map((lang: Language) => {
		const label = lang.language_name || lang.name;
		const isActive = currentLanguage.value === lang.language_code;

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
						label
					),
			},
			// One icon in the group makes every row reserve the space, so the list
			// stays aligned with a tick on only the active one.
			icon: isActive ? "lucide-check" : undefined,
			selected: isActive,
			onClick: () => changeLanguage(lang.language_code),
		};
	});
});
</script>
