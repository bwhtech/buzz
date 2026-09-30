<script setup lang="ts">
import { ItemListRow } from "frappe-ui"

defineProps<{ icon: string; title: string; subtitle?: string | null; active?: boolean }>()
</script>

<template>
	<!-- The button is written here, not passed as `as="button"`: a dynamic "button" resolves
	 to the globally registered frappe-ui Button. -->
	<button type="button" class="group block w-full rounded-4 text-left outline-none">
		<!-- ItemListRow centres its prefix and has no hover of its own: both are set here. -->
		<ItemListRow
			as="span"
			:active="active"
			class="!items-start duration-100 group-focus-visible:bg-surface-gray-2 group-active:bg-surface-gray-3"
			:class="!active && 'group-hover:bg-surface-gray-2'"
		>
			<template #prefix>
				<span class="mt-0.5 size-4 text-ink-gray-5" :class="icon" aria-hidden="true" />
			</template>
			<template #label>
				<span class="block truncate text-base text-ink-gray-8">{{ title }}</span>
				<span v-if="subtitle" class="block truncate text-p-sm text-ink-gray-5">{{ subtitle }}</span>
			</template>
		</ItemListRow>
	</button>
</template>
