import { toast } from "frappe-ui"
import { computed, ref } from "vue"

import { useHeldWrite } from "@/composables/useHeldWrite"
import {
	refreshRequestCounts,
	runRequestAction,
	useRegistrationRequests,
	useRequestCounts,
} from "@/data/requests"
import type { RegistrationRequest, RequestType } from "@/types"
import { formatPriceOrFree } from "@/utils/currency"
import { firstName, isPaid } from "@/utils/requestQueue"
import {
	type RequestAction,
	type RequestView,
	actionMessage,
	requestViewOf,
	viewAfter,
} from "@/utils/requestStatus"
import { serverErrorMessage } from "@/utils/serverError"

/**
 * One page of requests and the actions on them. An action moves its rows at once and
 * holds the write for as long as the toast offers Undo.
 */
export function useRequestQueue(event: string, type: RequestType) {
	const requests = useRegistrationRequests(event, type)
	const counts = useRequestCounts(() => event)
	const held = useHeldWrite()

	// Where a row shows while its write is held or on its way.
	const moved = ref(new Map<string, RequestView>())
	const rows = computed(() => requests.data ?? [])
	const viewOf = (row: RegistrationRequest) => moved.value.get(row.name) ?? requestViewOf(row)

	function move(names: string[], view: RequestView | null) {
		const next = new Map(moved.value)
		for (const name of names) {
			if (view) next.set(name, view)
			else next.delete(name)
		}
		moved.value = next
	}

	async function write(action: RequestAction, targets: RegistrationRequest[]) {
		try {
			for (const row of targets) await runRequestAction(action, row.name)
		} catch (error) {
			toast.error(serverErrorMessage(error) || "Could not update the request")
		}
		await requests.reload()
		refreshRequestCounts()
		move(
			targets.map((row) => row.name),
			null,
		)
	}

	function act(action: RequestAction, targets: RegistrationRequest[]) {
		if (!targets.length) return
		const [first] = targets
		const message = actionMessage(action, {
			type,
			names: targets.map(firstName),
			price: isPaid(first) ? formatPriceOrFree(first.total_amount, first.currency ?? "INR") : "",
		})
		for (const row of targets) move([row.name], viewAfter(action, type, isPaid(row)))
		// A resend changes nothing to undo.
		if (action === "resend") {
			toast.success(message)
			return write(action, targets)
		}
		held.hold({
			message,
			write: () => write(action, targets),
			undo: () =>
				move(
					targets.map((row) => row.name),
					null,
				),
		})
	}

	return { requests, counts, rows, viewOf, act }
}
