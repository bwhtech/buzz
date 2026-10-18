<template>
	<div class="flex justify-center px-4 py-8 md:py-12">
		<div
			class="w-full max-w-[480px] overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-gray-1 motion-safe:animate-[registration-in_280ms_cubic-bezier(0.23,1,0.32,1)]"
		>
			<div class="flex flex-col gap-2.5 px-5 pb-5 pt-6 md:px-7 md:pt-7">
				<span
					class="flex size-9 items-center justify-center rounded-full border border-outline-gray-2 bg-surface-base text-ink-gray-7"
				>
					<LucideClock v-if="pending" class="size-[18px]" />
					<LucideCircleCheck v-else class="size-[18px]" />
				</span>
				<h2 class="font-display text-[34px] uppercase leading-none text-ink-gray-9">{{ title }}</h2>
				<p class="text-base text-ink-gray-6 text-pretty"><slot /></p>
				<p v-if="reference" class="text-p-sm text-ink-gray-5">
					{{ __("Booking reference") }}:
					<span class="font-medium text-ink-gray-8">{{ reference }}</span>
				</p>
			</div>
			<div
				class="flex flex-col gap-2 border-t border-dashed border-outline-gray-3 bg-surface-base px-5 py-4 md:px-7"
			>
				<p class="text-p-sm text-ink-gray-5">{{ __("Want to manage your bookings?") }}</p>
				<Button variant="outline" class="self-start" @click="emit('login')">
					{{ __("Log in to your account") }}
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import LucideCircleCheck from "~icons/lucide/circle-check"
import LucideClock from "~icons/lucide/clock"

defineProps<{ title: string; reference?: string; pending?: boolean }>()
const emit = defineEmits<{ login: [] }>()
</script>

<style>
@keyframes registration-in {
	from {
		opacity: 0;
		transform: translateY(8px);
	}
}
</style>
