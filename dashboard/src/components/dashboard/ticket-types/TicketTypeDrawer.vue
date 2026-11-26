<script setup lang="ts">
import { useDoc } from "frappe-ui"
import { computed } from "vue"

import DrawerSection from "@/components/dashboard/DrawerSection.vue"
import EnabledAlert from "@/components/dashboard/EnabledAlert.vue"
import TicketTypeRequestsLink from "@/components/dashboard/requests/TicketTypeRequestsLink.vue"
import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import TicketTypeFields from "@/components/dashboard/ticket-types/TicketTypeFields.vue"
import TicketTypeGuests from "@/components/dashboard/ticket-types/TicketTypeGuests.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import { useSetTicketTypeAccess } from "@/data/ticketTypes"
import type { TicketCategoryItem, TicketTypeItem } from "@/types"
import { type TicketTypeAccess, accessChanged, withEventAccess } from "@/utils/approvalMode"
import { formatWholePriceOrFree } from "@/utils/currency"
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
	access: TicketTypeAccess
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [] }>()

const shownTicketType = keepLastValue(() => props.ticketType)

const ticketTypeDoc = useDoc<
	Omit<TicketTypeValues, "is_hidden" | "requires_approval" | "enable_waitlist"> & {
		name: string
		is_published: 0 | 1
		is_hidden: 0 | 1
		requires_approval: 0 | 1
		enable_waitlist: 0 | 1
	}
>({
	doctype: "Event Ticket Type",
	name: () => props.ticketType?.name ?? "",
	immediate: false,
})

const savedValues = computed(
	() => props.ticketType && withEventAccess(ticketTypeValuesOf(props.ticketType), props.access),
)
const accessSetter = useSetTicketTypeAccess()

const { draft, hasChanges, discardChanges, confirmAndSave } = useDrawerEdits<TicketTypeValues>(
	() => props.ticketType?.name,
	() => savedValues.value,
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

async function save(values: TicketTypeValues) {
	await ticketTypeDoc.setValue.submit(ticketTypeDocValues(values))
	if (ticketTypeDoc.setValue.error) throw ticketTypeDoc.setValue.error
	try {
		if (savedValues.value && accessChanged(savedValues.value, values))
			await accessSetter.save(props.ticketType!.name, values)
	} finally {
		emit("changed")
	}
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
			<EnabledAlert
				noun="Ticket type"
				:enabled="!!shownTicketType.is_published"
				:editable="canWrite"
				field="is_published"
				:set-value="ticketTypeDoc.setValue"
				@changed="emit('changed')"
			/>
		</template>

		<TicketTypeFields
			v-model="draft"
			:categories="categories"
			:hideable="!!shownTicketType.is_published"
			:locked-currencies="soldCurrencies"
			:disabled="!canWrite"
			@category-created="emit('changed')"
		/>

		<DrawerSection title="Guests">
			<TicketTypeRequestsLink v-if="canWrite" :event="event" :ticket-type="shownTicketType.title" />

			<TicketTypeGuests
				v-if="shownTicketType.tickets_sold"
				:event="event"
				:ticket-type="shownTicketType.name"
				:count="shownTicketType.tickets_sold"
			/>
			<p v-else class="w-full rounded-4 bg-surface-gray-1 p-4 text-base text-ink-gray-5">
				No confirmed guests yet.
			</p>
		</DrawerSection>

		<template v-if="canWrite && hasChanges" #footer>
			<DrawerSaveBar :disabled="isInvalid" @discard="discardChanges" @save="confirmAndSave" />
		</template>
	</SponsorshipDrawer>
</template>
