<script lang="ts">
export type QuickAction = {
	icon: string
	label: string
	link?: string
	loading?: boolean
	onClick?: () => void
}
</script>

<script setup lang="ts">
import { Button } from "frappe-ui"

import QuickActionTile, { PRESSABLE } from "@/components/dashboard/events/QuickActionTile.vue"

defineProps<{
	// What is open or closed — "Registration", "Proposals".
	subject: string
	closed: boolean
	canWrite: boolean
	openIcon: string
	closedIcon: string
	actions: QuickAction[]
}>()
defineEmits<{ toggle: [] }>()
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<!-- The tiles share the buttons' own background, so a caller that adds one more reads
		 as a second row of the same block rather than a second block. -->
	<div class="flex flex-col rounded-4 p-1 bg-surface-gray-2">
		<QuickActionTile
			:icon="closed ? closedIcon : openIcon"
			:title="subject"
			:subtitle="closed ? 'Closed' : 'Open'"
			:tone="closed ? 'red' : 'green'"
			:pulse="!closed"
			:disabled="!canWrite"
			@click="$emit('toggle')"
		/>
		<slot />
	</div>

	<section class="space-y-1 pt-1">
		<Button
			v-for="action in actions"
			:key="action.label"
			:class="`w-full !justify-start ${PRESSABLE}`"
			variant="ghost"
			:label="action.label"
			:link="action.link"
			:loading="action.loading"
			@click="action.onClick?.()"
		>
			<template #prefix>
				<span :class="[action.icon, 'size-4']" aria-hidden="true" />
			</template>
		</Button>
	</section>
</template>
