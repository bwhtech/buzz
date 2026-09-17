<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { FrappeError } from "@/types"

type TierDoc = { event: string; title: string; price: number; currency: string }

const DEFAULT_CURRENCY = "INR"

const props = defineProps<{ event: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const title = ref("")
const price = ref(0)
const currency = ref(DEFAULT_CURRENCY)
const showErrors = ref(false)

const creator = useNewDoc<TierDoc>("Sponsorship Tier")
const enabledCurrencies = useEnabledCurrencies()

const currencyOptions = computed(() =>
	(enabledCurrencies.data ?? []).map((enabledCurrency) => enabledCurrency.name),
)
const selectedCurrency = computed(() =>
	enabledCurrencies.data?.find((enabledCurrency) => enabledCurrency.name === currency.value),
)

const invalid = computed(() => !title.value.trim() || !(price.value >= 0))
const errorMessage = computed(() => (creator.error as FrappeError | null)?.messages?.join("\n"))

watch(isOpen, (open) => open && reset())

function reset() {
	title.value = ""
	price.value = 0
	currency.value = currencyOptions.value.includes(DEFAULT_CURRENCY)
		? DEFAULT_CURRENCY
		: (currencyOptions.value[0] ?? DEFAULT_CURRENCY)
	showErrors.value = false
	creator.reset()
}

async function submit() {
	// Enter in a field submits the form too, so guard against a second insert mid-request.
	if (creator.loading) return
	showErrors.value = true
	if (invalid.value) return

	Object.assign(creator.doc, {
		event: props.event,
		title: title.value.trim(),
		price: price.value,
		currency: currency.value,
	})
	await creator.submit().catch(() => null)
	if (creator.error) return

	toast.success("Tier added")
	emit("saved")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" title="Add Tier">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl v-model="title" label="Title" placeholder="Gold" autocomplete="off" required />

			<div class="grid grid-cols-[2fr_1fr] gap-4">
				<PriceInput
					v-model="price"
					label="Price"
					required
					:currency-symbol="selectedCurrency?.symbol || currency"
					:number-format="selectedCurrency?.number_format"
				/>
				<FormControl v-model="currency" type="select" label="Currency" :options="currencyOptions" />
			</div>

			<ErrorMessage
				:message="
					showErrors && invalid ? 'A tier needs a title and a price of zero or more.' : errorMessage
				"
			/>

			<Button
				type="button"
				variant="solid"
				class="w-full"
				label="Add"
				:loading="creator.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
