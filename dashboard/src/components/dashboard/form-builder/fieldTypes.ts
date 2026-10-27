export type FieldGroup = "Basic" | "Choice" | "Media" | "Layout" | "Standard"

export interface FieldType {
	label: string
	icon: string
	group: FieldGroup
	// Other words people search for this type by.
	keywords?: string
}

// Keyed by Buzz Form Field fieldtype, in palette order.
export const FIELD_TYPES: Record<string, FieldType> = {
	Data: { label: "Short text", icon: "lucide-type", group: "Basic", keywords: "input string name" },
	"Small Text": {
		label: "Long text",
		icon: "lucide-align-left",
		group: "Basic",
		keywords: "textarea multiline answer",
	},
	Email: { label: "Email", icon: "lucide-mail", group: "Basic", keywords: "mail address" },
	Phone: {
		label: "Phone",
		icon: "lucide-phone",
		group: "Basic",
		keywords: "mobile number contact whatsapp",
	},
	Number: {
		label: "Number",
		icon: "lucide-hash",
		group: "Basic",
		keywords: "integer amount count",
	},
	URL: { label: "Link", icon: "lucide-link", group: "Basic", keywords: "url website" },
	Date: {
		label: "Date",
		icon: "lucide-calendar",
		group: "Basic",
		keywords: "day calendar birthday",
	},
	Select: {
		label: "Dropdown",
		icon: "lucide-circle-chevron-down",
		group: "Choice",
		keywords: "picker options",
	},
	Radio: {
		label: "Single choice",
		icon: "lucide-circle-dot",
		group: "Choice",
		keywords: "radio option one",
	},
	"Multi Select": {
		label: "Multiple choice",
		icon: "lucide-list-checks",
		group: "Choice",
		keywords: "checkboxes many options",
	},
	Check: {
		label: "Checkbox",
		icon: "lucide-square-check",
		group: "Choice",
		keywords: "tick toggle boolean yes no agree consent",
	},
	Rating: { label: "Rating", icon: "lucide-star", group: "Choice", keywords: "stars score" },
	Attach: {
		label: "File upload",
		icon: "lucide-paperclip",
		group: "Media",
		keywords: "attachment document pdf resume",
	},
	"Attach Image": {
		label: "Image upload",
		icon: "lucide-image",
		group: "Media",
		keywords: "photo picture headshot",
	},
	Heading: { label: "Heading", icon: "lucide-heading", group: "Layout", keywords: "title section" },
	Paragraph: {
		label: "Paragraph",
		icon: "lucide-pilcrow",
		group: "Layout",
		keywords: "text info note",
	},
	Divider: {
		label: "Divider",
		icon: "lucide-minus",
		group: "Layout",
		keywords: "line separator rule",
	},
	"Page Break": { label: "Page break", icon: "lucide-separator-horizontal", group: "Layout" },
	// Only the form's own fields use these; they are never offered in the palette.
	"Text Editor": { label: "Rich text", icon: "lucide-text", group: "Standard" },
	Table: { label: "List", icon: "lucide-rows-3", group: "Standard" },
	Link: { label: "Dropdown", icon: "lucide-circle-chevron-down", group: "Standard" },
}

export const CHOICE_TYPES = ["Select", "Radio", "Multi Select"]

export const fieldType = (fieldtype: string): FieldType =>
	FIELD_TYPES[fieldtype] ?? { label: fieldtype, icon: "lucide-square", group: "Basic" }

export interface PresetField {
	fieldtype: string
	label: string
	options?: string
	placeholder?: string
	description?: string
	width?: "Full" | "Half"
	mandatory?: 0 | 1
}

export interface Preset {
	label: string
	icon: string
	description: string
	fields: PresetField[]
}

const SOCIAL: Preset = {
	label: "Social profiles",
	icon: "lucide-at-sign",
	description: "LinkedIn and Instagram",
	fields: [
		{ fieldtype: "URL", label: "LinkedIn", width: "Half", placeholder: "linkedin.com/in/" },
		{ fieldtype: "URL", label: "Instagram", width: "Half", placeholder: "instagram.com/" },
	],
}
const TSHIRT: Preset = {
	label: "T-shirt size",
	icon: "lucide-shirt",
	description: "XS to XXL",
	fields: [{ fieldtype: "Select", label: "T-shirt size", options: "XS\nS\nM\nL\nXL\nXXL" }],
}
const SOURCE: Preset = {
	label: "How did you hear",
	icon: "lucide-megaphone",
	description: "Where they found you",
	fields: [
		{
			fieldtype: "Select",
			label: "How did you hear about us?",
			options: "Instagram\nA friend\nNewsletter\nOther",
		},
	],
}
const COMPANY: Preset = {
	label: "Company and role",
	icon: "lucide-briefcase",
	description: "Where they work",
	fields: [
		{ fieldtype: "Data", label: "Company", width: "Half" },
		{ fieldtype: "Data", label: "Role", width: "Half" },
	],
}

// Ready-made groups of questions, per form doctype.
const PRESETS: Record<string, Preset[]> = {
	"Talk Proposal": [
		{
			label: "Speaker bio",
			icon: "lucide-user-round",
			description: "Short bio and headshot",
			fields: [
				{ fieldtype: "Small Text", label: "Speaker bio", placeholder: "A few lines about you" },
				{ fieldtype: "Attach Image", label: "Headshot", description: "Square, at least 400 × 400" },
			],
		},
		{
			label: "Previous talks",
			icon: "lucide-history",
			description: "Link to an earlier talk",
			fields: [{ fieldtype: "URL", label: "Link to a previous talk", placeholder: "https://" }],
		},
		SOCIAL,
		{
			label: "Travel support",
			icon: "lucide-plane",
			description: "Need support and city",
			fields: [
				{ fieldtype: "Check", label: "I need travel or stay support" },
				{ fieldtype: "Data", label: "Travelling from", placeholder: "City" },
			],
		},
		TSHIRT,
		{
			label: "Code of conduct",
			icon: "lucide-shield-check",
			description: "Required agreement",
			fields: [
				{ fieldtype: "Check", label: "I agree to the speaker code of conduct", mandatory: 1 },
			],
		},
	],
	"Event Booking": [
		COMPANY,
		SOURCE,
		{
			label: "GST invoice",
			icon: "lucide-receipt-text",
			description: "Company and GSTIN",
			fields: [
				{ fieldtype: "Check", label: "I need a GST invoice" },
				{ fieldtype: "Data", label: "GSTIN", width: "Half" },
				{ fieldtype: "Data", label: "Business name", width: "Half" },
			],
		},
	],
	"Event Booking Attendee": [
		{
			label: "Dietary needs",
			icon: "lucide-salad",
			description: "Preference and allergies",
			fields: [
				{
					fieldtype: "Select",
					label: "Dietary preference",
					options: "No preference\nVegetarian\nVegan\nJain",
				},
				{ fieldtype: "Data", label: "Allergies", placeholder: "Nuts, lactose…" },
			],
		},
		COMPANY,
		TSHIRT,
		SOCIAL,
	],
}

export const presetsFor = (formDoctype: string): Preset[] =>
	PRESETS[formDoctype] ?? [SOCIAL, SOURCE, COMPANY]

// Registration has its own steps on the booking page, so its forms take no page breaks.
export const takesSteps = (formDoctype: string) =>
	!["Event Booking", "Event Booking Attendee"].includes(formDoctype)

// Page breaks come only from "Add step", never as a field of their own.
export const paletteTypesFor = (): string[] =>
	Object.entries(FIELD_TYPES)
		.filter(([key, type]) => type.group !== "Standard" && key !== "Page Break")
		.map(([key]) => key)

export interface MenuItem {
	key: string
	label: string
	icon: string
	hint: string
	fields: PresetField[]
}

const GROUP_ORDER: FieldGroup[] = ["Basic", "Choice", "Media", "Layout"]

export const ADD_STEP: MenuItem = {
	key: "Add step",
	label: "Add step",
	icon: FIELD_TYPES["Page Break"].icon,
	hint: "",
	fields: [],
}

const words = (text: string) =>
	text
		.toLowerCase()
		.split(/[^a-z0-9]+/)
		.filter(Boolean)

// Every word typed must start a word of the terms, so "select" finds Dropdown and "ad" finds "Add step".
export function matchesSearch(query: string, ...terms: string[]): boolean {
	const known = words(terms.join(" "))
	return words(query).every((typed) => known.some((word) => word.startsWith(typed)))
}

const typeMatches = (query: string, key: string) => {
	const { label, group, keywords = "" } = FIELD_TYPES[key]
	return matchesSearch(query, key, label, group, keywords)
}

type TypeGroup = { group: string; options: { value: string }[] }

// For the "turn into" pickers, whose options carry the fieldtype as their value.
export const filterTypeGroups = <Group extends TypeGroup>(
	groups: Group[],
	query: string,
): Group[] =>
	groups
		.map((group) => ({
			...group,
			options: group.options.filter((option) => typeMatches(query, option.value)),
		}))
		.filter((group) => group.options.length)

const presetMatches = (query: string, preset: Preset) =>
	matchesSearch(
		query,
		"Ready-made readymade preset template",
		preset.label,
		preset.description,
		...preset.fields.map((field) => field.label),
	)

// What the add-field menu and the palette offer, grouped and filtered by the search text.
export function fieldMenu(formDoctype: string, query = ""): { group: string; items: MenuItem[] }[] {
	const types = paletteTypesFor()
	const groups = GROUP_ORDER.map((group) => ({
		group: group as string,
		items: types
			.filter((key) => FIELD_TYPES[key].group === group && typeMatches(query, key))
			.map((key): MenuItem => ({
				key,
				label: FIELD_TYPES[key].label,
				icon: FIELD_TYPES[key].icon,
				hint: "",
				fields: [{ fieldtype: key, label: FIELD_TYPES[key].label }],
			})),
	}))
	const presets = presetsFor(formDoctype)
		.filter((preset) => presetMatches(query, preset))
		.map((preset): MenuItem => ({
			key: preset.label,
			label: preset.label,
			icon: preset.icon,
			hint: preset.description,
			fields: preset.fields,
		}))
	groups.splice(1, 0, { group: "Ready-made", items: presets })
	if (takesSteps(formDoctype) && matchesSearch(query, ADD_STEP.label, "page break section"))
		groups.find((group) => group.group === "Layout")?.items.push(ADD_STEP)
	return groups.filter((group) => group.items.length)
}
