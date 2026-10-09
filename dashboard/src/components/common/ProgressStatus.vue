<script setup lang="ts">
// Delayed when it replaces content that is still fading out.
defineProps<{ text: string; failed?: boolean; delayed?: boolean }>()
</script>

<template>
	<!-- A little above true centre: a lone line sitting at exactly half reads low. -->
	<div class="flex min-h-[70dvh] items-center justify-center" aria-live="polite">
		<!-- Separate elements: the rise and the shimmer are both CSS animations. -->
		<span class="fade-up-in" :class="{ '[animation-delay:300ms]': delayed }">
			<span class="text-base" :class="failed ? 'text-ink-red-6' : 'text-shimmer'">
				{{ text }}
			</span>
		</span>
	</div>
</template>
