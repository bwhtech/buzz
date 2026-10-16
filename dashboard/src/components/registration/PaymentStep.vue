<template>
	<div class="flex flex-col gap-2">
		<h2 v-if="gateways.length > 1" class="pb-1 text-base font-semibold text-ink-gray-9">
			{{ __("Pay with") }}
		</h2>
		<RadioGroup
			v-if="gateways.length > 1"
			:model-value="selected ?? undefined"
			@update:model-value="selected = String($event)"
			:aria-label="__('Payment method')"
		>
			<div
				v-for="gateway in gateways"
				:key="gateway"
				class="rounded-5 border transition-colors duration-200 ease-out"
				:class="selected === gateway ? 'border-outline-gray-9' : 'border-outline-gray-2'"
			>
				<Radio :value="gateway" class="w-full p-3.5 md:px-4" :description="description(gateway)">
					<template #label>
						<PaymentGatewayLogo :gateway="gateway" class="h-5">
							<span class="text-base font-semibold text-ink-gray-9">{{ gateway }}</span>
						</PaymentGatewayLogo>
					</template>
				</Radio>
			</div>
		</RadioGroup>
		<p class="flex items-center gap-1.5 pt-1.5 text-xs text-ink-gray-5">
			<LucideLock class="size-3" />
			{{ __("Payments are encrypted and handled by the payment provider.") }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { Radio, RadioGroup } from "frappe-ui"
import LucideLock from "~icons/lucide/lock"

import PaymentGatewayLogo from "../PaymentGatewayLogo.vue"

const props = defineProps<{ gateways: string[]; offlineGateways: string[] }>()
const selected = defineModel<string | null>({ required: true })

function description(gateway: string) {
	return props.offlineGateways.includes(gateway)
		? __("Pay offline and share the payment details next")
		: __("You'll be redirected to complete the payment")
}
</script>
