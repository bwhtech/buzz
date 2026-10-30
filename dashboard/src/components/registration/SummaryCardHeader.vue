<template>
	<div class="flex items-center gap-2 border-b border-outline-gray-1 py-2 pl-4 pr-2">
		<h2 class="flex-1 text-base font-semibold text-ink-gray-9">{{ title }}</h2>
		<Button variant="ghost" :label="__('Edit')" @click="emit('edit')">
			<template #prefix><LucidePencil class="size-3.5" /></template>
		</Button>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import LucidePencil from "~icons/lucide/pencil"

defineProps<{ title: string }>()
const emit = defineEmits<{ edit: [] }>()
</script>
