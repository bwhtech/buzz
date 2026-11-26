<script setup lang="ts" generic="TicketType extends { name: string; title: string }">
import { Checkbox, TextInput } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"

const selected = defineModel<string[]>({ required: true })
const props = defineProps<{
	ticketTypes: TicketType[]
	disabled?: boolean
	describe?: (ticketType: TicketType) => string
	isSelectable?: (ticketType: TicketType) => boolean
}>()

const search = ref("")
const shownTicketTypes = computed(() => {
	const typed = search.value.trim().toLowerCase()
	return props.ticketTypes.filter((row) => row.title.toLowerCase().includes(typed))
})
const noMatchText = computed(() => `No ticket type has "${search.value.trim()}" in its name.`)

function toggle(name: string, picked: boolean) {
	const others = selected.value.filter((row) => row !== name)
	selected.value = picked ? [...others, name] : others
}
</script>

<template>
	<div class="space-y-2">
		<TextInput v-model="search" type="search" placeholder="Search ticket types">
			<template #prefix>
				<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
			</template>
		</TextInput>
		<p class="text-p-xs tabular-nums text-ink-gray-5">
			{{ selected.length }} of {{ ticketTypes.length }} selected
		</p>
		<EmptyState
			v-if="!shownTicketTypes.length"
			class="rounded-4 border border-dashed border-outline-gray-2 !py-6"
			icon="lucide-search"
			title="No matches"
			:description="noMatchText"
			:action="{ label: 'Clear search', variant: 'subtle', onClick: () => (search = '') }"
		/>
		<div v-else class="max-h-72 overflow-y-auto rounded-4 border border-outline-gray-2 p-1">
			<Checkbox
				v-for="ticketType in shownTicketTypes"
				:key="ticketType.name"
				padded
				:label="ticketType.title"
				:description="describe?.(ticketType)"
				:model-value="selected.includes(ticketType.name)"
				:disabled="disabled || (isSelectable && !isSelectable(ticketType))"
				@update:model-value="toggle(ticketType.name, !!$event)"
			/>
		</div>
	</div>
</template>
