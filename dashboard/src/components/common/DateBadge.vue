<script setup lang="ts">
import "@public/themes/date_badge.css"
import { dayjs } from "frappe-ui"
import { computed } from "vue"

const props = defineProps<{ date: string; size?: "sm" }>()

const day = computed(() => dayjs(props.date))
</script>

<template>
	<span class="date-badge" :data-size="size" aria-hidden="true">
		<span class="date-badge-month">{{ day.format("MMM") }}</span>
		<span class="date-badge-day">{{ day.format("D") }}</span>
	</span>
</template>
