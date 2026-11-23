<script setup lang="ts">
import "@public/themes/date_badge.css"
import { dayjs } from "frappe-ui"
import { computed } from "vue"

const props = defineProps<{ date: string | null; size?: "sm" }>()

const day = computed(() => (props.date ? dayjs(props.date) : null))
</script>

<template>
	<span class="date-badge" :data-size="size" aria-hidden="true">
		<span class="date-badge-month">{{ day ? day.format("MMM") : __("TBA") }}</span>
		<span class="date-badge-day">{{ day ? day.format("D") : "–" }}</span>
	</span>
</template>
