<script setup lang="ts">
import { BottomSheet, Button } from "frappe-ui"
import { ref } from "vue"

import NotificationsList from "./NotificationsList.vue"
import { useNotificationFeed } from "./useNotificationFeed"

const { unreadCount } = useNotificationFeed()
const open = ref(false)
</script>

<template>
	<Button
		variant="ghost"
		:aria-label="unreadCount ? `Notifications, ${unreadCount} unread` : 'Notifications'"
		@click="open = true"
	>
		<template #icon>
			<span class="relative">
				<span
					class="lucide-bell block size-4"
					:class="unreadCount ? 'text-ink-gray-9' : 'text-ink-gray-7'"
					aria-hidden="true"
				/>
				<span
					v-if="unreadCount"
					class="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-surface-gray-9 shadow-[0_0_0_2px_var(--surface-base)]"
				/>
			</span>
		</template>
	</Button>
	<BottomSheet v-model:open="open">
		<div class="flex max-h-[80vh] min-h-0 flex-col">
			<NotificationsList @close="open = false" />
		</div>
	</BottomSheet>
</template>
