<script setup lang="ts">
import { DatePicker, FormControl, Switch } from "frappe-ui"

import DrawerSection from "@/components/dashboard/DrawerSection.vue"
import type { CouponValues } from "@/utils/couponForm"

const values = defineModel<CouponValues>({ required: true })
defineProps<{ minDate: string; maxDate?: string; disabled?: boolean }>()
</script>

<template>
	<DrawerSection title="Usage limits">
		<FormControl
			:model-value="values.usage_limit || ''"
			type="number"
			label="Number of uses"
			placeholder="Unlimited"
			:min="0"
			:disabled="disabled"
			@update:model-value="values.usage_limit = Math.max(Number($event) || 0, 0)"
		/>
		<div class="rounded-4 border border-outline-gray-2 p-1">
			<Switch
				v-model="values.once_per_buyer"
				padded
				label="One use per person"
				description="Each email address can use it once"
				:disabled="disabled"
			/>
		</div>
	</DrawerSection>

	<DrawerSection title="Valid dates">
		<div class="grid grid-cols-2 gap-3">
			<DatePicker
				:model-value="values.starts_on ?? ''"
				label="Starts"
				placeholder="Right away"
				format="D MMM YYYY"
				:max="maxDate"
				:disabled="disabled"
				@update:model-value="values.starts_on = $event || null"
			/>
			<DatePicker
				:model-value="values.expires_on ?? ''"
				label="Ends"
				placeholder="When registration closes"
				format="D MMM YYYY"
				:min="values.starts_on || minDate"
				:max="maxDate"
				:disabled="disabled"
				@update:model-value="values.expires_on = $event || null"
			/>
		</div>
	</DrawerSection>
</template>
