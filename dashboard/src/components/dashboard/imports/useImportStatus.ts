import { Progress, call, toast } from "frappe-ui"
import { h } from "vue"

import {
	type ImportRowError,
	type ImportStatus,
	sponsorCount,
} from "@/components/dashboard/imports/importTypes"
import { downloadCsv } from "@/utils/csv"

const STAYS = Number.POSITIVE_INFINITY
const POLL_MS = 1000

// The toast is dark on a light page and light on a dark one, so the bar takes its colors
// from the toast's text rather than Progress's own track and fill.
const progressBar = (done: number, total: number) => () =>
	h("div", { class: "flex w-56 flex-col gap-1.5 pt-1" }, [
		h(Progress, {
			class: "[&_.bg-surface-gray-2]:!bg-surface-gray-7 [&_.bg-surface-gray-10]:!bg-current",
			value: total ? Math.round((done / total) * 100) : 0,
			size: "sm",
		}),
		h("span", { class: "tabular-nums" }, `${done} of ${total}`),
	])

const clip = (text: string, length: number) =>
	text.length > length ? `${text.slice(0, length - 1)}…` : text

// One line in a narrow toast; the downloaded rows carry every reason in full.
const failureLine = ([first, ...rest]: ImportRowError[]) =>
	`${clip(first.title || `Row ${first.row}`, 30)}: ${clip(first.reason, 60)}` +
	(rest.length ? ` And ${rest.length} more.` : "")

function downloadFailedRows({ header, failed, failed_cells }: ImportStatus) {
	downloadCsv("sponsors failed rows.csv", [
		[...header, "Reason"],
		...failed_cells.map((cells, index) => [...cells, failed[index]?.reason]),
	])
}

// One toast per import, updated in place by id while the page polls the background job.
// Polling outlives the page, so leaving it mid-import still ends the toast on the result.
export function useImportStatus(event: string, onImported: () => void) {
	const id = `import-${event}`
	let timer: ReturnType<typeof setTimeout> | undefined

	function showProgress(done: number, total: number) {
		toast.loading(`Importing ${sponsorCount(total)}`, {
			id,
			description: progressBar(done, total),
			duration: STAYS,
		})
	}

	function showResult(status: ImportStatus) {
		const { error, imported, failed } = status
		if (error) {
			toast.error("Import failed", { id, description: error, duration: STAYS })
			return
		}
		if (!failed.length) {
			toast.success(`${sponsorCount(imported)} imported`, {
				id,
				description: undefined,
				duration: 4000,
			})
			return
		}
		toast.warning(`${sponsorCount(imported)} imported, ${failed.length} couldn’t be`, {
			id,
			description: failureLine(failed),
			duration: STAYS,
			action: { label: "Download failed rows", onClick: () => downloadFailedRows(status) },
		})
	}

	function showLost() {
		toast.error("Lost track of the import", {
			id,
			description: "The sponsor list shows what went in.",
			duration: STAYS,
		})
	}

	async function poll() {
		const status = (await call("buzz.api.imports.get_import_status", { event }).catch(
			() => null,
		)) as ImportStatus | null
		// The server saves a status before queueing the job, so none means it expired or the call failed.
		if (!status || status.state === "done") {
			if (status) showResult(status)
			else showLost()
			onImported()
			return
		}
		showProgress(status.done, status.total)
		timer = setTimeout(poll, POLL_MS)
	}

	function start(total: number) {
		clearTimeout(timer)
		showProgress(0, total)
		timer = setTimeout(poll, POLL_MS)
	}

	return { start }
}
