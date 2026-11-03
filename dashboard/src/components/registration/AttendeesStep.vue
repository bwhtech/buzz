<template>
	<div class="flex flex-col gap-3 md:gap-4">
		<!-- No gap here: a closed Collapse would still leave one below the box. -->
		<div>
			<div
				class="flex flex-col gap-1 rounded-5 border border-outline-gray-1 bg-surface-gray-1 p-3.5 md:px-4"
			>
				<Checkbox
					:model-value="allForMe"
					:label="__('All tickets are for me')"
					@update:model-value="setAllForMe(Boolean($event))"
				/>
				<p class="pl-6 text-p-sm text-ink-gray-5 text-pretty">
					{{
						attendees.length === 1
							? __("Issue the ticket to {0}", [myName])
							: __("Issue all {0} tickets to {1} and skip the per-ticket forms", [
									attendees.length,
									myName,
								])
					}}
				</p>
			</div>

			<Collapse :open="allForMe">
				<section class="mt-3 overflow-hidden rounded-5 border border-outline-gray-2 md:mt-4">
					<h2
						class="border-b border-outline-gray-1 px-4 py-3 text-base font-semibold text-ink-gray-9"
					>
						{{ __("Your details") }}
					</h2>
					<div class="grid grid-cols-1 items-start gap-3.5 p-4 md:grid-cols-2">
						<CoreFieldInputs
							:fields="coreFields"
							:model="me"
							:errors="meErrors"
							:show-errors="showErrors"
							:size="inputSize"
							:required="requiredIdentity"
						/>
					</div>
					<div
						v-if="!hasExtras"
						class="flex flex-col gap-2 border-t border-outline-gray-1 px-4 pb-4 pt-3"
					>
						<h3 class="text-xs font-semibold uppercase tracking-[0.04em] text-ink-gray-5">
							{{ __("Issued to you") }}
						</h3>
						<ul class="flex flex-col gap-2">
							<li
								v-for="(attendee, index) in attendees"
								:key="attendee.id"
								class="flex justify-between gap-3 text-p-sm"
							>
								<span class="text-ink-gray-8">{{ __(titleOf(attendee)) }}</span>
								<span class="text-right text-ink-gray-5">{{ subtitle(attendee, index) }}</span>
							</li>
						</ul>
					</div>
				</section>
			</Collapse>
		</div>

		<AttendeeCard
			v-for="(attendee, index) in shownCards"
			:key="attendee.id"
			:attendee="attendee"
			:me="me"
			:index="index"
			:ticket-title="titleOf(attendee)"
			:subtitle="subtitle(attendee, index)"
			:add-ons="addOns"
			:custom-fields="fieldsFor(attendee)"
			:errors="errors[index]"
			:show-errors="showErrors"
			:core-fields="coreFields"
			:required-identity="requiredIdentity"
			:collapsible="collapsible"
			:open="openIndex === index"
			:has-next="index < attendees.length - 1"
			:identity-hidden="allForMe"
			@toggle="openIndex = openIndex === index ? -1 : index"
			@next="openIndex = index + 1"
			@update:is-me="setIsMe(attendee, $event)"
		/>
	</div>
</template>

<script setup lang="ts">
import { Checkbox } from "frappe-ui"
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
import CoreFieldInputs from "./CoreFieldInputs.vue"
import type { CoreField } from "./coreFields"

const props = defineProps<{
	attendees: BookingAttendee[]
	me: AttendeeIdentity
	meErrors: AttendeeErrors
	errors: AttendeeErrors[]
	ticketTypes: AvailableTicketType[]
	categories: BookingTicketCategory[]
	addOns: AvailableAddOn[]
	customFields: FrappeField[]
	// The questions one attendee is asked once rules have run.
	fieldsFor: (attendee: BookingAttendee) => FrappeField[]
	showErrors: boolean
	lastNameRequired: boolean
	coreFields: CoreField[]
	collapsible: boolean
}>()

const openIndex = ref(0)
const inputSize = computed(() => (props.collapsible ? "lg" : "sm"))
const requiredIdentity = computed(() =>
	props.lastNameRequired ? ["first_name", "last_name", "email"] : ["first_name", "email"],
)
const allForMe = computed(() => props.attendees.every((attendee) => attendee.is_me))
const myName = computed(() => `${props.me.first_name} ${props.me.last_name}`.trim() || __("you"))

// With every ticket issued to the registrant, cards remain only to ask for add-ons and fields.
const hasExtras = computed(() => props.addOns.length > 0 || props.customFields.length > 0)
const shownCards = computed(() => (allForMe.value && !hasExtras.value ? [] : props.attendees))

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

// Unticking hands the other tickets back to their own forms.
function setAllForMe(value: boolean) {
	props.attendees.forEach((attendee, index) => setIsMe(attendee, value || index === 0))
}

// A ticket that stops being the registrant's starts with an empty form.
function setIsMe(attendee: BookingAttendee, value: boolean) {
	if (attendee.is_me && !value)
		Object.assign(attendee, { first_name: "", last_name: "", email: "" })
	attendee.is_me = value
}

function titleOf(attendee: BookingAttendee) {
	return ticketTypesByName.value[String(attendee.ticket_type)]?.title ?? ""
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
