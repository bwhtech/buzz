<script setup lang="ts">
import { FormControl } from "frappe-ui"

import { stripUrlScheme } from "@/components/dashboard/sponsorships/helpers"

// Holds the address without a scheme; callers add https:// on save via websiteUrl.
const website = defineModel<string>({ required: true })
defineProps<{ disabled?: boolean; required?: boolean }>()
</script>

<template>
	<FormControl
		:model-value="website"
		label="Website"
		placeholder="example.com"
		autocomplete="off"
		:disabled="disabled"
		:required="required"
		@update:model-value="(value: string) => (website = stripUrlScheme(value))"
	>
		<template #prefix>
			<span class="lucide-globe size-4 text-ink-gray-5" aria-hidden="true" />
		</template>
	</FormControl>
</template>
