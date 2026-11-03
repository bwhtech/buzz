import type { Condition, LogicRule } from "@/utils/formLogic"

import { isTicketRule } from "./ticketTypeRule"

export type FieldAction = "show" | "require"

// A field's own rule acts on that field alone; its settings edit it, the Logic tab lists it.
const isOwnRule = (rule: LogicRule, action: FieldAction, fieldname: string) =>
	rule.actions.length === 1 &&
	rule.actions[0][0] === action &&
	rule.actions[0][1] === fieldname &&
	!isTicketRule(rule, fieldname)

export const ownRule = (rules: LogicRule[], action: FieldAction, fieldname: string) =>
	fieldname ? rules.find((rule) => isOwnRule(rule, action, fieldname)) : undefined

export function addOwnRule(
	rules: LogicRule[],
	action: FieldAction,
	fieldname: string,
	condition: Condition,
) {
	rules.push({ match: "all", conditions: [condition], actions: [[action, fieldname]] })
}

export function removeOwnRule(rules: LogicRule[], action: FieldAction, fieldname: string) {
	const index = rules.findIndex((rule) => isOwnRule(rule, action, fieldname))
	if (index >= 0) rules.splice(index, 1)
}

// Rules from the Logic tab that also act on the field, beyond the ones its settings edit.
export const otherRuleCount = (rules: LogicRule[], fieldname: string) =>
	rules.filter(
		(rule) =>
			rule.actions.some(([, target]) => target === fieldname) &&
			!isOwnRule(rule, "show", fieldname) &&
			!isOwnRule(rule, "require", fieldname) &&
			!isTicketRule(rule, fieldname),
	).length
