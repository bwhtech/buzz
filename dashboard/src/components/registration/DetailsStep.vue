<template>
	<div class="flex flex-col gap-3 md:gap-4">
		<RegistrationPanel
			v-if="showBuyer"
			:title="__('Buyer')"
			:description="__('Your confirmation and invoice are sent here')"
		>
			<div class="grid grid-cols-1 items-start gap-3.5 md:grid-cols-2">
				<FormControl
					v-model="buyer.first_name"
					:label="__('First name')"
					:size="inputSize"
					:error="shown(errors.first_name)"
					required
					autocomplete="given-name"
				/>
				<FormControl
					v-model="buyer.last_name"
					:label="__('Last name')"
					:size="inputSize"
					:error="shown(errors.last_name)"
					:required="lastNameRequired"
					autocomplete="family-name"
				/>
				<FormControl
					v-model="buyer.email"
					type="email"
					:label="__('Email')"
					:size="inputSize"
					:error="shown(errors.email)"
					required
					autocomplete="email"
				/>
				<PhoneInput
					v-if="needsPhone"
					v-model="buyer.phone"
					:placeholder="__('Enter your phone number')"
					:label="__('Phone')"
					:error="phoneError || shown(errors.phone)"
					required
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

		<section
			v-if="showInvoice"
			class="overflow-hidden rounded-[14px] border border-outline-gray-2 md:rounded-7"
		>
			<div class="flex flex-col gap-1 p-3.5 md:px-4">
				<Checkbox v-model="invoiceRequested" :label="__('I need a tax invoice')" />
				<p class="pl-6 text-p-sm text-ink-gray-5">
					{{ __("Add your {0} number to get an invoice for this order", [__(taxLabel)]) }}
				</p>
			</div>
			<Collapse :open="invoiceRequested">
				<div
					class="grid grid-cols-1 items-start gap-3.5 border-t border-outline-gray-1 p-4 md:grid-cols-2"
				>
					<FormControl v-model="taxId" :label="__(taxLabel)" :size="inputSize" />
					<FormControl
						v-model="billingAddress"
						type="textarea"
						:label="__('Billing address')"
						:error="shown(errors.billing_address)"
						required
					/>
				</div>
			</Collapse>
		</section>
	</div>
</template>

<script setup lang="ts">
import { Checkbox, FormControl } from "frappe-ui"
import { computed } from "vue"

import type { FrappeField } from "@/composables/useCustomFields"

import CustomFieldsSection from "../CustomFieldsSection.vue"
import PhoneInput from "../PhoneInput.vue"
import type { AttendeeErrors } from "./attendeeValidation"
import Collapse from "./Collapse.vue"
import RegistrationPanel from "./RegistrationPanel.vue"

const props = defineProps<{
	buyer: { first_name: string; last_name: string; email: string; phone: string }
	showBuyer: boolean
	needsPhone: boolean
	phoneError: string
	lastNameRequired: boolean
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
const invoiceRequested = defineModel<boolean>("invoiceRequested", { required: true })
const taxId = defineModel<string>("taxId", { required: true })
const billingAddress = defineModel<string>("billingAddress", { required: true })

const inputSize = computed(() => (props.large ? "lg" : "sm"))
const shown = (error?: string) => (props.showErrors ? error : undefined)
</script>
