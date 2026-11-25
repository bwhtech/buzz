<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core"
import { type ButtonProps, Dropdown, TabButtons } from "frappe-ui"
import { computed } from "vue"

import ListSection from "@/components/common/ListSection.vue"
import { useIsMobile } from "@/composables/useIsMobile"
import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { EventTicketTypes, TicketCategoryItem } from "@/types"

import TicketTypeBoard from "./TicketTypeBoard.vue"
import TicketTypeChips from "./TicketTypeChips.vue"
import TicketTypeGroups from "./TicketTypeGroups.vue"

const props = defineProps<{ page: EventTicketTypes; organizer: TicketTypeOrganizer }>()
const emit = defineEmits<{
	open: [name: string]
	add: [category: string]
	addCategory: []
	editCategory: [category: TicketCategoryItem]
}>()

const isMobile = useIsMobile()
const view = useLocalStorage<string>("buzz-ticket-types-view", "grouped")
// The list view is gone; a stored "list" falls back to grouped.
if (view.value !== "board") view.value = "grouped"
const viewOptions = [
	{ value: "grouped", iconLeft: "lucide-rows-3", label: "Grouped" },
	{ value: "board", iconLeft: "lucide-kanban", label: "Board" },
]

const isEmpty = computed(() => !props.page.ticket_types.length && !props.page.categories.length)
const addButton: ButtonProps = {
	label: "Add",
	variant: "subtle",
	iconLeft: "lucide-plus",
	iconRight: "lucide-chevron-down",
}
const addOptions = [
	{ label: "Ticket type", icon: "lucide-ticket", onClick: () => emit("add", "") },
	{ label: "Category", icon: "lucide-folder", onClick: () => emit("addCategory") },
]
</script>

<template>
	<ListSection
		title="Ticket Types"
		description="Set prices, seat limits and sale dates for each ticket type."
		:count="page.ticket_types.length"
		:empty="isEmpty"
		empty-title="No tickets yet"
		empty-icon="lucide-ticket"
	>
		<template v-if="!isEmpty && !isMobile" #actions>
			<TabButtons v-model="view" :options="viewOptions" />
			<Dropdown v-if="page.can_write" :button="addButton" :options="addOptions" align="end" />
		</template>
		<template #emptyDescription>
			People pick a ticket to register.<br />
			Tickets can be grouped under a
			<code>Category</code>
		</template>
		<template v-if="page.can_write" #emptyAction>
			<Dropdown :button="addButton" :options="addOptions" />
		</template>

		<TicketTypeChips
			v-if="isMobile"
			:organizer="organizer"
			:can-write="page.can_write"
			@open="$emit('open', $event)"
			@add="$emit('add', $event)"
			@add-category="$emit('addCategory')"
			@edit-category="$emit('editCategory', $event)"
		/>
		<component
			:is="view === 'board' ? TicketTypeBoard : TicketTypeGroups"
			v-else
			:organizer="organizer"
			:can-write="page.can_write"
			@open="$emit('open', $event)"
			@add="$emit('add', $event)"
			@edit-category="$emit('editCategory', $event)"
		/>
	</ListSection>
</template>
