<script setup lang="ts">
// The registration form past name and email: a text answer and a pick-one.
// Empty: only the two default fields and a button to add more.
defineProps<{ done: boolean }>()

const SIZES = ["S", "M", "L", "XL"]
</script>

<template>
	<div class="mini-panel space-y-2.5 p-3">
		<div class="space-y-1">
			<span class="mini-label block">Full name</span>
			<span class="mini-field">Riya Shah</span>
		</div>
		<template v-if="done">
			<div class="space-y-1">
				<span class="mini-label block">Company</span>
				<span class="mini-field">Zerodha</span>
			</div>
			<div class="space-y-1">
				<span class="mini-label block">T-shirt size</span>
				<span class="flex gap-1">
					<span
						v-for="size in SIZES"
						:key="size"
						class="mini-chip"
						:data-on="size === 'M' || undefined"
						>{{ size }}</span
					>
				</span>
			</div>
		</template>
		<template v-else>
			<div class="space-y-1">
				<span class="mini-label block">Email</span>
				<span class="mini-field">riya@example.com</span>
			</div>
			<span
				class="flex h-6 items-center justify-center gap-1 rounded-[6px] border border-dashed border-outline-gray-3 text-ink-gray-5"
			>
				<span class="lucide-plus size-3" />Add question
			</span>
		</template>
	</div>
</template>

<style scoped>
.mini-chip {
	display: grid;
	place-items: center;
	height: 22px;
	min-width: 28px;
	padding: 0 6px;
	border-radius: 6px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-6);
}
.mini-chip[data-on] {
	background: var(--ink-gray-9);
	color: var(--surface-elevation-1);
}
</style>
