<script setup lang="ts">
import { Button } from "frappe-ui"

import ZoomLogo from "@/components/common/ZoomLogo.vue"
import LocationMap from "@/components/dashboard/events/location/LocationMap.vue"

defineProps<{
	title: string
	subtitle?: string | null
	placeId?: string | null
	isZoom?: boolean
	disabled?: boolean
}>()
defineEmits<{ change: []; remove: [] }>()
</script>

<template>
	<div class="space-y-3 mt-3">
		<div class="flex items-start gap-2">
			<ZoomLogo v-if="isZoom" class="mt-0.5 size-5 shrink-0" />
			<div class="min-w-0 space-y-1">
				<p class="text-md font-medium text-ink-gray-9">{{ title }}</p>
				<p v-if="subtitle" class="line-clamp-2 text-p-sm text-ink-gray-6">{{ subtitle }}</p>
			</div>
		</div>
		<LocationMap class="h-44 rounded-5" :place-id="placeId" :title="title" />
		<div class="flex gap-2">
			<Button
				class="flex-1"
				variant="outline"
				label="Change"
				:disabled="disabled"
				@click="$emit('change')"
			/>
			<Button
				icon="lucide-trash"
				variant="outline"
				tooltip="Remove Location"
				label="Remove"
				:disabled="disabled"
				@click="$emit('remove')"
			/>
		</div>
	</div>
</template>
