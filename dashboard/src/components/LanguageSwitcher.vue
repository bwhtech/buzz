<template>
	<Dropdown :options="options">
		<Button
			variant="ghost"
			size="md"
			:loading="isSwitching"
			:aria-label="__('Change language, current: {0}', [currentLanguageName])"
			:title="currentLanguageName"
			data-testid="language-switcher"
		>
			<div class="flex items-center gap-1">
				<Globe class="size-4" />
				<span :lang="currentLanguage" class="text-sm tracking-wide">
					{{ currentLanguage.toUpperCase() }}
				</span>
			</div>
		</Button>
	</Dropdown>
</template>

<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import Globe from "~icons/lucide/globe"

import { useLanguageMenu } from "@/composables/useLanguageMenu"

const { options, currentLanguage, currentLanguageName, isSwitching } = useLanguageMenu()
</script>
