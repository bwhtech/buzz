<script setup lang="ts">
import { Avatar } from "frappe-ui"

import { fullName, profile } from "./useOnboarding"

defineProps<{ kind: string; active: boolean }>()
const crowd = ["A", "B", "C", "D"]
</script>

<template>
	<div
		class="illustration relative flex min-h-28 items-center justify-center overflow-hidden bg-surface-gray-1"
		:data-active="active || null"
	>
		<div
			v-if="kind === 'personal'"
			class="lift flex items-center gap-2 rounded-full bg-surface-elevation-2 py-1.5 pl-1.5 pr-3 shadow-sm"
		>
			<Avatar size="md" :image="profile.user_image || undefined" :label="fullName || '?'" />
			<span class="text-sm-medium text-ink-gray-8">
				{{ __("{0} hosts", [profile.first_name || __("You")]) }}
			</span>
		</div>
		<div v-else-if="kind === 'community'" class="lift flex -space-x-2">
			<Avatar
				v-for="initial in crowd"
				:key="initial"
				size="lg"
				:label="initial"
				style="box-shadow: 0 0 0 2px var(--surface-gray-1)"
			/>
		</div>
		<div
			v-else
			class="lift flex h-12 w-28 overflow-hidden rounded-md bg-surface-elevation-2 shadow-sm"
		>
			<div class="flex flex-1 flex-col justify-center gap-1 px-2.5">
				<span class="h-1.5 w-12 rounded-full bg-surface-gray-4" />
				<span class="h-1.5 w-8 rounded-full bg-surface-gray-3" />
			</div>
			<div class="w-6 border-l border-dashed border-outline-gray-3 bg-surface-gray-2" />
		</div>
	</div>
</template>

<style scoped>
.lift {
	transition: transform 240ms cubic-bezier(0.23, 1, 0.32, 1);
}
.illustration[data-active] .lift {
	transform: translateY(-3px) scale(1.04);
}
@media (hover: hover) and (pointer: fine) {
	.illustration:hover .lift {
		transform: translateY(-2px);
	}
}
@media (prefers-reduced-motion: reduce) {
	.lift {
		transition: none;
	}
}
</style>
