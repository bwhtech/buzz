// A cell opening with one of these is a formula to a spreadsheet, and the people in
// these lists write their own names — a leading quote makes it text again.
const FORMULA_START = /^[=+\-@\t\r]/

export function csvCell(value: string | null | undefined): string {
	const text = String(value ?? "")
	return `"${(FORMULA_START.test(text) ? `'${text}` : text).replace(/"/g, '""')}"`
}

export function toCsv(rows: (string | null | undefined)[][]): string {
	return rows.map((row) => row.map(csvCell).join(",")).join("\n")
}

/** Hands the browser a file it saves itself — no round trip, the rows are already here. */
export function downloadCsv(filename: string, rows: (string | null | undefined)[][]): void {
	const link = document.createElement("a")
	link.href = URL.createObjectURL(new Blob([toCsv(rows)], { type: "text/csv" }))
	link.download = filename
	document.body.appendChild(link)
	link.click()
	link.remove()
	URL.revokeObjectURL(link.href)
}
