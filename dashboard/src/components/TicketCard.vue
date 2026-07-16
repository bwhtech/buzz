<template>
	<li class="shadow-md p-4 rounded-lg bg-surface-white border border-outline-gray-2 relative">
		<!-- Status Badge -->
		<div v-if="isCancelled || isCancellationRequested" class="absolute top-2 left-2">
			<Badge
				v-if="isCancelled"
				variant="outline"
				theme="red"
				size="sm"
				:label="__('Cancelled')"
			/>
			<Badge
				v-else-if="isCancellationRequested"
				variant="subtle"
				theme="orange"
				size="sm"
				:label="__('Cancellation Requested')"
			/>
		</div>

		<!-- Three-dot dropdown menu -->
		<div class="absolute top-2 right-2">
			<Dropdown :options="ticketActions" placement="left" v-if="ticketActions.length > 0">
				<Button variant="ghost" icon="more-horizontal" size="sm" />
			</Dropdown>
		</div>

		<div>
			<h4
				class="text-md font-semibold text-ink-gray-9"
				:class="{ 'mt-6': isCancelled || isCancellationRequested }"
			>
				{{ ticket.attendee_name }}
			</h4>
			<p class="text-sm text-ink-gray-7">{{ __("Email") }}: {{ ticket.attendee_email }}</p>
			<p
				v-if="!['Default', 'Normal'].includes(ticket.ticket_type)"
				class="text-sm text-ink-gray-7"
			>
				{{ __("Ticket Type") }}: {{ ticket.ticket_type }}
			</p>

			<!-- Add-ons Section -->
			<div v-if="ticket.add_ons && ticket.add_ons.length > 0" class="mt-3">
				<h5 class="text-sm font-medium text-ink-gray-8 mb-2">{{ __("Add-ons:") }}</h5>
				<div class="space-y-3">
					<div
						v-for="addon in ticket.add_ons"
						:key="addon.name"
						class="bg-surface-gray-1 px-3 py-2 rounded text-xs"
					>
						<div class="font-medium text-ink-gray-8 mb-1">{{ addon.title }}</div>
						<div v-if="addon.user_selects_option" class="text-ink-gray-7">
							{{ addon.value }}
						</div>
					</div>
				</div>
			</div>

			<div class="mt-3">
				<img
					:src="ticket.qr_code"
					:alt="__('QR Code')"
					:title="__('Click to enlarge')"
					class="w-20 h-20 contrast-100 brightness-100 cursor-pointer hover:opacity-80 transition-opacity"
					@click.stop="showQRExpanded = true"
				/>
			</div>
		</div>

		<!-- QR Code Expand Dialog -->
		<QRCodeExpandDialog
			v-model="showQRExpanded"
			:qrCodeSrc="ticket.qr_code"
			:altText="__('QR Code')"
		/>

		<!-- Ticket Transfer Dialog -->
		<TicketTransferDialog
			v-model="showTransferDialog"
			:ticket="ticket"
			@success="onTicketTransferSuccess"
		/>

		<!-- Add-on Preference Dialog -->
		<AddOnPreferenceDialog
			v-model="showPreferenceDialog"
			:ticket="ticket"
			@success="onPreferenceChangeSuccess"
		/>
	</li>
</template>

<script setup lang="ts">
import type { TicketAddOn } from "@/types";
import { Badge, Button, Dropdown } from "frappe-ui";
import { type Component, computed, ref } from "vue";
import LucideEdit from "~icons/lucide/edit";
import LucideUserPen from "~icons/lucide/user-pen";
import AddOnPreferenceDialog from "./AddOnPreferenceDialog.vue";
import QRCodeExpandDialog from "./QRCodeExpandDialog.vue";
import TicketTransferDialog from "./TicketTransferDialog.vue";

interface TicketAction {
	label: string;
	icon: Component;
	onClick: () => void;
}

const props = defineProps({
	ticket: {
		type: Object,
		required: true,
	},
	canTransfer: {
		type: Boolean,
		default: false,
	},
	canChangeAddOns: {
		type: Boolean,
		default: false,
	},
	isCancellationRequested: {
		type: Boolean,
		default: false,
	},
	isCancelled: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["transfer-success"]);

const showTransferDialog = ref(false);
const showPreferenceDialog = ref(false);
const showQRExpanded = ref(false);

// Check if ticket has customizable add-ons
const hasCustomizableAddOns = computed(() => {
	return (
		props.ticket?.add_ons?.some(
			(addon: TicketAddOn) => addon.options && addon.options.length > 0
		) || false
	);
});

const ticketActions = computed(() => {
	const actions: TicketAction[] = [];

	// Don't show any actions if ticket is cancelled or has a pending cancellation request
	if (props.isCancelled || props.isCancellationRequested) {
		return actions;
	}

	// Only show transfer action if transfers are allowed
	if (props.canTransfer) {
		actions.push({
			label: __("Transfer Ticket"),
			icon: LucideUserPen,
			onClick: () => {
				showTransferDialog.value = true;
			},
		});
	}

	// Only show preference action if add-on changes are allowed and ticket has customizable add-ons
	if (props.canChangeAddOns && hasCustomizableAddOns.value) {
		actions.push({
			label: __("Change Add-on Preference"),
			icon: LucideEdit,
			onClick: () => {
				showPreferenceDialog.value = true;
			},
		});
	}

	return actions;
});

const onTicketTransferSuccess = () => {
	emit("transfer-success");
};

const onPreferenceChangeSuccess = () => {
	emit("transfer-success");
};
</script>
