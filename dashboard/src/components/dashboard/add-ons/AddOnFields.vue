<script setup lang="ts">
import { FormControl, TabButtons } from "frappe-ui"
import { computed } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import DrawerSection from "@/components/dashboard/DrawerSection.vue"
import PerkList from "@/components/dashboard/sponsorships/PerkList.vue"
import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import TicketTypePicker from "@/components/dashboard/TicketTypePicker.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { TicketTypeItem } from "@/types"

import type { AddOnValues } from "./addOnForm"

const values = defineModel<AddOnValues>({ required: true })
const props = defineProps<{ ticketTypes: TicketTypeItem[] }>()

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

const isPublished = (ticketType: TicketTypeItem) => !!ticketType.is_published
const describeTicketType = (ticketType: TicketTypeItem) =>
	isPublished(ticketType) ? "" : "Not published"
// A selected one stays toggleable so it can be removed.
const isSelectable = (ticketType: TicketTypeItem) =>
	isPublished(ticketType) || values.value.ticket_types.includes(ticketType.name)
</script>

<template>
	<form novalidate class="space-y-6" @submit.prevent>
		<div class="space-y-4">
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
				<p class="text-p-xs text-ink-gray-5">Leave at zero to offer it free.</p>
			</div>
		</div>
		<DrawerSection title="Choices">
			<PerkList
				v-model="values.options"
				label="Let attendees pick one, such as a T-shirt size. Leave empty if there is nothing to choose."
				add-label="Add choice"
				item-name="choice"
				placeholder="Choice name"
			/>
		</DrawerSection>
		<DrawerSection title="Available to">
			<TabButtons v-model="scope" fluid :options="scopeOptions" />
			<EmptyState
				v-if="scope === 'specific' && !ticketTypes.length"
				class="rounded-4 border border-dashed border-outline-gray-2 !py-6"
				icon="lucide-ticket"
				title="No ticket types yet"
				description="Add a ticket type first, then pick which ones this add-on is for."
			/>
			<TicketTypePicker
				v-else-if="scope === 'specific'"
				v-model="values.ticket_types"
				:ticket-types="ticketTypes"
				:describe="describeTicketType"
				:is-selectable="isSelectable"
			/>
		</DrawerSection>
	</form>
</template>
