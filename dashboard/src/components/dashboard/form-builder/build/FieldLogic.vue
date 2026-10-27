<script setup lang="ts">
import { TabButtons } from "frappe-ui"
import { computed } from "vue"

import type { LogicRule } from "@/utils/formLogic"

import ConditionList from "../logic/ConditionList.vue"
import {
	type FieldAction,
	addOwnRule,
	otherRuleCount,
	ownRule,
	removeOwnRule,
} from "../logic/fieldRule"
import { type RuleField, newCondition } from "../logic/ruleOptions"
import type { FormQuestion } from "../useFormBuilder"

type Mode = "always" | "if" | "never"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{
	rules: LogicRule[]
	fields: RuleField[]
	ensureFieldname: (question: FormQuestion) => string
	canHide: boolean
	canRequire: boolean
}>()
defineEmits<{ openLogic: [] }>()

// Each section has a flag that alone means one mode: hidden is "never", mandatory is "always".
const SECTIONS = [
	{ title: "Show this field", action: "show", flag: "enabled", flagMode: "never", flagValue: 0 },
	{ title: "Mandatory", action: "require", flag: "mandatory", flagMode: "always", flagValue: 1 },
] as const

type Section = (typeof SECTIONS)[number]

// Rules act only on the form's own questions, so core fields have no "Only if".
const takesRules = computed(() => !question.value.is_standard && props.fields.length > 0)

const sections = computed(() =>
	SECTIONS.filter(({ action }) => (action === "show" ? props.canHide : props.canRequire)).map(
		(section) => ({
			...section,
			rule: ownRule(props.rules, section.action, question.value.fieldname),
			mode: modeOf(section),
			options: [
				{ label: "Always", value: "always" },
				...(takesRules.value ? [{ label: "Only if…", value: "if" }] : []),
				{ label: "Never", value: "never" },
			],
		}),
	),
)

function modeOf({ action, flag, flagMode, flagValue }: Section): Mode {
	if (Number(question.value[flag] ?? 0) === flagValue) return flagMode
	if (ownRule(props.rules, action, question.value.fieldname)) return "if"
	return flagMode === "never" ? "always" : "never"
}

function setMode({ action, flag, flagMode, flagValue }: Section, mode: Mode) {
	question.value[flag] = (mode === flagMode ? flagValue : 1 - flagValue) as 0 | 1
	if (mode !== "if") return removeOwnRule(props.rules, action, question.value.fieldname)
	if (!ownRule(props.rules, action, question.value.fieldname))
		addOwnRule(
			props.rules,
			action as FieldAction,
			props.ensureFieldname(question.value),
			newCondition(likelyField.value),
		)
}

// The nearest choice question above is the likeliest thing to depend on.
const likelyField = computed(() => {
	const choices = props.fields.filter((field) => field.values)
	return choices[choices.length - 1] ?? props.fields[0]
})

const addCondition = (rule: LogicRule) => rule.conditions.push(newCondition(likelyField.value))
const others = computed(() => otherRuleCount(props.rules, question.value.fieldname))

const LINK =
	"rounded-5 px-1.5 py-0.5 text-p-sm text-ink-gray-5 transition-[color,background-color,transform] duration-150 ease-out active:scale-[0.97] [@media(hover:hover)]:hover:bg-surface-gray-2 [@media(hover:hover)]:hover:text-ink-gray-9"
</script>

<template>
	<section v-for="section in sections" :key="section.action" class="space-y-2">
		<h3 class="text-p-sm font-medium text-ink-gray-8">{{ section.title }}</h3>
		<TabButtons
			:model-value="section.mode"
			:options="section.options"
			fluid
			@update:model-value="(mode) => setMode(section, mode as Mode)"
		/>
		<div
			v-if="section.mode === 'if' && section.rule"
			class="flex flex-col gap-2 rounded-5 bg-surface-gray-1 p-3"
		>
			<ConditionList :model-value="section.rule" :fields="fields" outlined />
			<div class="-mx-1.5 flex items-center justify-between">
				<button type="button" :class="LINK" @click="addCondition(section.rule)">
					+ Add condition
				</button>
				<button
					type="button"
					:class="[LINK, 'flex items-center gap-1']"
					@click="$emit('openLogic')"
				>
					Open in Logic
					<span class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
				</button>
			</div>
		</div>
	</section>
	<p v-if="others" class="flex items-center justify-between text-p-sm text-ink-gray-5">
		{{ others }} more {{ others === 1 ? "rule acts" : "rules act" }} on this field
		<button type="button" :class="[LINK, 'flex items-center gap-1']" @click="$emit('openLogic')">
			Open in Logic
			<span class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
		</button>
	</p>
</template>
