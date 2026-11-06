<script setup lang="ts">
defineProps<{ bookingId: string }>()
</script>

<template>
	<div class="flex flex-col items-center gap-2 text-center">
		<h1 class="text-[30px] font-semibold leading-tight tracking-tight text-ink-gray-9 text-balance">
			{{ __("Your booking isn't confirmed") }}
		</h1>
		<p class="max-w-[460px] text-base text-ink-gray-6 text-pretty">
			{{
				__(
					"No ticket has been issued. If you were charged, contact the organiser with booking {0}.",
					[bookingId],
				)
			}}
		</p>
	</div>
</template>
