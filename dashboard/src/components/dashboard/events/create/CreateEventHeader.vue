<script setup lang="ts">
import { Button, PageHeaderMobile } from "frappe-ui"

import { useIsMobile } from "@/composables/useIsMobile"
import type { ChecklistItem } from "@/utils/eventValidation"

import CreateEventButton from "./CreateEventButton.vue"

// The page's own bar, since it covers the sidebar: the way back, the title, and on
// larger screens Create, which steps aside while the copy at the end of the form shows.
defineProps<{ missing: ChecklistItem[]; loading?: boolean; createHidden: boolean }>()
const showMissing = defineModel<boolean>("showMissing", { default: false })
const emit = defineEmits<{ create: []; close: [] }>()

const isMobile = useIsMobile()
</script>

<template>
	<!-- A phone gets the app's standard bar, title centred; Create lives at the end of the form. -->
	<PageHeaderMobile v-if="isMobile" :title="__('Create New Event')">
		<template #prefix>
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				:aria-label="__('Back')"
				@click="emit('close')"
			/>
		</template>
	</PageHeaderMobile>
	<header v-else class="flex h-12 shrink-0 items-center gap-3 bg-surface-base px-2 md:px-4">
		<Button
			variant="ghost"
			icon="lucide-chevron-left"
			:aria-label="__('Back')"
			@click="emit('close')"
		/>
		<h1 class="truncate text-base font-semibold text-ink-gray-9">{{ __("Create New Event") }}</h1>
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
