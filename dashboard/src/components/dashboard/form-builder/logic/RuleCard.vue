<script setup lang="ts">
import { Button, Dropdown, MultiSelect, TextInput } from "frappe-ui"
import { computed, onMounted } from "vue"

import type { Condition, LogicRule } from "@/utils/formLogic"

import type { DoctypeField, FormQuestion } from "../useFormBuilder"
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

const PILL = "!h-7 rounded-5 px-2 text-p-sm"

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
		icon: action.icon,
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
	<article class="space-y-3 rounded-8 bg-surface-base p-4 shadow-sm ring-1 ring-outline-gray-1">
		<div
			v-for="(condition, index) in rule.conditions"
			:key="`c${index}`"
			class="flex flex-wrap items-center gap-1.5"
		>
			<span class="w-12 text-p-sm text-ink-gray-5">
				<template v-if="index === 0">When</template>
				<button
					v-else
					type="button"
					class="rounded-5 px-1.5 py-0.5 text-p-sm text-ink-gray-7 ring-1 ring-outline-gray-2 [@media(hover:hover)]:hover:bg-surface-gray-2"
					:aria-label="`Match ${rule.match === 'any' ? 'all' : 'any'} conditions`"
					@click="rule.match = rule.match === 'any' ? 'all' : 'any'"
				>
					{{ rule.match === "any" ? "or" : "and" }}
				</button>
			</span>
			<Dropdown :options="fieldOptions(index)">
				<Button :class="PILL" variant="subtle" :label="fieldOf(condition)?.label ?? condition[0]" />
			</Dropdown>
			<Dropdown :options="operatorOptions(index)">
				<Button
					:class="PILL"
					variant="ghost"
					:label="operatorOf(condition)?.label ?? condition[1]"
				/>
			</Dropdown>
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
				<Dropdown v-else-if="fieldOf(condition)?.values" :options="valueOptions(index)">
					<Button
						:class="PILL"
						variant="subtle"
						:label="valueLabel(fieldOf(condition), condition[2])"
					/>
				</Dropdown>
				<TextInput
					v-else
					v-model="condition[2] as string"
					size="sm"
					class="w-40"
					placeholder="a value"
				/>
			</template>
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-x"
				label="Remove condition"
				class="ml-auto"
				@click="rule.conditions.splice(index, 1)"
			/>
		</div>
		<Button
			variant="ghost"
			size="sm"
			icon-left="lucide-plus"
			label="Condition"
			@click="addCondition"
		/>

		<div class="border-t border-outline-gray-1 pt-3">
			<div
				v-for="(action, index) in rule.actions"
				:key="`a${index}`"
				class="flex flex-wrap items-center gap-1.5"
			>
				<span class="w-12 text-p-sm text-ink-gray-5">{{ index === 0 ? "Then" : "and" }}</span>
				<Dropdown :options="actionOptions(index)">
					<Button :class="PILL" variant="subtle" :label="action[0]" />
				</Dropdown>
				<Dropdown :options="targetOptions(index)">
					<Button :class="PILL" variant="subtle" :label="labelOf(action[1])" />
				</Dropdown>
				<Button
					v-if="rule.actions.length > 1"
					variant="ghost"
					size="sm"
					icon="lucide-x"
					label="Remove action"
					class="ml-auto"
					@click="rule.actions.splice(index, 1)"
				/>
			</div>
		</div>
		<div class="flex items-center gap-1">
			<Button variant="ghost" size="sm" icon-left="lucide-plus" label="Action" @click="addAction" />
			<span class="flex-1" />
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-copy"
				label="Duplicate rule"
				@click="$emit('duplicate')"
			/>
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-trash-2"
				label="Delete rule"
				@click="$emit('delete')"
			/>
		</div>
	</article>
</template>
