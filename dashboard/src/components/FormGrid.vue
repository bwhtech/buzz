<script setup lang="ts" generic="T extends FrappeField">
import { type FrappeField, isLayoutField } from "@/composables/useCustomFields"

defineProps<{ fields: T[] }>()
defineSlots<{ default(props: { field: T }): unknown }>()
</script>

<template>
	<div class="grid grid-cols-1 items-start gap-4 md:grid-cols-2">
		<div
			v-for="field in fields"
			:key="field.fieldname"
			:class="{ 'md:col-span-2': field.width !== 'Half' || isLayoutField(field) }"
		>
			<slot :field="field" />
			<p v-if="field.description && !isLayoutField(field)" class="mt-1.5 text-p-sm text-ink-gray-5">
				{{ __(field.description) }}
			</p>
		</div>
	</div>
</template>
