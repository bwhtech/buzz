<script setup lang="ts">
import { Badge, Button, Spinner, TabButtons, dayjs, toast } from "frappe-ui"
import { computed, ref } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import BookingSummary from "@/components/dashboard/events/BookingSummary.vue"
import TicketAddOnList from "@/components/dashboard/tickets/TicketAddOnList.vue"
import { useBookingSummary } from "@/data/bookings"
import { useTicketDetails } from "@/data/tickets"
import type { TicketWithEvent } from "@/types"
import { copyEventUrl, eventUrl } from "@/utils/eventUrl"
import { ticketPdfUrl } from "@/utils/ticketPdf"

const props = defineProps<{ ticket: TicketWithEvent | null }>()

const open = defineModel<boolean>("open", { required: true })

const details = useTicketDetails(() => props.ticket?.name)

const panel = ref<"ticket" | "booking">("ticket")
const panels = [
	{ label: "Ticket", value: "ticket" },
	{ label: "Booking", value: "booking" },
]

const doc = computed(() => details.data?.doc)
const event = computed(() => details.data?.event)
const addOns = computed(() => details.data?.add_ons || [])

// The details call only returns the booking to whoever paid, so the buyer's name comes
// from there; the receipt below is fetched on read permission instead.
const booking = computed(() => details.data?.booking || null)

const bookingSummary = useBookingSummary(() => doc.value?.booking || undefined)

// A ticket issued outside a booking has no buyer at all, which is not the same as one
// booked by somebody else.
const bookedBy = computed(() => {
	if (!doc.value?.booking) return null
	return booking.value?.user || booking.value?.owner || "Someone else"
})
const bookedByHolder = computed(
	() => Boolean(doc.value?.attendee_email) && bookedBy.value === doc.value?.attendee_email,
)

const rows = computed(() => [
	{ label: "Email", value: doc.value?.attendee_email },
	{ label: "Tier", value: details.data?.ticket_type?.title || props.ticket?.ticket_type },
	{
		label: "Issued",
		value: doc.value ? dayjs(doc.value.creation).format("D MMM YYYY, HH:mm") : "",
	},
])

async function copyLink() {
	const route = event.value?.route
	if (!route) return
	try {
		await copyEventUrl(route)
		toast.success("Event link copied")
	} catch {
		// Clipboard access is refused outside a secure context, and on an http:// host
		// in development that is every time.
		toast.error("Could not copy the link")
	}
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="ticket">
				<!-- These wire the drawer's aria-labelledby and aria-describedby, so they stay
				     mounted whichever tab is open. -->
				<DrawerTitle class="sr-only">
					Ticket for {{ ticket.attendee_name }}, {{ ticket.event_title }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">
					Ticket #{{ ticket.name }}. Show the QR code at the door.
				</DrawerDescription>

				<div class="flex gap-2 p-2">
					<DrawerClose as-child>
						<Button size="sm" icon="lucide-chevrons-right" aria-label="Close" />
					</DrawerClose>

					<template v-if="event?.route">
						<Button size="sm" label="Copy Link" icon-left="lucide-copy" @click="copyLink" />
						<Button
							size="sm"
							label="Event Page"
							icon-right="lucide-arrow-up-right"
							:link="eventUrl(event.route)"
						/>
					</template>
				</div>

				<div class="px-4 pb-2">
					<TabButtons v-model="panel" :options="panels" size="md" />
				</div>

				<div class="flex-1 overflow-y-auto">
					<template v-if="panel === 'ticket'">
						<!-- The stub, as printed: holder on top, tear line, then the code to scan. -->
						<div class="m-4 overflow-hidden rounded-6 border border-outline-gray-2">
							<div class="flex flex-col gap-2 p-4">
								<div class="flex items-start justify-between gap-3">
									<h2 class="text-2xl font-semibold text-ink-gray-9">
										{{ ticket.attendee_name }}
									</h2>
									<Badge variant="subtle" size="lg" class="font-mono">#{{ ticket.name }}</Badge>
								</div>
								<div class="flex flex-wrap gap-2">
									<Badge variant="subtle" size="lg">{{ ticket.ticket_type }}</Badge>
									<Badge v-if="addOns.length" theme="violet" variant="subtle" size="lg">
										+ {{ addOns.length }} add-on{{ addOns.length > 1 ? "s" : "" }}
									</Badge>
								</div>
							</div>

							<div class="tear-line" />

							<div class="flex flex-col items-center gap-2 p-4">
								<div
									class="grid aspect-square w-full place-items-center rounded-6 border border-outline-gray-2"
								>
									<img
										v-if="doc?.qr_code"
										class="h-full w-full object-contain p-6"
										:src="doc.qr_code"
										:alt="`QR code for ticket ${ticket.name}`"
									/>
									<Spinner v-else-if="details.loading" class="size-5" />
									<span v-else class="text-p-base text-ink-gray-5">No QR code on this ticket</span>
								</div>
								<p class="font-mono text-p-base tracking-widest text-ink-gray-8">
									{{ ticket.name }}
								</p>
								<p class="text-p-sm text-ink-gray-5">Show this at the door</p>
							</div>
						</div>

						<div class="flex flex-col gap-2 px-4 pb-4">
							<h3 class="text-p-xs uppercase tracking-wide text-ink-gray-5">Ticket holder</h3>
							<dl
								class="flex flex-col divide-y divide-outline-gray-1 border-t border-outline-gray-1"
							>
								<div v-for="row in rows" :key="row.label" class="flex gap-4 py-2">
									<dt class="w-24 shrink-0 text-p-base text-ink-gray-5">{{ row.label }}</dt>
									<dd class="min-w-0 flex-1 text-p-base text-ink-gray-8">{{ row.value || "—" }}</dd>
								</div>
								<div class="flex items-center gap-4 py-2">
									<dt class="w-24 shrink-0 text-p-base text-ink-gray-5">Booked by</dt>
									<dd class="flex min-w-0 flex-1 items-center gap-2 text-p-base text-ink-gray-8">
										<span class="truncate">{{ bookedBy || "—" }}</span>
										<Badge v-if="bookedBy && !bookedByHolder" variant="subtle" size="sm">
											Not the holder
										</Badge>
									</dd>
								</div>
							</dl>
						</div>

						<TicketAddOnList :add-ons="addOns" />
					</template>

					<div v-else class="p-4">
						<Spinner v-if="bookingSummary.loading" class="size-4" />
						<BookingSummary
							v-else-if="bookingSummary.data"
							:booking="bookingSummary.data"
							show-id
						/>
						<p v-else-if="bookingSummary.error" class="text-p-base text-ink-gray-5">
							You are not allowed to view this booking.
						</p>
						<p v-else class="text-p-base text-ink-gray-5">No booking is attached to this ticket.</p>
					</div>
				</div>

				<div v-if="panel === 'ticket'" class="border-t border-outline-gray-1 p-4">
					<Button
						v-if="doc"
						class="w-full"
						variant="outline"
						size="md"
						label="Ticket PDF"
						icon-left="lucide-download"
						:link="ticketPdfUrl(ticket.name, event?.ticket_print_format)"
					/>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
/* The tear across the stub, with a notch bitten out of each edge. */
.tear-line {
	height: 1px;
	background: repeating-linear-gradient(90deg, var(--outline-gray-3) 0 6px, transparent 6px 12px);
	mask-image:
		radial-gradient(circle 7px at 0 50%, transparent 6px, black 7px),
		radial-gradient(circle 7px at 100% 50%, transparent 6px, black 7px);
	mask-composite: intersect;
	-webkit-mask-image:
		radial-gradient(circle 7px at 0 50%, transparent 6px, black 7px),
		radial-gradient(circle 7px at 100% 50%, transparent 6px, black 7px);
	-webkit-mask-composite: source-in;
}
</style>
