<script setup lang="ts">
import { computed } from "vue"

import { useRegistrationRequests } from "@/data/requests"
import type { RegistrationRequest, RequestType } from "@/types"
import { ticketTypeOf } from "@/utils/requestQueue"
import { OPEN_VIEW, requestViewOf } from "@/utils/requestStatus"

const props = defineProps<{ event: string; ticketType: string }>()

// ponytail: counts per ticket type come from the full lists, add them to
// get_request_counts if events grow past a few hundred requests.
const approvals = useRegistrationRequests(props.event, "Approval")
const waitlist = useRegistrationRequests(props.event, "Waitlist")

const openFor = (rows: RegistrationRequest[] | null, type: RequestType) =>
	(rows ?? []).filter(
		(row) => ticketTypeOf(row) === props.ticketType && requestViewOf(row) === OPEN_VIEW[type],
	).length

const pending = computed(() => openFor(approvals.data, "Approval"))
const waiting = computed(() => openFor(waitlist.data, "Waitlist"))
// A tinted icon tells the two apart: amber needs action, blue waits on free seats.
const links = computed(() =>
	[
		{
			count: pending.value,
			label: "Pending",
			icon: "lucide-user-check",
			page: "approvals",
			tone: "text-ink-amber-6",
		},
		{
			count: waiting.value,
			label: "Waitlisted",
			icon: "lucide-list-ordered",
			page: "waitlist",
			tone: "text-ink-blue-6",
		},
	].filter((link) => link.count),
)
</script>

<template>
	<div v-if="links.length" class="flex gap-2">
		<RouterLink
			v-for="link in links"
			:key="link.page"
			:to="`/manage/events/${event}/${link.page}`"
			class="flex flex-1 items-center gap-2 rounded-5 bg-surface-gray-1 px-3 py-2.5 text-base font-medium text-ink-gray-8 transition-colors hover:bg-surface-gray-2 duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
		>
			<span :class="[link.icon, link.tone]" class="size-4 shrink-0" aria-hidden="true" />
			<span class="min-w-0 flex-1 truncate tabular-nums">{{ link.count }} {{ link.label }}</span>
			<span class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
		</RouterLink>
	</div>
</template>
