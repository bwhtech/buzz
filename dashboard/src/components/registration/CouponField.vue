<template>
	<div
		v-if="applied"
		class="flex items-center gap-2.5 rounded-6 border border-dashed border-outline-green-3 bg-surface-green-1 py-2.5 pl-3 pr-2.5 motion-safe:animate-[coupon-in_220ms_cubic-bezier(0.23,1,0.32,1)]"
	>
		<span
			class="flex size-7 flex-none items-center justify-center rounded-5 bg-surface-green-2 text-ink-green-7"
		>
			<LucideBadgePercent class="size-4" />
		</span>
		<div class="flex min-w-0 flex-1 flex-col gap-px">
			<span class="text-p-sm font-semibold tracking-[0.08em] text-ink-green-8">{{ code }}</span>
			<span class="text-xs text-ink-green-7">{{ appliedNote }}</span>
		</div>
		<Button
			variant="ghost"
			icon="lucide-x"
			class="text-ink-green-7"
			:aria-label="__('Remove code')"
			@click="emit('remove')"
		/>
	</div>
	<div v-else class="flex flex-col">
		<button
			type="button"
			class="flex min-h-7 items-center gap-2 text-p-sm text-ink-gray-7 transition-colors duration-150 hover:text-ink-gray-9"
			:aria-expanded="open"
			@click="open = !open"
		>
			<LucideTag class="size-3.5" />
			<span class="flex-1 text-left">{{ __("Add discount code") }}</span>
			<LucideChevronDown
				class="size-3.5 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
				:class="{ 'rotate-180': open }"
			/>
		</button>
		<Collapse :open="open || Boolean(error)">
			<div class="flex items-start gap-1.5 pb-0.5 pt-2">
				<FormControl
					v-model="code"
					class="flex-1 [&_input]:uppercase"
					size="sm"
					:placeholder="__('Enter code')"
					:aria-label="__('Discount code')"
					:error="error || undefined"
					@keydown.enter.prevent="emit('apply')"
				/>
				<Button variant="outline" size="sm" :loading="loading" @click="emit('apply')">
					{{ __("Apply") }}
				</Button>
			</div>
		</Collapse>
	</div>
</template>

<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { ref } from "vue"
import LucideBadgePercent from "~icons/lucide/badge-percent"
import LucideChevronDown from "~icons/lucide/chevron-down"
import LucideTag from "~icons/lucide/tag"

import Collapse from "./Collapse.vue"

defineProps<{ applied: boolean; appliedNote: string; error: string; loading: boolean }>()
const emit = defineEmits<{ apply: []; remove: [] }>()

const code = defineModel<string>({ required: true })
const open = ref(false)
</script>

<style>
@keyframes coupon-in {
	from {
		opacity: 0;
		transform: scale(0.96) translateY(4px);
	}
}
</style>
