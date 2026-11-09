<script setup lang="ts">
import { flow, steps } from "./useOnboarding"
</script>

<template>
	<div
		class="flex items-center gap-1.5"
		role="progressbar"
		:aria-valuenow="flow.stepIndex + 1"
		:aria-valuemax="steps.length"
	>
		<span
			v-for="(step, index) in steps"
			:key="step"
			class="progress-dot h-1.5 rounded-full"
			:class="[
				index === flow.stepIndex ? 'w-5 bg-surface-gray-9' : 'w-1.5',
				index < flow.stepIndex
					? 'bg-surface-gray-5'
					: index > flow.stepIndex
						? 'bg-surface-gray-3'
						: '',
			]"
		/>
	</div>
</template>

<style scoped>
.progress-dot {
	transition:
		width 220ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 200ms ease;
}
@media (prefers-reduced-motion: reduce) {
	.progress-dot {
		transition: none;
	}
}
</style>
