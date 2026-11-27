<script setup lang="ts">
import { Button, Dropdown, Tooltip } from "frappe-ui"
import { useRouter } from "vue-router"

import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { TransactionDetail, TransactionTicket } from "@/types"

const props = defineProps<{
	transaction: TransactionDetail
	event: string
	// download_tickets reads the booking itself, which takes guests access.
	canDownloadAll: boolean
}>()

const router = useRouter()
const copy = useCopyToClipboard()

const guests = (query: Record<string, string>) => ({
	path: `/manage/events/${props.event}/guests`,
	query,
})
const ticketUrl = (ticket: TransactionTicket) =>
	`/api/v2/method/buzz.api.transactions.download_ticket?event=${encodeURIComponent(props.event)}&ticket=${encodeURIComponent(ticket.name)}`
const allTicketsUrl = () =>
	`/api/v2/method/buzz.api.booking.download_tickets?booking_id=${encodeURIComponent(props.transaction.name)}`

const guestName = (ticket: TransactionTicket) =>
	ticket.attendee_name || ticket.attendee_email || "Unnamed guest"

const actions = (ticket: TransactionTicket) => [
	{
		label: "Open guest",
		icon: "lucide-user-round",
		onClick: () => router.push(guests({ guest: ticket.name })),
	},
	{
		label: "Find in guest list",
		icon: "lucide-list-filter",
		onClick: () => router.push(guests({ q: ticket.name })),
	},
	{
		label: "Download ticket",
		icon: "lucide-download",
		onClick: () => window.open(ticketUrl(ticket)),
	},
	{
		label: "Copy ticket ID",
		icon: "lucide-copy",
		onClick: () => copy(ticket.name, "Ticket ID copied"),
	},
]
</script>

<template>
	<CollapsibleCard
		icon="lucide-ticket"
		title="Tickets"
		:summary="`${transaction.tickets.length} ${transaction.tickets.length === 1 ? 'ticket' : 'tickets'}`"
	>
		<ul class="px-2 py-2">
			<li
				v-for="ticket in transaction.tickets"
				:key="ticket.name"
				class="row flex items-center gap-3 rounded-4 px-2 py-2 transition-colors hover:bg-surface-gray-1"
			>
				<span class="lucide-ticket size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
				<RouterLink
					:to="guests({ guest: ticket.name })"
					class="min-w-0 flex-1 rounded-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				>
					<span class="flex items-baseline gap-2">
						<span class="truncate text-base text-ink-gray-9">{{ guestName(ticket) }}</span>
						<span class="shrink-0 font-mono text-xs text-ink-gray-5">{{ ticket.name }}</span>
					</span>
					<span class="block truncate text-sm text-ink-gray-5">
						{{ [ticket.ticket_type, ...ticket.add_ons].filter(Boolean).join(" · ") }}
					</span>
				</RouterLink>
				<span
					v-if="ticket.checked_in"
					class="flex shrink-0 items-center gap-1 text-sm text-ink-gray-6"
				>
					<span class="lucide-circle-check size-3.5 text-ink-green-3" aria-hidden="true" />Checked
					in
				</span>
				<Tooltip text="Download ticket">
					<Button
						class="row-action"
						variant="ghost"
						size="sm"
						icon="lucide-download"
						:aria-label="`Download ticket ${ticket.name}`"
						:href="ticketUrl(ticket)"
					/>
				</Tooltip>
				<Dropdown :options="actions(ticket)" align="end">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-ellipsis"
						:aria-label="`More actions for ${guestName(ticket)}`"
					/>
				</Dropdown>
			</li>
		</ul>
		<div v-if="canDownloadAll && transaction.tickets.length > 1" class="px-2 pb-2">
			<Button
				variant="ghost"
				size="sm"
				icon-left="lucide-download"
				label="Download all"
				:href="allTicketsUrl()"
			/>
		</div>
	</CollapsibleCard>
</template>

<style scoped>
@media (hover: hover) and (pointer: fine) {
	.row-action {
		opacity: 0;
		transition: opacity 120ms ease;
	}

	.row:hover .row-action,
	.row-action:focus-visible {
		opacity: 1;
	}
}
</style>
