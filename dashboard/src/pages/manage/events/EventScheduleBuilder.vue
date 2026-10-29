<script setup lang="ts">
import { Button } from "frappe-ui"
import { useRoute } from "vue-router"

const route = useRoute()
</script>

<template>
	<div class="flex h-full flex-col bg-surface-base">
		<header class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-2.5">
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				label="Back to talks"
				:route="{ name: 'event-talks', params: { eventId: route.params.eventId } }"
			/>
			<span class="text-p-sm font-medium text-ink-gray-9">Schedule</span>
		</header>
	</div>
</template>
