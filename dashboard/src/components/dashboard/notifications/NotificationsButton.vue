<script setup lang="ts">
import { BottomSheet, Button } from "frappe-ui"
import { ref } from "vue"

import NotificationsList from "./NotificationsList.vue"
import { useNotificationFeed } from "./useNotificationFeed"

const { unreadCount } = useNotificationFeed()
const open = ref(false)
</script>

<template>
	<div class="relative">
		<Button variant="ghost" icon="lucide-bell" aria-label="Notifications" @click="open = true" />
		<span
			v-if="unreadCount"
			class="pointer-events-none absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-surface-gray-7 px-1 text-xs text-ink-white tabular-nums"
		>
			{{ unreadCount }}
		</span>
	</div>
	<BottomSheet v-model:open="open">
		<div class="flex max-h-[80vh] min-h-0 flex-col">
			<NotificationsList @close="open = false" />
		</div>
	</BottomSheet>
</template>
