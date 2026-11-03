<script setup lang="ts">
import { BottomSheet, Button, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

import type { QuestionEditor } from "../build/useQuestionEditor"
import { fieldType } from "../fieldTypes"
import type { BuzzFormDoc, DoctypeField } from "../useFormBuilder"
import RuleCard from "./RuleCard.vue"
import { emptyRule } from "./ruleOptions"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{ doctypeFields: DoctypeField[]; editor: QuestionEditor }>()
defineEmits<{ openBuild: [] }>()

const NO_TARGETS = "Add a question first: core fields are always asked"

// Rules act on the form's own questions; core fields always show.
const targets = computed(() =>
	form.value.questions.filter(
		(question) => !question.is_standard && fieldType(question.fieldtype).group !== "Layout",
	),
)

// On a phone, rules list as summaries and the one tapped is edited in a sheet.
const isPhone = useIsMobile()
const editing = ref<number | null>(null)
const sheetOpen = computed({
	get: () => editing.value !== null,
	set: (open) => open || (editing.value = null),
})

// The last question has the most answers above it to depend on.
function addRule() {
	const last = targets.value.at(-1)
	if (!last) return
	form.value.logic_rules.push(emptyRule(props.editor.ensureFieldname(last)))
	if (isPhone.value) editing.value = form.value.logic_rules.length - 1
}

function duplicate(index: number) {
	form.value.logic_rules.splice(
		index + 1,
		0,
		JSON.parse(JSON.stringify(form.value.logic_rules[index])),
	)
}

function remove(index: number) {
	editing.value = null
	form.value.logic_rules.splice(index, 1)
}
</script>

<template>
	<div class="h-full overflow-y-auto bg-surface-base">
		<div
			class="mx-auto flex w-full max-w-[760px] flex-col gap-3 px-4 pb-36 pt-5 sm:px-6 sm:pb-72 sm:pt-10"
		>
			<header class="mb-1 flex items-end gap-3 px-1 sm:mb-3 sm:px-0">
				<div class="flex min-w-0 flex-1 flex-col gap-1">
					<h2 class="text-lg font-semibold tracking-[-0.01em] text-ink-gray-9 sm:text-xl">Logic</h2>
					<p class="text-p-sm text-ink-gray-5">
						Show, hide or require fields based on earlier answers
					</p>
				</div>
				<Tooltip v-if="!isPhone" :text="NO_TARGETS" :disabled="!!targets.length">
					<Button
						variant="solid"
						icon-left="lucide-plus"
						label="Add rule"
						:disabled="!targets.length"
						@click="addRule"
					/>
				</Tooltip>
			</header>

			<RuleCard
				v-for="(rule, index) in form.logic_rules"
				:key="index"
				v-model="form.logic_rules[index]"
				:questions="form.questions"
				:doctype-fields="doctypeFields"
				:ensure-fieldname="editor.ensureFieldname"
				:readonly="isPhone"
				:class="{ 'cursor-pointer transition-transform duration-150 active:scale-[0.99]': isPhone }"
				@click="isPhone && (editing = index)"
				@duplicate="duplicate(index)"
				@delete="remove(index)"
			/>

			<div
				v-if="!form.logic_rules.length"
				class="flex flex-col items-center gap-2 rounded-5 border border-dashed border-outline-gray-3 px-6 py-10 text-center sm:py-12"
			>
				<template v-if="targets.length">
					<p class="text-p-base font-medium text-ink-gray-8">No rules yet</p>
					<p class="max-w-[340px] text-p-sm text-ink-gray-5">
						A rule reads like a sentence. If someone picks Workshop, then show Max participants.
					</p>
					<Button
						v-if="!isPhone"
						class="mt-2"
						variant="subtle"
						icon-left="lucide-plus"
						label="Add rule"
						@click="addRule"
					/>
				</template>
				<template v-else>
					<p class="text-p-base font-medium text-ink-gray-8">Logic needs a question you add</p>
					<p class="max-w-[340px] text-p-sm text-ink-gray-5">
						This form only has core fields, and those are always asked, so no rule can change them.
						Add a question in Build to show, hide or require it based on answers.
					</p>
					<Button
						class="mt-2"
						variant="subtle"
						icon-left="lucide-layout-list"
						label="Go to Build"
						@click="$emit('openBuild')"
					/>
				</template>
			</div>

			<Button
				v-if="isPhone && targets.length"
				class="w-full"
				size="lg"
				icon-left="lucide-plus"
				label="Add rule"
				@click="addRule"
			/>
		</div>

		<BottomSheet v-if="isPhone" v-model:open="sheetOpen" title="Edit rule">
			<div v-if="editing !== null" class="px-4 pb-8">
				<RuleCard
					v-model="form.logic_rules[editing]"
					:questions="form.questions"
					:doctype-fields="doctypeFields"
					:ensure-fieldname="editor.ensureFieldname"
					@duplicate="duplicate(editing)"
					@delete="remove(editing)"
				/>
			</div>
		</BottomSheet>
	</div>
</template>
