<template>
	<div class="flex flex-col gap-3 md:gap-4">
		<RegistrationPanel
			:title="__('Buyer')"
			:description="__('Order confirmation and invoice are sent here')"
		>
			<div class="grid grid-cols-1 items-start gap-3.5 md:grid-cols-2">
				<CoreFieldInputs
					:fields="coreFields"
					:model="billing"
					:errors="errors"
					:show-errors="showErrors"
					:size="inputSize"
					:required="requiredBuyer"
					:phone-error="phoneError"
				/>
			</div>
		</RegistrationPanel>

		<RegistrationPanel v-if="bookingCustomFields.length" :title="__('Booking information')">
			<CustomFieldsSection
				v-model="bookingCustomFieldsData"
				:custom-fields="bookingCustomFields"
				:show-title="false"
			/>
		</RegistrationPanel>

		<section v-if="showInvoice" class="overflow-hidden rounded-5 border border-outline-gray-2">
			<div class="flex flex-col gap-1 p-3.5 md:px-4">
				<Checkbox
					v-model="billing.invoice_requested"
					:label="__('I need a {0} invoice', [__(taxLabel)])"
				/>
				<p class="pl-6 text-p-sm text-ink-gray-5">
					{{ __("Add your {0} to claim input tax credit on this order", [taxIdLabel]) }}
				</p>
			</div>
			<Collapse :open="billing.invoice_requested">
				<div
					class="grid grid-cols-1 items-start gap-3.5 border-t border-outline-gray-1 p-4 md:grid-cols-2"
				>
					<FormControl
						:model-value="billing.tax_id"
						:label="taxIdLabel"
						:size="inputSize"
						:placeholder="isGst ? '29ABCDE1234F1Z5' : ''"
						:error="shown(errors.tax_id)"
						required
						@update:model-value="billing.tax_id = String($event).toUpperCase()"
					/>
					<FormControl
						v-model="billing.business_name"
						:label="__('Business Name')"
						:size="inputSize"
						:error="shown(errors.business_name)"
						required
						autocomplete="organization"
					/>
					<FormControl
						v-model="billing.billing_address"
						type="textarea"
						:label="__('Billing address')"
						:rows="2"
						autocomplete="street-address"
					/>
					<Combobox
						:model-value="billing.billing_state || null"
						:label="__('State')"
						:size="inputSize"
						:placeholder="__('Search state')"
						:options="INDIAN_STATES"
						open-on-click
						@update:model-value="billing.billing_state = String($event ?? '')"
					/>
				</div>
			</Collapse>
		</section>
	</div>
</template>

<script setup lang="ts">
import { Checkbox, Combobox, FormControl } from "frappe-ui"
import { computed } from "vue"

import type { BillingDetails } from "@/composables/useBookingFormStorage"
import type { FrappeField } from "@/composables/useCustomFields"

import CustomFieldsSection from "../CustomFieldsSection.vue"
import type { AttendeeErrors } from "./attendeeValidation"
import Collapse from "./Collapse.vue"
import CoreFieldInputs from "./CoreFieldInputs.vue"
import type { CoreField } from "./coreFields"
import { INDIAN_STATES } from "./indianStates"
import RegistrationPanel from "./RegistrationPanel.vue"
import { isGstLabel, taxIdFieldLabel } from "./registrationSteps"

const props = defineProps<{
	billing: BillingDetails
	phoneRequired: boolean
	phoneError: string
	coreFields: CoreField[]
	bookingCustomFields: FrappeField[]
	showInvoice: boolean
	taxLabel: string
	errors: AttendeeErrors
	showErrors: boolean
	large: boolean
}>()

const bookingCustomFieldsData = defineModel<Record<string, any>>("bookingCustomFieldsData", {
	required: true,
})

const isGst = computed(() => isGstLabel(props.taxLabel))
const taxIdLabel = computed(() => taxIdFieldLabel(props.taxLabel))
const inputSize = computed(() => (props.large ? "lg" : "sm"))
const requiredBuyer = computed(() =>
	props.phoneRequired
		? ["buyer_name", "buyer_email", "buyer_phone"]
		: ["buyer_name", "buyer_email"],
)
const shown = (error?: string) => (props.showErrors ? error : undefined)
</script>
