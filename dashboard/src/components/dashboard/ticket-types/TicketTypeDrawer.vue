<script setup lang="ts">
import { Alert, DatePicker, FormControl, toast, useDoc } from "frappe-ui"
import { computed } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import type { TicketTypeItem, TierPrice } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

type TicketTypeValues = {
	title: string
	prices: TierPrice[]
	max_tickets_available: number
	auto_unpublish_after: string | null
}

const props = defineProps<{ ticketType: TicketTypeItem | null; canWrite: boolean }>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [] }>()

const shownTicketType = keepLastValue(() => props.ticketType)

const ticketTypeDoc = useDoc<TicketTypeValues & { name: string; is_published: 0 | 1 }>({
	doctype: "Event Ticket Type",
	name: () => props.ticketType?.name ?? "",
	immediate: false,
})

const { draft, hasChanges, discardChanges, confirmAndSave } = useDrawerEdits<TicketTypeValues>(
	() => props.ticketType?.name,
	() => props.ticketType && toValues(props.ticketType),
	save,
	{
		title: "Save ticket type",
		message: "Changes show on the booking page right away.",
		success: "Ticket type updated",
	},
)

const isInvalid = computed(
	() =>
		!draft.value.title?.trim() ||
		draft.value.prices?.some((row) => !row.currency || !(row.price >= 0)),
)

// A price stops being editable once tickets sell in its currency.
const soldCurrencies = computed(() =>
	(props.ticketType?.prices ?? []).filter((row) => row.tickets_sold).map((row) => row.currency),
)

const defaultPrice = computed(() => {
	const row = props.ticketType?.prices[0]
	return row ? formatWholePriceOrFree(row.price, row.currency) : ""
})

const publishedAlert = computed(() =>
	props.ticketType?.is_published
		? { theme: "green" as const, title: "Ticket type is Enabled", action: "Disable" }
		: { theme: "amber" as const, title: "Ticket type is Disabled", action: "Enable" },
)

function toValues(ticketType: TicketTypeItem): TicketTypeValues {
	return {
		title: ticketType.title,
		prices: ticketType.prices.map(({ currency, price }) => ({ currency, price })),
		max_tickets_available: ticketType.max_tickets_available,
		auto_unpublish_after: ticketType.auto_unpublish_after,
	}
}

async function togglePublished() {
	if (!props.ticketType) return
	const enabling = !props.ticketType.is_published
	await ticketTypeDoc.setValue.submit({ is_published: enabling ? 1 : 0 })
	if (ticketTypeDoc.setValue.error) {
		toast.error("Could not update the ticket type. Try again.")
		return
	}
	toast.success(enabling ? "Ticket type enabled" : "Ticket type disabled")
	emit("changed")
}

async function save(values: TicketTypeValues) {
	await ticketTypeDoc.setValue.submit({ ...values, title: values.title.trim() })
	if (ticketTypeDoc.setValue.error) throw ticketTypeDoc.setValue.error
	emit("changed")
}
</script>

<template>
	<SponsorshipDrawer
		v-if="shownTicketType"
		v-model:open="open"
		:title="shownTicketType.title"
		:description="defaultPrice"
	>
		<template #notice>
			<Alert
				:theme="publishedAlert.theme"
				:title="publishedAlert.title"
				:primary-action="
					canWrite
						? {
								label: publishedAlert.action,
								variant: 'outline',
								theme: 'gray',
								loading: ticketTypeDoc.setValue.loading,
								onClick: togglePublished,
							}
						: undefined
				"
			/>
		</template>

		<form novalidate class="space-y-4" @submit.prevent>
			<FormControl
				v-model="draft.title"
				label="Name"
				required
				placeholder="General admission"
				autocomplete="off"
				:disabled="!canWrite"
			/>
			<PriceList
				v-model="draft.prices"
				:locked-currencies="soldCurrencies"
				locked-message="Tickets have sold at this price, so it can't be changed. To charge a different price, disable this ticket type and add a new one."
				:disabled="!canWrite"
			/>
			<FormControl
				:model-value="draft.max_tickets_available || ''"
				type="number"
				label="Seats"
				placeholder="Unlimited"
				:min="0"
				:disabled="!canWrite"
				@update:model-value="draft.max_tickets_available = Math.max(Number($event) || 0, 0)"
			/>
			<DatePicker
				:model-value="draft.auto_unpublish_after ?? ''"
				label="Auto Unpublish On"
				description="Leave empty to sell until the event starts."
				placeholder="Select date"
				clearable
				:disabled="!canWrite"
				@update:model-value="draft.auto_unpublish_after = $event || null"
			/>
		</form>

		<template v-if="canWrite && hasChanges" #footer>
			<DrawerSaveBar :disabled="isInvalid" @discard="discardChanges" @save="confirmAndSave" />
		</template>
	</SponsorshipDrawer>
</template>
