<script setup lang="ts">
import { Button, ErrorMessage, SidebarItem, Skeleton, TabButtons } from "frappe-ui"
import { computed, onBeforeUnmount, ref } from "vue"
import { useRouter } from "vue-router"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { useSetSubscription } from "@/data/comments"
import { useMarkAsRead, useNotifications } from "@/data/notifications"
import { useSocket } from "@/socket"
import type { NotificationGroup } from "@/types"

import NotificationGroupCard from "./NotificationGroupCard.vue"

const router = useRouter()
const notifications = useNotifications()
const marking = useMarkAsRead()
const subscribing = useSetSubscription()

const open = ref(false)
const filter = ref<"unread" | "all">("unread")

const groups = computed(() => notifications.data ?? [])
const isUnread = (group: NotificationGroup) => group.notifications.some((entry) => !entry.read)
const unreadCount = computed(
	() => groups.value.flatMap((group) => group.notifications).filter((entry) => !entry.read).length,
)
const visible = computed(() =>
	filter.value === "all" ? groups.value : groups.value.filter(isUnread),
)

const ignore = () => {}
const reload = () => notifications.reload()
const reference = (group: NotificationGroup) => ({
	reference_doctype: group.reference_doctype,
	reference_name: group.reference_name,
})

// Frappe pushes this to the user whenever a Notification Log is created for them.
const socket = useSocket()
socket?.on("notification", reload)
onBeforeUnmount(() => socket?.off("notification", reload))

const markRead = (group: NotificationGroup) => marking.submit(reference(group)).then(reload, ignore)

const toggleSubscription = (group: NotificationGroup) =>
	subscribing.submit({ ...reference(group), subscribed: !group.subscribed }).then(reload, ignore)

// Links are absolute and carry the router base.
function routeOf(link: string) {
	const url = new URL(link, window.location.origin)
	return url.pathname.replace(/^\/b(?=\/)/, "") + url.search
}

function openRecord(group: NotificationGroup) {
	open.value = false
	if (isUnread(group)) markRead(group)
	if (group.link) router.push(routeOf(group.link))
}
</script>

<template>
	<SidebarItem
		label="Notifications"
		icon="lucide-bell"
		:active="open"
		:on-click="() => (open = true)"
	>
		<template #suffix>
			<span v-if="unreadCount" class="mr-2 text-sm text-ink-gray-7 tabular-nums">
				{{ unreadCount }}
			</span>
		</template>
	</SidebarItem>

	<Drawer v-model:open="open" swipe-direction="left">
		<DrawerContent>
			<header class="flex items-center justify-between gap-2 px-5 pt-5 pb-3">
				<DrawerTitle class="text-lg font-semibold text-ink-gray-9">Notifications</DrawerTitle>
				<DrawerDescription class="sr-only">
					New notes and speaker replies on talks you follow
				</DrawerDescription>
				<div class="flex items-center gap-1">
					<TabButtons
						v-model="filter"
						:options="[
							{ label: 'Unread', value: 'unread' },
							{ label: 'All', value: 'all' },
						]"
					/>
					<DrawerClose as-child>
						<Button variant="ghost" size="sm" icon="lucide-x" aria-label="Close" />
					</DrawerClose>
				</div>
			</header>

			<div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-4">
				<ErrorMessage
					class="px-2 pb-2"
					:message="notifications.error || marking.error || subscribing.error"
				/>
				<div v-if="notifications.loading && !notifications.data" class="space-y-3">
					<Skeleton v-for="row in 3" :key="row" class="h-28 w-full rounded-6" />
				</div>
				<div
					v-else-if="!visible.length"
					class="flex flex-col items-center gap-2 px-6 pt-16 pb-10 text-center"
				>
					<span class="lucide-bell size-5 text-ink-gray-4" aria-hidden="true" />
					<p class="text-base text-ink-gray-6">
						{{ filter === "unread" ? "You're all caught up" : "No notifications yet" }}
					</p>
					<p class="text-sm text-ink-gray-5">
						Notes and speaker replies on talks you follow show up here.
					</p>
				</div>
				<TransitionGroup v-else tag="div" name="notification" class="relative space-y-3">
					<NotificationGroupCard
						v-for="group in visible"
						:key="`${group.reference_doctype}:${group.reference_name}`"
						:group="group"
						@open="openRecord(group)"
						@read="markRead(group)"
						@toggle-subscription="toggleSubscription(group)"
					/>
				</TransitionGroup>
			</div>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
/* A card read away from the Unread tab fades out, and the ones below close the gap. */
.notification-move {
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.notification-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms ease-out,
		transform 150ms ease-out;
}
.notification-leave-to {
	opacity: 0;
	transform: scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
	.notification-move,
	.notification-leave-active {
		transition: opacity 150ms ease-out;
	}
	.notification-leave-to {
		transform: none;
	}
}
</style>
