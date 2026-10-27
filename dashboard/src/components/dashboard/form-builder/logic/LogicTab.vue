<script setup lang="ts">
import { Button } from "frappe-ui"

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
	<div class="h-full overflow-y-auto bg-surface-base">
		<div class="mx-auto flex w-full max-w-[760px] flex-col gap-3 px-4 pb-72 pt-10 sm:px-6">
			<header class="mb-3 flex items-end gap-3">
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<h2 class="text-xl font-semibold tracking-[-0.01em] text-ink-gray-9">Logic</h2>
					<p class="text-p-sm text-ink-gray-5">
						Show, hide or require fields based on earlier answers
					</p>
				</div>
				<Button variant="solid" icon-left="lucide-plus" label="Add rule" @click="addRule" />
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

			<div
				v-if="!form.logic_rules.length"
				class="flex flex-col items-center gap-2 rounded-5 border border-dashed border-outline-gray-3 px-6 py-12 text-center"
			>
				<p class="text-p-base font-medium text-ink-gray-8">No rules yet</p>
				<p class="max-w-[340px] text-p-sm text-ink-gray-5">
					A rule reads like a sentence. If someone picks Workshop, then show Max participants.
				</p>
				<Button
					class="mt-2"
					variant="subtle"
					icon-left="lucide-plus"
					label="Add rule"
					@click="addRule"
				/>
			</div>
		</div>
	</div>
</template>
