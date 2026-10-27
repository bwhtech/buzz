export type FieldGroup = "Basic" | "Choice" | "Media" | "Layout" | "Standard"

export interface FieldType {
	label: string
	icon: string
	group: FieldGroup
}

// Keyed by Buzz Form Field fieldtype, in palette order.
export const FIELD_TYPES: Record<string, FieldType> = {
	Data: { label: "Short text", icon: "lucide-type", group: "Basic" },
	"Small Text": { label: "Long text", icon: "lucide-align-left", group: "Basic" },
	Email: { label: "Email", icon: "lucide-mail", group: "Basic" },
	Phone: { label: "Phone", icon: "lucide-phone", group: "Basic" },
	Number: { label: "Number", icon: "lucide-hash", group: "Basic" },
	URL: { label: "Link", icon: "lucide-link", group: "Basic" },
	Date: { label: "Date", icon: "lucide-calendar", group: "Basic" },
	Select: { label: "Dropdown", icon: "lucide-circle-chevron-down", group: "Choice" },
	Radio: { label: "Single choice", icon: "lucide-circle-dot", group: "Choice" },
	"Multi Select": { label: "Multiple choice", icon: "lucide-list-checks", group: "Choice" },
	Check: { label: "Checkbox", icon: "lucide-square-check", group: "Choice" },
	Rating: { label: "Rating", icon: "lucide-star", group: "Choice" },
	Attach: { label: "File upload", icon: "lucide-paperclip", group: "Media" },
	"Attach Image": { label: "Image upload", icon: "lucide-image", group: "Media" },
	Heading: { label: "Heading", icon: "lucide-heading", group: "Layout" },
	Paragraph: { label: "Paragraph", icon: "lucide-pilcrow", group: "Layout" },
	Divider: { label: "Divider", icon: "lucide-minus", group: "Layout" },
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

// Steps come from "Add step", so page breaks stay out of the add-field menu.
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

// What the add-field menu and the palette offer, grouped and filtered by the search text.
export function fieldMenu(formDoctype: string, query = ""): { group: string; items: MenuItem[] }[] {
	const search = query.trim().toLowerCase()
	const matches = (label: string) => !search || label.toLowerCase().includes(search)
	const types = paletteTypesFor()
	const groups = GROUP_ORDER.map((group) => ({
		group: group as string,
		items: types
			.filter((key) => FIELD_TYPES[key].group === group && matches(FIELD_TYPES[key].label))
			.map((key): MenuItem => ({
				key,
				label: FIELD_TYPES[key].label,
				icon: FIELD_TYPES[key].icon,
				hint: "",
				fields: [{ fieldtype: key, label: FIELD_TYPES[key].label }],
			})),
	}))
	const presets = presetsFor(formDoctype)
		.filter((preset) => matches(preset.label))
		.map((preset): MenuItem => ({
			key: preset.label,
			label: preset.label,
			icon: preset.icon,
			hint: preset.description,
			fields: preset.fields,
		}))
	groups.splice(1, 0, { group: "Ready-made", items: presets })
	return groups.filter((group) => group.items.length)
}
