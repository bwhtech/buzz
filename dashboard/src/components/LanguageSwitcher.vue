<template>
	<Dropdown :options="languageOptions">
		<template #default="{ open }">
			<Button variant="ghost" size="md" :loading="isSwitching" :aria-label="triggerLabel">
				<div class="flex items-center gap-2">
					<Globe class="w-4 h-4" />
					<span :lang="currentLanguage">{{ currentLanguageName }}</span>
					<ChevronDown class="w-3 h-3" :class="{ 'rotate-180': open }" />
				</div>
			</Button>
		</template>
		<template #item="{ item }">
			<button
				type="button"
				class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-base focus:outline-none data-[highlighted]:bg-surface-gray-3"
				:lang="(item as LanguageOption).code"
				role="menuitemradio"
				:aria-checked="(item as LanguageOption).isActive ? 'true' : 'false'"
			>
				<Check
					class="h-4 w-4 shrink-0"
					:class="(item as LanguageOption).isActive ? 'text-ink-gray-9' : 'invisible'"
				/>
				<span
					class="whitespace-nowrap"
					:class="
						(item as LanguageOption).isActive
							? 'font-medium text-ink-gray-9'
							: 'text-ink-gray-7'
					"
					>{{ item.label }}</span
				>
			</button>
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import { useLanguage } from "@/composables/useLanguage";
import { Button, Dropdown } from "frappe-ui";
import type { Language } from "@/types";
import { computed } from "vue";
import Check from "~icons/lucide/check";
import ChevronDown from "~icons/lucide/chevron-down";
import Globe from "~icons/lucide/globe";

const { availableLanguages, currentLanguage, changeLanguage, isSwitching } = useLanguage();

// Dropdown options carry custom fields on top of frappe-ui's DropdownOption.
interface LanguageOption {
	label: string;
	code: string;
	isActive: boolean;
	onClick: () => void;
}

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

	return availableLanguages.data.map(
		(lang: Language): LanguageOption => ({
			label: lang.language_name || lang.name,
			code: lang.language_code,
			isActive: currentLanguage.value === lang.language_code,
			onClick: () => changeLanguage(lang.language_code),
		})
	);
});
</script>
