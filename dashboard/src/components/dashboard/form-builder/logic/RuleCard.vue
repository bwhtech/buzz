<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import type { LogicRule } from "@/utils/formLogic"

import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import ConditionList from "./ConditionList.vue"
import LogicPill from "./LogicPill.vue"
import { ACTIONS, ruleFields } from "./ruleOptions"

const rule = defineModel<LogicRule>({ required: true })
const props = defineProps<{
	questions: FormQuestion[]
	doctypeFields: DoctypeField[]
	ensureFieldname: (question: FormQuestion) => string
	// A summary on a phone: tapping the card opens the editable rule in a sheet.
	readonly?: boolean
}>()
defineEmits<{ duplicate: []; delete: [] }>()

const targets = computed(() => props.questions.filter((question) => !question.is_standard))
const firstTarget = computed(() =>
	Math.min(
		...rule.value.actions.map(([, target]) =>
			props.questions.findIndex((question) => question.fieldname === target),
		),
	),
)
const fields = computed(() => ruleFields(props.doctypeFields, props.questions, firstTarget.value))
const labelOf = (fieldname: string) =>
	props.questions.find((question) => question.fieldname === fieldname)?.label || "pick a question"

function targetOptions(index: number) {
	return targets.value.map((question) => ({
		label: question.label,
		onClick: () => (rule.value.actions[index][1] = props.ensureFieldname(question)),
	}))
}

function actionOptions(index: number) {
	return ACTIONS.map((action) => ({
		label: action.label,
		onClick: () => (rule.value.actions[index][0] = action.value),
	}))
}

const conditionList = ref<InstanceType<typeof ConditionList> | null>(null)

function addAction() {
	const target = targets.value.find(
		(question) => !rule.value.actions.some(([, name]) => name === question.fieldname),
	)
	if (target) rule.value.actions.push(["show", props.ensureFieldname(target)])
}
</script>

<template>
	<article
		class="relative flex flex-col gap-2.5 rounded-5 bg-surface-base pb-3.5 pl-[18px] pr-4 pt-4 ring-1 ring-inset ring-outline-gray-2"
		:class="{ 'pr-20': !readonly }"
	>
		<div v-if="!readonly" class="absolute right-2.5 top-2.5 flex gap-0.5">
			<Tooltip text="Duplicate rule">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-layers-2"
					label="Duplicate rule"
					@click="$emit('duplicate')"
				/>
			</Tooltip>
			<Tooltip text="Delete rule">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-trash-2"
					label="Delete rule"
					@click="$emit('delete')"
				/>
			</Tooltip>
		</div>

		<ConditionList
			ref="conditionList"
			v-model="rule"
			:fields="fields"
			:readonly="readonly"
			lead-words
		/>
		<div v-if="!rule.conditions.length" class="flex min-h-7 items-center">
			<span class="w-11 text-p-base font-medium text-ink-gray-6">If</span>
			<span class="text-p-sm text-ink-gray-5">no conditions yet, so this rule never runs</span>
		</div>
		<div v-if="!readonly" class="flex pl-11">
			<button
				type="button"
				class="-ml-1.5 rounded-5 px-1.5 py-0.5 text-p-sm text-ink-gray-5 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-9"
				@click="conditionList?.addCondition()"
			>
				+ condition
			</button>
		</div>

		<div
			v-for="(action, index) in rule.actions"
			:key="`a${index}`"
			class="flex min-h-7 flex-wrap items-center gap-1.5"
		>
			<span class="w-11 shrink-0 text-p-base font-medium text-ink-gray-6">
				{{ index === 0 ? "then" : "and" }}
			</span>
			<LogicPill
				:kind="action[0] as 'show' | 'hide' | 'require'"
				:label="action[0]"
				:options="readonly ? undefined : actionOptions(index)"
			/>
			<LogicPill
				:label="labelOf(action[1])"
				:options="readonly ? undefined : targetOptions(index)"
			/>
			<button
				v-if="!readonly && rule.actions.length > 1"
				type="button"
				class="grid size-[22px] place-items-center rounded-5 text-ink-gray-4 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-8"
				aria-label="Remove action"
				@click="rule.actions.splice(index, 1)"
			>
				<span class="lucide-x size-3" aria-hidden="true" />
			</button>
		</div>
		<div v-if="!readonly" class="flex pl-11">
			<button
				type="button"
				class="-ml-1.5 rounded-5 px-1.5 py-0.5 text-p-sm text-ink-gray-5 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-9"
				@click="addAction"
			>
				+ action
			</button>
		</div>
	</article>
</template>
