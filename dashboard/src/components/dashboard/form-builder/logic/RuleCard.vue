<script setup lang="ts">
import { Button, MultiSelect, Tooltip } from "frappe-ui"
import { computed, onMounted } from "vue"

import type { Condition, LogicRule } from "@/utils/formLogic"

import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import LogicPill from "./LogicPill.vue"
import {
	ACTIONS,
	type RuleField,
	newCondition,
	operatorOf,
	operatorsFor,
	ruleFields,
} from "./ruleOptions"

const rule = defineModel<LogicRule>({ required: true })
const props = defineProps<{
	questions: FormQuestion[]
	doctypeFields: DoctypeField[]
	ensureFieldname: (question: FormQuestion) => string
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
const fieldOf = (condition: Condition) =>
	fields.value.find((field) => field.fieldname === condition[0])
const labelOf = (fieldname: string) =>
	props.questions.find((question) => question.fieldname === fieldname)?.label || "pick a question"

const valueLabel = (field: RuleField | undefined, value: unknown) =>
	field?.values?.find((option) => option.value === value)?.label ?? String(value ?? "pick…")

function fieldOptions(index: number) {
	return fields.value.map((field) => ({
		label: field.label,
		onClick: () => (rule.value.conditions[index] = newCondition(field)),
	}))
}

function operatorOptions(index: number) {
	const condition = rule.value.conditions[index]
	return operatorsFor(fieldOf(condition)).map((operator) => ({
		label: operator.label,
		onClick: () => {
			const value =
				operator.fixed ?? (operator.list ? [] : (fieldOf(condition)?.values?.[0]?.value ?? ""))
			rule.value.conditions[index] = [condition[0], operator.value, value]
		},
	}))
}

function valueOptions(index: number) {
	const condition = rule.value.conditions[index]
	return (fieldOf(condition)?.values ?? []).map((option) => ({
		label: option.label,
		onClick: () => (condition[2] = option.value),
	}))
}

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

function addCondition() {
	if (fields.value.length) rule.value.conditions.push(newCondition(fields.value[0]))
}

// A new rule opens with a condition to fill in.
onMounted(() => rule.value.conditions.length || addCondition())

function addAction() {
	const target = targets.value.find(
		(question) => !rule.value.actions.some(([, name]) => name === question.fieldname),
	)
	if (target) rule.value.actions.push(["show", props.ensureFieldname(target)])
}
</script>

<template>
	<article
		class="relative flex flex-col gap-2.5 rounded-5 bg-surface-base pb-3.5 pl-[18px] pr-4 pt-4 ring-1 ring-inset ring-outline-gray-2 sm:pr-20"
	>
		<div class="absolute right-2.5 top-2.5 flex gap-0.5">
			<Tooltip text="Duplicate rule">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-copy"
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

		<div
			v-for="(condition, index) in rule.conditions"
			:key="`c${index}`"
			class="flex min-h-7 flex-wrap items-center gap-1.5"
		>
			<span class="flex w-11 shrink-0">
				<span v-if="index === 0" class="text-p-base font-medium text-ink-gray-6">If</span>
				<LogicPill
					v-else
					kind="join"
					:label="rule.match === 'any' ? 'or' : 'and'"
					:aria-label="`Match ${rule.match === 'any' ? 'all' : 'any'} conditions`"
					@click="rule.match = rule.match === 'any' ? 'all' : 'any'"
				/>
			</span>
			<LogicPill
				:label="fieldOf(condition)?.label ?? condition[0]"
				:options="fieldOptions(index)"
			/>
			<LogicPill
				kind="word"
				:label="operatorOf(condition)?.label ?? condition[1]"
				:options="operatorOptions(index)"
			/>
			<template v-if="!operatorOf(condition)?.fixed">
				<MultiSelect
					v-if="operatorOf(condition)?.list && fieldOf(condition)?.values"
					:model-value="Array.isArray(condition[2]) ? condition[2] : []"
					@update:model-value="
						(items: any[]) => (condition[2] = items.map((item) => item?.value ?? item))
					"
					class="min-w-40"
					:options="fieldOf(condition)?.values as any"
					placeholder="pick…"
				/>
				<LogicPill
					v-else-if="fieldOf(condition)?.values"
					:label="valueLabel(fieldOf(condition), condition[2])"
					:options="valueOptions(index)"
				/>
				<input
					v-else
					v-model="condition[2] as string"
					placeholder="a value"
					aria-label="Value"
					class="h-[26px] w-40 rounded-5 border-0 bg-surface-gray-2 px-2 text-p-base text-ink-gray-8 outline-none placeholder:text-ink-gray-4 focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				/>
			</template>
			<button
				type="button"
				class="grid size-[22px] place-items-center rounded-5 text-ink-gray-4 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-8"
				aria-label="Remove condition"
				@click="rule.conditions.splice(index, 1)"
			>
				<span class="lucide-x size-3" aria-hidden="true" />
			</button>
		</div>
		<div v-if="!rule.conditions.length" class="flex min-h-7 items-center">
			<span class="w-11 text-p-base font-medium text-ink-gray-6">If</span>
			<span class="text-p-sm text-ink-gray-5">no conditions yet, so this rule never runs</span>
		</div>
		<div class="flex pl-11">
			<button
				type="button"
				class="-ml-1.5 rounded-5 px-1.5 py-0.5 text-p-sm text-ink-gray-5 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-9"
				@click="addCondition"
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
				:options="actionOptions(index)"
			/>
			<LogicPill :label="labelOf(action[1])" :options="targetOptions(index)" />
			<button
				v-if="rule.actions.length > 1"
				type="button"
				class="grid size-[22px] place-items-center rounded-5 text-ink-gray-4 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-8"
				aria-label="Remove action"
				@click="rule.actions.splice(index, 1)"
			>
				<span class="lucide-x size-3" aria-hidden="true" />
			</button>
		</div>
		<div class="flex pl-11">
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
