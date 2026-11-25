<script setup lang="ts">
// The online location: which app, and the link guests get once they register.
// Empty: the apps to pick from over a blank link field.
defineProps<{ done: boolean }>()

const APPS = ["Zoom", "Google Meet", "Other"]
</script>

<template>
	<div class="mini-panel space-y-2.5 p-3">
		<div class="flex gap-1">
			<span
				v-for="app in APPS"
				:key="app"
				class="mini-chip"
				:data-on="(done && app === 'Zoom') || undefined"
				>{{ app }}</span
			>
		</div>
		<div class="space-y-1">
			<span class="mini-label block">Meeting link</span>
			<span class="mini-field">
				<span class="lucide-video size-3 shrink-0 text-ink-gray-5" />
				<span v-if="done" class="mini-value truncate">zoom.us/j/84213907751</span>
				<span v-else class="mini-empty">Paste a link</span>
			</span>
		</div>
		<p class="mini-label">Sent to guests after they register</p>
	</div>
</template>

<style scoped>
.mini-chip {
	display: grid;
	place-items: center;
	height: 22px;
	padding: 0 8px;
	border-radius: 6px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-6);
}
.mini-chip[data-on] {
	background: var(--ink-gray-9);
	color: var(--surface-elevation-1);
}
</style>
