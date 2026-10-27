import type { LogicRule } from "@/utils/formLogic"

// "Ask only for these ticket types" is a show rule with one ticket_type condition.
export const isTicketRule = (rule: LogicRule, fieldname: string) =>
	(rule.match ?? "all") === "all" &&
	rule.conditions.length === 1 &&
	rule.conditions[0][0] === "ticket_type" &&
	rule.conditions[0][1] === "in" &&
	rule.actions.length === 1 &&
	rule.actions[0][0] === "show" &&
	rule.actions[0][1] === fieldname

export function ticketTypesOf(rules: LogicRule[], fieldname: string): string[] {
	const rule = rules.find((candidate) => isTicketRule(candidate, fieldname))
	return rule ? (rule.conditions[0][2] as string[]) : []
}

export function setTicketTypes(rules: LogicRule[], fieldname: string, ticketTypes: string[]) {
	const index = rules.findIndex((rule) => isTicketRule(rule, fieldname))
	const rule: LogicRule = {
		match: "all",
		conditions: [["ticket_type", "in", ticketTypes]],
		actions: [["show", fieldname]],
	}
	if (index >= 0 && !ticketTypes.length) rules.splice(index, 1)
	else if (index >= 0) rules[index] = rule
	else if (ticketTypes.length) rules.push(rule)
}
