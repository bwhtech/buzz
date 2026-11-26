<script setup lang="ts">
import { Checkbox, FormControl, TabButtons, TextInput } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import DrawerSection from "@/components/dashboard/DrawerSection.vue"
import PerkList from "@/components/dashboard/sponsorships/PerkList.vue"
import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
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

const search = ref("")
const shownTicketTypes = computed(() => {
	const typed = search.value.trim().toLowerCase()
	return props.ticketTypes.filter((row) => row.title.toLowerCase().includes(typed))
})

const noMatchText = computed(() => `No ticket type has "${search.value.trim()}" in its name.`)

function toggleTicketType(name: string, picked: boolean) {
	const others = values.value.ticket_types.filter((row) => row !== name)
	values.value.ticket_types = picked ? [...others, name] : others
}
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
		<DrawerSection title="Options">
			<PerkList
				v-model="values.options"
				label="Attendees pick one, such as a T-shirt size"
				add-label="Add option"
				item-name="option"
				placeholder="Option name"
			/>
		</DrawerSection>
		<DrawerSection title="Applies to">
			<TabButtons v-model="scope" fluid :options="scopeOptions" />
			<EmptyState
				v-if="scope === 'specific' && !ticketTypes.length"
				class="rounded-4 border border-dashed border-outline-gray-2 !py-6"
				icon="lucide-ticket"
				title="No ticket types yet"
				description="Add a ticket type first, then pick which ones this add-on is for."
			/>
			<div v-else-if="scope === 'specific'" class="space-y-2">
				<TextInput v-model="search" type="search" placeholder="Search ticket types">
					<template #prefix>
						<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</TextInput>
				<p class="text-p-xs tabular-nums text-ink-gray-5">
					{{ values.ticket_types.length }} of {{ ticketTypes.length }} selected
				</p>
				<EmptyState
					v-if="!shownTicketTypes.length"
					class="rounded-4 border border-dashed border-outline-gray-2 !py-6"
					icon="lucide-search"
					title="No matches"
					:description="noMatchText"
					:action="{ label: 'Clear search', variant: 'subtle', onClick: () => (search = '') }"
				/>
				<div v-else class="max-h-72 overflow-y-auto rounded-4 border border-outline-gray-2 p-1">
					<Checkbox
						v-for="ticketType in shownTicketTypes"
						:key="ticketType.name"
						padded
						:label="ticketType.title"
						:model-value="values.ticket_types.includes(ticketType.name)"
						@update:model-value="toggleTicketType(ticketType.name, !!$event)"
					/>
				</div>
			</div>
		</DrawerSection>
	</form>
</template>
