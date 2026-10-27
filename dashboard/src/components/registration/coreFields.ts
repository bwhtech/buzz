// The registration form's own fields, as the organiser labelled, ordered and sized them.
export interface CoreField {
	fieldname: string
	label: string
	width: "Full" | "Half"
	enabled: 0 | 1
}

const core = (fieldname: string, label: string): CoreField => ({
	fieldname,
	label,
	width: "Half",
	enabled: 1,
})

// What the booking page asks when an event's forms carry no core rows.
export const DEFAULT_CORE_FIELDS: Record<string, CoreField[]> = {
	Ticket: [
		core("first_name", "First name"),
		core("last_name", "Last name"),
		core("email", "Email"),
	],
	Booking: [
		core("buyer_name", "Full name"),
		core("buyer_email", "Email"),
		core("buyer_phone", "Phone"),
	],
}
