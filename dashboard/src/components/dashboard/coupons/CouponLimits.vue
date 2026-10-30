<script setup lang="ts">
import { DatePicker, FormControl, Icon, Switch, dayjsLocal } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { CouponValues } from "@/utils/couponForm"

const values = defineModel<CouponValues>({ required: true })
defineProps<{ minDate: string; disabled?: boolean }>()

const open = ref(false)

// No field of its own: on while either date is set, or once switched on to pick them.
const hasDates = computed(() => Boolean(values.value.starts_on || values.value.expires_on))
const scheduleShown = ref(hasDates.value)
watch(hasDates, (set) => (scheduleShown.value = set))
const scheduled = computed<boolean>({
	get: () => scheduleShown.value,
	set: (on) => {
		scheduleShown.value = on
		if (!on) values.value = { ...values.value, starts_on: null, expires_on: null }
	},
})

const shortDate = (date: string) => dayjsLocal(date).format("D MMM")
const scheduleSummary = computed(() => {
	const { starts_on, expires_on } = values.value
	if (starts_on && expires_on) return `${shortDate(starts_on)} – ${shortDate(expires_on)}`
	if (starts_on) return `From ${shortDate(starts_on)}`
	return expires_on ? `Ends ${shortDate(expires_on)}` : "Until registration closes"
})

const summary = computed(() =>
	[
		values.value.usage_limit
			? `${values.value.usage_limit.toLocaleString()} redemptions`
			: "Unlimited",
		values.value.once_per_buyer ? "Once per participant" : "Reusable",
		scheduleSummary.value,
	].join(" · "),
)
</script>

<template>
	<section class="space-y-4">
		<button
			type="button"
			class="-mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-3 px-2 py-1.5 text-left hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			:aria-expanded="open"
			@click="open = !open"
		>
			<span class="min-w-0 flex-1">
				<span class="block text-base font-semibold text-ink-gray-9">Limits &amp; schedule</span>
				<span class="mt-0.5 block truncate text-sm text-ink-gray-5">{{ summary }}</span>
			</span>
			<Icon
				icon="lucide-chevron-down"
				class="size-4 text-ink-gray-5 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
				:class="{ 'rotate-180': open }"
			/>
		</button>

		<div
			class="grid transition-[grid-template-rows] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			:class="open ? 'grid-rows-[1fr] duration-200' : 'grid-rows-[0fr] duration-150'"
			:inert="!open"
		>
			<div class="space-y-4 overflow-hidden px-0.5 pb-0.5">
				<FormControl
					:model-value="values.usage_limit || ''"
					type="number"
					label="Total redemptions"
					placeholder="Unlimited"
					:min="0"
					:disabled="disabled"
					@update:model-value="values.usage_limit = Math.max(Number($event) || 0, 0)"
				/>
				<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
					<div class="p-1">
						<Switch
							v-model="values.once_per_buyer"
							padded
							label="Once per participant"
							description="Matched by email at checkout."
							:disabled="disabled"
						/>
					</div>
					<div class="p-1">
						<Switch
							v-model="scheduled"
							padded
							label="Set a schedule"
							description="When off, it works until registration closes."
							:disabled="disabled"
						/>
					</div>
					<div v-if="scheduled" class="grid grid-cols-2 gap-3 p-3">
						<DatePicker
							:model-value="values.starts_on ?? ''"
							label="Starts"
							placeholder="Right away"
							format="D MMM YYYY"
							:disabled="disabled"
							@update:model-value="values.starts_on = $event || null"
						/>
						<DatePicker
							:model-value="values.expires_on ?? ''"
							label="Ends"
							placeholder="No end date"
							format="D MMM YYYY"
							:min="values.starts_on || minDate"
							:disabled="disabled"
							@update:model-value="values.expires_on = $event || null"
						/>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>
