<template>
	<div class="mb-6 flex items-center justify-between text-ink-gray-6">
		<BackButton :to="{ name: 'sponsorships-list' }" label="Back to Sponsorships" />

		<!-- Withdraw Button (show only if not paid and not withdrawn) -->
		<Button
			v-if="canWithdraw"
			variant="outline"
			size="sm"
			@click="showWithdrawDialog = true"
			:loading="withdrawResource.loading"
		>
			Withdraw Inquiry
		</Button>
	</div>

	<div class="w-4" v-if="enquiryDetails.loading">
		<Spinner />
	</div>

	<div v-else-if="enquiryDetails.data">
		<!-- Success Message (only shown on payment success) -->
		<Transition
			name="success-message"
			enter-active-class="transition-all duration-500 ease-out"
			leave-active-class="transition-all duration-500 ease-in"
			enter-from-class="opacity-0 transform -translate-y-4 scale-95"
			enter-to-class="opacity-100 transform translate-y-0 scale-100"
			leave-from-class="opacity-100 transform translate-y-0 scale-100"
			leave-to-class="opacity-0 transform -translate-y-4 scale-95"
		>
			<div
				v-if="showSuccessMessage"
				class="mb-6 bg-surface-green-1 border border-outline-green-1 rounded-lg p-4"
			>
				<div class="flex items-center">
					<LucideCheckCircle class="w-6 h-6 text-ink-green-2 mr-3" />
					<div>
						<h3 class="text-ink-green-3 font-semibold">Payment Successful! 🎉</h3>
						<p class="text-ink-green-2">
							Your sponsorship payment has been confirmed. You'll receive
							confirmation details via email.
						</p>
					</div>
				</div>
			</div>
		</Transition>

		<h2 class="text-ink-gray-9 font-semibold text-lg mb-6">
			Sponsorship Inquiry Details
			<span class="text-ink-gray-5 font-mono">(#{{ enquiryId }})</span>
		</h2>

		<!-- Sponsorship Confirmation (shown at top if sponsored) -->
		<div
			v-if="sponsorDetails"
			class="mb-6 bg-surface-green-1 border border-outline-green-1 rounded-lg p-6"
		>
			<div class="flex items-center mb-4">
				<LucideCheckCircle class="w-6 h-6 text-ink-green-2 mr-3" />
				<h3 class="text-ink-green-3 font-semibold text-lg">Sponsorship Confirmed</h3>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label class="block text-sm font-medium text-ink-green-3 mb-1"
						>Sponsor Name</label
					>
					<p class="text-ink-green-3">{{ sponsorDetails.company_name }}</p>
				</div>
				<div>
					<label class="block text-sm font-medium text-ink-green-3 mb-1"
						>Confirmed On</label
					>
					<p class="text-ink-green-3">{{ formatDate(sponsorDetails.creation) }}</p>
				</div>
				<div v-if="sponsorDetails.tier_title" class="md:col-span-2">
					<label class="block text-sm font-medium text-ink-green-3 mb-1"
						>Sponsorship Tier</label
					>
					<p class="text-ink-green-3">{{ sponsorDetails.tier_title }}</p>
				</div>
			</div>
		</div>

		<!-- Withdrawn Alert (shown at top for withdrawn inquiries) -->
		<div
			v-if="enquiryDetails.data.enquiry.status === 'Withdrawn'"
			class="mb-6 bg-surface-red-1 border border-outline-red-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideXCircle class="w-6 h-6 text-ink-red-2 mr-3" />
				<div>
					<h3 class="text-ink-red-3 font-semibold">Inquiry Withdrawn</h3>
					<p class="text-ink-red-2 text-sm mt-1">
						This sponsorship inquiry has been withdrawn and is no longer active.
					</p>
				</div>
			</div>
		</div>

		<!-- Approval Pending Alert (shown at top for pending approval) -->
		<div
			v-if="enquiryDetails.data.enquiry.status === 'Approval Pending'"
			class="mb-6 bg-surface-blue-1 border border-outline-blue-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideClock class="w-6 h-6 text-ink-blue-2 mr-3" />
				<div>
					<h3 class="text-ink-blue-3 font-semibold">Awaiting Approval</h3>
					<p class="text-ink-blue-2 text-sm mt-1">
						Your sponsorship inquiry has been submitted and is pending approval from
						the event management team. You'll be notified once it's approved and ready
						for payment.
					</p>
				</div>
			</div>
		</div>

		<!-- Payment Pending Alert (shown at top for pending payments) -->
		<div
			v-else-if="enquiryDetails.data.enquiry.status === 'Payment Pending'"
			class="mb-6 bg-surface-orange-1 border border-outline-orange-1 rounded-lg p-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center">
					<LucideClock class="w-6 h-6 text-ink-gray-8 mr-3" />
					<div>
						<h3 class="text-ink-gray-8 font-semibold">Payment Pending</h3>
						<p class="text-ink-gray-7 text-sm mt-1">
							Your sponsorship inquiry has been approved! Complete your payment to
							confirm your sponsorship.
						</p>
					</div>
				</div>
				<div>
					<Button variant="solid" @click="showPaymentDialog = true"> Pay Now </Button>
				</div>
			</div>
		</div>

		<div class="space-y-6">
			<!-- Company Information -->
			<div class="bg-surface-white border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">Company Information</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div>
						<label class="block text-sm font-medium text-ink-gray-6 mb-1"
							>Company Name</label
						>
						<p class="text-ink-gray-9">
							{{ enquiryDetails.data.enquiry.company_name }}
						</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-ink-gray-6 mb-2"
							>Company Logo</label
						>
						<FileUploader
							@success="(file: { file_url: string }) => updateLogo(file.file_url)"
							:validateFile="validateIsImageFile"
							:uploadArgs="logoUploadArgs"
						>
							<template
								#default="{
									openFileSelector,
									error: uploadError,
									uploading,
									progress,
								}"
							>
								<div class="space-y-2">
									<!-- Logo Display -->
									<div v-if="currentLogo" class="mb-2">
										<img
											:src="currentLogo"
											:alt="companyName"
											class="h-16 w-auto object-contain border border-outline-gray-1 rounded p-1 contrast-100 brightness-100"
											:class="{
												'opacity-50':
													uploading || updateLogoResource.loading,
											}"
										/>
									</div>
									<div v-else class="mb-2">
										<div
											class="h-16 w-20 border-2 border-dashed border-outline-gray-2 rounded flex items-center justify-center"
										>
											<span class="text-ink-gray-4 text-xs">No Logo</span>
										</div>
									</div>

									<!-- Change Logo Button -->
									<div>
										<Button
											variant="outline"
											size="sm"
											:disabled="uploading || updateLogoResource.loading"
											@click="openFileSelector"
										>
											{{ currentLogo ? "Change Logo" : "Upload Logo" }}
										</Button>
									</div>

									<!-- Upload Progress -->
									<div v-if="uploading" class="text-xs text-ink-gray-7">
										Uploading... {{ progress }}%
										<div
											class="w-full bg-surface-gray-2 rounded-full h-1 mt-1"
										>
											<div
												class="bg-ink-blue-2 h-1 rounded-full transition-all duration-300"
												:style="{ width: progress + '%' }"
											></div>
										</div>
									</div>

									<!-- Update Status -->
									<div
										v-else-if="updateLogoResource.loading"
										class="text-xs text-ink-gray-7"
									>
										Updating logo...
									</div>

									<!-- Error Message -->
									<ErrorMessage
										v-if="uploadError"
										:message="uploadError as string"
										class="text-xs"
									/>
								</div>
							</template>
						</FileUploader>
					</div>
				</div>
			</div>

			<!-- Event & Sponsorship Details -->
			<div class="bg-surface-white border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">Sponsorship Details</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-ink-gray-6 mb-1">Event</label>
						<p class="text-ink-gray-9">
							{{
								enquiryDetails.data.event_details.title ||
								enquiryDetails.data.enquiry.event
							}}
						</p>
					</div>
					<div v-if="enquiryDetails.data.enquiry.tier_title">
						<label class="block text-sm font-medium text-ink-gray-6 mb-1"
							>Sponsorship Tier</label
						>
						<p class="text-ink-gray-9">{{ enquiryDetails.data.enquiry.tier_title }}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-ink-gray-6 mb-1"
							>Status</label
						>
						<Badge
							:theme="getStatusTheme(enquiryDetails.data.enquiry.status)"
							variant="subtle"
							size="md"
						>
							{{ enquiryDetails.data.enquiry.status }}
						</Badge>
					</div>
					<div>
						<label class="block text-sm font-medium text-ink-gray-6 mb-1"
							>Submitted On</label
						>
						<p class="text-ink-gray-9">
							{{ formatDate(enquiryDetails.data.enquiry.creation) }}
						</p>
					</div>
				</div>
			</div>

			<!-- Event Information (if available) -->
			<div
				v-if="enquiryDetails.data.event_details"
				class="bg-surface-white border border-outline-gray-1 rounded-lg p-6"
			>
				<h3 class="text-ink-gray-8 font-semibold text-lg mb-4">Event Information</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div v-if="enquiryDetails.data.event_details.start_date">
						<label class="block text-sm font-medium text-ink-gray-6 mb-1"
							>Event Date</label
						>
						<p class="text-ink-gray-9">
							{{ formatDate(enquiryDetails.data.event_details.start_date) }}
						</p>
					</div>
					<div v-if="enquiryDetails.data.event_details.venue">
						<label class="block text-sm font-medium text-ink-gray-6 mb-1">Venue</label>
						<p class="text-ink-gray-9">
							{{ enquiryDetails.data.event_details.venue }}
						</p>
					</div>
				</div>
				<div v-if="enquiryDetails.data.event_details.short_description" class="mt-4">
					<label class="block text-sm font-medium text-ink-gray-6 mb-1"
						>Event Description</label
					>
					<p class="text-ink-gray-9">
						{{ enquiryDetails.data.event_details.short_description }}
					</p>
				</div>
				<div v-if="enquiryDetails.data.event_details.about" class="mt-4">
					<label class="block text-sm font-medium text-ink-gray-6 mb-1"
						>About Event</label
					>
					<div
						class="text-ink-gray-9"
						v-html="enquiryDetails.data.event_details.about"
					></div>
				</div>
			</div>
		</div>
	</div>

	<div v-else-if="enquiryDetails.error" class="text-center py-8">
		<div class="text-ink-red-3 text-lg mb-2">Error loading sponsorship details</div>
		<div class="text-ink-gray-4 text-sm">{{ enquiryDetails.error }}</div>
	</div>

	<!-- Payment Dialog -->
	<SponsorshipPaymentDialog
		v-if="enquiryDetails.data && enquiryDetails.data.enquiry.status === 'Payment Pending'"
		v-model:open="showPaymentDialog"
		:enquiry-id="enquiryId"
		:event-id="enquiryDetails.data?.enquiry.event"
		:event-title="enquiryDetails.data?.event_details.title"
		@payment-started="onPaymentStarted"
	/>

	<!-- Withdraw Confirmation Dialog -->
	<Dialog
		v-model="showWithdrawDialog"
		:options="{
			title: 'Withdraw Sponsorship Inquiry',
			message:
				'Are you sure you want to withdraw this sponsorship inquiry? This action cannot be undone.',
			size: 'lg',
			icon: {
				name: 'alert-triangle',
				appearance: 'warning',
			},
			actions: [
				{
					label: 'Withdraw Inquiry',
					variant: 'solid',
					theme: 'red',
					onClick: () => withdrawResource.submit(),
				},
			],
		}"
	/>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { usePaymentSuccess } from "@/composables/usePaymentSuccess";
import {
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FileUploader,
	Spinner,
	createResource,
} from "frappe-ui";
import { toast } from "frappe-ui";
import { dayjsLocal } from "frappe-ui";
import { computed, ref } from "vue";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideClock from "~icons/lucide/clock";
import LucideXCircle from "~icons/lucide/x-circle";
import SponsorshipPaymentDialog from "../components/SponsorshipPaymentDialog.vue";
import BackButton from "../components/common/BackButton.vue";

const props = defineProps({
	enquiryId: {
		type: String,
		required: true,
	},
});

const showPaymentDialog = ref(false);
const showWithdrawDialog = ref(false);

const enquiryDetails = createResource({
	url: "buzz.api.get_sponsorship_details",
	params: {
		enquiry_id: props.enquiryId,
	},
	auto: true,
});

// Resource to withdraw sponsorship inquiry
const withdrawResource = createResource({
	url: "buzz.api.withdraw_sponsorship_enquiry",
	makeParams() {
		return {
			enquiry_id: props.enquiryId,
		};
	},
	onSuccess: () => {
		toast.success("Inquiry withdrawn successfully");
		showWithdrawDialog.value = false;
		// Reload the enquiry details to show updated status
		enquiryDetails.reload();
	},
	onError: (err: FrappeError) => {
		toast.error(err.messages?.[0] || "Failed to withdraw inquiry");
		showWithdrawDialog.value = false;
	},
});

// Resource to update company logo
const updateLogoResource = createResource({
	url: "frappe.client.set_value",
	makeParams(fileUrl: string) {
		// If we have a confirmed sponsor, update the Event Sponsor document
		if (sponsorDetails.value) {
			return {
				doctype: "Event Sponsor",
				name: sponsorDetails.value.name,
				fieldname: "company_logo",
				value: fileUrl,
			};
		}

		// If it's still an inquiry, update the Sponsorship Enquiry document
		return {
			doctype: "Sponsorship Enquiry",
			name: props.enquiryId,
			fieldname: "company_logo",
			value: fileUrl,
		};
	},
	onSuccess: () => {
		// Reload the enquiry details to get updated data
		enquiryDetails.reload();
	},
	onError: (err: FrappeError) => {
		console.error("Failed to update company logo:", err);
	},
});

// Use the payment success composable
const { showSuccessMessage } = usePaymentSuccess({
	onSuccess: () => {
		// Reload the enquiry details to get updated status
		enquiryDetails.reload();
	},
});

// Extract sponsor details from the response
const sponsorDetails = computed(() => {
	return enquiryDetails.data?.sponsor_details || null;
});

// Check if inquiry can be withdrawn (not paid and not already withdrawn)
const canWithdraw = computed(() => {
	if (!enquiryDetails.data?.enquiry) return false;
	const status = enquiryDetails.data.enquiry.status;
	return status !== "Paid" && status !== "Withdrawn";
});

// Get the current company logo (from sponsor if confirmed, otherwise from enquiry)
const currentLogo = computed(() => {
	if (sponsorDetails.value?.company_logo) {
		return sponsorDetails.value.company_logo;
	}
	return enquiryDetails.data?.enquiry?.company_logo || null;
});

// Get the company name
const companyName = computed(() => {
	if (sponsorDetails.value?.company_name) {
		return sponsorDetails.value.company_name;
	}
	return enquiryDetails.data?.enquiry?.company_name || "";
});

// Upload arguments for file uploader
const logoUploadArgs = computed(() => {
	return {
		private: false,
		folder: "Home/Attachments",
	};
});

const getStatusTheme = (status: string) => {
	switch (status) {
		case "Paid":
			return "green";
		case "Payment Pending":
			return "orange";
		case "Approval Pending":
			return "blue";
		case "Withdrawn":
			return "red";
		default:
			return "gray";
	}
};

const formatDate = (dateString: string) => {
	return dayjsLocal(dateString).format("MMM DD, YYYY");
};

const onPaymentStarted = () => {
	// Optional: Show a loading state or toast message
	console.log("Payment process started");
};

// Validate that uploaded file is an image
const validateIsImageFile = (file: File) => {
	const allowedTypes = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"];
	const maxSize = 5 * 1024 * 1024; // 5MB

	if (!allowedTypes.includes(file.type)) {
		return "Please upload a valid image file (JPEG, PNG, GIF, or WebP)";
	}

	if (file.size > maxSize) {
		return "File size must be less than 5MB";
	}

	return null;
};

// Update logo after successful upload
const updateLogo = (fileUrl: string) => {
	// Update the local data immediately for better UX
	if (sponsorDetails.value) {
		// Update sponsor details if it's a confirmed sponsorship
		sponsorDetails.value.company_logo = fileUrl;
	} else if (enquiryDetails.data?.enquiry) {
		// Update enquiry details if it's still an inquiry
		enquiryDetails.data.enquiry.company_logo = fileUrl;
	}

	// Update the document field using the resource
	updateLogoResource.submit(fileUrl);
};
</script>
