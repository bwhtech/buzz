<script setup lang="ts">
import { type ButtonProps, Icon } from "frappe-ui"

import EmptyState from "@/components/common/EmptyState.vue"
import SectionHeader from "@/components/common/SectionHeader.vue"

defineProps<{
	title: string
	description?: string
	count?: number | null
	action?: (ButtonProps & { onClick: () => void }) | null
	empty: boolean
	emptyTitle: string
	emptyDescription: string
	emptyIcon: string
}>()
</script>

<template>
	<section class="space-y-3">
		<div>
			<SectionHeader :title="title" :count="count" :action="action" />
			<p v-if="description" class="mt-1 text-p-base text-ink-gray-5">{{ description }}</p>
		</div>
		<EmptyState v-if="empty" :title="emptyTitle" :description="emptyDescription">
			<template #illustration>
				<Icon :name="emptyIcon" class="size-5 text-ink-gray-5" />
			</template>
		</EmptyState>
		<slot v-else />
	</section>
</template>
