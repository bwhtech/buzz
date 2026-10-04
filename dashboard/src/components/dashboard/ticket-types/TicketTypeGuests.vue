<script setup lang="ts">
import { Avatar, Icon, useCall } from "frappe-ui"
import { computed } from "vue"

import type { EventGuests } from "@/types"

const props = defineProps<{ event: string; ticketType: string; count: number }>()

// The card is gray, so the avatars take color to stand off it.
const AVATAR_THEMES = ["blue", "green", "violet"] as const

// Only the three newest holders are drawn; the count comes from the ticket type itself.
const latest = useCall<EventGuests, Record<string, string | number>>({
	url: "/api/v2/method/buzz.api.events.get_event_guests",
	params: () => ({
		event: props.event,
		filters: JSON.stringify([["ticket_type", "in", [props.ticketType]]]),
		limit: 3,
	}),
})

const names = computed(() => (latest.data?.guests ?? []).map((guest) => guest.attendee_name ?? ""))

const summary = computed(() => {
	const others = props.count - names.value.length
	return others > 0 ? `${names.value.join(", ")} and ${others} more` : names.value.join(", ")
})
</script>

<template>
	<RouterLink
		:to="{ name: 'event-guests', params: { eventId: event }, query: { ticket_type: ticketType } }"
		class="flex w-full items-center gap-3 rounded-4 bg-surface-gray-1 p-4 transition-[background-color,transform] duration-150 ease-out [@media(hover:hover)]:hover:bg-surface-gray-2 active:scale-[0.99] focus-visible:outline-none focus-visible:focus-ring motion-reduce:transform-none"
	>
		<span class="flex shrink-0 -space-x-1.5" aria-hidden="true">
			<Avatar
				v-for="(name, index) in names"
				:key="index"
				:label="name"
				:theme="AVATAR_THEMES[index]"
				size="md"
			/>
		</span>
		<span class="min-w-0 flex-1">
			<span class="block text-base font-medium text-ink-gray-9">
				{{ count }} {{ count === 1 ? "guest" : "guests" }}
			</span>
			<span class="block truncate text-sm text-ink-gray-5">{{ summary }}</span>
		</span>
		<Icon name="lucide-chevron-right" class="size-4 text-ink-gray-5" />
	</RouterLink>
</template>
