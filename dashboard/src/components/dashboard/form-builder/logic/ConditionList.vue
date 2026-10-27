<script setup lang="ts">
import { MultiSelect } from "frappe-ui"
import { computed, onMounted } from "vue"

import type { Condition, LogicRule } from "@/utils/formLogic"

import LogicPill from "./LogicPill.vue"
import { type RuleField, newCondition, operatorOf, operatorsFor } from "./ruleOptions"

const rule = defineModel<LogicRule>({ required: true })
const props = defineProps<{
	fields: RuleField[]
	readonly?: boolean
	// Rule cards lead each row with "If" / "and"; a field's settings show the conditions alone.
	leadWords?: boolean
	// On a grey panel the pills are white and outlined.
	outlined?: boolean
}>()

const pillKind = computed(() => (props.outlined ? "outline" : "value"))

const fieldOf = (condition: Condition) =>
	props.fields.find((field) => field.fieldname === condition[0])

const valueLabel = (field: RuleField | undefined, value: unknown) =>
	field?.values?.find((option) => option.value === value)?.label ?? String(value ?? "pick…")

const listLabel = (condition: Condition) =>
	(Array.isArray(condition[2]) ? condition[2] : [])
		.map((value) => valueLabel(fieldOf(condition), value))
		.join(", ") || "pick…"

function fieldOptions(index: number) {
	return props.fields.map((field) => ({
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

function addCondition() {
	if (props.fields.length) rule.value.conditions.push(newCondition(props.fields[0]))
}

const toggleMatch = () => (rule.value.match = rule.value.match === "any" ? "all" : "any")

// A new rule opens with a condition to fill in.
onMounted(() => props.readonly || rule.value.conditions.length || addCondition())

defineExpose({ addCondition })
</script>

<template>
	<div
		v-for="(condition, index) in rule.conditions"
		:key="index"
		class="flex min-h-7 items-start gap-1.5"
	>
		<div class="flex min-w-0 flex-wrap items-center gap-1.5">
			<span v-if="leadWords" class="flex w-11 shrink-0">
				<span v-if="index === 0" class="text-p-base font-medium text-ink-gray-6">If</span>
				<LogicPill
					v-else
					kind="join"
					:label="rule.match === 'any' ? 'or' : 'and'"
					:aria-label="`Match ${rule.match === 'any' ? 'all' : 'any'} conditions`"
					@click="readonly || toggleMatch()"
				/>
			</span>
			<LogicPill
				v-else-if="index > 0"
				kind="join"
				:label="rule.match === 'any' ? 'or' : 'and'"
				:aria-label="`Match ${rule.match === 'any' ? 'all' : 'any'} conditions`"
				@click="readonly || toggleMatch()"
			/>
			<LogicPill
				:kind="pillKind"
				:label="fieldOf(condition)?.label ?? condition[0]"
				:options="readonly ? undefined : fieldOptions(index)"
			/>
			<LogicPill
				kind="word"
				:label="operatorOf(condition)?.label ?? condition[1]"
				:options="readonly ? undefined : operatorOptions(index)"
			/>
			<template v-if="!operatorOf(condition)?.fixed">
				<LogicPill
					:kind="pillKind"
					v-if="readonly && operatorOf(condition)?.list"
					:label="listLabel(condition)"
				/>
				<MultiSelect
					v-else-if="operatorOf(condition)?.list && fieldOf(condition)?.values"
					:model-value="Array.isArray(condition[2]) ? condition[2] : []"
					@update:model-value="
						(items: any[]) => (condition[2] = items.map((item) => item?.value ?? item))
					"
					class="min-w-40"
					:options="fieldOf(condition)?.values as any"
					placeholder="pick…"
				/>
				<LogicPill
					:kind="pillKind"
					v-else-if="fieldOf(condition)?.values"
					:label="valueLabel(fieldOf(condition), condition[2])"
					:options="readonly ? undefined : valueOptions(index)"
				/>
				<LogicPill
					:kind="pillKind"
					v-else-if="readonly"
					:label="String(condition[2] || 'a value')"
				/>
				<input
					v-else
					v-model="condition[2] as string"
					placeholder="a value"
					aria-label="Value"
					class="h-[26px] w-40 rounded-3 border-0 px-2 text-p-base text-ink-gray-8 outline-none placeholder:text-ink-gray-4 focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
					:class="
						outlined ? 'bg-surface-base ring-1 ring-inset ring-outline-gray-2' : 'bg-surface-gray-2'
					"
				/>
			</template>
		</div>
		<button
			v-if="!readonly"
			type="button"
			class="mt-0.5 grid size-[22px] shrink-0 place-items-center rounded-5 text-ink-gray-4 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-8"
			aria-label="Remove condition"
			@click="rule.conditions.splice(index, 1)"
		>
			<span class="lucide-x size-3" aria-hidden="true" />
		</button>
	</div>
</template>
