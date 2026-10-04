/** Mirrors `buzz.api.filters.schemas`: the server says what a list can be filtered on. */
export interface FilterOption {
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

export type ValueInput = "choice" | "text" | "number" | "date" | "rating" | "none"

const ICONS: Record<string, string> = {
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
const FIELD_ICONS: Record<string, string> = {
	tier: "lucide-circle-star",
}

export const fieldIcon = (field: FilterField) =>
	FIELD_ICONS[field.key] ?? ICONS[field.fieldtype] ?? "lucide-type"

export function valueInput(field: FilterField, operator: FilterOperator): ValueInput {
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
export function valueFor(
	field: FilterField,
	next: FilterOperator,
	previous?: ConditionValue,
): ConditionValue {
	if (next.value) return next.value
	if (next.operator === "between")
		return Array.isArray(previous) && previous.length === 2 ? previous : ["", ""]
	if (field.options.length) return Array.isArray(previous) ? previous : []
	return typeof previous === "string" ? previous : ""
}
