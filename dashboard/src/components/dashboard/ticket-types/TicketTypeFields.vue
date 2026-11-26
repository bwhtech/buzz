<script setup lang="ts">
import { DatePicker, FormControl, Switch, Tooltip, dayjs } from "frappe-ui"
import { computed } from "vue"

import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import TicketCategoryCombobox from "@/components/dashboard/ticket-types/TicketCategoryCombobox.vue"
import type { TicketCategoryItem } from "@/types"
import type { TicketTypeValues } from "@/utils/ticketTypeForm"

const values = defineModel<TicketTypeValues>({ required: true })
const props = defineProps<{
	categories: TicketCategoryItem[]
	// Only a published ticket type can be hidden behind an access code.
	hideable: boolean
	lockedCurrencies?: string[]
	disabled?: boolean
}>()
defineEmits<{ categoryCreated: [] }>()

const hasSeatLimit = computed(() => values.value.max_tickets_available > 0)

const waitlistHint = computed(() =>
	hasSeatLimit.value
		? "People can request to join once seats run out"
		: "Ticket with unlimited seats cannot be waitlisted",
)

const closesIn = computed(() => {
	const date = values.value.auto_unpublish_after
	if (!date) return "Sells until the event starts"
	const days = dayjs(date).diff(dayjs().startOf("day"), "day")
	if (days < 0) return "Sales have closed"
	return days === 0 ? "Sales close today" : `Sales close in ${days} day${days === 1 ? "" : "s"}`
})
</script>

<template>
	<form novalidate class="space-y-4" @submit.prevent>
		<div v-if="hideable" class="rounded-4 border border-outline-gray-2 p-1">
			<Switch
				v-model="values.is_hidden"
				padded
				label="Hidden ticket"
				description="Only people with an access code can see it."
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
			:rows="2"
			:disabled="disabled"
		/>
		<TicketCategoryCombobox
			v-model="values.category"
			:categories="categories"
			:disabled="disabled"
			@created="$emit('categoryCreated')"
		/>
		<PriceList
			v-model="values.prices"
			:locked-currencies="lockedCurrencies"
			locked-message="This price has sales, so it can't change. To charge differently, disable this ticket type and add a new one."
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
		<div class="space-y-1.5">
			<DatePicker
				:model-value="values.auto_unpublish_after ?? ''"
				label="Auto close sales on"
				placeholder="Never"
				format="ddd, D MMM YYYY"
				:min="dayjs().format('YYYY-MM-DD')"
				clearable
				:disabled="disabled"
				@update:model-value="values.auto_unpublish_after = $event || null"
			/>
			<p class="text-p-xs tabular-nums text-ink-gray-5">{{ closesIn }}</p>
		</div>
		<fieldset class="space-y-2">
			<legend class="pb-2 text-sm font-semibold text-ink-gray-9">Access</legend>
			<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
				<div class="p-1">
					<Switch
						v-model="values.requires_approval"
						padded
						label="Require approval"
						description="Review guests for this ticket type before accepting them"
						:disabled="disabled"
					/>
				</div>
				<Tooltip text="Limit seats to use waitlist feature" :disabled="hasSeatLimit || disabled">
					<div class="p-1">
						<Switch
							:model-value="hasSeatLimit && values.enable_waitlist"
							padded
							label="Waitlist when sold out"
							:description="waitlistHint"
							:disabled="disabled || !hasSeatLimit"
							@update:model-value="values.enable_waitlist = $event"
						/>
					</div>
				</Tooltip>
			</div>
		</fieldset>
	</form>
</template>
