<script setup lang="ts">
import EmptyState from "@/components/common/EmptyState.vue"

import type { BuzzFormDoc, DoctypeField } from "../useFormBuilder"
import FieldRow from "./FieldRow.vue"

const form = defineModel<BuzzFormDoc>({ required: true })
defineProps<{ doctypeFields: Record<string, DoctypeField> }>()
</script>

<template>
	<div class="mx-auto w-full max-w-[760px] px-4 py-8 sm:px-7">
		<div class="rounded-8 bg-surface-base p-5 shadow-sm ring-1 ring-outline-gray-1 sm:p-8">
			<input
				v-model="form.title"
				class="w-full border-0 bg-transparent p-0 text-2xl font-semibold text-ink-gray-9 outline-none focus:ring-0"
				aria-label="Form name"
			/>
			<textarea
				v-model="form.description"
				rows="1"
				class="mb-6 mt-1 w-full resize-none border-0 bg-transparent p-0 text-p-base text-ink-gray-6 outline-none [field-sizing:content] placeholder:text-ink-gray-4 focus:ring-0"
				placeholder="Add a description"
				aria-label="Form description"
			/>
			<div v-if="form.questions.length" class="-mx-3 space-y-1">
				<FieldRow
					v-for="(question, index) in form.questions"
					:key="question.name ?? index"
					v-model="form.questions[index]"
					:doctype-field="question.is_standard ? doctypeFields[question.fieldname] : undefined"
				/>
			</div>
			<EmptyState
				v-else
				title="No questions yet"
				description="Add questions to ask more than the form's own fields."
				icon="lucide-list-plus"
			/>
		</div>
	</div>
</template>
