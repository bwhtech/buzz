export interface FieldType {
	label: string
	icon: string
}

// Keyed by Buzz Form Field fieldtype.
export const FIELD_TYPES: Record<string, FieldType> = {
	Data: { label: "Short text", icon: "lucide-type" },
	"Small Text": { label: "Long text", icon: "lucide-align-left" },
	Email: { label: "Email", icon: "lucide-mail" },
	Phone: { label: "Phone", icon: "lucide-phone" },
	Number: { label: "Number", icon: "lucide-hash" },
	Date: { label: "Date", icon: "lucide-calendar" },
	Select: { label: "Dropdown", icon: "lucide-circle-chevron-down" },
	"Multi Select": { label: "Multiple choice", icon: "lucide-list-checks" },
	Check: { label: "Checkbox", icon: "lucide-square-check" },
	Rating: { label: "Rating", icon: "lucide-star" },
	Attach: { label: "File upload", icon: "lucide-paperclip" },
	"Attach Image": { label: "Image upload", icon: "lucide-image" },
}

export const fieldType = (fieldtype: string): FieldType =>
	FIELD_TYPES[fieldtype] ?? { label: fieldtype, icon: "lucide-square" }
