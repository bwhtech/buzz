<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { onBeforeUnmount, useTemplateRef, watchEffect } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import type { ChecklistItem } from "@/utils/eventValidation"

import CreateEventButton from "./CreateEventButton.vue"

// The form's last row. While it is on screen the header hands Create over to it, so the
// button is wherever the organiser finished. A phone pins it to the bottom of the screen
// instead, under the thumb, and the header carries none.
defineProps<{ missing: ChecklistItem[]; loading?: boolean }>()
const showMissing = defineModel<boolean>("showMissing", { default: false })
const visible = defineModel<boolean>("visible", { default: false })
const emit = defineEmits<{ create: [] }>()

const isMobile = useIsMobile()
const row = useTemplateRef<HTMLElement>("row")
useIntersectionObserver(
	row,
	([entry]) => (visible.value = isMobile.value || Boolean(entry?.isIntersecting)),
	{ threshold: 0.6 },
)
watchEffect(() => isMobile.value && (visible.value = true))
onBeforeUnmount(() => (visible.value = false))
</script>

<template>
	<div
		v-if="isMobile"
		class="fixed inset-x-0 bottom-0 z-20 border-t border-outline-gray-2 bg-surface-base px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3"
	>
		<CreateEventButton
			v-model:show-missing="showMissing"
			placement="end"
			wide
			:missing="missing"
			:loading="loading"
			@create="emit('create')"
		/>
	</div>
	<div v-else ref="row" class="flex justify-end border-t border-outline-gray-1 pt-5">
		<CreateEventButton
			v-model:show-missing="showMissing"
			placement="end"
			:missing="missing"
			:loading="loading"
			@create="emit('create')"
		/>
	</div>
</template>
