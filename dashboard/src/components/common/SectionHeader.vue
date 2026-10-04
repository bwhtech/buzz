<script setup lang="ts">
import { Button, type ButtonProps } from "frappe-ui"

type SectionAction = ButtonProps & { onClick: () => void }

defineProps<{
	title: string
	// Omitted while the count is unknown, so a loading list never reads as empty.
	count?: number | null
	action?: SectionAction | null
}>()
</script>

<template>
	<div class="flex items-center justify-between gap-2">
		<h2 class="flex items-baseline gap-2 text-xl font-semibold text-ink-gray-9">
			{{ title }}
			<span v-if="count != null" class="text-sm font-normal text-ink-gray-5">{{ count }}</span>
		</h2>
		<Button v-if="action" v-bind="action" />
	</div>
</template>
