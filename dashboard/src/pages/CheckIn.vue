<script setup lang="ts">
import { useRouter } from "vue-router"

import CheckInGuestList from "@/components/checkin/CheckInGuestList.vue"
import EventSelector from "@/components/EventSelector.vue"

defineProps<{ eventName?: string }>()

const router = useRouter()
</script>

<template>
	<CheckInGuestList v-if="eventName" :key="eventName" :event="eventName" />
	<EventSelector
		v-else
		@select="(event) => router.push({ name: 'check-in', params: { eventName: event.name } })"
	/>
</template>
