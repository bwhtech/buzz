<script setup lang="ts">
import { useRouter } from "vue-router"

import CheckInGuestList from "@/components/checkin/CheckInGuestList.vue"
import EventSelector from "@/components/EventSelector.vue"

defineProps<{ eventName?: string }>()

const router = useRouter()
</script>

<template>
	<CheckInGuestList v-if="eventName" :key="eventName" :event="eventName" />
	<div v-else class="mx-auto w-full max-w-3xl p-4">
		<EventSelector
			@select="(event) => router.push({ name: 'check-in', params: { eventName: event.name } })"
		/>
	</div>
</template>
