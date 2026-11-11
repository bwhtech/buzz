<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { computed } from "vue"

import MyTicket from "@/components/dashboard/tickets/MyTicket.vue"
import TicketBookingDetails from "@/components/dashboard/tickets/TicketBookingDetails.vue"
import { useMyBookings } from "@/data/bookings"
import { useMyTickets } from "@/data/tickets"
import { userResource } from "@/data/user"
import type { MyBooking, MyEvent, TicketWithEvent } from "@/types"

const props = defineProps<{ event: MyEvent }>()

const tickets = useMyTickets(() => props.event.name)
const bookings = useMyBookings(() => props.event.name)

// A ticket whose event columns did not come over the link hop has nothing to print.
// The venue is two hops away, and the feed row already carries it.
const myTickets = computed(() =>
	(tickets.data || [])
		.map((ticket) => ({ ...ticket, venue: props.event.venue }))
		.filter((ticket): ticket is TicketWithEvent =>
			Boolean(ticket.start_date && ticket.event_title),
		),
)

// A draft is a booking only while an offline payment waits on approval or while it is a
// registration request; any other draft is a checkout that never reached the gateway's end.
const isListedBooking = (booking: MyBooking) =>
	booking.docstatus !== 0 ||
	Boolean(booking.request_type) ||
	(booking.status === "Approval Pending" && booking.payment_method === "Offline")

const myBookingNames = computed(() =>
	(bookings.data || []).filter(isListedBooking).map((booking) => booking.name),
)

// Bookings with none of the user's tickets in them — pending, rejected, cancelled or bought
// for others — still get their receipt, on their own.
const bookingsWithoutTickets = computed(() =>
	myBookingNames.value.filter((name) => !myTickets.value.some((ticket) => ticket.booking === name)),
)

// The feed row already says the viewer is attending, so the section can hold its place
// while the calls are still out and the drawer stops jumping.
const ticketsPending = computed(
	() =>
		Boolean(props.event.is_attendee) &&
		(tickets.loading || bookings.loading) &&
		!myTickets.value.length &&
		!bookingsWithoutTickets.value.length,
)

const hasTickets = computed(() => Boolean(myTickets.value.length || ticketsPending.value))

// Several tickets can share one booking; the receipt goes under the first of them rather
// than repeating, call and all, beneath every ticket.
function ownsBookingReceipt(ticket: TicketWithEvent, index: number) {
	if (!ticket.booking) return false
	return myTickets.value.findIndex((row) => row.booking === ticket.booking) === index
}

function reload() {
	tickets.reload()
	bookings.reload()
}

const greeting = computed(() => {
	const name = userResource.data?.first_name || userResource.data?.full_name
	return name ? `You're in, ${name}` : "You're in"
})
</script>

<template>
	<div
		v-if="hasTickets || bookingsWithoutTickets.length"
		class="space-y-3 rounded-6 bg-surface-gray-1 p-4"
	>
		<h3 v-if="hasTickets" class="flex items-center gap-2 text-xl font-semibold text-ink-gray-7">
			{{ greeting }}
		</h3>
		<h3 v-else class="text-xl font-semibold text-ink-gray-7">Your bookings</h3>

		<div v-if="ticketsPending" class="space-y-3">
			<div class="flex gap-2">
				<Skeleton class="h-7 w-28 rounded-md" />
				<Skeleton class="h-7 w-7 rounded-md" />
			</div>
			<Skeleton class="h-40 w-full rounded-6" />
		</div>

		<template v-else>
			<MyTicket
				v-for="(ticket, index) in myTickets"
				:key="ticket.name"
				:ticket="ticket"
				:show-receipt="ownsBookingReceipt(ticket, index)"
				:is-booker="myBookingNames.includes(ticket.booking!)"
				@transferred="reload"
			/>
			<TicketBookingDetails
				v-for="booking in bookingsWithoutTickets"
				:key="booking"
				:booking="booking"
				is-booker
			/>
		</template>
	</div>
</template>
