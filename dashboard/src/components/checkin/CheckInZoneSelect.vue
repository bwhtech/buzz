<script setup lang="ts">
import { Select } from "frappe-ui"
import { computed } from "vue"

import { ANY_ZONE } from "@/composables/useCheckInZone"
import type { GuestZone } from "@/types"

const props = defineProps<{ zones: GuestZone[]; anyZone?: boolean }>()

const model = defineModel<string>({ required: true })

const options = computed(() => [
	...props.zones.map((zone) => ({ label: zone.title, value: zone.name })),
	...(props.anyZone ? [{ label: __("Any zone"), value: ANY_ZONE }] : []),
])
</script>

<template>
	<Select v-if="zones.length > 1" v-model="model" :options="options" aria-label="Check-in zone" />
</template>
