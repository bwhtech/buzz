<template>
	<div class="flex flex-col gap-3">
		<section class="flex items-center gap-3.5 rounded-5 border border-outline-gray-2 px-4 py-3">
			<DateBadge v-if="eventDetails.start_date" :date="eventDetails.start_date" />
			<div class="flex min-w-0 flex-col gap-0.5">
				<span class="text-base font-semibold text-ink-gray-9">{{ __(eventDetails.title) }}</span>
				<span class="text-p-sm text-ink-gray-5 text-pretty">{{ eventLine }}</span>
			</div>
		</section>

		<section class="overflow-hidden rounded-5 border border-outline-gray-2">
			<SummaryCardHeader :title="__('Tickets and attendees')" @edit="emit('edit', 'attendees')" />
			<ul>
				<li
					v-for="row in ticketRows"
					:key="row.key"
					class="flex items-center gap-3 border-outline-gray-1 px-4 py-3 [&:not(:first-child)]:border-t"
				>
					<Avatar :label="row.holder" size="md" class="flex-none" />
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-base font-semibold text-ink-gray-9">{{ row.holder }}</span>
						<span class="truncate text-p-sm text-ink-gray-5">{{ row.email }}</span>
						<div v-if="row.addOns.length" class="flex flex-wrap gap-1 pt-1">
							<Badge v-for="addOn in row.addOns" :key="addOn" theme="gray" variant="subtle">
								{{ addOn }}
							</Badge>
						</div>
					</div>
					<div class="flex flex-none flex-col items-end gap-0.5">
						<span class="text-p-sm text-ink-gray-8">{{ row.ticket }}</span>
						<span class="text-p-sm tabular-nums text-ink-gray-5">{{ row.price }}</span>
					</div>
				</li>
			</ul>
		</section>

		<section class="overflow-hidden rounded-5 border border-outline-gray-2">
			<SummaryCardHeader :title="__('Billing')" @edit="emit('edit', 'details')" />
			<dl class="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-x-4 gap-y-3 px-4 py-3">
				<div v-for="field in billingRows" :key="field.label" class="flex min-w-0 flex-col gap-0.5">
					<dt class="text-p-sm text-ink-gray-5">{{ field.label }}</dt>
					<dd class="text-base text-ink-gray-8 [overflow-wrap:anywhere]">{{ field.value }}</dd>
				</div>
			</dl>
		</section>

		<section class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-gray-1">
			<slot name="totals" />
		</section>

		<slot />
	</div>
</template>

<script setup lang="ts">
import { Avatar, Badge } from "frappe-ui"
import { computed } from "vue"

import DateBadge from "@/components/common/DateBadge.vue"
import type { BillingDetails } from "@/composables/useBookingFormStorage"
import type { AvailableAddOn, AvailableTicketType, BookingAttendee } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

import { taxIdFieldLabel } from "./registrationSteps"
import SummaryCardHeader from "./SummaryCardHeader.vue"
import { useEventDateLabels } from "./useEventDateLabels"
import type { RegistrationStepId } from "./useRegistrationSteps"

const props = defineProps<{
	eventDetails: Record<string, any>
	attendees: BookingAttendee[]
	me: { first_name: string; last_name: string; email: string }
	ticketTypesMap: Record<string, AvailableTicketType>
	addOnsMap: Record<string, AvailableAddOn>
	billing: BillingDetails
	invoiceShown: boolean
	taxLabel: string
	currency: string
	showCurrency: boolean
}>()
const emit = defineEmits<{ edit: [step: RegistrationStepId] }>()

const { dateLabel, timeLabel, venueLabel } = useEventDateLabels(() => props.eventDetails)
const eventLine = computed(() =>
	[dateLabel.value, timeLabel.value, venueLabel.value].filter(Boolean).join(" · "),
)

const ticketRows = computed(() =>
	props.attendees.map((attendee) => {
		const person = attendee.is_me ? props.me : attendee
		const ticketType = props.ticketTypesMap[String(attendee.ticket_type)]
		return {
			key: attendee.id,
			holder: `${person.first_name} ${person.last_name}`.trim(),
			email: person.email,
			addOns: addOnLabels(attendee),
			ticket: __(ticketType?.title ?? ""),
			price: formatWholePriceOrFree(attendeeAmount(attendee, ticketType), props.currency),
		}
	}),
)

function selectedAddOns(attendee: BookingAttendee) {
	return Object.entries(attendee.add_ons ?? {}).filter(
		([name, selection]) => selection.selected && props.addOnsMap[name],
	)
}

function addOnLabels(attendee: BookingAttendee) {
	return selectedAddOns(attendee).map(([name, selection]) => {
		const addOn = props.addOnsMap[name]
		const title = __(addOn?.title ?? "")
		return addOn?.user_selects_option && selection.option
			? `${title} · ${__(selection.option)}`
			: title
	})
}

function attendeeAmount(attendee: BookingAttendee, ticketType?: AvailableTicketType) {
	const addOnsTotal = selectedAddOns(attendee).reduce(
		(sum, [name]) => sum + (props.addOnsMap[name]?.price ?? 0),
		0,
	)
	return (ticketType?.price ?? 0) + addOnsTotal
}

const billingRows = computed(() => {
	const billing = props.billing
	const rows = [
		{ label: __("Name"), value: billing.buyer_name },
		{ label: __("Email"), value: billing.buyer_email },
		{ label: __("Phone"), value: billing.buyer_phone.replace("-", " ") || __("Not added") },
	]
	if (props.invoiceShown && billing.invoice_requested)
		rows.push(
			{ label: taxIdFieldLabel(props.taxLabel), value: billing.tax_id },
			{ label: __("Business Name"), value: billing.business_name },
			...(billing.billing_state ? [{ label: __("State"), value: billing.billing_state }] : []),
		)
	if (props.showCurrency) rows.push({ label: __("Currency"), value: props.currency })
	return rows
})
</script>
