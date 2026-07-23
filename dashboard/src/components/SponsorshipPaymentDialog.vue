<template>
	<Dialog
		v-model="isOpen"
		:title="__('Select Sponsorship Tier')"
		size="xl"
		:message="__('Choose your preferred sponsorship tier and proceed to payment')"
	>
		<div v-if="!props.eventId" class="text-center py-8">
			<p class="text-ink-gray-5">{{ __("Loading event information...") }}</p>
		</div>

		<div v-else-if="tiers.loading" class="flex justify-center py-8">
			<Spinner />
		</div>

		<div v-else-if="tiers.data && tiers.data.length > 0" class="space-y-6">
			<p
				class="text-ink-gray-7"
				v-html="
					__(
						'Select a sponsorship tier for <strong>{0}</strong> and proceed to payment.',
						[eventTitle || __('this event')]
					)
				"
			></p>

			<!-- Tier Selection -->
			<div class="space-y-3">
				<div
					v-for="tier in tiers.data"
					:key="tier.name"
					class="border border-outline-gray-2 rounded-lg p-4 cursor-pointer transition-all hover:border-outline-gray-3 hover:bg-surface-gray-1"
					:class="{
						'border-outline-gray-4 bg-surface-gray-2':
							selectedTier?.name === tier.name,
					}"
					@click="selectedTier = tier"
				>
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-3">
							<input
								type="radio"
								:checked="selectedTier?.name === tier.name"
								@change="selectedTier = tier"
								class="text-ink-gray-6"
							/>
							<div>
								<h3 class="font-semibold text-ink-gray-9">
									{{ tier.title }}
								</h3>
							</div>
						</div>
						<div class="text-right">
							<p class="text-lg-bold text-ink-gray-9">
								{{ formatCurrency(tier.price, tier.currency) }}
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Payment Gateway Selection (only shown when tier is selected and multiple gateways exist) -->
			<div v-if="selectedTier && hasMultipleGateways" class="space-y-3">
				<h4 class="font-semibold text-ink-gray-8">
					{{ __("Select Payment Method") }}
				</h4>
				<div class="flex flex-wrap gap-3">
					<div
						v-for="gateway in paymentGateways"
						:key="gateway"
						class="border border-outline-gray-2 rounded-lg px-4 py-3 cursor-pointer transition-all hover:border-outline-gray-3 hover:bg-surface-gray-1"
						:class="{
							'border-outline-gray-4 bg-surface-gray-2': selectedGateway === gateway,
						}"
						@click="selectedGateway = gateway"
					>
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								:checked="selectedGateway === gateway"
								@change="selectedGateway = gateway"
								class="text-ink-gray-6"
							/>
							<span class="font-medium text-ink-gray-9">{{ gateway }}</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Selected Summary -->
			<div
				v-if="selectedTier"
				class="p-4 bg-surface-green-1 border border-outline-green-1 rounded-lg"
			>
				<div class="flex items-center justify-between">
					<div>
						<h4 class="font-semibold text-ink-green-6">
							{{ __("Selected Tier") }}
						</h4>
						<p class="text-ink-green-6">{{ selectedTier.title }}</p>
					</div>
					<div class="text-right">
						<p class="text-sm text-ink-green-6">{{ __("Total Amount") }}</p>
						<p class="text-2xl-bold text-ink-green-6">
							{{ formatCurrency(selectedTier.price, selectedTier.currency) }}
						</p>
					</div>
				</div>
			</div>
		</div>

		<div v-else-if="tiers.error" class="text-center py-8">
			<p class="text-ink-red-5">{{ __("Error loading sponsorship tiers") }}</p>
			<p class="text-ink-gray-5 text-sm">{{ tiers.error }}</p>
		</div>

		<div v-else class="text-center py-8">
			<p class="text-ink-gray-5">
				{{ __("No sponsorship tiers available for this event") }}
			</p>
		</div>

		<template #actions>
			<div class="flex justify-end space-x-3">
				<Button variant="ghost" @click="closeDialog">{{ __("Cancel") }}</Button>
				<Button
					variant="solid"
					:disabled="!canProceed || paymentLink.loading"
					:loading="paymentLink.loading"
					@click="proceedToPayment"
				>
					{{ __("Proceed to Pay") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { formatCurrency } from "@/utils/currency";
import { Button, Dialog, Spinner, createResource, useList } from "frappe-ui";
import { computed, ref, watch } from "vue";

interface Tier {
	name: string;
	title?: string;
	price?: number;
	currency?: string;
}

const props = defineProps({
	open: {
		type: Boolean,
		default: false,
	},
	enquiryId: {
		type: String,
		required: true,
	},
	eventId: {
		type: String,
		required: true,
	},
	eventTitle: {
		type: String,
		required: false,
	},
});

const emit = defineEmits(["update:open", "payment-started"]);

const isOpen = ref(props.open);
const selectedTier = ref<Tier | null>(null);
const selectedGateway = ref<any>(null);
const paymentGateways = ref<any[]>([]);

const hasMultipleGateways = computed(() => paymentGateways.value.length > 1);

const canProceed = computed(() => {
	if (!selectedTier.value) return false;
	// If multiple gateways, require gateway selection
	if (hasMultipleGateways.value && !selectedGateway.value) return false;
	return true;
});

// Watch for prop changes
watch(
	() => props.open,
	(newVal) => {
		isOpen.value = newVal;
		if (newVal && props.eventId) {
			// Reset selection when dialog opens
			selectedTier.value = null;
			selectedGateway.value = null;
			tiers.fetch();
			fetchPaymentGateways();
		}
	}
);

watch(isOpen, (newVal) => {
	emit("update:open", newVal);
});

// Resource to fetch sponsorship tiers
const tiers = useList<Tier>({
	doctype: "Sponsorship Tier",
	filters: { event: props.eventId },
	fields: ["name", "title", "price", "currency"],
	orderBy: "price asc",
	onError: console.error,
	immediate: false, // Don't auto-fetch, we'll fetch manually when dialog opens
});

// Fetch payment gateways for the event
const paymentGatewaysResource = createResource({
	url: "buzz.api.get_event_payment_gateways",
	onSuccess: (data: any[]) => {
		paymentGateways.value = data || [];
	},
	onError: console.error,
});

function fetchPaymentGateways() {
	paymentGatewaysResource.submit({
		event: props.eventId,
	});
}

// Resource to create payment link
const paymentLink = createResource({
	url: "buzz.api.create_sponsorship_payment_link",
	onSuccess: (paymentUrl: string) => {
		emit("payment-started");
		closeDialog();
		// Redirect to payment page
		window.location.href = paymentUrl;
	},
	onError: (error: unknown) => {
		console.error("Payment link creation failed:", error);
		// TODO: Show error toast
	},
});

const closeDialog = () => {
	isOpen.value = false;
	selectedTier.value = null;
	selectedGateway.value = null;
};

const proceedToPayment = () => {
	if (!selectedTier.value) return;

	// Use selected gateway or first available (for single gateway case)
	const gateway = selectedGateway.value || paymentGateways.value[0] || null;

	paymentLink.submit({
		enquiry_id: props.enquiryId,
		tier_id: selectedTier.value.name,
		payment_gateway: gateway,
	});
};
</script>
