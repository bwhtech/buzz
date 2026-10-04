/** Mirrors `buzz.api.filters.schemas`: the server says what a list can be filtered on. */
interface FilterOption {
	value: string
	label: string
}

export interface FilterOperator {
	operator: string
	label: string
	/** Fixed by the operator itself, as "is answered" fixes "set". */
	value?: string | null
}

export interface FilterField {
	key: string
	label: string
	fieldtype: string
	section: "standard" | "question"
	options: FilterOption[]
	operators: FilterOperator[]
}

export type ConditionValue = string | string[]

/** A Frappe filter triple, sent to the server and kept in the URL as is. */
export type Condition = [field: string, operator: string, value: ConditionValue]

type InputType = "choice" | "text" | "number" | "date" | "rating" | "none"

const ICONS_BY_FIELDTYPE: Record<string, string> = {
	Select: "lucide-circle-dot",
	Link: "lucide-link",
	Check: "lucide-square-check",
	"Multi Select": "lucide-list-checks",
	Number: "lucide-hash",
	Rating: "lucide-star",
	Date: "lucide-calendar",
	Email: "lucide-at-sign",
	Phone: "lucide-phone",
	"Small Text": "lucide-align-left",
	Attach: "lucide-paperclip",
	"Attach Image": "lucide-image",
}

// Icons are CSS classes generated from names found in this source, so they cannot come from the server.
const ICONS_BY_FIELD_KEY: Record<string, string> = {
	tier: "lucide-circle-star",
	ticket_type: "lucide-tag",
	status: "lucide-circle-dashed",
}

export const fieldIcon = (field: FilterField) =>
	ICONS_BY_FIELD_KEY[field.key] ?? ICONS_BY_FIELDTYPE[field.fieldtype] ?? "lucide-type"

export function inputTypeFor(field: FilterField, operator: FilterOperator): InputType {
	if (operator.value || field.fieldtype.startsWith("Attach")) return "none"
	if (field.options.length) return "choice"
	if (field.fieldtype === "Number") return "number"
	if (field.fieldtype === "Date") return "date"
	if (field.fieldtype === "Rating") return "rating"
	return "text"
}

/** The operator a condition currently uses; fixed-value operators are told apart by value. */
export function currentOperator(field: FilterField, [, operator, value]: Condition) {
	const candidates = field.operators.filter((choice) => choice.operator === operator)
	return candidates.find((choice) => !choice.value || choice.value === value) ?? candidates[0]
}

/** Keeps what was typed when the new operator takes the same shape of value. */
export function valueForOperator(
	field: FilterField,
	operator: FilterOperator,
	previous?: ConditionValue,
): ConditionValue {
	if (operator.value) return operator.value
	if (operator.operator === "between")
		return Array.isArray(previous) && previous.length === 2 ? previous : ["", ""]
	if (field.options.length) return Array.isArray(previous) ? previous : []
	return typeof previous === "string" ? previous : ""
}

/** Whether a row whose status just changed still answers the list's status conditions. */
export const matchesStatusConditions = (conditions: Condition[], status: string) =>
	conditions.every(
		([field, operator, value]) =>
			field !== "status" || !value.length || (operator === "in") === value.includes(status),
	)
