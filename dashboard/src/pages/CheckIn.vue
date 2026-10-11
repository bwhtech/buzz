<script setup lang="ts">
import { useRouter } from "vue-router"

import CheckInGuestList from "@/components/checkin/CheckInGuestList.vue"
import BackButton from "@/components/common/BackButton.vue"
import EventSelector from "@/components/EventSelector.vue"

defineProps<{ eventName?: string }>()

const router = useRouter()
</script>

<template>
	<div v-if="eventName">
		<BackButton class="ml-2 mt-2" label="All events" :to="{ name: 'check-in' }" />
		<CheckInGuestList :key="eventName" :event="eventName" />
	</div>
	<div v-else class="mx-auto w-full max-w-3xl p-4">
		<EventSelector
			@select="(event) => router.push({ name: 'check-in', params: { eventName: event.name } })"
		/>
	</div>
</template>
