<script setup lang="ts">
import { ErrorMessage, FormControl, Radio, RadioGroup, Switch } from "frappe-ui"
import { computed } from "vue"

import SectionHeader from "@/components/common/SectionHeader.vue"
import type { TaxSettingsForm } from "@/composables/useTaxSettingsForm"

const props = defineProps<{ form: TaxSettingsForm; canWrite: boolean }>()
const { applyTax, payer, taxLabel, taxPercentage } = props.form
const fieldsDisabled = computed(() => !props.canWrite || !applyTax.value)
</script>

<template>
	<section class="space-y-3">
		<div>
			<SectionHeader title="Taxes" />
			<p class="mt-1 text-p-base text-ink-gray-5">Tax charged on every ticket for this event</p>
		</div>

		<Switch
			v-model="applyTax"
			padded
			label="Charge tax on tickets"
			description="Applies to new bookings. Existing bookings keep the tax they were charged."
			:disabled="!canWrite"
		/>

		<div class="grid gap-3 md:grid-cols-2">
			<div class="rounded-4 border border-outline-gray-2 p-4">
				<RadioGroup v-model="payer" label="Who pays the tax" :disabled="fieldsDisabled">
					<Radio
						value="participant"
						label="Participant"
						description="Tax is added on top of the ticket price at checkout."
					/>
					<Radio
						value="organiser"
						label="Organiser"
						description="Tax is included in the ticket price. Participants pay exactly the listed price."
					/>
				</RadioGroup>
			</div>

			<div class="space-y-3 rounded-4 border border-outline-gray-2 p-4">
				<FormControl
					v-model="taxLabel"
					label="Tax name"
					placeholder="GST"
					description="Shown to participants at checkout and on their booking."
					:disabled="fieldsDisabled"
				/>
				<FormControl
					v-model="taxPercentage"
					type="number"
					label="Tax rate"
					min="0"
					max="100"
					step="0.01"
					:disabled="fieldsDisabled"
				>
					<template #suffix><span class="text-sm text-ink-gray-5">%</span></template>
				</FormControl>
			</div>
		</div>

		<ErrorMessage :message="form.errorMessage.value" />
	</section>
</template>
