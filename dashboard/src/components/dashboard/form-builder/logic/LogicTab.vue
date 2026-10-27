<script setup lang="ts">
import { Button } from "frappe-ui"

import EmptyState from "@/components/common/EmptyState.vue"

import type { QuestionEditor } from "../build/useQuestionEditor"
import type { BuzzFormDoc, DoctypeField } from "../useFormBuilder"
import RuleCard from "./RuleCard.vue"
import { emptyRule } from "./ruleOptions"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{ doctypeFields: DoctypeField[]; editor: QuestionEditor }>()

// The last question has the most answers above it to depend on.
function addRule() {
	const last = form.value.questions.findLast((question) => !question.is_standard)
	if (last) form.value.logic_rules.push(emptyRule(props.editor.ensureFieldname(last)))
}

function duplicate(index: number) {
	form.value.logic_rules.splice(
		index + 1,
		0,
		JSON.parse(JSON.stringify(form.value.logic_rules[index])),
	)
}
</script>

<template>
	<div class="h-full overflow-y-auto">
		<div class="mx-auto w-full max-w-[760px] space-y-4 px-4 pb-24 pt-8 sm:px-7">
			<header class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-lg font-semibold text-ink-gray-9">Logic</h2>
					<p class="text-p-sm text-ink-gray-5">
						Show, hide or require questions based on earlier answers.
					</p>
				</div>
				<Button variant="solid" icon-left="lucide-plus" label="New rule" @click="addRule" />
			</header>

			<RuleCard
				v-for="(rule, index) in form.logic_rules"
				:key="index"
				v-model="form.logic_rules[index]"
				:questions="form.questions"
				:doctype-fields="doctypeFields"
				:ensure-fieldname="editor.ensureFieldname"
				@duplicate="duplicate(index)"
				@delete="form.logic_rules.splice(index, 1)"
			/>

			<EmptyState
				v-if="!form.logic_rules.length"
				title="No rules yet"
				description="Add questions first, then make them appear only when an earlier answer calls for them."
				icon="lucide-workflow"
			/>
		</div>
	</div>
</template>
