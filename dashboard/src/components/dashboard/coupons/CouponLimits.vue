<script setup lang="ts">
import { DatePicker, FormControl, Switch } from "frappe-ui"
import { computed, ref, watch } from "vue"

import DrawerSection from "@/components/dashboard/DrawerSection.vue"
import type { CouponValues } from "@/utils/couponForm"

const values = defineModel<CouponValues>({ required: true })
defineProps<{ minDate: string; disabled?: boolean }>()

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
</script>

<template>
	<DrawerSection title="Limits &amp; schedule">
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
	</DrawerSection>
</template>
