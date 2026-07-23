<template>
	<Dialog v-model="isOpen" size="md" bare>
		<div class="p-4">
			<!-- Title (shows custom label if set, otherwise default) -->
			<h3 class="text-lg-semibold mb-4 text-ink-gray-9">
				{{ offlineSettings.label }}
			</h3>

			<div class="space-y-4">
				<!-- Amount -->
				<div class="text-center p-3 bg-surface-gray-1 rounded">
					<div class="text-2xl-bold text-ink-gray-9">
						{{ formatCurrency(amount, currency) }}
					</div>
				</div>

				<!-- Payment Details (HTML Content) -->
				<div
					v-if="offlineSettings.payment_details"
					class="prose-sm [&>:first-child]:mt-0 bg-surface-gray-1 border border-outline-gray-1 rounded p-3 text-ink-gray-9"
					v-html="offlineSettings.payment_details"
				></div>

				<!-- Custom Fields -->
				<CustomFieldsSection
					v-if="offlineCustomFields.length > 0"
					:custom-fields="offlineCustomFields"
					v-model="customFieldsData"
					:show-title="false"
				/>

				<!-- Upload Proof -->
				<div v-if="offlineSettings.collect_payment_proof">
					<label class="block text-sm-medium text-ink-gray-8 mb-2"
						>{{ __("Proof of Payment") }} *</label
					>
					<FileUploader
						ref="fileUploaderRef"
						v-model="paymentProof"
						:file-types="['image/*']"
						@success="onFileUpload"
					>
						<template #default="{ openFileSelector, uploading, progress }">
							<div
								v-if="paymentProof"
								class="flex items-center gap-1.5 text-sm text-ink-green-6"
							>
								<LucideCheckCircle class="h-4 w-4 flex-shrink-0" />
								<span class="truncate">{{
									paymentProof.file_name || paymentProof.name
								}}</span>
								<button
									type="button"
									class="ml-auto p-1 rounded hover:bg-surface-gray-2 text-ink-gray-5 hover:text-ink-gray-8"
									:title="__('Replace')"
									@click="openFileSelector"
								>
									<LucideRefreshCw class="h-3.5 w-3.5" />
								</button>
							</div>
							<Button
								v-else
								@click="openFileSelector"
								:loading="uploading"
								variant="outline"
							>
								{{
									uploading
										? __("Uploading {0}%", [progress])
										: __("Upload File")
								}}
							</Button>
						</template>
					</FileUploader>
				</div>
			</div>

			<div class="flex gap-2 mt-4">
				<Button variant="outline" class="flex-1" @click="$emit('cancel')">
					{{ __("Cancel") }}
				</Button>
				<Button
					variant="solid"
					class="flex-1"
					@click="submitOfflinePayment"
					:loading="loading"
					:disabled="isSubmitDisabled"
				>
					{{ __("Submit") }}
				</Button>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import type { FrappeField } from "@/types";
import { Button, Dialog, FileUploader, toast } from "frappe-ui";
import { computed, type PropType, ref } from "vue";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import { formatCurrency } from "../utils/currency";
import CustomFieldsSection from "./CustomFieldsSection.vue";

const props = defineProps({
	open: {
		type: Boolean,
		default: false,
	},
	amount: {
		type: Number,
		required: true,
	},
	currency: {
		type: String,
		default: "INR",
	},
	offlineSettings: {
		type: Object as PropType<Record<string, any>>,
		required: true,
	},
	loading: {
		type: Boolean,
		default: false,
	},
	customFields: {
		type: Array as PropType<FrappeField[]>,
		default: () => [],
	},
});

const emit = defineEmits(["update:open", "submit", "cancel"]);

const isOpen = computed({
	get: () => props.open,
	set: (value) => emit("update:open", value),
});

const paymentProof = ref<Record<string, any> | null>(null);
const customFieldsData = ref<Record<string, any>>({});

// Custom fields are now pre-filtered by method in BookingForm
const offlineCustomFields = computed(() => props.customFields);

// Check if submit should be disabled
const isSubmitDisabled = computed(() => {
	// Check payment proof requirement
	if (props.offlineSettings.collect_payment_proof && !paymentProof.value) {
		return true;
	}

	// Check mandatory custom fields
	for (const field of offlineCustomFields.value) {
		if (
			field.mandatory &&
			(!customFieldsData.value[field.fieldname] ||
				customFieldsData.value[field.fieldname] === "")
		) {
			return true;
		}
	}

	return false;
});

const onFileUpload = (file: Record<string, any>) => {
	paymentProof.value = file;
};

const submitOfflinePayment = () => {
	if (isSubmitDisabled.value) {
		toast.error(__("Please fill all required fields"));
		return;
	}

	emit("submit", {
		payment_proof: paymentProof.value,
		custom_fields: customFieldsData.value,
	});
};
</script>
