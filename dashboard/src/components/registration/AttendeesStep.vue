<template>
	<div class="flex flex-col gap-3 md:gap-4">
		<div
			class="flex flex-col gap-1 rounded-[14px] border border-outline-gray-1 bg-surface-gray-1 p-3.5 md:rounded-7 md:px-4"
		>
			<Checkbox
				:model-value="allForMe"
				:indeterminate="someForMe && !allForMe"
				:label="__('All tickets are for me')"
				@update:model-value="setAllForMe(Boolean($event))"
			/>
			<p class="pl-6 text-p-sm text-ink-gray-5 text-pretty">
				{{ __("Issue all {0} tickets to you and fill your details once", [attendees.length]) }}
			</p>
		</div>

		<Collapse :open="someForMe">
			<section class="overflow-hidden rounded-[14px] border border-outline-gray-2 md:rounded-7">
				<h2
					class="border-b border-outline-gray-1 px-4 py-3 text-base font-semibold text-ink-gray-9"
				>
					{{ __("Your details") }}
				</h2>
				<div class="grid grid-cols-1 items-start gap-3.5 p-4 md:grid-cols-3">
					<FormControl
						v-model="me.first_name"
						:label="__('First name')"
						:size="inputSize"
						:error="showErrors ? meErrors.first_name : undefined"
						required
						autocomplete="given-name"
					/>
					<FormControl
						v-model="me.last_name"
						:label="__('Last name')"
						:size="inputSize"
						:error="showErrors ? meErrors.last_name : undefined"
						:required="lastNameRequired"
						autocomplete="family-name"
					/>
					<FormControl
						v-model="me.email"
						type="email"
						:label="__('Email')"
						:size="inputSize"
						:error="showErrors ? meErrors.email : undefined"
						required
						autocomplete="email"
					/>
				</div>
			</section>
		</Collapse>

		<AttendeeCard
			v-for="(attendee, index) in attendees"
			:key="attendee.id"
			:attendee="attendee"
			:index="index"
			:ticket-title="ticketTypesByName[String(attendee.ticket_type)]?.title ?? ''"
			:subtitle="subtitle(attendee, index)"
			:add-ons="addOns"
			:custom-fields="customFields"
			:errors="errors[index]"
			:show-errors="showErrors"
			:last-name-required="lastNameRequired"
			:collapsible="collapsible"
			:open="openIndex === index"
			:has-next="index < attendees.length - 1"
			@toggle="openIndex = openIndex === index ? -1 : index"
			@next="openIndex = index + 1"
			@update:is-me="attendee.is_me = $event"
		/>
	</div>
</template>

<script setup lang="ts">
import { Checkbox, FormControl } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { FrappeField } from "@/composables/useCustomFields"
import type {
	AvailableAddOn,
	AvailableTicketType,
	BookingAttendee,
	BookingTicketCategory,
} from "@/types"

import AttendeeCard from "./AttendeeCard.vue"
import type { AttendeeErrors, AttendeeIdentity } from "./attendeeValidation"
import Collapse from "./Collapse.vue"

const props = defineProps<{
	attendees: BookingAttendee[]
	me: AttendeeIdentity
	meErrors: AttendeeErrors
	errors: AttendeeErrors[]
	ticketTypes: AvailableTicketType[]
	categories: BookingTicketCategory[]
	addOns: AvailableAddOn[]
	customFields: FrappeField[]
	showErrors: boolean
	lastNameRequired: boolean
	collapsible: boolean
}>()

const openIndex = ref(0)
const inputSize = computed(() => (props.collapsible ? "lg" : "sm"))
const allForMe = computed(() => props.attendees.every((attendee) => attendee.is_me))
const someForMe = computed(() => props.attendees.some((attendee) => attendee.is_me))

const ticketTypesByName = computed(() =>
	Object.fromEntries(props.ticketTypes.map((ticketType) => [String(ticketType.name), ticketType])),
)
const categoryTitles = computed(() =>
	Object.fromEntries(props.categories.map((category) => [category.name, category.title])),
)

// A failed Continue opens the first card that still needs something.
watch(
	() => props.showErrors && props.errors.findIndex((error) => Object.keys(error).length),
	(firstInvalid) => {
		if (typeof firstInvalid === "number" && firstInvalid >= 0) openIndex.value = firstInvalid
	},
)

function setAllForMe(value: boolean) {
	for (const attendee of props.attendees) attendee.is_me = value
}

function subtitle(attendee: BookingAttendee, index: number) {
	const ticketType = String(attendee.ticket_type)
	const sameType = props.attendees.filter((other) => String(other.ticket_type) === ticketType)
	const category = categoryTitles.value[ticketTypesByName.value[ticketType]?.category ?? ""]
	const position =
		sameType.length > 1
			? __("{0} of {1}", [sameType.indexOf(props.attendees[index]) + 1, sameType.length])
			: ""
	return (
		[category && __(category), position].filter(Boolean).join(" · ") ||
		__("Ticket {0}", [index + 1])
	)
}
</script>
