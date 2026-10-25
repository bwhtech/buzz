<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core"
import { Button, TabButtons } from "frappe-ui"

import ListSection from "@/components/common/ListSection.vue"
import { useIsMobile } from "@/composables/useIsMobile"
import type { TicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import type { EventTicketTypes, TicketCategoryItem } from "@/types"
import { salesLabel } from "@/utils/ticketTypeLabels"

import TicketTypeBoard from "./TicketTypeBoard.vue"
import TicketTypeChips from "./TicketTypeChips.vue"
import TicketTypeGroups from "./TicketTypeGroups.vue"
import TicketTypeRow from "./TicketTypeRow.vue"

defineProps<{ page: EventTicketTypes; organizer: TicketTypeOrganizer }>()
defineEmits<{
	open: [name: string]
	add: [category: string]
	addCategory: []
	editCategory: [category: TicketCategoryItem]
}>()

const isMobile = useIsMobile()
const view = useLocalStorage<"list" | "grouped" | "board">("buzz-ticket-types-view", "grouped")
const viewOptions = [
	{ value: "list", iconLeft: "lucide-list", label: "List" },
	{ value: "grouped", iconLeft: "lucide-rows-3", label: "Grouped" },
	{ value: "board", iconLeft: "lucide-kanban", label: "Board" },
]
</script>

<template>
	<ListSection
		title="Ticket Types"
		description="Types of tickets that a participant can buy for this event"
		:count="page.ticket_types.length"
		:empty="!page.ticket_types.length && !page.categories.length"
		empty-title="No ticket types yet"
		empty-description="Add one so people can register."
		empty-icon="lucide-ticket"
		:empty-action="
			page.can_write
				? { label: 'Add ticket type', iconLeft: 'lucide-plus', onClick: () => $emit('add', '') }
				: null
		"
	>
		<template #toolbar>
			<div class="flex items-center gap-2">
				<TabButtons v-if="!isMobile" v-model="view" :options="viewOptions" />
				<Button
					v-if="page.can_write && !isMobile"
					class="ml-auto"
					variant="outline"
					icon-left="lucide-folder-plus"
					label="New Category"
					@click="$emit('addCategory')"
				/>
			</div>
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
		<ul v-else-if="view === 'list'" class="space-y-2">
			<li v-for="ticketType in page.ticket_types" :key="ticketType.name">
				<TicketTypeRow
					:ticket-type="ticketType"
					:subtitle="
						organizer.categoryOf(ticketType)
							? `${organizer.titleOf(organizer.categoryOf(ticketType))} · ${salesLabel(ticketType)}`
							: undefined
					"
					:disabled="!page.can_write"
					@click="$emit('open', ticketType.name)"
				/>
			</li>
			<li v-if="page.can_write">
				<Button
					variant="ghost"
					icon-left="lucide-plus"
					label="Add ticket type"
					@click="$emit('add', '')"
				/>
			</li>
		</ul>
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
