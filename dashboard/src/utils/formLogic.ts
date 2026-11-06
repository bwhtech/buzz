// The browser twin of buzz/api/forms/conditions.py; logic_cases.json keeps the two in step.

export type Condition = [string, string, unknown]

export interface LogicRule {
	match?: "all" | "any"
	conditions: Condition[]
	actions: [string, string][]
}

type Values = Record<string, unknown>

const isSet = (value: unknown) => value !== undefined && value !== null && value !== ""
const number = (value: unknown) => Number(value) || 0

export function conditionMatches(
	[fieldname, operator, expected]: Condition,
	values: Values,
): boolean {
	const value = values[fieldname]
	const list = Array.isArray(expected) ? expected : [expected]
	// A Multi Select answer is a list: it is in the expected values when any of them is.
	if (Array.isArray(value) && (operator === "in" || operator === "not in")) {
		const found = value.some((item) => list.includes(item))
		return operator === "in" ? found : !found
	}
	switch (operator) {
		case "=":
			return value === expected
		case "!=":
			return value !== expected
		case "in":
			return list.includes(value)
		case "not in":
			return !list.includes(value)
		case ">":
			return number(value) > number(expected)
		case "<":
			return number(value) < number(expected)
		case ">=":
			return number(value) >= number(expected)
		case "<=":
			return number(value) <= number(expected)
		case "like":
			return String(value ?? "")
				.toLowerCase()
				.includes(String(expected ?? "").toLowerCase())
		case "is":
			return expected === "set" ? isSet(value) : !isSet(value)
	}
	return false
}

export function ruleMatches(rule: LogicRule, values: Values): boolean {
	const results = (rule.conditions || []).map((condition) => conditionMatches(condition, values))
	if (!results.length) return false
	return rule.match === "any" ? results.some(Boolean) : results.every(Boolean)
}

function fires(rules: LogicRule[], action: string, fieldname: string, values: Values): boolean[] {
	return rules
		.filter((rule) =>
			rule.actions.some(([verb, target]) => verb === action && target === fieldname),
		)
		.map((rule) => ruleMatches(rule, values))
}

export function isShown(rules: LogicRule[], fieldname: string, values: Values): boolean {
	const shows = fires(rules, "show", fieldname, values)
	return (
		(!shows.length || shows.some(Boolean)) && !fires(rules, "hide", fieldname, values).some(Boolean)
	)
}

export function isRequired(
	rules: LogicRule[],
	question: { fieldname: string; mandatory?: unknown },
	values: Values,
): boolean {
	if (!isShown(rules, question.fieldname, values)) return false
	return !!question.mandatory || fires(rules, "require", question.fieldname, values).some(Boolean)
}

/**
 * Walk the questions top to bottom as the server does: each one sees the form's own values and
 * the answers of the shown questions above it. Returns the shown questions, each with its
 * effective `mandatory`.
 */
export function applyLogic<T extends { fieldname: string; mandatory?: unknown }>(
	questions: T[],
	rules: LogicRule[],
	context: Values,
	answers: Values,
): T[] {
	const values: Values = { ...context }
	const shown: T[] = []
	for (const question of questions) {
		if (!isShown(rules, question.fieldname, values)) continue
		values[question.fieldname] = answers[question.fieldname]
		shown.push({ ...question, mandatory: isRequired(rules, question, values) ? 1 : 0 })
	}
	return shown
}
