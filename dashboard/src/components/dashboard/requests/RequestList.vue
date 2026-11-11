<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import SelectionBar from "@/components/common/SelectionBar.vue"
import { useRowSelection } from "@/composables/useRowSelection"
import type { RegistrationRequest, RequestType } from "@/types"
import { OPEN_VIEW, type RequestAction, type RequestView } from "@/utils/requestStatus"

import RequestRow from "./RequestRow.vue"

const props = defineProps<{
	type: RequestType
	rows: RegistrationRequest[]
	viewOf: (row: RegistrationRequest) => RequestView
	selectedName: string | null
	showStatus: boolean
}>()
const emit = defineEmits<{
	open: [name: string]
	act: [action: RequestAction, rows: RegistrationRequest[]]
}>()

const openRows = computed(() =>
	props.rows.filter((row) => props.viewOf(row) === OPEN_VIEW[props.type]),
)
const selection = useRowSelection(computed(() => openRows.value.map((row) => row.name)))
const chosen = computed(() => openRows.value.filter((row) => selection.isSelected(row.name)))
const allChosen = computed(() => chosen.value.length === openRows.value.length)
const waitlist = computed(() => props.type === "Waitlist")

// A selection is spent once it has been acted on.
function actOnChosen(action: RequestAction) {
	emit("act", action, chosen.value)
	selection.clear()
}
</script>

<template>
	<div class="relative">
		<SelectionBar
			:count="chosen.length"
			:label="`${chosen.length} selected`"
			@clear="selection.clear()"
		>
			<Button
				variant="ghost"
				:label="allChosen ? 'Deselect all' : `Select all ${openRows.length}`"
				@click="allChosen ? selection.clear() : selection.selectAll()"
			/>
			<Button
				icon-left="lucide-x"
				:label="waitlist ? 'Remove' : 'Decline'"
				@click="actOnChosen('decline')"
			/>
			<Button
				variant="solid"
				icon-left="lucide-check"
				:label="waitlist ? 'Let in' : 'Approve'"
				@click="actOnChosen('approve')"
			/>
		</SelectionBar>

		<TransitionGroup
			tag="ul"
			name="request"
			class="divide-y divide-outline-gray-1 overflow-hidden rounded-6 border border-outline-gray-2"
		>
			<RequestRow
				v-for="row in rows"
				:key="row.name"
				:request="row"
				:view="viewOf(row)"
				:selected="row.name === selectedName"
				:checked="selection.isSelected(row.name)"
				:selecting="chosen.length > 0"
				:show-status="showStatus"
				@open="emit('open', row.name)"
				@toggle="selection.toggle(row.name)"
				@approve="emit('act', 'approve', [row])"
				@decline="emit('act', 'decline', [row])"
			/>
		</TransitionGroup>

		<div class="relative mt-6 flex justify-center">
			<span
				class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-surface-gray-2"
				aria-hidden="true"
			/>
			<p
				class="relative bg-surface-elevation-1 px-4 py-1 text-xs italic text-ink-gray-4 font-serif"
			>
				End of list
			</p>
		</div>
	</div>
</template>

<style scoped>
/* A decided row slides out of the view instead of vanishing under the pointer. */
.request-leave-active {
	transition:
		opacity 200ms ease-out,
		transform 260ms cubic-bezier(0.23, 1, 0.32, 1);
}

.request-leave-to {
	opacity: 0;
	transform: translateX(12px);
}

@media (prefers-reduced-motion: reduce) {
	.request-leave-active {
		transition: opacity 150ms ease-out;
	}

	.request-leave-to {
		transform: none;
	}
}
</style>
