<script setup lang="ts">
import { computed } from "vue"

import { useRegistrationRequests } from "@/data/requests"
import type { RegistrationRequest, RequestType } from "@/types"
import { ticketTypeOf } from "@/utils/requestQueue"
import { OPEN_VIEW, requestViewOf } from "@/utils/requestStatus"

const props = defineProps<{ event: string; ticketType: string; guests: number }>()

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
const to = computed(
	() =>
		`/manage/events/${props.event}/${waiting.value && !pending.value ? "waitlist" : "approvals"}`,
)
</script>

<template>
	<RouterLink
		v-if="pending || waiting"
		:to="to"
		class="flex items-center gap-3 rounded-6 bg-surface-gray-2 px-3.5 py-3 transition-colors duration-150 hover:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
	>
		<span class="lucide-users size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
		<span class="min-w-0 flex-1 space-y-0.5">
			<span class="block text-base font-medium text-ink-gray-9">
				{{ guests }} {{ guests === 1 ? "guest" : "guests" }}
			</span>
			<span class="block text-sm text-ink-gray-5">
				{{ pending }} pending approval · {{ waiting }} on waitlist
			</span>
		</span>
		<span class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-4" aria-hidden="true" />
	</RouterLink>
</template>
