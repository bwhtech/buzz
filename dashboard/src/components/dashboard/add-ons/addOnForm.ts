import type { AddOnItem } from "@/types"

export type AddOnValues = {
	title: string
	description: string
	price: number
	currency: string
	enabled: boolean
	user_selects_option: boolean
	options: string[]
	applies_to_all_ticket_types: boolean
	ticket_types: string[]
}

export function blankAddOnValues(currency: string): AddOnValues {
	return {
		title: "",
		description: "",
		price: 0,
		currency,
		enabled: true,
		user_selects_option: false,
		options: [""],
		applies_to_all_ticket_types: true,
		ticket_types: [],
	}
}

export function addOnValuesOf(addOn: AddOnItem): AddOnValues {
	return {
		title: addOn.title,
		description: addOn.description ?? "",
		price: addOn.price ?? 0,
		currency: addOn.currency,
		enabled: Boolean(addOn.enabled),
		user_selects_option: Boolean(addOn.user_selects_option),
		options: addOn.options.length ? [...addOn.options] : [""],
		applies_to_all_ticket_types: !addOn.ticket_types.length,
		ticket_types: [...addOn.ticket_types],
	}
}

const filledOptions = (values: AddOnValues) =>
	values.options.map((option) => option.trim()).filter(Boolean)

/** Why the add-on can't be saved yet, or null when it can. */
export function addOnError(values: AddOnValues) {
	if (!values.title.trim()) return "Enter a name."
	if (!(values.price >= 0)) return "Enter a price of zero or more."
	if (values.user_selects_option && !filledOptions(values).length) return "Add at least one option."
	if (!values.applies_to_all_ticket_types && !values.ticket_types.length)
		return "Pick at least one ticket type."
	return null
}

/** The values as the doctype stores them. */
export function addOnDocValues(values: AddOnValues) {
	return {
		title: values.title.trim(),
		description: values.description.trim(),
		price: values.price,
		currency: values.currency,
		enabled: (values.enabled ? 1 : 0) as 0 | 1,
		user_selects_option: (values.user_selects_option ? 1 : 0) as 0 | 1,
		options: filledOptions(values).join("\n"),
		ticket_types: values.applies_to_all_ticket_types
			? []
			: values.ticket_types.map((ticket_type) => ({ ticket_type })),
	}
}
