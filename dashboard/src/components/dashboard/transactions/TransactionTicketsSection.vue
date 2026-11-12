<script setup lang="ts">
import { Badge } from "frappe-ui"

import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionDetail } from "@/types"

defineProps<{ transaction: TransactionDetail; event: string }>()
</script>

<template>
	<TransactionSection title="Tickets">
		<ul class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
			<li v-for="ticket in transaction.tickets" :key="ticket.name">
				<RouterLink
					:to="`/manage/events/${event}/guests?guest=${encodeURIComponent(ticket.name)}`"
					class="flex items-center gap-3 px-3 py-2 text-base transition-colors hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:focus-ring"
				>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-ink-gray-9">
							{{ ticket.attendee_name || ticket.attendee_email || "Unnamed guest" }}
						</span>
						<span class="block truncate text-sm text-ink-gray-5">
							{{ [ticket.ticket_type, ...ticket.add_ons].filter(Boolean).join(" · ") }}
						</span>
					</span>
					<Badge v-if="ticket.checked_in" variant="subtle" theme="green" label="Checked in" />
				</RouterLink>
			</li>
		</ul>
	</TransactionSection>
</template>
