<script setup lang="ts">
import { useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
</script>

<template>
	<Transition name="schedule-toast">
		<div
			v-if="builder.toastMessage.value"
			class="fixed bottom-5 left-1/2 z-[60] flex -translate-x-1/2 items-center gap-2.5 whitespace-nowrap rounded-5 bg-surface-gray-9 py-1.5 pl-3.5 pr-1.5 text-p-sm text-ink-base shadow-xl"
			role="status"
		>
			<span>{{ builder.toastMessage.value }}</span>
			<button
				type="button"
				class="rounded-4 px-2 py-1 font-semibold text-ink-gray-3 hover:bg-surface-gray-8 hover:text-ink-base"
				@click="builder.undo"
			>
				Undo
			</button>
		</div>
	</Transition>
</template>

<style scoped>
.schedule-toast-enter-active {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.schedule-toast-leave-active {
	transition: opacity 120ms ease-out;
}
.schedule-toast-enter-from {
	opacity: 0;
	transform: translate(-50%, 8px);
}
.schedule-toast-leave-to {
	opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
	.schedule-toast-enter-active {
		transition: opacity 120ms ease-out;
	}
	.schedule-toast-enter-from {
		transform: translate(-50%, 0);
	}
}
</style>
