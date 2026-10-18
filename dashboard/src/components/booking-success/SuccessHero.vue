<script setup lang="ts">
defineProps<{ eventTitle: string; ticketCount: number }>()
</script>

<template>
	<div class="flex flex-col items-center gap-4 text-center">
		<div class="relative size-[52px]" aria-hidden="true">
			<span class="check-ring absolute inset-0 rounded-full bg-surface-green-3" />
			<span
				class="check-badge absolute inset-0 flex items-center justify-center rounded-full bg-surface-green-2 text-ink-green-6"
			>
				<svg
					class="size-6"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2.4"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path class="check-mark" d="M5 12.5l4.5 4.5L19 7.5" />
				</svg>
			</span>
		</div>

		<div class="fade-up-in flex flex-col items-center gap-2" style="animation-delay: 80ms">
			<h1
				class="text-[30px] font-semibold leading-tight tracking-tight text-ink-gray-9 text-balance"
			>
				{{ __("You're going to {0}", [eventTitle]) }}
			</h1>
			<p class="max-w-[460px] text-base text-ink-gray-6 text-pretty">
				{{
					ticketCount > 1
						? __("We've emailed your {0} tickets.", [ticketCount])
						: __("We've emailed your ticket.")
				}}
				{{ __("Show the QR code at the entrance to check in.") }}
			</p>
		</div>
	</div>
</template>

<style scoped>
.check-badge {
	animation: check-pop 450ms cubic-bezier(0.23, 1, 0.32, 1) both;
}
.check-ring {
	animation: check-ring 900ms cubic-bezier(0.23, 1, 0.32, 1) 350ms both;
}
.check-mark {
	stroke-dasharray: 24;
	animation: check-draw 380ms cubic-bezier(0.23, 1, 0.32, 1) 220ms both;
}

@keyframes check-pop {
	from {
		opacity: 0;
		transform: scale(0.5);
	}
}
@keyframes check-ring {
	from {
		opacity: 0.5;
	}
	to {
		opacity: 0;
		transform: scale(1.9);
	}
}
@keyframes check-draw {
	from {
		stroke-dashoffset: 24;
	}
}

@media (prefers-reduced-motion: reduce) {
	.check-badge,
	.check-ring,
	.check-mark {
		animation: none;
	}
	.check-ring {
		opacity: 0;
	}
}
</style>
