import type { Condition, LogicRule } from "@/utils/formLogic"

import { CHOICE_TYPES, fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"

export interface RuleField {
	fieldname: string
	label: string
	fieldtype: string
	values: { label: string; value: unknown }[] | null
}

export interface Operator {
	label: string
	value: string
	// "is set" and "is empty" are the `is` operator with a fixed value.
	fixed?: string
	list?: boolean
}

export const OPERATORS: Record<string, Operator> = {
	"=": { label: "is", value: "=" },
	"!=": { label: "is not", value: "!=" },
	in: { label: "is any of", value: "in", list: true },
	"not in": { label: "is none of", value: "not in", list: true },
	">": { label: "is more than", value: ">" },
	"<": { label: "is less than", value: "<" },
	like: { label: "contains", value: "like" },
	set: { label: "is filled", value: "is", fixed: "set" },
	"not set": { label: "is empty", value: "is", fixed: "not set" },
}

export const ACTIONS = [
	{ label: "show", value: "show", icon: "lucide-eye" },
	{ label: "hide", value: "hide", icon: "lucide-eye-off" },
	{ label: "require", value: "require", icon: "lucide-asterisk" },
]

const CHECK_VALUES = [
	{ label: "checked", value: 1 },
	{ label: "not checked", value: 0 },
]
// A rating is saved as a share of five stars.
const RATING_VALUES = [1, 2, 3, 4, 5].map((stars) => ({
	label: `${stars} ${stars === 1 ? "star" : "stars"}`,
	value: stars / 5,
}))

export function operatorsFor(field: RuleField | undefined): Operator[] {
	const keys =
		field?.fieldtype === "Check"
			? ["="]
			: ["Number", "Rating"].includes(field?.fieldtype ?? "")
				? ["=", "!=", ">", "<", "set", "not set"]
				: field?.values
					? ["=", "!=", "in", "not in", "set", "not set"]
					: ["=", "!=", "like", "set", "not set"]
	return keys.map((key) => OPERATORS[key])
}

export function operatorOf([, operator, value]: Condition): Operator {
	return operator === "is" ? OPERATORS[value === "set" ? "set" : "not set"] : OPERATORS[operator]
}

const lines = (options: string | null | undefined) =>
	String(options ?? "")
		.split("\n")
		.filter(Boolean)
		.map((option) => ({ label: option, value: option }))

function valuesOf(
	fieldtype: string,
	options: string | null | undefined,
	links?: DoctypeField["link_options"],
) {
	if (fieldtype === "Check") return CHECK_VALUES
	if (fieldtype === "Rating") return RATING_VALUES
	if (links) return links
	if (CHOICE_TYPES.includes(fieldtype)) return lines(options)
	return null
}

// What a condition may test: the doctype's own fields, then questions above the rule's targets.
export function ruleFields(
	doctypeFields: DoctypeField[],
	questions: FormQuestion[],
	firstTarget: number,
): RuleField[] {
	const standard = doctypeFields
		.filter((field) => fieldType(field.fieldtype).group !== "Layout")
		.map((field) => ({
			fieldname: field.fieldname,
			label: field.label,
			fieldtype: field.fieldtype,
			values: valuesOf(field.fieldtype, field.options, field.link_options),
		}))
	const above = questions
		.slice(0, firstTarget)
		.filter((question) => !question.is_standard && fieldType(question.fieldtype).group !== "Layout")
		.map((question) => ({
			fieldname: question.fieldname,
			label: question.label,
			fieldtype: question.fieldtype,
			values: valuesOf(question.fieldtype, question.options),
		}))
	return [...standard, ...above]
}

export function newCondition(field: RuleField): Condition {
	return [field.fieldname, "=", field.values?.[0]?.value ?? ""]
}

export function emptyRule(target: string): LogicRule {
	return { match: "all", conditions: [], actions: [["show", target]] }
}
