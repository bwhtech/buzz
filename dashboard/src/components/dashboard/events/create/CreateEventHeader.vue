<script setup lang="ts">
import { Button } from "frappe-ui"

import { useIsMobile } from "@/composables/useIsMobile"
import type { ChecklistItem } from "@/utils/eventValidation"

import CreateEventButton from "./CreateEventButton.vue"

// The page's own bar, since it covers the sidebar: the way out, where you are, and
// Create, which steps aside while the copy at the end of the form is on screen.
defineProps<{ missing: ChecklistItem[]; loading?: boolean; createHidden: boolean }>()
const showMissing = defineModel<boolean>("showMissing", { default: false })
const emit = defineEmits<{ create: []; close: [] }>()

const isMobile = useIsMobile()
</script>

<template>
	<header
		class="flex h-12 shrink-0 items-center gap-3 border-b border-outline-gray-1 bg-surface-base px-2 md:px-4"
	>
		<Button variant="ghost" icon="lucide-x" :aria-label="__('Close')" @click="emit('close')" />
		<span v-if="isMobile" class="text-base font-semibold text-ink-gray-9">{{
			__("New event")
		}}</span>
		<nav v-else :aria-label="__('Breadcrumb')" class="flex min-w-0 items-center gap-1.5 text-base">
			<router-link :to="{ name: 'events' }" class="text-ink-gray-5 hover:text-ink-gray-8">{{
				__("Events")
			}}</router-link>
			<span class="text-ink-gray-4" aria-hidden="true">/</span>
			<span class="whitespace-nowrap font-medium text-ink-gray-9">{{ __("New event") }}</span>
		</nav>
		<div class="flex-1" />
		<!-- Kept in the layout while hidden, so nothing beside it jumps when it hands over. -->
		<div
			class="header-create"
			:data-hidden="createHidden || undefined"
			:inert="createHidden || undefined"
		>
			<CreateEventButton
				v-model:show-missing="showMissing"
				placement="header"
				:missing="missing"
				:loading="loading"
				@create="emit('create')"
			/>
		</div>
	</header>
</template>

<style scoped>
.header-create {
	transition:
		opacity 160ms ease-out,
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.header-create[data-hidden] {
	opacity: 0;
	transform: scale(0.96);
	pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
	.header-create[data-hidden] {
		transform: none;
	}
}
</style>
