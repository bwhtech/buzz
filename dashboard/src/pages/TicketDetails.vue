<template>
	<div class="mb-6">
		<BackButton :to="{ name: 'tickets-list' }" :label="__('Back to My Tickets')" />
	</div>

	<div class="w-4" v-if="ticketDetails.loading">
		<Spinner />
	</div>

	<div v-else-if="ticketDetails.data">
		<div class="flex justify-between items-start mb-6">
			<div>
				<h2 class="text-ink-gray-9 font-semibold text-lg mb-1">
					{{ __("Ticket Details") }}
					<span class="text-ink-gray-5 font-mono">(#{{ ticketId }})</span>
				</h2>
			</div>

			<!-- Actions moved to top right -->
			<div class="flex gap-2">
				<Button
					variant="outline"
					:link="`/api/method/frappe.utils.print_format.download_pdf?doctype=Event%20Ticket&name=${ticketId}&format=Buzz%20Print%20Format&no_letterhead=1&letterhead=No%20Letterhead&settings=%7B%7D&_lang=en&pdf_generator=wkhtmltopdf`"
					:loading="downloadingTicket"
					size="sm"
				>
					<template #prefix>
						<LucideDownload class="w-4 h-4" />
					</template>
					{{ __("Download") }}
				</Button>

				<Button
					v-if="canTransferTicket"
					variant="outline"
					@click="showTransferDialog = true"
					size="sm"
				>
					<template #prefix>
						<LucideUserPlus class="w-4 h-4" />
					</template>
					{{ __("Transfer") }}
				</Button>
			</div>
		</div>

		<div
			v-if="hasCustomizableAddOns && !canChangeAddOns"
			class="mb-4 bg-surface-amber-1 border border-outline-amber-1 rounded-lg p-4"
		>
			<div class="flex items-center">
				<LucideTriangleAlert class="w-5 h-5 text-ink-amber-2 mr-3" />
				<div>
					<p class="text-ink-amber-3 text-sm">
						<strong>{{
							__("Add-on preference changes are no longer available")
						}}</strong>
						- {{ __("The change window has closed as the event is approaching.") }}
					</p>
				</div>
			</div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Ticket Information -->
			<div class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">
					{{ __("Ticket Information") }}
				</h3>

				<div class="space-y-3">
					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Attendee Name")
						}}</label>
						<p class="text-ink-gray-9">{{ ticketDetails.data.doc.attendee_name }}</p>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Attendee Email")
						}}</label>
						<p class="text-ink-gray-9">{{ ticketDetails.data.doc.attendee_email }}</p>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Event")
						}}</label>
						<p class="text-ink-gray-9">{{ ticketDetails.data.doc.event_title }}</p>
					</div>

					<div
						v-if="
							!['Default', 'Normal'].includes(
								ticketDetails.data.doc.ticket_type_title
							)
						"
					>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Ticket Type")
						}}</label>
						<p class="text-ink-gray-9">
							{{ ticketDetails.data.doc.ticket_type_title }}
						</p>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Status")
						}}</label>
						<Badge
							:theme="getTicketStatusTheme(ticketDetails.data.doc.ticket_status)"
							variant="subtle"
							size="md"
						>
							{{ ticketDetails.data.doc.ticket_status }}
						</Badge>
					</div>
				</div>
			</div>

			<!-- QR Code Display -->
			<div
				v-if="ticketDetails.data.doc.qr_code"
				class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6"
			>
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">{{ __("QR Code") }}</h3>
				<div class="flex justify-center">
					<img
						:src="ticketDetails.data.doc.qr_code"
						:alt="__('Ticket QR Code')"
						:title="__('Click to enlarge')"
						class="max-w-48 h-auto border border-outline-gray-1 rounded contrast-100 brightness-100 cursor-pointer hover:opacity-80 transition-opacity"
						@click="showQRExpanded = true"
					/>
				</div>
			</div>

			<!-- Add-ons Information -->
			<div
				v-if="ticketDetails.data.add_ons && ticketDetails.data.add_ons.length > 0"
				class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6"
			>
				<div class="flex justify-between items-center mb-4">
					<h3 class="text-ink-gray-8 font-semibold text-lg">{{ __("Add-ons") }}</h3>
					<Button
						v-if="hasCustomizableAddOns && canChangeAddOns"
						variant="outline"
						@click="showAddOnPreferenceDialog = true"
						size="sm"
					>
						<template #prefix>
							<LucideEdit class="w-4 h-4" />
						</template>
						{{ __("Edit") }}
					</Button>
				</div>

				<div class="space-y-3">
					<div
						v-for="addon in ticketDetails.data.add_ons"
						:key="addon.name"
						class="flex justify-between items-center p-3 bg-surface-gray-1 rounded-lg"
					>
						<div>
							<p class="font-medium text-ink-gray-9">
								{{ addon.title || addon.name }}
							</p>
							<p v-if="addon.user_selects_option" class="text-sm text-ink-gray-6">
								{{ addon.value }}
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Event Information -->
			<div class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">
					{{ __("Event Information") }}
				</h3>

				<div class="space-y-3">
					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Start Date")
						}}</label>
						<p class="text-ink-gray-9">
							{{ ticketDetails.data.doc.formatted_start_date }}
						</p>
					</div>

					<div v-if="ticketDetails.data.doc.formatted_end_date">
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("End Date")
						}}</label>
						<p class="text-ink-gray-9">
							{{ ticketDetails.data.doc.formatted_end_date }}
						</p>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Venue")
						}}</label>
						<p class="text-ink-gray-9">{{ ticketDetails.data.doc.venue }}</p>
					</div>

					<div v-if="ticketDetails.data.doc.description">
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Description")
						}}</label>
						<p class="text-ink-gray-9">{{ ticketDetails.data.doc.description }}</p>
					</div>
				</div>
			</div>

			<!-- Zoom Webinar Access (only shown if webinar is linked) -->
			<div
				v-if="ticketDetails.data.zoom_join_url"
				class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6"
			>
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">
					{{ __("Webinar Access") }}
				</h3>

				<div class="space-y-3">
					<p class="text-sm text-ink-gray-6">
						{{ __("Click the button below to join the webinar on Zoom.") }}
					</p>
					<a
						:href="ticketDetails.data.zoom_join_url"
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-2 px-4 py-2 bg-ink-blue-3 text-surface-white rounded-lg hover:bg-ink-blue-4 transition-colors"
					>
						<span>{{ __("Join Zoom Webinar") }}</span>
						<LucideExternalLink class="w-4 h-4" />
					</a>
				</div>
			</div>

			<!-- Booking Information (only shown if user owns the booking) -->
			<div
				v-if="ticketDetails.data.booking"
				class="bg-surface-cards border border-outline-gray-1 rounded-lg p-6"
			>
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">
					{{ __("Booking Information") }}
				</h3>

				<div class="space-y-3">
					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Booking ID")
						}}</label>
						<RouterLink
							:to="{
								name: 'booking-details',
								params: { bookingId: ticketDetails.data.doc.booking },
							}"
							class="text-ink-blue-link hover:underline"
						>
							#{{ ticketDetails.data.doc.booking }}
						</RouterLink>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Booking Status")
						}}</label>
						<Badge
							:theme="
								ticketDetails.data.doc.booking_status === 'Confirmed'
									? 'green'
									: 'red'
							"
							variant="subtle"
							size="md"
						>
							{{ ticketDetails.data.doc.booking_status }}
						</Badge>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Total Amount")
						}}</label>
						<p class="text-ink-gray-9">
							{{ ticketDetails.data.doc.formatted_amount }}
						</p>
					</div>

					<div>
						<label class="block text-sm font-medium text-ink-gray-6">{{
							__("Booked On")
						}}</label>
						<p class="text-ink-gray-9">
							{{ ticketDetails.data.doc.formatted_creation }}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Ticket Transfer Dialog -->
		<TicketTransferDialog
			v-model="showTransferDialog"
			:ticket="ticketDetails.data.doc"
			@success="onTicketTransferSuccess"
		/>

		<!-- Add-on Preference Dialog -->
		<AddOnPreferenceDialog
			v-model="showAddOnPreferenceDialog"
			:ticket="{ ...ticketDetails.data.doc, add_ons: ticketDetails.data.add_ons }"
			@success="onAddOnPreferenceSuccess"
		/>

		<!-- QR Code Expand Dialog -->
		<QRCodeExpandDialog
			v-model="showQRExpanded"
			:qrCodeSrc="ticketDetails.data.doc.qr_code"
			:altText="__('Ticket QR Code')"
		/>
	</div>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils/currency";
import { Badge, Button, Spinner, createResource } from "frappe-ui";
import { dayjsLocal } from "frappe-ui";
import { computed, ref } from "vue";
import LucideDownload from "~icons/lucide/download";
import LucideEdit from "~icons/lucide/edit";
import LucideExternalLink from "~icons/lucide/external-link";
import LucideTriangleAlert from "~icons/lucide/triangle-alert";
import LucideUserPlus from "~icons/lucide/user-plus";
import AddOnPreferenceDialog from "../components/AddOnPreferenceDialog.vue";
import QRCodeExpandDialog from "../components/QRCodeExpandDialog.vue";
import TicketTransferDialog from "../components/TicketTransferDialog.vue";
import BackButton from "../components/common/BackButton.vue";

const props = defineProps({
	ticketId: {
		type: String,
		required: true,
	},
});

// Helper function to format date and time together
const formatEventDateTime = (date: string, time: string) => {
	if (!date) return "";

	// Create a date object from the date string
	const dateObj = dayjsLocal(date);

	// If time is provided, combine it with the date
	if (time) {
		// Parse the time (format: "HH:mm:ss")
		const [hours, minutes] = time.split(":");
		const dateTimeObj = dateObj.hour(Number.parseInt(hours)).minute(Number.parseInt(minutes));
		return dateTimeObj.format("MMMM DD, YYYY [at] h:mm A");
	}

	// If no time, just show the date
	return dateObj.format("MMMM DD, YYYY");
};

const downloadingTicket = ref(false);
const showTransferDialog = ref(false);
const showAddOnPreferenceDialog = ref(false);
const showQRExpanded = ref(false);

const ticketDetails = createResource({
	url: "buzz.api.get_ticket_details",
	params: { ticket_id: props.ticketId },
	auto: true,
	transform(data: any) {
		if (!data) return null;

		return {
			...data,
			// Transform the main ticket document
			doc: {
				...data.doc,
				formatted_amount:
					data.booking && data.booking.total_amount !== 0
						? formatCurrency(data.booking.total_amount, data.booking.currency || "USD")
						: "FREE",
				booking_status: data.booking
					? data.booking.docstatus === 1
						? __("Confirmed")
						: __("Cancelled")
					: __("Unknown"),
				ticket_status: data.booking
					? data.booking.docstatus === 1
						? __("Confirmed")
						: __("Cancelled")
					: __("Unknown"),
				formatted_start_date: data.event?.start_date
					? formatEventDateTime(data.event.start_date, data.event.start_time)
					: "",
				formatted_end_date: data.event?.end_date
					? formatEventDateTime(data.event.end_date, data.event.end_time)
					: null,
				formatted_creation: dayjsLocal(data.doc.creation).format(
					"MMMM DD, YYYY [at] h:mm A"
				),
				event_title: data.event?.title || "",
				venue: data.event?.venue || "",
				description: data.event?.description || "",
				ticket_type_title: data.ticket_type?.title || data.doc.ticket_type,
			},
			// Add-ons with proper titles
			add_ons: data.add_ons || [],
			event: data.event,
			booking: data.booking,
			ticket_type: data.ticket_type,
			can_transfer_ticket: data.can_transfer_ticket?.can_transfer || false,
		};
	},
});

const canTransferTicket = computed(() => {
	if (!ticketDetails.data) return false;
	return (
		ticketDetails.data.doc.booking_status === "Confirmed" &&
		ticketDetails.data.can_transfer_ticket
	);
});

const hasCustomizableAddOns = computed(() => {
	if (!ticketDetails.data?.add_ons) {
		console.log("No add_ons data found:", ticketDetails.data);
		return false;
	}

	console.log("Add-ons data:", ticketDetails.data.add_ons);
	const hasCustomizable = ticketDetails.data.add_ons.some((addon: any) => {
		console.log(
			"Checking addon:",
			addon,
			"has options:",
			addon.options && addon.options.length > 0
		);
		return addon.options && addon.options.length > 0;
	});
	console.log("Has customizable add-ons:", hasCustomizable);
	return hasCustomizable;
});

const canChangeAddOns = computed(() => {
	if (!ticketDetails.data) return false;
	return (
		ticketDetails.data.doc.booking_status === "Confirmed" &&
		ticketDetails.data.can_change_add_ons?.can_change_add_ons
	);
});

const getTicketStatusTheme = (status: string) => {
	switch (status) {
		case "Confirmed":
		case "Active":
			return "green";
		case "Cancelled":
			return "red";
		case "Transferred":
			return "blue";
		default:
			return "gray";
	}
};

const onTicketTransferSuccess = () => {
	ticketDetails.reload();
};

const onAddOnPreferenceSuccess = () => {
	ticketDetails.reload();
};

const downloadTicket = async () => {
	downloadingTicket.value = true;
	try {
		// Implementation for downloading ticket
		// This would typically call an API endpoint that generates a PDF ticket
		console.log("Downloading ticket:", props.ticketId);
		// await createResource({
		//   url: "buzz.api.download_ticket",
		//   params: { ticket_id: props.ticketId }
		// }).fetch();
	} catch (error) {
		console.error("Error downloading ticket:", error);
	} finally {
		downloadingTicket.value = false;
	}
};
</script>
