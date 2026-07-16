<template>
	<div class="mb-6">
		<BackButton :to="{ name: 'bookings-list' }" :label="__('Back to Bookings')" />
	</div>

	<h2 class="text-ink-gray-9 font-semibold text-lg mb-3">
		{{ __("Booking Details") }}
		<span class="text-ink-gray-5 font-mono">(#{{ bookingId }})</span>
	</h2>
</template>

<script setup lang="ts">
import BackButton from "./common/BackButton.vue";

defineProps({
	bookingId: {
		type: String,
		required: true,
	},
});
</script>
