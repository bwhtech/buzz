import { createSharedComposable } from "@vueuse/core"
import { computed, onScopeDispose, ref } from "vue"
import { useRouter } from "vue-router"

import { useMarkAllAsRead, useMarkAsRead, useNotifications } from "@/data/notifications"
import { useSocket } from "@/socket"
import type { NotificationItem } from "@/types"

// Links are absolute and carry the router base.
function routeOf(link: string) {
	const url = new URL(link, window.location.origin)
	return url.pathname.replace(/^\/b(?=\/)/, "") + url.search
}

const ignore = () => {}

export const useNotificationFeed = createSharedComposable(() => {
	const router = useRouter()
	const notifications = useNotifications()
	const marking = useMarkAsRead()
	const markingAll = useMarkAllAsRead()

	// Read locally first, so the dot fades on click instead of after the round trip.
	const readLocally = ref(new Set<string>())
	const items = computed(() =>
		(notifications.data ?? []).map((item) =>
			readLocally.value.has(item.name) ? { ...item, read: true } : item,
		),
	)
	const unreadCount = computed(() => items.value.filter((item) => !item.read).length)

	const reload = () => notifications.reload()

	// Frappe pushes this to the user whenever a Notification Log is created for them.
	const socket = useSocket()
	socket?.on("notification", reload)
	onScopeDispose(() => socket?.off("notification", reload))

	function markRead(item: NotificationItem) {
		readLocally.value = new Set(readLocally.value).add(item.name)
		marking.submit({ name: item.name }).catch(ignore)
	}

	function markAllRead() {
		readLocally.value = new Set(items.value.map((item) => item.name))
		markingAll.submit().then(reload, ignore)
	}

	function openNotification(item: NotificationItem) {
		if (!item.read) markRead(item)
		if (item.link) router.push(routeOf(item.link))
	}

	return { notifications, marking, markingAll, items, unreadCount, markAllRead, openNotification }
})
