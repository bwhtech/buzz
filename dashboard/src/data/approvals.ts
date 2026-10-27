import { useCall } from "frappe-ui"

import type {
	ApproveBookingsResult,
	PendingAction,
	PendingBookings,
	SetApprovalResult,
} from "@/types"

const METHOD = "/api/v2/method/buzz.api.booking.approvals"

export function usePendingBookings(event: string) {
	return useCall<PendingBookings, { event: string }>({
		url: `${METHOD}.get_pending_bookings`,
		params: { event },
	})
}

export function useApproveBookings() {
	return useCall<ApproveBookingsResult, { event: string; bookings: string[] }>({
		url: `${METHOD}.approve_bookings`,
		method: "POST",
		immediate: false,
	})
}

export function useDeclineBookings() {
	return useCall<
		{ declined: string[] },
		{ event: string; bookings: string[]; message: string | null }
	>({
		url: `${METHOD}.decline_bookings`,
		method: "POST",
		immediate: false,
	})
}

export function useAffectedRequests() {
	return useCall<{ count: number }, { event: string; ticket_type?: string }>({
		url: `${METHOD}.get_affected_requests`,
		immediate: false,
	})
}

export function useSetApproval() {
	return useCall<
		SetApprovalResult,
		{ event: string; enabled: boolean; ticket_type?: string; pending_action?: PendingAction }
	>({
		url: `${METHOD}.set_approval`,
		method: "POST",
		immediate: false,
	})
}
