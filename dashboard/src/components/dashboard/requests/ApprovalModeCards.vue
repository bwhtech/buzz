<script setup lang="ts">
import { APPROVAL_MODES, type ApprovalMode } from "@/utils/approvalMode"

defineProps<{ mode: ApprovalMode; disabled: boolean }>()
const emit = defineEmits<{ pick: [mode: ApprovalMode] }>()
</script>

<template>
	<section class="space-y-3.5">
		<div class="space-y-1">
			<h2 class="text-lg font-semibold text-ink-gray-9">Registration approval</h2>
			<p class="text-base text-ink-gray-5">
				Choose whether people get in right away or wait for you to review them
			</p>
		</div>
		<div role="radiogroup" aria-label="Registration approval" class="grid gap-2.5 sm:grid-cols-3">
			<label
				v-for="option in APPROVAL_MODES"
				:key="option.value"
				class="flex cursor-pointer flex-col gap-0.5 rounded-6 border p-3.5 transition-[border-color,box-shadow] duration-150 ease-out has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-outline-gray-3 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60 motion-reduce:transition-none"
				:class="
					mode === option.value
						? 'border-outline-gray-8 shadow-[0_0_0_1px_var(--outline-gray-8)]'
						: 'border-outline-gray-2 hover:border-outline-gray-3'
				"
			>
				<input
					type="radio"
					name="approval-mode"
					class="sr-only"
					:value="option.value"
					:checked="mode === option.value"
					:disabled="disabled"
					@change="emit('pick', option.value)"
				/>
				<span class="flex items-center justify-between">
					<span :class="option.icon" class="size-4 text-ink-gray-6" aria-hidden="true" />
					<span
						class="size-4 rounded-full border transition-[border-width] duration-150"
						:class="
							mode === option.value ? 'border-[5px] border-outline-gray-8' : 'border-outline-gray-4'
						"
						aria-hidden="true"
					/>
				</span>
				<span class="mt-2.5 text-base font-medium text-ink-gray-9">{{ option.title }}</span>
				<span class="text-sm leading-snug text-ink-gray-5">{{ option.description }}</span>
			</label>
		</div>
	</section>
</template>
