import { useCall } from "frappe-ui"

import type { NotificationGroup } from "@/types"

type Reference = { reference_doctype: string; reference_name: string }

// Uncached: notifications belong to the session user.
export function useNotifications() {
	return useCall<NotificationGroup[]>({
		url: "/api/v2/method/buzz.api.notifications.get_notifications",
	})
}

export function useMarkAsRead() {
	return useCall<null, Reference>({
		url: "/api/v2/method/buzz.api.notifications.mark_as_read",
		method: "POST",
		immediate: false,
	})
}
