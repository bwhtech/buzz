<script setup lang="ts">
import { Checkbox, FormControl, Switch, TabButtons } from "frappe-ui"
import { computed } from "vue"

import PerkList from "@/components/dashboard/sponsorships/PerkList.vue"
import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { TicketTypeItem } from "@/types"

import type { AddOnValues } from "./addOnForm"

const values = defineModel<AddOnValues>({ required: true })
defineProps<{
	ticketTypes: TicketTypeItem[]
	// The enabled switch shows only on a saved add-on.
	showEnabled?: boolean
}>()

const enabledCurrencies = useEnabledCurrencies()

// An add-on keeps its currency even if the site later disables it.
const currencyOptions = computed(() => {
	const names = (enabledCurrencies.data ?? []).map((currency) => currency.name)
	return names.includes(values.value.currency) ? names : [values.value.currency, ...names]
})
const currencyDetails = computed(() =>
	enabledCurrencies.data?.find((currency) => currency.name === values.value.currency),
)

const scopeOptions = [
	{ label: "All ticket types", value: "all" },
	{ label: "Specific ticket types", value: "specific" },
]
const scope = computed({
	get: () => (values.value.applies_to_all_ticket_types ? "all" : "specific"),
	set: (picked) => (values.value.applies_to_all_ticket_types = picked === "all"),
})

function toggleTicketType(name: string, picked: boolean) {
	const others = values.value.ticket_types.filter((row) => row !== name)
	values.value.ticket_types = picked ? [...others, name] : others
}
</script>

<template>
	<form novalidate class="space-y-4" @submit.prevent>
		<div v-if="showEnabled" class="rounded-4 border border-outline-gray-2 p-1">
			<Switch
				v-model="values.enabled"
				padded
				label="Enabled"
				description="Participants can pick it while registering."
			/>
		</div>
		<FormControl
			v-model="values.title"
			label="Name"
			required
			placeholder="Lunch"
			autocomplete="off"
		/>
		<FormControl
			v-model="values.description"
			type="textarea"
			label="Description"
			placeholder="Buffet lunch on both days"
			description="Shown below the name on the booking page."
			:rows="2"
		/>
		<div class="space-y-1.5">
			<span class="block text-xs text-ink-gray-5">Price</span>
			<div class="grid grid-cols-[2fr_1fr] gap-2">
				<PriceInput
					v-model="values.price"
					aria-label="Price"
					:currency-symbol="currencyDetails?.symbol || values.currency"
					:number-format="currencyDetails?.number_format"
				/>
				<FormControl
					v-model="values.currency"
					type="select"
					aria-label="Currency"
					:options="currencyOptions"
				/>
			</div>
			<p class="text-sm text-ink-gray-5">Leave at zero to offer it free.</p>
		</div>
		<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
			<div class="p-1">
				<Switch
					v-model="values.user_selects_option"
					padded
					label="Let attendees choose an option"
					description="Such as a T-shirt size or a meal preference."
				/>
			</div>
			<div v-if="values.user_selects_option" class="p-3">
				<PerkList
					v-model="values.options"
					label="Options"
					add-label="Add option"
					item-name="option"
					placeholder="Option name"
				/>
			</div>
		</div>
		<fieldset class="space-y-2">
			<legend class="pb-2 text-sm font-semibold text-ink-gray-9">Applies to</legend>
			<TabButtons v-model="scope" fluid :options="scopeOptions" />
			<div v-if="scope === 'specific'" class="rounded-4 border border-outline-gray-2 p-1">
				<Checkbox
					v-for="ticketType in ticketTypes"
					:key="ticketType.name"
					padded
					:label="ticketType.title"
					:model-value="values.ticket_types.includes(ticketType.name)"
					@update:model-value="toggleTicketType(ticketType.name, !!$event)"
				/>
			</div>
		</fieldset>
	</form>
</template>
