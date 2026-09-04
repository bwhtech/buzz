<script setup lang="ts">
// A manage page and the actions that belong to it: the page proper takes the column,
// the actions sit in the margin without a surface of their own and stay put while the
// column scrolls. The sidebar is optional — without it the column keeps its width
// rather than sliding across the page.
</script>

<template>
	<div class="m-auto flex max-w-5xl w-full gap-8 py-8 px-4">
		<div class="min-w-0 flex-1 space-y-8">
			<slot />
		</div>

		<aside v-if="$slots.sidebar" class="sticky top-8 w-56 shrink-0 self-start space-y-3 pt-1">
			<slot name="sidebar" />
		</aside>
	</div>
</template>
