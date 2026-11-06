<script setup lang="ts">
import { onClickOutside, onKeyStroke } from "@vueuse/core"
import { SidebarItem } from "frappe-ui"
import { nextTick, ref, useTemplateRef, watch } from "vue"

import NotificationsList from "./NotificationsList.vue"
import { useNotificationFeed } from "./useNotificationFeed"

const { unreadCount } = useNotificationFeed()

const open = ref(false)

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

	<Teleport defer to="#sidebar-panel">
		<Transition name="panel">
			<aside
				v-if="open"
				ref="panel"
				role="dialog"
				aria-labelledby="notifications-title"
				class="absolute inset-y-0 left-0 flex w-[400px] flex-col border-x border-outline-gray-1 bg-surface-elevation-2 shadow-lg"
			>
				<NotificationsList @close="close" />
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

@media (prefers-reduced-motion: reduce) {
	.panel-enter-from,
	.panel-leave-to {
		transform: none;
	}
}
</style>
