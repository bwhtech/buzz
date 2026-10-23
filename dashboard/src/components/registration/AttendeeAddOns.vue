<template>
	<div class="flex flex-col gap-3 border-t border-outline-gray-1 pt-3">
		<span class="text-xs font-semibold uppercase tracking-[0.04em] text-ink-gray-5">
			{{ __("Add-ons") }}
		</span>
		<div v-for="addOn in addOns" :key="addOn.name" class="flex flex-col gap-2">
			<div class="flex items-start justify-between gap-3">
				<Checkbox
					:model-value="selection(addOn).selected"
					:label="__(addOn.title ?? '')"
					:description="addOn.description ? __(addOn.description) : undefined"
					:disabled="Boolean(addOn.price_note)"
					@update:model-value="select(addOn, Boolean($event))"
				/>
				<span class="whitespace-nowrap text-p-sm tabular-nums text-ink-gray-7">
					{{ addOn.price_note || formatWholePriceOrFree(addOn.price, addOn.currency) }}
				</span>
			</div>
			<div v-if="addOn.user_selects_option && selection(addOn).selected" class="pl-6">
				<FormControl
					v-model="selection(addOn).option"
					type="select"
					size="sm"
					:aria-label="__('{0} option', [__(addOn.title ?? '')])"
					:options="(addOn.options ?? []).map((option) => ({ label: __(option), value: option }))"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Checkbox, FormControl } from "frappe-ui"

import type { AvailableAddOn, BookingAttendee } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

const props = defineProps<{ attendee: BookingAttendee; addOns: AvailableAddOn[] }>()

function selection(addOn: AvailableAddOn) {
	props.attendee.add_ons ??= {}
	props.attendee.add_ons[addOn.name] ??= { selected: false, option: addOn.options?.[0] ?? null }
	return props.attendee.add_ons[addOn.name]
}

function select(addOn: AvailableAddOn, selected: boolean) {
	const current = selection(addOn)
	current.selected = selected
	if (selected && !current.option) current.option = addOn.options?.[0] ?? null
}
</script>
