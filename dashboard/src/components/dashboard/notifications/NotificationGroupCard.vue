<script setup lang="ts">
import { Avatar, Button, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { NotificationGroup } from "@/types"

const props = defineProps<{ group: NotificationGroup }>()
const emit = defineEmits<{ open: []; read: []; toggleSubscription: [] }>()

const hasUnread = computed(() => props.group.notifications.some((entry) => !entry.read))
const verb = { comment: "commented", reply: "replied" }
</script>

<template>
	<article
		class="group/card relative rounded-6 border border-outline-gray-1 bg-surface-elevation-1 transition-colors duration-150 ease-out hover:border-outline-gray-2"
	>
		<!-- The whole card opens the record; its actions sit above this layer. -->
		<button
			class="absolute inset-0 rounded-6 focus-visible:outline-none focus-visible:focus-ring"
			:aria-label="`Open ${group.title}`"
			@click="emit('open')"
		/>
		<header class="flex items-start justify-between gap-3 px-4 pt-3.5 pb-2">
			<div class="min-w-0 space-y-0.5">
				<p v-if="group.event_title" class="truncate text-sm text-ink-gray-5">
					{{ group.event_title }}
				</p>
				<h3 class="truncate text-base font-semibold text-ink-gray-9">{{ group.title }}</h3>
			</div>
			<div
				class="relative flex shrink-0 gap-0.5 opacity-0 transition-opacity duration-150 ease-out group-hover/card:opacity-100 focus-within:opacity-100"
			>
				<Tooltip :text="group.subscribed ? 'Unsubscribe' : 'Subscribe'">
					<Button
						variant="ghost"
						size="sm"
						:icon="group.subscribed ? 'lucide-bell-off' : 'lucide-bell'"
						:aria-label="group.subscribed ? 'Unsubscribe' : 'Subscribe'"
						@click="emit('toggleSubscription')"
					/>
				</Tooltip>
				<Tooltip v-if="hasUnread" text="Mark as read">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-check"
						aria-label="Mark as read"
						@click="emit('read')"
					/>
				</Tooltip>
			</div>
		</header>

		<ol class="space-y-3 px-4 pb-4">
			<li v-for="entry in group.notifications" :key="entry.name" class="flex gap-2.5">
				<Avatar :image="entry.actor_image ?? undefined" :label="entry.actor" size="sm" />
				<div class="min-w-0 flex-1 space-y-1">
					<p class="flex items-center gap-1.5 text-sm text-ink-gray-6">
						<span class="truncate font-medium text-ink-gray-9">{{ entry.actor }}</span>
						<span class="shrink-0">{{ verb[entry.kind] }}</span>
						<time :datetime="entry.creation" class="shrink-0 text-ink-gray-5">
							· {{ dayjsLocal(entry.creation).fromNow() }}
						</time>
						<span
							v-if="!entry.read"
							class="size-1.5 shrink-0 rounded-full bg-surface-gray-7"
							aria-label="Unread"
						/>
					</p>
					<p
						v-if="entry.snippet"
						class="line-clamp-3 border-l-2 border-outline-gray-2 pl-2.5 text-sm leading-relaxed text-ink-gray-7"
					>
						{{ entry.snippet }}
					</p>
				</div>
			</li>
		</ol>
		<p v-if="!group.subscribed" class="px-4 pb-3 text-sm text-ink-gray-5">
			Unsubscribed. You won't hear about new activity here.
		</p>
	</article>
</template>
