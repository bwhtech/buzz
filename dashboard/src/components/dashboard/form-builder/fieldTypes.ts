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
