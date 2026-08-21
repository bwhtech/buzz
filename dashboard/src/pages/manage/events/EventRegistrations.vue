<script setup lang="ts">
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue";
import EventRegistrationDialog from "@/components/dashboard/events/EventRegistrationDialog.vue";
import EventToggleTile from "@/components/dashboard/events/EventToggleTile.vue";
import GuestRegistrationDialog from "@/components/dashboard/events/GuestRegistrationDialog.vue";
import TicketTypeDialog from "@/components/dashboard/events/TicketTypeDialog.vue";
import { eventDetail } from "@/data/events";
import { useEventTicketTypes } from "@/data/tickets";
import type { TicketType } from "@/types";
import { formatPriceOrFree } from "@/utils/currency";
import { Badge, Button, LoadingText } from "frappe-ui";
import { ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = route.params.eventId as string;

const event = eventDetail(eventId);
const ticketTypes = useEventTicketTypes(eventId);

const editingRegistration = ref(false);
const editingGuestRegistration = ref(false);
const editingTicketType = ref(false);
// Null while creating; the tier being edited otherwise.
const ticketTypeInEdit = ref<TicketType | null>(null);

function editTicketType(ticketType: TicketType | null) {
	ticketTypeInEdit.value = ticketType;
	editingTicketType.value = true;
}

function saveTicketType(doc: Partial<TicketType> & Record<string, unknown>) {
	return doc.name ? ticketTypes.setValue.submit(doc) : ticketTypes.insert.submit(doc);
}
</script>

<template>
	<EventPageHeader :title="event.data?.title" section="Registrations" />

	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-8">
		<div v-if="event.data" class="grid grid-cols-2 gap-3">
			<EventToggleTile
				icon="lucide-ticket"
				label="Registration"
				:status="event.data.registrations_closed ? 'Closed' : 'Open'"
				@click="editingRegistration = true"
			/>
			<EventToggleTile
				icon="lucide-hat-glasses"
				label="Guest Registration"
				:status="event.data.allow_guest_booking ? 'On' : 'Off'"
				@click="editingGuestRegistration = true"
			/>
		</div>

		<section class="space-y-3">
			<div class="flex items-center justify-between gap-3">
				<h2 class="text-xl font-semibold text-ink-gray-9">Tickets</h2>
				<Button
					variant="subtle"
					icon-left="plus"
					label="New Ticket Type"
					@click="editTicketType(null)"
				/>
			</div>

			<LoadingText v-if="ticketTypes.loading" text="Loading ticket types…" />

			<ul
				v-else-if="ticketTypes.data?.length"
				aria-label="Ticket types"
				class="grid grid-cols-2 gap-3"
			>
				<li v-for="ticketType in ticketTypes.data" :key="ticketType.name">
					<button
						type="button"
						class="w-full space-y-2 rounded-xl border border-outline-gray-2 bg-surface-white p-4 text-left transition-colors hover:border-outline-gray-3"
						@click="editTicketType(ticketType)"
					>
						<Badge
							:theme="ticketType.is_published ? 'green' : 'gray'"
							variant="subtle"
							size="sm"
						>
							{{ ticketType.is_published ? __("Available") : __("Sale Ended") }}
						</Badge>

						<p class="text-lg font-medium text-ink-gray-9">{{ ticketType.title }}</p>

						<span class="flex items-center gap-1.5 text-sm text-ink-gray-6">
							<span class="lucide-banknote size-4" aria-hidden="true" />
							{{ formatPriceOrFree(ticketType.price, ticketType.currency) }}
						</span>
					</button>
				</li>
			</ul>

			<p v-else class="text-base text-ink-gray-5">No ticket types yet.</p>
		</section>
	</div>

	<EventRegistrationDialog
		v-if="event.data"
		v-model="editingRegistration"
		:event="eventId"
		:time-zone="event.data.time_zone"
		:closed="event.data.registrations_closed"
		@saved="event.reload()"
	/>

	<GuestRegistrationDialog
		v-if="event.data"
		v-model="editingGuestRegistration"
		:event="eventId"
		:allowed="event.data.allow_guest_booking"
		:verification="event.data.guest_verification_method"
		@saved="event.reload()"
	/>

	<TicketTypeDialog
		v-model="editingTicketType"
		:event="eventId"
		:tier="ticketTypeInEdit"
		:save="saveTicketType"
	/>
</template>
