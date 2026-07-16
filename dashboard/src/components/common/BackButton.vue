<template>
	<Button variant="ghost" icon-left="chevron-left" :route="to" @click="$emit('click', $event)">
		{{ label }}
	</Button>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router";

withDefaults(
	defineProps<{
		to?: RouteLocationRaw | null;
		label?: string;
	}>(),
	{
		to: null,
		label: "Back",
	}
);

defineEmits<{
	click: [];
}>();
</script>
