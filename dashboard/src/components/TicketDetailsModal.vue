<!-- TODO: This component needs a refactor -->
<template>
	<Dialog v-model="showTicketModal">
		<template #title>
			<h3 class="text-lg-semibold text-gray-900 dark:text-white">
				{{ validationResult ? __("Valid Ticket") : __("Invalid Ticket") }}
			</h3>
		</template>

		<!-- Success State -->
		<div v-if="validationResult?.ticket">
			<div class="text-center mb-6">
				<div
					class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<LucideCheckCircle class="w-8 h-8 text-green-600 dark:text-green-400" />
				</div>
				<h4 class="text-lg-semibold text-gray-900 dark:text-white">
					{{ __("Valid Ticket") }}
				</h4>
				<p class="text-gray-600 dark:text-gray-400">{{ __("Ready for check-in") }}</p>
			</div>

			<div class="space-y-4 mb-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<h3 class="text-sm-medium text-gray-700 dark:text-gray-300">
							{{ __("Attendee") }}
						</h3>
						<p class="text-sm text-gray-900 dark:text-white">
							{{ validationResult?.ticket?.attendee_name }}
						</p>
					</div>
					<div>
						<h3 class="text-sm-medium text-gray-700 dark:text-gray-300">
							{{ __("Email") }}
						</h3>
						<p class="text-sm text-gray-900 dark:text-white">
							{{ validationResult?.ticket?.attendee_email }}
						</p>
					</div>
					<div>
						<h3 class="text-sm-medium text-gray-700 dark:text-gray-300">
							{{ __("Ticket Type") }}
						</h3>
						<p class="text-sm text-gray-900 dark:text-white">
							{{ validationResult?.ticket?.ticket_type }}
						</p>
					</div>
					<div>
						<h3 class="text-sm-medium text-gray-700 dark:text-gray-300">
							{{ __("Ticket ID") }}
						</h3>
						<p class="text-sm font-mono text-gray-900 dark:text-white">
							{{ validationResult?.ticket?.id }}
						</p>
					</div>
				</div>

				<!-- Add-ons -->
				<div
					v-if="validationResult?.ticket?.add_ons?.length"
					class="border-t border-gray-200 dark:border-gray-600 pt-4"
				>
					<h3 class="text-sm-medium text-gray-700 dark:text-gray-300 mb-2">
						{{ __("Add-ons") }}
					</h3>
					<div class="space-y-2">
						<div
							v-for="addon in validationResult?.ticket?.add_ons"
							:key="addon.add_on"
							class="flex justify-between text-sm"
						>
							<span class="text-gray-900 dark:text-white"
								>{{ __(addon.add_on_title || addon.add_on) }} ({{
									formatPriceOrFree(addon.price, addon.currency)
								}})</span
							>
							<span class="text-gray-600 dark:text-gray-400">{{ addon.value }}</span>
						</div>
					</div>
				</div>

				<!-- Payment details -->
				<div v-if="validationResult?.payment_details">
					<h3 class="text-sm-medium text-gray-700 dark:text-gray-300">
						{{ __("Payment Details") }}
					</h3>

					<div class="grid grid-cols-2 mt-3 text-sm text-gray-900 dark:text-white">
						<div class="space-y-1">
							<p class="text-sm-medium text-gray-700 dark:text-gray-300">
								{{ __("ID") }}
							</p>
							<p>{{ validationResult?.payment_details?.name }}</p>
						</div>
						<div class="space-y-1">
							<p class="text-sm-medium text-gray-700 dark:text-gray-300">
								{{ __("Amount Paid") }}
							</p>
							<p>
								{{
									formatPriceOrFree(
										validationResult?.payment_details?.amount,
										validationResult?.payment_details?.currency
									)
								}}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Error State -->
		<div v-else>
			<div class="text-center mb-6">
				<div
					class="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
				>
					<LucideXCircle class="w-8 h-8 text-red-600 dark:text-red-400" />
				</div>
				<h4 class="text-lg-semibold text-gray-900 dark:text-white">
					{{ validationResult?.error || "Invalid Ticket" }}
				</h4>
				<p class="text-gray-600 dark:text-gray-400">
					{{ validationResult?.message }}
				</p>
			</div>
		</div>

		<template #actions>
			<div v-if="!validationResult?.ticket?.is_checked_in" class="flex gap-3 flex-col">
				<Button @click="handleCheckIn" :loading="isCheckingIn" class="w-full">
					<template #prefix>
						<LucideUserCheck class="w-4 h-4" />
					</template>
					{{ __("Check In") }}
				</Button>
				<Button @click="handleModalClose" variant="outline" class="w-full">
					{{ __("Cancel") }}
				</Button>
			</div>

			<!-- TODO: I don't understand why this is here. -->
			<div v-else>
				<Button @click="handleModalClose" class="w-full" variant="outline">
					{{ __("Close") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { useTicketValidation } from "@/composables/useTicketValidation";
import { formatPriceOrFree } from "@/utils/currency";
import { Button, Dialog } from "frappe-ui";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideUserCheck from "~icons/lucide/user-check";
import LucideXCircle from "~icons/lucide/x-circle";

const props = defineProps({
	selectedEvent: {
		type: Object,
		default: null,
	},
});

const { showTicketModal, isCheckingIn, validationResult, checkInTicket, closeModal } =
	useTicketValidation();

const handleCheckIn = () => {
	checkInTicket();
};

const handleModalClose = () => {
	closeModal();
};
</script>
