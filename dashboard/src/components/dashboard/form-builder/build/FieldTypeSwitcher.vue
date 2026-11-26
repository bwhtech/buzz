<script setup lang="ts">
import { Combobox } from "frappe-ui"
import { computed, ref } from "vue"

import { convertTargets, fieldType, filterTypeGroups } from "../fieldTypes"
import type { FormQuestion } from "../useFormBuilder"
import type { QuestionEditor } from "./useQuestionEditor"

const props = defineProps<{ question: FormQuestion; editor: QuestionEditor }>()

const query = ref("")
const type = computed(() => fieldType(props.question.fieldtype))
const options = computed(() =>
	filterTypeGroups(convertTargets(props.question.fieldtype), query.value),
)

function pick(fieldtype: unknown) {
	if (fieldtype) props.editor.convert(props.question, String(fieldtype))
}
</script>

<template>
	<Combobox
		trigger="button"
		:model-value="question.fieldtype"
		v-model:query="query"
		:options="options"
		:filterable="false"
		placeholder="Search field types"
		empty-text="No field type matches"
		align="start"
		@update:open="(isOpen: boolean) => isOpen || (query = '')"
		@update:model-value="pick"
	>
		<template #trigger>
			<slot :type="type" />
		</template>
	</Combobox>
</template>
