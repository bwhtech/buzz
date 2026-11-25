<script setup lang="ts">
// Proposals coming in, each with its review state. Empty: the call is closed.
defineProps<{ done: boolean }>()

const TALKS = [
	{ title: "Frappe at scale", status: "Accepted" },
	{ title: "Vue islands in Jinja", status: "In review" },
	{ title: "Payments, the hard way", status: "In review" },
]
</script>

<template>
	<div class="mini-panel">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-2.5 py-2">
			<span class="font-medium">Call for talks</span>
			<span class="mini-value">{{ done ? "Open · 3" : "Closed" }}</span>
		</div>
		<div v-if="done" class="divide-y divide-outline-gray-1">
			<div v-for="talk in TALKS" :key="talk.title" class="flex items-center gap-2 px-2.5 py-2">
				<span class="lucide-mic size-3 text-ink-gray-5" />
				<span class="flex-1 truncate">{{ talk.title }}</span>
				<span class="mini-value">{{ talk.status }}</span>
			</div>
		</div>
		<div v-else class="space-y-1.5 px-2.5 py-3 opacity-60">
			<span
				v-for="width in ['80%', '64%', '72%']"
				:key="width"
				class="mini-bar"
				:style="{ width }"
			/>
		</div>
	</div>
</template>
