<script setup lang="ts">
import { DatePicker, FormControl, Switch, dayjs } from "frappe-ui"
import { computed } from "vue"

import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import type { TicketCategoryItem } from "@/types"
import type { TicketTypeValues } from "@/utils/ticketTypeForm"

const values = defineModel<TicketTypeValues>({ required: true })
const props = defineProps<{
	categories: TicketCategoryItem[]
	paidEventsEnabled: boolean
	// Only a published ticket type can be hidden behind an access code.
	hideable: boolean
	lockedCurrencies?: string[]
	disabled?: boolean
}>()

// No field of its own: on while a date is set. Switching on leaves an empty date ("") for the
// organiser to pick; switching off clears it, so saving removes the date.
const autoUnpublish = computed<boolean>({
	get: () => values.value.auto_unpublish_after != null,
	set: (on) => (values.value.auto_unpublish_after = on ? "" : null),
})

const closesIn = computed(() => {
	const date = values.value.auto_unpublish_after
	if (!date) return "Pick the last day to sell"
	const days = dayjs(date).diff(dayjs().startOf("day"), "day")
	if (days < 0) return "Sales have closed"
	return days === 0 ? "Sales close today" : `Sales close in ${days} day${days === 1 ? "" : "s"}`
})

const categoryOptions = computed(() => [
	{ label: "Uncategorized", value: "" },
	...props.categories.map((category) => ({ label: category.title, value: category.name })),
])
</script>

<template>
	<form novalidate class="space-y-4" @submit.prevent>
		<div v-if="hideable" class="rounded-4 border border-outline-gray-2 p-1">
			<Switch
				v-model="values.is_hidden"
				padded
				label="Hidden Ticket"
				description="Participants see this ticket only after they enter an access code."
				:disabled="disabled"
			/>
		</div>
		<FormControl
			v-model="values.title"
			label="Name"
			required
			placeholder="General admission"
			autocomplete="off"
			:disabled="disabled"
		/>
		<FormControl
			v-model="values.description"
			type="textarea"
			label="Description"
			placeholder="Talks, expo and lunch on both days"
			description="Shown below the name on the booking page."
			:rows="2"
			:disabled="disabled"
		/>
		<FormControl
			v-if="categories.length"
			v-model="values.category"
			type="select"
			label="Category"
			:options="categoryOptions"
			:disabled="disabled"
		/>
		<PriceList
			v-if="paidEventsEnabled"
			v-model="values.prices"
			:locked-currencies="lockedCurrencies"
			locked-message="Tickets have sold at this price, so it can't be changed. To charge a different price, disable this ticket type and add a new one."
			:disabled="disabled"
		/>
		<FormControl
			:model-value="values.max_tickets_available || ''"
			type="number"
			label="Seats"
			placeholder="Unlimited"
			:min="0"
			:disabled="disabled"
			@update:model-value="values.max_tickets_available = Math.max(Number($event) || 0, 0)"
		/>
		<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
			<div class="p-1">
				<Switch
					v-model="autoUnpublish"
					padded
					label="Close sales automatically"
					description="When off, it sells until the event starts."
					:disabled="disabled"
				/>
			</div>
			<div v-if="autoUnpublish" class="grid grid-cols-2 items-end gap-3 p-3">
				<DatePicker
					:model-value="values.auto_unpublish_after ?? ''"
					label="Auto Unpublish On"
					placeholder="Select date"
					format="ddd, D MMM YYYY"
					:min="dayjs().format('YYYY-MM-DD')"
					:disabled="disabled"
					@update:model-value="values.auto_unpublish_after = $event"
				/>
				<p class="pb-1.5 text-sm tabular-nums text-ink-gray-6">{{ closesIn }}</p>
			</div>
		</div>
	</form>
</template>
