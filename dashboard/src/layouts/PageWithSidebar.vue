<script setup lang="ts">
// A manage page and the actions that belong to it: the page proper takes the column,
// the actions sit in the margin without a surface of their own and stay put while the
// column scrolls. The sidebar is optional — without it the column keeps its width
// rather than sliding across the page. Below `lg` there is no margin to sit in, so the
// actions stack above the column instead of squeezing it.
</script>

<template>
	<div class="m-auto flex max-w-5xl w-full flex-col-reverse gap-8 py-8 px-4 lg:flex-row">
		<div class="min-w-0 flex-1 space-y-8">
			<slot />
		</div>

		<aside
			v-if="$slots.sidebar"
			class="w-full shrink-0 space-y-3 pt-1 lg:sticky lg:top-8 lg:w-56 lg:self-start"
		>
			<slot name="sidebar" />
		</aside>
	</div>
</template>
