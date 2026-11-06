<script setup lang="ts">
import { Avatar, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { NotificationItem } from "@/types"

const props = defineProps<{ notification: NotificationItem }>()
const emit = defineEmits<{ open: [] }>()

const KIND = {
	comment: { icon: "lucide-message-square", verb: "commented" },
	reply: { icon: "lucide-reply", verb: "replied" },
}

const kind = computed(() => KIND[props.notification.kind])

// "12m", "3h", "2d", then the date: a narrow column that never wraps.
const age = computed(() => {
	const created = dayjsLocal(props.notification.creation)
	const minutes = dayjsLocal().diff(created, "minute")
	if (minutes < 60) return `${Math.max(minutes, 1)}m`
	if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}h`
	if (minutes < 60 * 24 * 7) return `${Math.floor(minutes / (60 * 24))}d`
	return created.format("D MMM")
})

const summary = computed(() => {
	const { actor, snippet, event_title } = props.notification
	if (snippet) return `${actor}: ${snippet}`
	return [`${actor} ${kind.value.verb}`, event_title].filter(Boolean).join(" · ")
})
</script>

<template>
	<button
		type="button"
		class="flex w-full items-start gap-3 rounded-[10px] px-3 py-2.5 text-left transition-[background-color,transform] duration-150 ease-out hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:focus-ring active:scale-[0.99]"
		@click="emit('open')"
	>
		<span class="relative size-8 shrink-0">
			<Avatar
				:image="notification.actor_image ?? undefined"
				:label="notification.actor"
				size="xl"
			/>
			<span
				class="absolute -right-1 -bottom-1 grid size-[18px] place-items-center rounded-full bg-surface-gray-3 text-ink-gray-7 shadow-[0_0_0_2px_var(--surface-elevation-2)]"
				aria-hidden="true"
			>
				<span :class="[kind.icon, 'size-2.5']" />
			</span>
		</span>
		<span class="flex min-w-0 flex-1 flex-col gap-0.5">
			<span class="flex items-center gap-2">
				<span
					class="min-w-0 flex-1 truncate text-base font-medium transition-colors duration-150"
					:class="notification.read ? 'text-ink-gray-7' : 'text-ink-gray-9'"
				>
					{{ notification.title }}
				</span>
				<time
					:datetime="notification.creation"
					:title="dayjsLocal(notification.creation).format('D MMM YYYY, h:mm A')"
					class="shrink-0 text-sm text-ink-gray-5 tabular-nums"
				>
					{{ age }}
				</time>
				<span
					class="size-[7px] shrink-0 rounded-full bg-surface-blue-6 transition-opacity duration-200 ease-out"
					:class="notification.read ? 'opacity-0' : 'opacity-100'"
				/>
				<span v-if="!notification.read" class="sr-only">Unread</span>
			</span>
			<span class="truncate text-sm leading-snug text-ink-gray-6">{{ summary }}</span>
		</span>
	</button>
</template>
