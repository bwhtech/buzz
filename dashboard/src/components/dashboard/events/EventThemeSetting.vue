<script setup lang="ts">
import { FormControl, toast } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import { useEnabledThemes } from "@/data/themes"

const props = defineProps<{ event: string; disabled: boolean }>()

const eventDoc = useEventDoc(() => props.event)
const themes = useEnabledThemes()

const options = computed(() => [
	{ label: __("Site default"), value: "" },
	...(themes.data ?? []).map((theme) => ({ label: theme.name, value: theme.name })),
])

async function change(theme: string) {
	await eventDoc.setValue.submit({ theme: theme || null }).catch(() => null)
	if (eventDoc.setValue.error) {
		toast.error(eventDoc.setValue.error.message || __("Could not save the event"))
		return
	}
	toast.success(__("Theme updated"))
}
</script>

<template>
	<div class="flex flex-wrap items-center justify-between gap-3 p-4">
		<div class="space-y-1">
			<h3 class="font-medium text-base text-ink-gray-8">{{ __("Page theme") }}</h3>
			<p class="text-p-sm text-ink-gray-6">
				{{ __("Colours, fonts and sizes of the public event page.") }}
			</p>
		</div>
		<div class="w-44">
			<FormControl
				type="select"
				:model-value="eventDoc.doc?.theme ?? ''"
				:options="options"
				:disabled="disabled || eventDoc.setValue.loading"
				:aria-label="__('Page theme')"
				@update:model-value="change"
			/>
		</div>
	</div>
</template>
