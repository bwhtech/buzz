import { toast } from "frappe-ui"
import { ref } from "vue"

import { useAffectedRequests, useSetApproval } from "@/data/approvals"
import type { PendingAction } from "@/types"
import { approvalResultMessage } from "@/utils/bookingApproval"
import { serverErrorMessage } from "@/utils/serverError"

export interface WaitingRequests {
	ticketType?: string
	count: number
}

/**
 * Switches approval on or off for the event, or for one ticket type. Turning it off with
 * requests waiting asks what to do with them first.
 */
export function useApprovalToggle(event: string, onChanged: () => void) {
	const affectedRequests = useAffectedRequests()
	const setApproval = useSetApproval()
	const waiting = ref<WaitingRequests | null>(null)

	async function apply(enabled: boolean, ticketType?: string, pendingAction?: PendingAction) {
		try {
			const result = await setApproval.submit({
				event,
				enabled,
				ticket_type: ticketType,
				pending_action: pendingAction,
			})
			const message = result && approvalResultMessage(result)
			if (message) (result.failed ? toast.warning : toast.success)(message)
			waiting.value = null
			onChanged()
		} catch (error) {
			toast.error(serverErrorMessage(error))
		}
	}

	async function change(enabled: boolean, ticketType?: string) {
		if (enabled) return apply(true, ticketType)
		try {
			const affected = await affectedRequests.submit({ event, ticket_type: ticketType })
			if (affected?.count) waiting.value = { ticketType, count: affected.count }
			else await apply(false, ticketType)
		} catch (error) {
			toast.error(serverErrorMessage(error))
		}
	}

	function confirm(pendingAction: PendingAction) {
		if (waiting.value) return apply(false, waiting.value.ticketType, pendingAction)
	}

	return { change, confirm, waiting, saving: () => setApproval.loading }
}
