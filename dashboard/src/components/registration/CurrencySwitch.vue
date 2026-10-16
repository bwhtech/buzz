<template>
	<div class="flex flex-col">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex flex-col gap-0.5">
				<span class="text-base font-semibold text-ink-gray-9">{{ __("Pay in") }}</span>
				<span class="text-p-sm text-ink-gray-5">
					{{ __("Prices are set per ticket. Some are sold in fewer currencies.") }}
				</span>
			</div>
			<TabButtons
				class="w-full md:w-56"
				fluid
				:options="options"
				:model-value="modelValue"
				@update:model-value="emit('update:modelValue', String($event))"
			/>
		</div>
		<Collapse :open="Boolean(removedMessage)">
			<div
				class="mt-3 flex items-center gap-2.5 rounded-6 bg-surface-amber-1 py-2 pl-3 pr-2 text-p-sm text-ink-amber-8"
			>
				<LucideInfo class="size-3.5 flex-none" />
				<span class="min-w-0 flex-1 text-pretty">{{ removedMessage }}</span>
				<Button variant="ghost" size="sm" @click="emit('undo')">{{ __("Undo") }}</Button>
			</div>
		</Collapse>
	</div>
</template>

<script setup lang="ts">
import { Button, TabButtons } from "frappe-ui"
import { computed } from "vue"
import LucideInfo from "~icons/lucide/info"

import { getCurrencySymbol } from "@/utils/currency"

import Collapse from "./Collapse.vue"

const props = defineProps<{ currencies: string[]; modelValue: string; removedMessage: string }>()
const emit = defineEmits<{ "update:modelValue": [currency: string]; undo: [] }>()

const options = computed(() =>
	props.currencies.map((currency) => ({
		value: currency,
		label: `${getCurrencySymbol(currency)} ${currency}`,
	})),
)
</script>
