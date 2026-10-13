<script setup lang="ts">
import { Button, MultiSelect, useList } from "frappe-ui"
import { computed } from "vue"

import { topicIcon } from "@/utils/topicIcons"

const MAX_TOPICS = 5

const topics = defineModel<string[]>({ required: true })

const enabledTopics = useList<{ name: string }>({
	doctype: "Event Topic",
	fields: ["name"],
	filters: { enabled: 1 },
	orderBy: "name asc",
	limit: 100,
})

// Saved topics stay listed after an admin disables them, or the picker would drop them.
const options = computed(() =>
	[...new Set([...topics.value, ...(enabledTopics.data ?? []).map(({ name }) => name)])]
		.toSorted()
		.map((name) => ({
			label: name,
			value: name,
			icon: topicIcon(name),
			disabled: topics.value.length >= MAX_TOPICS && !topics.value.includes(name),
		})),
)
</script>

<template>
	<section class="space-y-3">
		<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">{{ __("Topics") }}</h2>
		<MultiSelect
			v-model="topics"
			:options="options"
			:placeholder="__('Pick up to {0} topics', [MAX_TOPICS])"
			class="w-full"
		>
			<template #summary="{ summary, selectedOptions }">
				{{
					selectedOptions.length
						? selectedOptions.map((option) => option.label).join(", ")
						: summary
				}}
			</template>
			<!-- Clear only: the default footer's Select All would go past the limit. -->
			<template #footer="{ clear }">
				<div class="flex justify-end p-1">
					<Button :label="__('Clear')" :disabled="!topics.length" @click="clear" />
				</div>
			</template>
		</MultiSelect>
	</section>
</template>
