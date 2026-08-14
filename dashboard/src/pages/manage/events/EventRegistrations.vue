<script setup lang="ts">
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue";
import EventRegistrationDialog from "@/components/dashboard/events/EventRegistrationDialog.vue";
import EventToggleTile from "@/components/dashboard/events/EventToggleTile.vue";
import GuestRegistrationDialog from "@/components/dashboard/events/GuestRegistrationDialog.vue";
import TicketTypeDialog from "@/components/dashboard/events/TicketTypeDialog.vue";
import { eventDetail } from "@/data/events";
import { useEventTicketTypes } from "@/data/tickets";
import { formatPriceOrFree } from "@/utils/currency";
import { Button, LoadingText } from "frappe-ui";
import { ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = route.params.eventId as string;

const event = eventDetail(eventId);
const ticketTypes = useEventTicketTypes(eventId);

const editingRegistration = ref(false);
const editingGuestRegistration = ref(false);
const addingTicketType = ref(false);
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
					@click="addingTicketType = true"
				/>
			</div>

			<LoadingText v-if="ticketTypes.loading" text="Loading ticket types…" />

			<ul
				v-else-if="ticketTypes.data?.length"
				aria-label="Ticket types"
				class="divide-y divide-outline-gray-1 overflow-hidden rounded-xl border border-outline-gray-2"
			>
				<li
					v-for="ticketType in ticketTypes.data"
					:key="ticketType.name"
					class="flex items-baseline gap-2 px-4 py-3"
				>
					<span class="text-base font-medium text-ink-gray-9">{{
						ticketType.title
					}}</span>
					<span class="text-base text-ink-gray-5">
						{{ formatPriceOrFree(ticketType.price, ticketType.currency) }}
					</span>
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
		v-model="addingTicketType"
		:event="eventId"
		:insert="ticketTypes.insert.submit"
	/>
</template>
