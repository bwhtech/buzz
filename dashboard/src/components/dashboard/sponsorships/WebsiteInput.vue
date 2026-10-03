<script setup lang="ts">
import { FormControl } from "frappe-ui"

import { stripUrlScheme } from "@/components/dashboard/sponsorships/helpers"

// Holds the address without a scheme; callers add https:// on save via websiteUrl.
const website = defineModel<string>({ required: true })
withDefaults(
	defineProps<{ label?: string; error?: string; disabled?: boolean; required?: boolean }>(),
	{
		label: "Website",
		error: "",
	},
)
</script>

<template>
	<FormControl
		:model-value="website"
		:label="label"
		placeholder="example.com"
		autocomplete="off"
		:disabled="disabled"
		:required="required"
		:error="error"
		@update:model-value="(value: string) => (website = stripUrlScheme(value))"
	>
		<template #prefix>
			<span class="lucide-globe size-4 text-ink-gray-5" aria-hidden="true" />
		</template>
	</FormControl>
</template>
