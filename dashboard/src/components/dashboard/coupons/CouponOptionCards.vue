<script setup lang="ts" generic="T extends string">
import { Icon } from "frappe-ui"
import { RadioGroupItem, RadioGroupRoot } from "reka-ui"

export type CouponOption<T> = { value: T; icon: string; title: string; description: string }

defineProps<{ label: string; options: CouponOption<T>[] }>()
const model = defineModel<T>({ required: true })
</script>

<template>
	<div class="space-y-2">
		<p class="text-xs text-ink-gray-5">{{ label }}</p>
		<RadioGroupRoot
			v-model="model"
			:aria-label="label"
			class="grid grid-cols-1 gap-2 sm:grid-cols-2"
		>
			<RadioGroupItem
				v-for="option in options"
				:key="option.value"
				:value="option.value"
				class="option-card group flex flex-col gap-3 rounded-4 border border-outline-gray-2 bg-surface-white p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 data-[state=checked]:border-outline-gray-5 data-[state=checked]:shadow-[0_0_0_1px_var(--outline-gray-5)] max-sm:flex-row max-sm:items-center"
			>
				<span
					class="flex size-8 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-6 transition-colors group-data-[state=checked]:bg-surface-gray-9 group-data-[state=checked]:text-ink-base"
				>
					<Icon :icon="option.icon" class="size-4" />
				</span>
				<span class="min-w-0">
					<span class="block text-base font-medium text-ink-gray-9">{{ option.title }}</span>
					<span class="mt-0.5 block text-sm text-ink-gray-5 text-pretty">{{
						option.description
					}}</span>
				</span>
			</RadioGroupItem>
		</RadioGroupRoot>
	</div>
</template>

<style scoped>
.option-card {
	transition:
		border-color 150ms ease,
		box-shadow 150ms ease,
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.option-card:active {
	transform: scale(0.98);
}
@media (prefers-reduced-motion: reduce) {
	.option-card:active {
		transform: none;
	}
}
</style>
