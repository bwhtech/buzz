<script setup lang="ts">
import { Badge } from "frappe-ui"
import { computed } from "vue"

import { fieldType } from "../fieldTypes"
import type { FormQuestion } from "../useFormBuilder"

const question = defineModel<FormQuestion>({ required: true })

const type = computed(() => fieldType(question.value.fieldtype))
</script>

<template>
	<div
		class="group flex items-center gap-3 rounded-4 px-3 py-2.5 transition-colors duration-150 focus-within:bg-surface-gray-1 [@media(hover:hover)]:hover:bg-surface-gray-1"
		:class="{ 'opacity-50': !question.enabled }"
	>
		<span :class="[type.icon, 'size-4 shrink-0 text-ink-gray-5']" aria-hidden="true" />
		<input
			v-model="question.label"
			class="min-w-0 flex-1 border-0 bg-transparent p-0 text-p-base font-medium text-ink-gray-9 outline-none focus:ring-0"
			:aria-label="`Label of ${type.label} field`"
			@keydown.enter="($event.target as HTMLInputElement).blur()"
		/>
		<Badge v-if="question.mandatory" label="Required" theme="gray" size="sm" />
		<span class="text-p-sm text-ink-gray-4">{{ type.label }}</span>
	</div>
</template>
