export type ImportType = "checkins" | "talks" | "sponsors"

type ImportConfig = {
	title: string
	// Matches the server's Importer.noun, which tags the socket messages.
	noun: string
	one: string
	intro: string
	needs: string
	// The template's header row: the server matches these labels exactly.
	columns: string[]
	emailLabel?: string
}

export const IMPORTS: Record<ImportType, ImportConfig> = {
	checkins: {
		title: "Import check-ins",
		noun: "check-ins",
		one: "check-in",
		intro: "Check guests in from a front-desk list. Guests are not emailed.",
		needs: "a Ticket ID or an Email column",
		columns: ["Ticket ID", "Email", "Date"],
	},
	talks: {
		title: "Import talks",
		noun: "talks",
		one: "talk",
		intro: "Add accepted talks and their speakers. New speakers get a profile.",
		needs: "Title and Speaker Email",
		columns: [
			"Title",
			"Description",
			"Speaker Email",
			"Speaker Name",
			"Designation",
			"Company",
			"Track",
			"Date",
			"Start Time",
			"End Time",
		],
		emailLabel: "Email new speakers a welcome",
	},
	sponsors: {
		title: "Import sponsors",
		noun: "sponsors",
		one: "sponsor",
		intro: "Add sponsors on the event's tiers. A logo is optional.",
		needs: "Company Name and Tier",
		columns: ["Company Name", "Tier", "Website", "Country", "Contact Email", "Logo URL"],
	},
}

export type ImportOption = { value: string; label: string }

export type ImportIssue = {
	kind: "column" | "missing" | "value" | "rows"
	choice: string | null
	column: string | null
	suggestion: ImportOption | null
	field: string | null
	label: string | null
	value: string | null
	count: number
	options: ImportOption[]
	rows: { row: number; reason: string }[]
}

export type ImportCheck = {
	total_rows: number
	ready_rows: number
	ready: boolean
	fields: ImportOption[]
	columns: { column: string; field: string | null }[]
	issues: ImportIssue[]
	notes: string[]
	days: ImportOption[]
}

export type ImportDone = {
	event: string
	import_type: string
	imported?: number
	failed?: { row: number; reason: string }[]
	notes?: string[]
	header?: string[]
	failed_cells?: string[][]
	error?: string
}
