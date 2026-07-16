<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Request Ticket Cancellation'),
			size: '3xl',
		}"
	>
		<template #body-content>
			<div class="space-y-6">
				<p class="text-ink-gray-7">
					{{
						__(
							"Select the tickets you would like to cancel. Please note that cancellation requests are subject to approval and refund policies."
						)
					}}
				</p>

				<!-- Info about excluded tickets -->
				<div
					v-if="cancelledTickets.length > 0 || cancellationRequestedTickets.length > 0"
					class="p-4 bg-surface-blue-1 border border-outline-blue-1 rounded-lg"
				>
					<p class="text-sm text-ink-blue-2">
						<span v-if="cancelledTickets.length > 0">
							{{ pluralize(cancelledTickets.length, __("ticket")) }}
							{{ __("already cancelled") }}.
						</span>
						<span
							v-if="
								cancelledTickets.length > 0 &&
								cancellationRequestedTickets.length > 0
							"
						>
							<br />
						</span>
						<span v-if="cancellationRequestedTickets.length > 0">
							{{ pluralize(cancellationRequestedTickets.length, __("ticket")) }}
							{{ __("already have pending cancellation requests") }}.
						</span>
					</p>
				</div>

				<!-- Select All Option -->
				<div
					v-if="availableTickets.length > 0"
					class="border border-outline-gray-2 rounded-lg p-4 cursor-pointer transition-all hover:border-outline-gray-3 hover:bg-surface-gray-1"
					:class="{
						'border-outline-gray-4 bg-surface-gray-2': isAllSelected,
					}"
					@click="toggleSelectAll"
				>
					<div class="flex items-center space-x-3">
						<input
							type="checkbox"
							:checked="isAllSelected"
							@change="toggleSelectAll"
							class="h-4 w-4 text-ink-gray-6 border-outline-gray-1 rounded focus:ring-ink-gray-5"
						/>
						<div>
							<h3 class="font-semibold text-ink-gray-9">
								{{ __("Select All Available Tickets") }}
							</h3>
							<p class="text-sm text-ink-gray-6">
								{{ __("Cancel all") }}
								{{ pluralize(availableTickets.length, __("remaining ticket")) }}
							</p>
						</div>
					</div>
				</div>

				<!-- Individual Ticket Selection -->
				<div class="space-y-4">
					<h4 class="font-medium text-ink-gray-8">
						{{ __("Or select individual tickets:") }}
					</h4>
					<div v-if="availableTickets.length === 0" class="text-center py-8">
						<p class="text-ink-gray-5">
							{{
								__(
									"No tickets available for cancellation. All tickets are either already cancelled or have pending cancellation requests."
								)
							}}
						</p>
					</div>
					<div v-else class="space-y-3 max-h-64 overflow-y-auto">
						<div
							v-for="ticket in availableTickets"
							:key="ticket.name"
							class="border border-outline-gray-2 rounded-lg p-4 cursor-pointer transition-all hover:border-outline-gray-3 hover:bg-surface-gray-1"
							:class="{
								'border-outline-gray-4 bg-surface-gray-2':
									selectedTickets.includes(ticket.name),
							}"
							@click="toggleTicketSelection(ticket.name)"
						>
							<div class="flex items-start space-x-3">
								<input
									type="checkbox"
									:checked="selectedTickets.includes(ticket.name)"
									@change="toggleTicketSelection(ticket.name)"
									class="h-4 w-4 text-ink-gray-6 border-outline-gray-1 rounded focus:ring-ink-gray-5 mt-1"
								/>
								<div class="flex-1">
									<div class="flex items-center justify-between">
										<div>
											<h3 class="font-semibold text-ink-gray-9">
												{{ ticket.attendee_name }}
											</h3>
											<p class="text-sm text-ink-gray-6">
												{{ ticket.attendee_email }}
											</p>
											<p class="text-sm text-ink-gray-5">
												{{ ticket.ticket_type }}
											</p>
										</div>
									</div>

									<!-- Add-ons if any -->
									<div
										v-if="ticket.add_ons && ticket.add_ons.length > 0"
										class="mt-2 pt-2 border-t border-outline-gray-1"
									>
										<p class="text-xs text-ink-gray-5 mb-1">
											{{ __("Add-ons:") }}
										</p>
										<div class="flex flex-wrap gap-1">
											<span
												v-for="addon in ticket.add_ons"
												:key="addon.name"
												class="inline-flex items-center px-2 py-1 rounded-full text-xs bg-surface-gray-1 text-ink-gray-7"
											>
												{{ addon.title }}: {{ addon.value }}
											</span>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Warning if no tickets selected -->
				<div v-if="selectedTickets.length === 0" class="text-center py-4">
					<p class="text-ink-red-3 text-sm">
						{{ __("Please select at least one ticket to cancel.") }}
					</p>
				</div>

				<!-- Summary -->
				<div
					v-if="selectedTickets.length > 0"
					class="p-4 bg-surface-blue-1 border border-outline-blue-1 rounded-lg"
				>
					<div class="flex items-center justify-between">
						<div>
							<h4 class="font-semibold text-ink-blue-2">
								{{ __("Cancellation Summary") }}
							</h4>
							<p class="text-ink-blue-2">
								{{ pluralize(selectedTickets.length, __("ticket")) }}
								{{ __("selected for cancellation") }}
								<span v-if="isAllSelected" class="font-medium">{{
									__("(Full booking)")
								}}</span>
							</p>
						</div>
						<div class="text-right">
							<p class="text-sm text-ink-blue-2">{{ __("Request Type") }}</p>
							<p class="font-medium text-ink-blue-2">
								{{
									isAllSelected
										? __("Full Cancellation")
										: __("Partial Cancellation")
								}}
							</p>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end space-x-3">
				<Button variant="ghost" @click="closeDialog" :loading="submitting">
					{{ __("Cancel") }}
				</Button>
				<Button
					variant="solid"
					@click="submitCancellationRequest"
					:disabled="selectedTickets.length === 0"
					:loading="submitting"
				>
					{{ __("Submit Cancellation Request") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import type { DashboardTicket, FrappeError } from "@/types";
import { pluralize } from "@/utils/pluralize";
import { Button, Dialog, createResource, toast } from "frappe-ui";
import { type PropType, computed, ref, watch } from "vue";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	tickets: {
		type: Array as PropType<DashboardTicket[]>,
		required: true,
	},
	bookingId: {
		type: String,
		required: true,
	},
	cancellationRequestedTickets: {
		type: Array as PropType<string[]>,
		default: () => [],
	},
	cancelledTickets: {
		type: Array as PropType<string[]>,
		default: () => [],
	},
});

const emit = defineEmits(["update:modelValue", "success"]);

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit("update:modelValue", val),
});

// Filter out tickets that are already cancelled or have pending cancellation request
const availableTickets = computed(() => {
	return props.tickets.filter(
		(ticket) =>
			!props.cancelledTickets.includes(ticket.name) &&
			!props.cancellationRequestedTickets.includes(ticket.name)
	);
});

const selectedTickets = ref<string[]>([]);
const submitting = ref(false);

const isAllSelected = computed({
	get: () =>
		selectedTickets.value.length === availableTickets.value.length &&
		availableTickets.value.length > 0,
	set: (val) => {
		if (val) {
			selectedTickets.value = availableTickets.value.map((ticket) => ticket.name);
		} else {
			selectedTickets.value = [];
		}
	},
});

const toggleSelectAll = () => {
	isAllSelected.value = !isAllSelected.value;
};

const toggleTicketSelection = (ticketId: string) => {
	const index = selectedTickets.value.indexOf(ticketId);
	if (index > -1) {
		selectedTickets.value.splice(index, 1);
	} else {
		selectedTickets.value.push(ticketId);
	}
};

const closeDialog = () => {
	show.value = false;
	selectedTickets.value = [];
};

const createCancellationRequest = createResource({
	url: "buzz.api.create_cancellation_request",
	onSuccess: (data: any) => {
		submitting.value = false;
		const ticketCount = selectedTickets.value.length;
		const isFullCancellation = isAllSelected.value;

		toast.success(
			isFullCancellation
				? __("Full booking cancellation request submitted successfully!")
				: `${__("Cancellation request submitted for")} ${pluralize(
						ticketCount,
						__("ticket")
				  )}!`
		);
		emit("success", data);
		closeDialog();
	},
	onError: (error: FrappeError) => {
		submitting.value = false;
		toast.error(
			error?.messages?.[0] || __("Failed to submit cancellation request. Please try again.")
		);
	},
});

const submitCancellationRequest = () => {
	if (selectedTickets.value.length === 0) return;

	submitting.value = true;
	createCancellationRequest.submit({
		booking_id: props.bookingId,
		ticket_ids: selectedTickets.value,
	});
};

// Reset selected tickets when dialog closes
watch(show, (newVal) => {
	if (!newVal) {
		selectedTickets.value = [];
	}
});
</script>
