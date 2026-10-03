<script setup lang="ts">
import { Alert, ErrorMessage, FormControl, Radio, RadioGroup, Switch } from "frappe-ui"
import { computed, ref } from "vue"

import SectionHeader from "@/components/common/SectionHeader.vue"
import TeamTaxDetailsDialog from "@/components/dashboard/ticket-types/TeamTaxDetailsDialog.vue"
import type { TaxSettingsForm } from "@/composables/useTaxSettingsForm"

const props = defineProps<{
	event: string
	form: TaxSettingsForm
	canWrite: boolean
	teamLegalName: string | null
	teamTaxId: string | null
	canEditTeam: boolean
}>()
const emit = defineEmits<{ taxDetailsAdded: [] }>()

const { applyTax, payer, taxLabel, taxPercentage } = props.form
const dialogOpen = ref(false)
const hasTaxDetails = computed(() => !!props.teamTaxId)

// Without tax details the switch only lets an event that already charges tax turn it off.
const switchDisabled = computed(() => !props.canWrite || (!hasTaxDetails.value && !applyTax.value))
const fieldsDisabled = computed(() => !props.canWrite || !hasTaxDetails.value || !applyTax.value)

const missingDetailsMessage = computed(() => {
	const request = props.canEditTeam
		? "Add your team's tax details to charge tax on tickets."
		: "A team owner or admin needs to add your team's tax details before tax can be charged on tickets."
	return `${request} Until then, tickets are sold without tax, and your team is responsible for all tax and accounting obligations on its sales.`
})

const missingDetailsAction = computed(() =>
	props.canEditTeam
		? {
				label: "Add tax details",
				onClick: () => {
					dialogOpen.value = true
				},
			}
		: undefined,
)
</script>

<template>
	<section class="space-y-3">
		<Alert
			v-if="!hasTaxDetails"
			class="mb-6"
			theme="amber"
			title="Tax details required"
			:description="missingDetailsMessage"
			:primary-action="missingDetailsAction"
		/>

		<div>
			<SectionHeader title="Taxes" />
			<p class="mt-1 text-p-base text-ink-gray-5">Tax charged on every ticket for this event</p>
		</div>

		<p v-if="hasTaxDetails" class="flex items-center gap-1.5 text-p-sm text-ink-gray-6">
			<span class="lucide-landmark size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
			<span>
				Invoiced as <span class="font-medium text-ink-gray-8">{{ teamLegalName }}</span> · Tax ID
				<span class="font-mono text-ink-gray-8">{{ teamTaxId }}</span>
			</span>
		</p>

		<Switch
			v-model="applyTax"
			padded
			label="Charge tax on tickets"
			description="Applies to new bookings. Existing bookings keep the tax they were charged."
			:disabled="switchDisabled"
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

		<TeamTaxDetailsDialog v-model="dialogOpen" :event="event" @saved="emit('taxDetailsAdded')" />
	</section>
</template>
