<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { onBeforeUnmount, useTemplateRef } from "vue"

import type { ChecklistItem } from "@/utils/eventValidation"

import CreateEventButton from "./CreateEventButton.vue"

// The form's last row. While it is on screen the header hands Create over to it, so the
// button is wherever the organiser finished.
defineProps<{ missing: ChecklistItem[]; loading?: boolean }>()
const showMissing = defineModel<boolean>("showMissing", { default: false })
const visible = defineModel<boolean>("visible", { default: false })
const emit = defineEmits<{ create: [] }>()

const row = useTemplateRef<HTMLElement>("row")
useIntersectionObserver(row, ([entry]) => (visible.value = Boolean(entry?.isIntersecting)), {
	threshold: 0.6,
})
onBeforeUnmount(() => (visible.value = false))
</script>

<template>
	<div ref="row" class="flex justify-end border-t border-outline-gray-1 pt-5">
		<CreateEventButton
			v-model:show-missing="showMissing"
			placement="end"
			:missing="missing"
			:loading="loading"
			@create="emit('create')"
		/>
	</div>
</template>
