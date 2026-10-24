<script setup lang="ts">
import { onClickOutside, onKeyStroke } from "@vueuse/core"
import {
	Badge,
	Button,
	ErrorMessage,
	SidebarItem,
	Skeleton,
	TabButtons,
	Tooltip,
	dayjsLocal,
} from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from "vue"
import { useRouter } from "vue-router"

import { useMarkAllAsRead, useMarkAsRead, useNotifications } from "@/data/notifications"
import { useSocket } from "@/socket"
import type { NotificationItem } from "@/types"

import NotificationRow from "./NotificationRow.vue"

type Filter = "all" | "unread" | "mentions" | "updates"

const router = useRouter()
const notifications = useNotifications()
const marking = useMarkAsRead()
const markingAll = useMarkAllAsRead()

const open = ref(false)
const filter = ref<Filter>("all")

const FILTERS: { label: string; value: Filter }[] = [
	{ label: "All", value: "all" },
	{ label: "Unread", value: "unread" },
	{ label: "Mentions", value: "mentions" },
	{ label: "Updates", value: "updates" },
]

// Notes and replies are people talking to you; status changes and publishing will be updates.
const CONVERSATION_KINDS = new Set<NotificationItem["kind"]>(["comment", "reply"])
const MATCHES: Record<Filter, (item: NotificationItem) => boolean> = {
	all: () => true,
	unread: (item) => !item.read,
	mentions: (item) => CONVERSATION_KINDS.has(item.kind),
	updates: (item) => !CONVERSATION_KINDS.has(item.kind),
}

// Read locally first, so the dot fades on click instead of after the round trip.
const readLocally = ref(new Set<string>())
const items = computed(() =>
	(notifications.data ?? []).map((item) =>
		readLocally.value.has(item.name) ? { ...item, read: true } : item,
	),
)
const unreadCount = computed(() => items.value.filter((item) => !item.read).length)
const visible = computed(() => items.value.filter(MATCHES[filter.value]))

function dayOf(creation: string) {
	const day = dayjsLocal(creation)
	if (day.isToday()) return "Today"
	if (day.isSame(dayjsLocal().subtract(1, "day"), "day")) return "Yesterday"
	return "Earlier"
}

const sections = computed(() => {
	const byDay = new Map<string, NotificationItem[]>()
	for (const item of visible.value) {
		const day = dayOf(item.creation)
		byDay.set(day, [...(byDay.get(day) ?? []), item])
	}
	return [...byDay].map(([label, rows]) => ({ label, rows }))
})

const EMPTY: Record<Filter, string> = {
	all: "No notifications yet",
	unread: "You're all caught up",
	mentions: "No notes or replies yet",
	updates: "No updates yet",
}

const ignore = () => {}
const reload = () => notifications.reload()

// Frappe pushes this to the user whenever a Notification Log is created for them.
const socket = useSocket()
socket?.on("notification", reload)
onBeforeUnmount(() => socket?.off("notification", reload))

function markRead(item: NotificationItem) {
	readLocally.value = new Set(readLocally.value).add(item.name)
	marking.submit({ name: item.name }).catch(ignore)
}

function markAllRead() {
	readLocally.value = new Set(items.value.map((item) => item.name))
	markingAll.submit().then(reload, ignore)
}

// Docked beside the sidebar like the desk's panel: no overlay, so the page stays in view.
const panel = useTemplateRef<HTMLElement>("panel")
const trigger = useTemplateRef<HTMLElement>("trigger")
const close = () => (open.value = false)
onClickOutside(panel, close, { ignore: [trigger] })
onKeyStroke("Escape", () => open.value && close())

// Focus lands on the tabs, not the first header button, whose tooltip would pop on every open.
watch(open, async (isOpen) => {
	if (!isOpen) return
	await nextTick()
	panel.value?.querySelector<HTMLElement>("[data-state=active]")?.focus()
})

// Links are absolute and carry the router base.
function routeOf(link: string) {
	const url = new URL(link, window.location.origin)
	return url.pathname.replace(/^\/b(?=\/)/, "") + url.search
}

function openNotification(item: NotificationItem) {
	if (!item.read) markRead(item)
	open.value = false
	if (item.link) router.push(routeOf(item.link))
}
</script>

<template>
	<div ref="trigger">
		<SidebarItem
			label="Notifications"
			icon="lucide-bell"
			:active="open"
			:on-click="() => (open = !open)"
		>
			<template #suffix>
				<span v-if="unreadCount" class="mr-2 text-sm text-ink-gray-7 tabular-nums">
					{{ unreadCount }}
				</span>
			</template>
		</SidebarItem>
	</div>

	<Teleport defer to="#shell-content">
		<Transition name="panel">
			<aside
				v-if="open"
				ref="panel"
				role="dialog"
				aria-labelledby="notifications-title"
				class="absolute inset-y-0 left-0 z-30 flex w-[400px] max-w-full flex-col border-r border-outline-gray-1 bg-surface-elevation-2 shadow-xl"
			>
				<header class="flex flex-col gap-3 border-b border-outline-gray-1 pt-3.5 pr-3 pb-3 pl-5">
					<div class="flex items-center gap-1">
						<div class="flex flex-1 items-center gap-2">
							<h2 id="notifications-title" class="text-lg font-semibold text-ink-gray-9">
								Notifications
							</h2>
							<Badge v-if="unreadCount" :label="String(unreadCount)" />
						</div>
						<Tooltip text="Mark all as read">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-check-check"
								aria-label="Mark all as read"
								:disabled="!unreadCount"
								@click="markAllRead"
							/>
						</Tooltip>
						<Button variant="ghost" size="sm" icon="lucide-x" aria-label="Close" @click="close" />
					</div>
					<div class="pr-2">
						<TabButtons v-model="filter" :options="FILTERS" fluid />
					</div>
				</header>

				<div
					class="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-2 pt-1.5 pb-4"
				>
					<ErrorMessage
						class="px-3 py-2"
						:message="notifications.error || marking.error || markingAll.error"
					/>
					<div v-if="notifications.loading && !notifications.data" class="space-y-1 px-1 pt-2">
						<Skeleton v-for="row in 5" :key="row" class="h-14 w-full rounded-[10px]" />
					</div>
					<div
						v-else-if="!sections.length"
						class="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center"
					>
						<span class="lucide-inbox size-5 text-ink-gray-5" aria-hidden="true" />
						<p class="text-base text-ink-gray-5">{{ EMPTY[filter] }}</p>
					</div>
					<section v-for="section in sections" v-else :key="section.label">
						<h3 class="px-3 pt-2.5 pb-1 text-sm text-ink-gray-5">{{ section.label }}</h3>
						<TransitionGroup tag="ul" name="notification" class="relative">
							<li v-for="item in section.rows" :key="item.name">
								<NotificationRow :notification="item" @open="openNotification(item)" />
							</li>
						</TransitionGroup>
					</section>
				</div>
			</aside>
		</Transition>
	</Teleport>
</template>

<style scoped>
/* Slides out from behind the sidebar edge; leaves faster than it arrives. */
.panel-enter-active {
	transition:
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1),
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.panel-leave-active {
	transition:
		transform 150ms ease-out,
		opacity 150ms ease-out;
}
.panel-enter-from,
.panel-leave-to {
	opacity: 0;
	transform: translateX(-12px);
}

/* A row read away from the Unread tab fades out, and the ones below close the gap. */
.notification-move {
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.notification-leave-active {
	position: absolute;
	inset-inline: 0;
	transition: opacity 150ms ease-out;
}
.notification-leave-to {
	opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
	.notification-move {
		transition: none;
	}
	.panel-enter-from,
	.panel-leave-to {
		transform: none;
	}
}
</style>
