<script setup lang="ts">
import { Avatar, Badge, Button, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { EventGuest, EventGuests, TicketWithEvent } from "@/types"

const props = defineProps<{
	guest: EventGuest | null
	event: EventGuests | null
	hasPrevious: boolean
	hasNext: boolean
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ previous: []; next: [] }>()

const copyToClipboard = useCopyToClipboard()

// A ticket can be issued before anyone is named on it, so the email stands in.
const name = computed(
	() => props.guest?.attendee_name || props.guest?.attendee_email || "Unnamed guest",
)

// "3 Sep 2026, 4:30 PM", with how long ago that was on hover — the same readout the
// event header gives for a modified date.
const registeredAt = computed(() =>
	props.guest?.registered_at ? dayjsLocal(props.guest.registered_at) : null,
)

// The row is a ticket, so the drawer opens on the paper rather than on a field list.
// Drawn only once the event carries a title and a date — PrintedTicket has nothing to
// print without them.
const ticket = computed<TicketWithEvent | null>(() => {
	const event = props.event
	if (!props.guest || !event?.title || !event.start_date) return null

	return {
		name: props.guest.name,
		attendee_name: name.value,
		attendee_email: props.guest.attendee_email,
		ticket_type: props.guest.ticket_type || "",
		qr_code: null,
		booking: null,
		event_title: event.title,
		start_date: event.start_date,
		start_time: event.start_time,
		end_date: event.end_date,
		venue: event.venue,
	}
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<template v-if="guest">
				<div class="flex items-center gap-1 p-4 pb-0">
					<DrawerClose as-child>
						<Button size="sm" icon="lucide-chevrons-right" aria-label="Close guest" />
					</DrawerClose>

					<!-- Paging sits at the far end, so the list can be walked without going back
					     to it: the row under the pointer is never the one that closes the panel. -->
					<div class="ml-auto flex items-center gap-1">
						<Tooltip text="Previous guest">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-up"
								aria-label="Previous guest"
								:disabled="!hasPrevious"
								@click="emit('previous')"
							/>
						</Tooltip>
						<Tooltip text="Next guest">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-down"
								aria-label="Next guest"
								:disabled="!hasNext"
								@click="emit('next')"
							/>
						</Tooltip>
					</div>
				</div>

				<div class="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
					<PrintedTicket v-if="ticket" :ticket="ticket" static />

					<div class="flex items-center gap-3">
						<Avatar :label="name" size="2xl" />
						<div class="min-w-0 space-y-1">
							<DrawerTitle class="truncate text-xl font-semibold text-ink-gray-9">
								{{ name }}
							</DrawerTitle>
							<DrawerDescription class="truncate text-base text-ink-gray-5">
								{{ guest.attendee_email || "No email on this ticket" }}
							</DrawerDescription>
						</div>
					</div>

					<dl class="space-y-3 text-base">
						<div class="flex items-baseline gap-3">
							<dt class="w-24 shrink-0 text-ink-gray-5">Ticket type</dt>
							<dd class="min-w-0">
								<Badge v-if="guest.ticket_type" variant="subtle" :label="guest.ticket_type" />
								<span v-else class="text-ink-gray-5">—</span>
							</dd>
						</div>

						<div class="flex items-baseline gap-3">
							<dt class="w-24 shrink-0 text-ink-gray-5">Email</dt>
							<dd class="min-w-0">
								<button
									v-if="guest.attendee_email"
									type="button"
									class="max-w-full cursor-copy truncate text-ink-gray-8"
									:aria-label="`Copy email ${guest.attendee_email}`"
									@click="copyToClipboard(guest.attendee_email, 'Email copied')"
								>
									{{ guest.attendee_email }}
								</button>
								<span v-else class="text-ink-gray-5">—</span>
							</dd>
						</div>

						<div class="flex items-baseline gap-3">
							<dt class="w-24 shrink-0 text-ink-gray-5">Ticket ID</dt>
							<dd class="min-w-0">
								<button
									type="button"
									class="cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-8"
									:aria-label="`Copy ticket id ${guest.name}`"
									@click="copyToClipboard(guest.name, 'Ticket ID copied')"
								>
									{{ guest.name }}
								</button>
							</dd>
						</div>

						<div class="flex items-baseline gap-3">
							<dt class="w-24 shrink-0 text-ink-gray-5">Registered</dt>
							<dd class="min-w-0 text-ink-gray-8">
								<Tooltip v-if="registeredAt" :text="registeredAt.fromNow()">
									<span>{{ registeredAt.format("D MMM YYYY, h:mm A") }}</span>
								</Tooltip>
								<span v-else class="text-ink-gray-5">—</span>
							</dd>
						</div>

						<div v-if="guest.add_ons.length" class="flex items-baseline gap-3">
							<dt class="w-24 shrink-0 text-ink-gray-5">Add-ons</dt>
							<dd class="flex min-w-0 flex-wrap gap-1.5">
								<Badge
									v-for="addOn in guest.add_ons"
									:key="`${addOn.title}: ${addOn.value}`"
									theme="blue"
									variant="subtle"
									:label="addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title"
								/>
							</dd>
						</div>
					</dl>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
