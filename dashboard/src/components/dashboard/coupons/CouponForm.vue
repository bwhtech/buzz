<script setup lang="ts">
import {
	Button,
	Checkbox,
	FormControl,
	FormLabel,
	Switch,
	TabButtons,
	TextInput,
	dayjs,
} from "frappe-ui"
import { computed } from "vue"

import type { CouponTicketType } from "@/types"
import {
	type CouponValues,
	cleanPromoCode,
	couponCurrencies,
	generateCode,
} from "@/utils/couponForm"
import { amountsLabel } from "@/utils/couponLabels"

import CouponLimits from "./CouponLimits.vue"
import CurrencyAmounts from "./CurrencyAmounts.vue"

const values = defineModel<CouponValues>({ required: true })
const props = defineProps<{ ticketTypes: CouponTicketType[]; disabled?: boolean }>()

const QUICK_PERCENTAGES = [10, 15, 25, 50]

const isPaid = (ticketType: CouponTicketType) => ticketType.prices.some((row) => row.price > 0)

const isCode = computed(() => values.value.coupon_type === "Promo Code")
const currencies = computed(() => couponCurrencies(values.value, props.ticketTypes))

const scopeOptions = [
	{ label: "All ticket types", value: "all" },
	{ label: "Specific ticket types", value: "specific" },
]
const scope = computed({
	get: () => (values.value.applies_to_all_ticket_types ? "all" : "specific"),
	set: (picked) => {
		values.value.applies_to_all_ticket_types = picked === "all"
		// Narrowing starts from every paid ticket type, so the organiser unticks rather than hunts.
		if (picked === "specific" && !values.value.ticket_types.length)
			values.value.ticket_types = props.ticketTypes.filter(isPaid).map((row) => row.name)
	},
})

function toggleTicketType(name: string, picked: boolean) {
	const others = values.value.ticket_types.filter((row) => row !== name)
	values.value.ticket_types = picked ? [...others, name] : others
}

const minimumOptions = computed(() => [
	...(isCode.value ? [] : [{ label: "Any order", value: "None" }]),
	{ label: "Order total is at least", value: "Minimum Order Amount" },
	{ label: "Number of tickets is at least", value: "Minimum Ticket Count" },
])
const requiresMinimum = computed({
	get: () => values.value.minimum_requirement !== "None",
	set: (on) => (values.value.minimum_requirement = on ? "Minimum Order Amount" : "None"),
})

const currencyHint = computed(() => {
	if (!currencies.value.length) return "Pick at least one paid ticket type."
	if (currencies.value.length === 1) return `Your selected tickets sell in ${currencies.value[0]}.`
	return `Your selected tickets sell in ${currencies.value.join(" and ")}, so set an amount for each.`
})

const priceLabel = (ticketType: CouponTicketType) =>
	isPaid(ticketType) ? amountsLabel(ticketType.prices) : "Free"

const today = dayjs().format("YYYY-MM-DD")

// Only a code saved before the character rule can hold anything cleanPromoCode would drop.
const hasInvalidCode = computed(
	() => cleanPromoCode(values.value.code) !== values.value.code.toUpperCase(),
)
</script>

<template>
	<div class="divide-y divide-outline-gray-1">
		<section class="space-y-4 pb-5">
			<div>
				<h3 class="text-base font-semibold text-ink-gray-9">Discount</h3>
				<p class="mt-0.5 text-sm text-ink-gray-5">
					{{ isCode ? "The code and what it takes off" : "What it takes off" }}
				</p>
			</div>

			<div v-if="isCode" class="space-y-1.5">
				<FormLabel id="coupon-code" label="Code" required />
				<div class="flex gap-2">
					<TextInput
						id="coupon-code"
						:model-value="values.code ?? ''"
						class="flex-1 [&_input]:font-mono [&_input]:uppercase [&_input]:tracking-wide"
						placeholder="EARLYBIRD"
						autocomplete="off"
						:disabled="disabled"
						@update:model-value="values.code = cleanPromoCode($event)"
					/>
					<Button
						variant="subtle"
						icon-left="lucide-shuffle"
						label="Generate"
						:disabled="disabled"
						@click="values.code = generateCode()"
					/>
				</div>
				<p
					class="text-xs text-pretty"
					:class="hasInvalidCode ? 'text-ink-red-5' : 'text-ink-gray-5'"
				>
					{{
						hasInvalidCode
							? "Remove the spaces and symbols to save. Letters, numbers, - and _ only"
							: "Entered by participants at checkout. Letters, numbers, - and _ only"
					}}
				</p>
			</div>

			<FormControl
				v-else
				v-model="values.code"
				label="Offer name"
				required
				placeholder="Group discount"
				description="Shown to participants at checkout when it applies"
				autocomplete="off"
				:disabled="disabled"
			/>

			<FormControl
				v-model="values.description"
				type="textarea"
				label="Description"
				placeholder="What this offer is for and who it's meant for"
				description="Only visible to organizers"
				:rows="2"
				:disabled="disabled"
			/>

			<div v-if="values.discount_type === 'Percentage'" class="space-y-1.5">
				<FormLabel label="Percentage off" required />
				<div class="flex flex-wrap items-center gap-1.5">
					<FormControl
						:model-value="values.discount_percentage || ''"
						class="w-28"
						type="number"
						placeholder="20"
						:min="1"
						:max="100"
						:disabled="disabled"
						@update:model-value="values.discount_percentage = Number($event) || 0"
					>
						<template #suffix><span class="text-base text-ink-gray-5">%</span></template>
					</FormControl>
					<Button
						v-for="percentage in QUICK_PERCENTAGES"
						:key="percentage"
						variant="ghost"
						:label="`${percentage}%`"
						:disabled="disabled"
						@click="values.discount_percentage = percentage"
					/>
				</div>
			</div>

			<div v-else class="space-y-2">
				<CurrencyAmounts
					v-model="values.discount_amounts"
					label="Amount off the order"
					:currencies="currencies"
					:disabled="disabled"
				/>
				<p class="text-sm text-ink-gray-5">{{ currencyHint }}</p>
			</div>
		</section>

		<section class="space-y-4 py-5">
			<div>
				<h3 class="text-base font-semibold text-ink-gray-9">Eligibility</h3>
				<p class="mt-0.5 text-sm text-ink-gray-5">
					{{
						isCode ? "Which tickets and orders the code works on" : "Which orders qualify for it"
					}}
				</p>
			</div>

			<div class="space-y-2">
				<TabButtons v-model="scope" fluid :options="scopeOptions" />
				<div v-if="scope === 'specific'" class="rounded-4 border border-outline-gray-2 p-1">
					<Checkbox
						v-for="ticketType in ticketTypes"
						:key="ticketType.name"
						padded
						:label="ticketType.title"
						:description="priceLabel(ticketType)"
						:model-value="values.ticket_types.includes(ticketType.name)"
						:disabled="disabled || !isPaid(ticketType)"
						@update:model-value="toggleTicketType(ticketType.name, !!$event)"
					/>
				</div>
			</div>

			<div class="rounded-4 border border-outline-gray-2">
				<div v-if="isCode" class="p-1">
					<Switch
						v-model="requiresMinimum"
						padded
						label="Require a minimum"
						description="When off, the code works on any order."
						:disabled="disabled"
					/>
				</div>
				<div v-else class="px-3 pt-3">
					<p class="text-base text-ink-gray-8">Applies when</p>
					<p class="mt-0.5 text-sm text-ink-gray-6">
						Added to the order as soon as it qualifies, no code needed.
					</p>
				</div>
				<div v-if="!isCode || requiresMinimum" class="space-y-2 p-3">
					<FormControl
						v-model="values.minimum_requirement"
						type="select"
						:options="minimumOptions"
						:disabled="disabled"
					/>
					<CurrencyAmounts
						v-if="values.minimum_requirement === 'Minimum Order Amount'"
						v-model="values.minimum_order_amounts"
						label="Order total"
						:currencies="currencies"
						:disabled="disabled"
					/>
					<FormControl
						v-if="values.minimum_requirement === 'Minimum Ticket Count'"
						:model-value="values.minimum_ticket_count || ''"
						type="number"
						placeholder="5"
						:min="1"
						:disabled="disabled"
						@update:model-value="values.minimum_ticket_count = Math.max(Number($event) || 0, 0)"
					>
						<template #suffix><span class="text-sm text-ink-gray-5">tickets</span></template>
					</FormControl>
				</div>
			</div>
		</section>

		<CouponLimits v-model="values" class="pt-5" :min-date="today" :disabled="disabled" />
	</div>
</template>
