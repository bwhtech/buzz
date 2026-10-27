// The registration form's own fields, as the organiser labelled, ordered and sized them.
export interface CoreField {
	fieldname: string
	label: string
	width: "Full" | "Half"
	enabled: 0 | 1
}
