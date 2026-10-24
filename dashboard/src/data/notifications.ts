import { useCall } from "frappe-ui"

import type { NotificationItem } from "@/types"

// Uncached: notifications belong to the session user.
export function useNotifications() {
	return useCall<NotificationItem[]>({
		url: "/api/v2/method/buzz.api.notifications.get_notifications",
	})
}

export function useMarkAsRead() {
	return useCall<null, { name: string }>({
		url: "/api/v2/method/buzz.api.notifications.mark_as_read",
		method: "POST",
		immediate: false,
	})
}

export function useMarkAllAsRead() {
	return useCall<null>({
		url: "/api/v2/method/buzz.api.notifications.mark_all_as_read",
		method: "POST",
		immediate: false,
	})
}
