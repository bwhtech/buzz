<script setup lang="ts">
import {
	Alert,
	DatePicker,
	ErrorMessage,
	FormControl,
	Switch,
	dayjs,
	toast,
	useDoc,
} from "frappe-ui"
import { computed, ref } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import TicketTypeGuests from "@/components/dashboard/ticket-types/TicketTypeGuests.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import type { TicketCategoryItem, TicketTypeItem, TierPrice } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"

type TicketTypeValues = {
	title: string
	description: string
	category: string
	is_hidden: boolean
	prices: TierPrice[]
	max_tickets_available: number
	auto_unpublish_after: string | null
}

const props = defineProps<{
	event: string
	ticketType: TicketTypeItem | null
	categories: TicketCategoryItem[]
	canWrite: boolean
	paidEventsEnabled: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [] }>()

const shownTicketType = keepLastValue(() => props.ticketType)

const ticketTypeDoc = useDoc<
	Omit<TicketTypeValues, "is_hidden"> & { name: string; is_published: 0 | 1; is_hidden: 0 | 1 }
>({
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
		draft.value.prices?.some((row) => !row.currency || !(row.price >= 0)) ||
		draft.value.auto_unpublish_after === "",
)

// No field of its own: on while a date is set. Switching on leaves an empty date ("") for the
// organiser to pick; switching off clears it, so saving removes the date.
const autoUnpublish = computed<boolean>({
	get: () => draft.value.auto_unpublish_after != null,
	set: (on) => (draft.value.auto_unpublish_after = on ? "" : null),
})

const closesIn = computed(() => {
	const date = draft.value.auto_unpublish_after
	if (!date) return "Pick the last day to sell"
	const days = dayjs(date).diff(dayjs().startOf("day"), "day")
	if (days < 0) return "Sales have closed"
	return days === 0 ? "Sales close today" : `Sales close in ${days} day${days === 1 ? "" : "s"}`
})

// A price stops being editable once tickets sell in its currency.
const soldCurrencies = computed(() =>
	(props.ticketType?.prices ?? []).filter((row) => row.tickets_sold).map((row) => row.currency),
)

const defaultPrice = computed(() => {
	const row = props.ticketType?.prices[0]
	return row ? formatWholePriceOrFree(row.price, row.currency) : ""
})

const categoryOptions = computed(() => [
	{ label: "Uncategorized", value: "" },
	...props.categories.map((category) => ({ label: category.title, value: category.name })),
])

const publishedAlert = computed(() =>
	props.ticketType?.is_published
		? { theme: "green" as const, title: "Ticket type is Enabled", action: "Disable" }
		: { theme: "amber" as const, title: "Ticket type is Disabled", action: "Enable" },
)

function toValues(ticketType: TicketTypeItem): TicketTypeValues {
	return {
		title: ticketType.title,
		description: ticketType.description ?? "",
		category: ticketType.category ?? "",
		is_hidden: ticketType.is_hidden,
		prices: ticketType.prices.map(({ currency, price }) => ({ currency, price })),
		max_tickets_available: ticketType.max_tickets_available,
		auto_unpublish_after: ticketType.auto_unpublish_after,
	}
}

const publishError = ref("")

async function togglePublished() {
	if (!props.ticketType) return
	const enabling = !props.ticketType.is_published
	publishError.value = ""
	await ticketTypeDoc.setValue.submit({ is_published: enabling ? 1 : 0 }).catch(() => null)
	if (ticketTypeDoc.setValue.error) {
		publishError.value =
			serverErrorMessage(ticketTypeDoc.setValue.error) ||
			"Could not update the ticket type. Try again."
		return
	}
	toast.success(enabling ? "Ticket type enabled" : "Ticket type disabled")
	emit("changed")
}

async function save(values: TicketTypeValues) {
	await ticketTypeDoc.setValue.submit({
		...values,
		is_hidden: values.is_hidden ? 1 : 0,
		title: values.title.trim(),
		description: values.description.trim(),
	})
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
			<ErrorMessage class="mt-2" :message="publishError" />
		</template>

		<form novalidate class="space-y-4" @submit.prevent>
			<div v-if="shownTicketType.is_published" class="rounded-4 border border-outline-gray-2 p-1">
				<Switch
					v-model="draft.is_hidden"
					padded
					label="Hidden — only available with an access code"
					description="Not shown on the booking page until a participant enters a valid access code."
					:disabled="!canWrite"
				/>
			</div>
			<FormControl
				v-model="draft.title"
				label="Name"
				required
				placeholder="General admission"
				autocomplete="off"
				:disabled="!canWrite"
			/>
			<FormControl
				v-model="draft.description"
				type="textarea"
				label="Description"
				placeholder="Talks, expo and lunch on both days"
				description="Shown below the name on the booking page."
				:rows="2"
				:disabled="!canWrite"
			/>
			<FormControl
				v-if="categories.length"
				v-model="draft.category"
				type="select"
				label="Category"
				:options="categoryOptions"
				:disabled="!canWrite"
			/>
			<PriceList
				v-if="paidEventsEnabled"
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
			<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
				<div class="p-1">
					<Switch
						v-model="autoUnpublish"
						padded
						label="Close sales automatically"
						description="When off, it sells until the event starts."
						:disabled="!canWrite"
					/>
				</div>
				<div v-if="autoUnpublish" class="grid grid-cols-2 items-end gap-3 p-3">
					<DatePicker
						:model-value="draft.auto_unpublish_after ?? ''"
						label="Auto Unpublish On"
						placeholder="Select date"
						format="ddd, D MMM YYYY"
						:min="dayjs().format('YYYY-MM-DD')"
						:disabled="!canWrite"
						@update:model-value="draft.auto_unpublish_after = $event"
					/>
					<p class="pb-1.5 text-sm tabular-nums text-ink-gray-6">{{ closesIn }}</p>
				</div>
			</div>
		</form>

		<TicketTypeGuests
			v-if="shownTicketType.tickets_sold"
			:event="event"
			:ticket-type="shownTicketType.name"
			:count="shownTicketType.tickets_sold"
		/>
		<p v-else class="w-full rounded-4 bg-surface-gray-1 p-4 text-base text-ink-gray-5">
			No one has bought this ticket yet.
		</p>

		<template v-if="canWrite && hasChanges" #footer>
			<DrawerSaveBar :disabled="isInvalid" @discard="discardChanges" @save="confirmAndSave" />
		</template>
	</SponsorshipDrawer>
</template>
