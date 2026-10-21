export const sponsorCount = (n: number) => `${n} ${n === 1 ? "sponsor" : "sponsors"}`

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
	rows: ImportRowError[]
}

export type ImportRowError = { row: number; title: string | null; reason: string }

export type ImportPreviewRow = { row: number; values: Record<string, string | null> }

export type ImportCheck = {
	total_rows: number
	ready_rows: number
	ready: boolean
	fields: ImportOption[]
	columns: { column: string; field: string | null }[]
	issues: ImportIssue[]
	notes: string[]
	preview: ImportPreviewRow[]
}

// buzz.api.imports.get_import_status
export type ImportStatus = {
	state: "queued" | "running" | "done"
	done: number
	total: number
	imported: number
	failed: ImportRowError[]
	header: string[]
	failed_cells: string[][]
	error: string | null
}
