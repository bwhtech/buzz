<script setup lang="ts">
import { Alert, ErrorMessage, toast, useDoc } from "frappe-ui"
import { computed, ref } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import TicketTypeFields from "@/components/dashboard/ticket-types/TicketTypeFields.vue"
import TicketTypeGuests from "@/components/dashboard/ticket-types/TicketTypeGuests.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import type { TicketCategoryItem, TicketTypeItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"
import {
	type TicketTypeValues,
	ticketTypeDocValues,
	ticketTypeError,
	ticketTypeValuesOf,
} from "@/utils/ticketTypeForm"

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
	() => props.ticketType && ticketTypeValuesOf(props.ticketType),
	save,
	{
		title: "Save ticket type",
		message: "Changes show on the booking page right away.",
		success: "Ticket type updated",
	},
)

const isInvalid = computed(() => !!ticketTypeError(draft.value))

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
	await ticketTypeDoc.setValue.submit(ticketTypeDocValues(values))
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

		<TicketTypeFields
			v-model="draft"
			:categories="categories"
			:paid-events-enabled="paidEventsEnabled"
			:hideable="!!shownTicketType.is_published"
			:locked-currencies="soldCurrencies"
			:disabled="!canWrite"
		/>

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
