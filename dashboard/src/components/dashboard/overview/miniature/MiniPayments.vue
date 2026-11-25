<script setup lang="ts">
// Payment providers: the default one connected, a second one waiting. Empty: neither.
defineProps<{ done: boolean }>()
</script>

<template>
	<div class="mini-panel divide-y divide-outline-gray-1">
		<div
			v-for="(provider, index) in ['Razorpay', 'Stripe']"
			:key="provider"
			class="flex items-center gap-2 px-2.5 py-2"
		>
			<span class="grid size-5 place-items-center rounded-[5px] bg-surface-gray-2">
				<span class="lucide-credit-card size-3 text-ink-gray-6" />
			</span>
			<span class="flex-1 space-y-0.5">
				<span class="block font-medium">{{ provider }}</span>
				<span class="mini-value block">{{
					done && index === 0 ? "rzp_live_••••4f2a" : "Not connected"
				}}</span>
			</span>
			<span class="mini-switch" :data-on="(done && index === 0) || undefined" />
		</div>
	</div>
</template>

<style scoped>
.mini-switch {
	position: relative;
	width: 22px;
	height: 13px;
	border-radius: 999px;
	background: var(--surface-gray-3);
	transition: background-color 200ms ease;
}
.mini-switch::after {
	content: "";
	position: absolute;
	top: 2px;
	left: 2px;
	width: 9px;
	height: 9px;
	border-radius: 999px;
	background: var(--surface-white);
	box-shadow: 0 1px 1px rgba(0, 0, 0, 0.15);
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.mini-switch[data-on] {
	background: var(--ink-gray-9);
}
.mini-switch[data-on]::after {
	transform: translateX(9px);
}
</style>
