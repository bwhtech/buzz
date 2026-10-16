<template>
	<article
		class="overflow-hidden rounded-[14px] border border-outline-gray-2 bg-surface-base md:rounded-7"
	>
		<button
			v-if="collapsible"
			type="button"
			class="flex min-h-[60px] w-full items-center gap-3 px-3.5 py-2.5 text-left active:bg-surface-gray-1"
			:aria-expanded="open"
			@click="emit('toggle')"
		>
			<LucideCircleCheck v-if="isComplete" class="size-[18px] flex-none text-ink-green-6" />
			<LucideCircleDashed v-else class="size-[18px] flex-none text-ink-gray-4" />
			<div class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-base font-semibold text-ink-gray-9">{{ displayName }}</span>
				<span class="truncate text-p-sm text-ink-gray-5"
					>{{ __(ticketTitle) }} · {{ subtitle }}</span
				>
			</div>
			<LucideChevronDown
				class="size-[18px] flex-none text-ink-gray-5 transition-transform duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]"
				:class="{ 'rotate-180': open }"
			/>
		</button>
		<div v-else class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3">
			<span
				class="flex size-6 flex-none items-center justify-center rounded-4 bg-surface-gray-2 text-xs font-semibold text-ink-gray-6"
			>
				{{ index + 1 }}
			</span>
			<div class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-base font-semibold text-ink-gray-9">{{ __(ticketTitle) }}</span>
				<span class="truncate text-p-sm text-ink-gray-5">{{ subtitle }}</span>
			</div>
			<Checkbox
				:model-value="attendee.is_me"
				:label="__('This is me')"
				@update:model-value="emit('update:isMe', Boolean($event))"
			/>
		</div>

		<Collapse :open="!collapsible || open">
			<div
				class="flex flex-col gap-3 p-3.5 md:p-4"
				:class="{ 'border-t border-outline-gray-1': collapsible }"
			>
				<Checkbox
					v-if="collapsible"
					:model-value="attendee.is_me"
					:label="__('This is me')"
					@update:model-value="emit('update:isMe', Boolean($event))"
				/>
				<div
					class="grid grid-cols-1 items-start gap-3.5 md:grid-cols-[repeat(auto-fit,minmax(200px,1fr))]"
				>
					<FormControl
						v-model="attendee.first_name"
						:label="__('First name')"
						:size="inputSize"
						:disabled="attendee.is_me"
						:error="showErrors ? errors.first_name : undefined"
						required
						autocomplete="given-name"
					/>
					<FormControl
						v-model="attendee.last_name"
						:label="__('Last name')"
						:size="inputSize"
						:disabled="attendee.is_me"
						:error="showErrors ? errors.last_name : undefined"
						:required="lastNameRequired"
						autocomplete="family-name"
					/>
					<FormControl
						v-model="attendee.email"
						type="email"
						:label="__('Email')"
						:size="inputSize"
						:disabled="attendee.is_me"
						:error="showErrors ? errors.email : undefined"
						required
						autocomplete="email"
					/>
					<CustomFieldInput
						v-for="field in customFields"
						:key="field.fieldname"
						:field="field"
						:model-value="attendee.custom_fields?.[field.fieldname] ?? ''"
						@update:model-value="setCustomField(field.fieldname, $event)"
					/>
				</div>
				<AttendeeAddOns v-if="addOns.length" :attendee="attendee" :add-ons="addOns" />
				<Button
					v-if="collapsible && hasNext"
					variant="subtle"
					size="lg"
					icon-right="lucide-arrow-down"
					class="w-full"
					@click="emit('next')"
				>
					{{ __("Next ticket") }}
				</Button>
			</div>
		</Collapse>
	</article>
</template>

<script setup lang="ts">
import { Button, Checkbox, FormControl } from "frappe-ui"
import { computed } from "vue"
import LucideChevronDown from "~icons/lucide/chevron-down"
import LucideCircleCheck from "~icons/lucide/circle-check"
import LucideCircleDashed from "~icons/lucide/circle-dashed"

import type { FrappeField } from "@/composables/useCustomFields"
import type { AvailableAddOn, BookingAttendee } from "@/types"

import CustomFieldInput from "../CustomFieldInput.vue"
import AttendeeAddOns from "./AttendeeAddOns.vue"
import type { AttendeeErrors } from "./attendeeValidation"
import Collapse from "./Collapse.vue"

const props = defineProps<{
	attendee: BookingAttendee
	index: number
	ticketTitle: string
	subtitle: string
	addOns: AvailableAddOn[]
	customFields: FrappeField[]
	errors: AttendeeErrors
	showErrors: boolean
	lastNameRequired: boolean
	collapsible?: boolean
	open?: boolean
	hasNext?: boolean
}>()
const emit = defineEmits<{ toggle: []; next: []; "update:isMe": [isMe: boolean] }>()

const inputSize = computed(() => (props.collapsible ? "lg" : "sm"))
const isComplete = computed(() => !Object.keys(props.errors).length)
const displayName = computed(
	() => `${props.attendee.first_name} ${props.attendee.last_name}`.trim() || __("Unassigned"),
)

function setCustomField(fieldname: string, value: unknown) {
	props.attendee.custom_fields = { ...props.attendee.custom_fields, [fieldname]: value }
}
</script>
