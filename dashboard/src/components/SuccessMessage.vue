<template>
	<Transition
		name="success-message"
		enter-active-class="transition-all duration-500 ease-out"
		leave-active-class="transition-all duration-500 ease-in"
		enter-from-class="opacity-0 transform -translate-y-4 scale-95"
		enter-to-class="opacity-100 transform translate-y-0 scale-100"
		leave-from-class="opacity-100 transform translate-y-0 scale-100"
		leave-to-class="opacity-0 transform -translate-y-4 scale-95"
	>
		<div
			v-if="show"
			class="mb-6 bg-surface-green-1 border border-outline-green-1 rounded-lg p-4"
		>
			<div class="flex items-center">
				<LucideCheckCircle class="w-6 h-6 text-ink-green-2 mr-3" />
				<div>
					<h3 class="text-ink-green-3 font-semibold">
						{{ __("Payment Successful! 🎉") }}
					</h3>
					<p class="text-ink-green-2">
						{{
							isWebinar
								? __(
										"Your registration has been confirmed. You will receive an invite shortly."
								  )
								: __(
										"Your booking has been confirmed. Check your email for tickets and details."
								  )
						}}
					</p>
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup lang="ts">
import LucideCheckCircle from "~icons/lucide/check-circle";

withDefaults(
	defineProps<{
		show?: boolean;
		isWebinar?: boolean;
	}>(),
	{
		show: false,
		isWebinar: false,
	}
);
</script>
