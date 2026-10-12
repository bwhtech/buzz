<script setup lang="ts">
import "@public/themes/countdown.css"
import { EventCountdown } from "@public/js/event_countdown"

// The event page's own pill, so the banner here reads the same as the one guests see.
if (!customElements.get("event-countdown")) customElements.define("event-countdown", EventCountdown)

defineProps<{ startsAt: string; endsAt: string }>()
</script>

<template>
	<event-countdown
		class="countdown-pill"
		role="timer"
		:starts-at="startsAt"
		:ends-at="endsAt"
		hidden
	>
		<span class="live-dot" aria-hidden="true" />
		<span class="countdown-live">Live</span>
		<span class="countdown-upcoming"
			>Starting in <span class="countdown-value" aria-hidden="true"
		/></span>
	</event-countdown>
</template>

<style>
/* countdown.css reads the event page's theme tokens; these are the dashboard's. */
.countdown-pill {
	--surface-raised: var(--surface-elevation-1);
	--border: var(--outline-gray-2);
	--ink-muted: var(--ink-gray-5);
	--ink-strong: var(--ink-gray-9);
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}
</style>
