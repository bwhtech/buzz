import { useCall } from "frappe-ui"

import type { CommunicationItem, EventCommunications } from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this team's messages to IndexedDB past a logout.
export function useEventCommunications(event: string) {
	return useCall<EventCommunications, { event: string }>({
		url: "/api/v2/method/buzz.api.communications.get_event_communications",
		params: { event },
	})
}

export type RecipientQuery = {
	event: string
	audience: string
	ticket_types: string
	statuses: string
}

export function useRecipientCount(params: () => RecipientQuery) {
	return useCall<{ count: number }, RecipientQuery>({
		url: "/api/v2/method/buzz.api.communications.count_recipients",
		params,
		refetch: true,
	})
}

export type SendPayload = RecipientQuery & {
	message: string
	subject: string
	scheduled_at: string | null
}

export function useSendCommunication() {
	return useCall<CommunicationItem, SendPayload>({
		url: "/api/v2/method/buzz.api.communications.send_communication",
		method: "POST",
		immediate: false,
	})
}

export function useUpdateSupportEmail() {
	return useCall<null, { event: string; support_email: string }>({
		url: "/api/v2/method/buzz.api.communications.update_support_email",
		method: "POST",
		immediate: false,
	})
}
