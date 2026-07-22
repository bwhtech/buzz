<!-- AttendeeCard.vue -->
<template>
	<div
		class="bg-surface-white border border-outline-gray-3 rounded-xl p-4 md:p-6 mb-6 shadow-sm relative"
	>
		<!-- Remove Button -->

		<div class="flex justify-between items-start mb-4 border-b pb-2">
			<h4 class="text-lg font-semibold text-ink-gray-9">
				{{ __("Attendee") }} #{{ index + 1 }}
			</h4>

			<Tooltip :text="__('Remove Attendee')" :hover-delay="0.5">
				<Button
					v-if="showRemove"
					@click="$emit('remove')"
					type="button"
					theme="red"
					icon="lucide-x"
				/>
			</Tooltip>
		</div>

		<!-- Name, Email and Custom Fields -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 items-end">
			<FormControl
				v-model="attendee.first_name"
				:label="__('First Name')"
				:placeholder="__('Enter first name')"
				required
				type="text"
			/>
			<FormControl
				v-model="attendee.last_name"
				:label="__('Last Name')"
				:placeholder="__('Enter last name')"
				:required="eventDetails.category === 'Webinars'"
				type="text"
			/>
			<FormControl
				v-model="attendee.email"
				:label="__('Email')"
				:placeholder="__('Enter email address')"
				required
				type="email"
			/>

			<!-- Ticket Type -->

			<!-- Show selector only if there are multiple ticket types -->
			<FormControl
				v-if="
					availableTicketTypes.length > 1 &&
					!(eventDetails.category == 'Webinars' && eventDetails.free_webinar)
				"
				v-model="attendee.ticket_type"
				:label="__('Ticket Type')"
				type="select"
				:options="
					availableTicketTypes.map((tt) => ({
						label: `${__(tt.title ?? '')} (${formatPriceOrFree(
							tt.price,
							tt.currency
						)})`,
						value: String(tt.name),
					}))
				"
			/>

			<!-- Custom Fields for Tickets integrated with basic fields -->
			<template v-if="customFields.length > 0">
				<CustomFieldInput
					v-for="field in customFields"
					:key="field.fieldname"
					:field="field"
					:model-value="getCustomFieldValue(field.fieldname)"
					@update:model-value="updateCustomFieldValue(field.fieldname, $event)"
				/>
			</template>
		</div>

		<!-- Add-ons -->
		<div v-if="availableAddOns.length > 0">
			<hr class="my-4" />

			<div v-for="addOn in availableAddOns" :key="addOn.name" class="mb-4">
				<div class="flex flex-col gap-3">
					<FormControl
						type="checkbox"
						:model-value="getAddOnSelected(addOn.name)"
						@update:model-value="updateAddOnSelection(addOn.name, $event)"
						:id="`add_on_${addOn.name}_${index}`"
						:label="__(addOn.title ?? '')"
					/>
					<div class="text-ink-gray-5 text-sm/4" v-if="addOn.description">
						<p>
							{{ __(addOn.description) }}
						</p>
					</div>
				</div>

				<div
					v-if="addOn.user_selects_option && getAddOnSelected(addOn.name)"
					class="mt-2 ml-6"
				>
					<FormControl
						:model-value="getAddOnOption(addOn.name)"
						@update:model-value="updateAddOnOption(addOn.name, $event)"
						type="select"
						:options="
							(addOn.options ?? []).map((option) => ({
								label: __(option),
								value: option,
							}))
						"
						size="sm"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { type FrappeField, getFieldDefaultValue } from "@/composables/useCustomFields";
import { formatPriceOrFree } from "@/utils/currency";
import { Tooltip } from "frappe-ui";
import { type PropType } from "vue";
import CustomFieldInput from "./CustomFieldInput.vue";

interface AvailableTicketType {
	name: string | number;
	title?: string;
	price?: number;
	currency?: string;
}

interface AvailableAddOn {
	name: string;
	title?: string;
	description?: string;
	price?: number;
	options?: string[];
	user_selects_option?: 0 | 1 | boolean;
}

interface AttendeeAddOnSelection {
	selected: boolean;
	option: string | null;
}

interface Attendee {
	ticket_type?: string;
	add_ons?: Record<string, AttendeeAddOnSelection>;
	custom_fields?: Record<string, any>;
	[key: string]: any;
}

const props = defineProps({
	attendee: { type: Object as PropType<Attendee>, required: true },
	index: { type: Number, required: true },
	availableTicketTypes: {
		type: Array as PropType<AvailableTicketType[]>,
		required: true,
	},
	availableAddOns: { type: Array as PropType<AvailableAddOn[]>, required: true },
	customFields: { type: Array as PropType<FrappeField[]>, default: () => [] },
	showRemove: { type: Boolean, default: false },
	eventDetails: {
		type: Object as PropType<Record<string, any>>,
		required: false,
		default: () => ({}),
	},
});

defineEmits(["remove"]);

// Helper methods to safely access add-on properties
const ensureAddOnExists = (addOnName: string) => {
	if (!props.attendee.add_ons) {
		props.attendee.add_ons = {};
	}
	if (!props.attendee.add_ons[addOnName]) {
		const addOn = props.availableAddOns.find((a) => a.name === addOnName);
		props.attendee.add_ons[addOnName] = {
			selected: false,
			option: addOn?.options ? addOn.options[0] || null : null,
		};
	}
};

const getAddOnSelected = (addOnName: string) => {
	ensureAddOnExists(addOnName);
	return props.attendee.add_ons![addOnName].selected;
};

const getAddOnOption = (addOnName: string) => {
	ensureAddOnExists(addOnName);
	return props.attendee.add_ons![addOnName].option;
};

const updateAddOnSelection = (addOnName: string, selected: boolean) => {
	ensureAddOnExists(addOnName);
	props.attendee.add_ons![addOnName].selected = selected;

	// If selecting an add-on and it has options, ensure the first option is selected
	if (selected) {
		const addOn = props.availableAddOns.find((a) => a.name === addOnName);
		if (
			addOn?.options &&
			addOn.options.length > 0 &&
			!props.attendee.add_ons![addOnName].option
		) {
			props.attendee.add_ons![addOnName].option = addOn.options[0];
		}
	}
};

const updateAddOnOption = (addOnName: string, option: string) => {
	ensureAddOnExists(addOnName);
	props.attendee.add_ons![addOnName].option = option;
};

// Custom fields helper methods
const ensureCustomFieldsExists = () => {
	if (!props.attendee.custom_fields) {
		props.attendee.custom_fields = {};
	}
};

const getCustomFieldValue = (fieldname: string) => {
	ensureCustomFieldsExists();
	const currentValue = props.attendee.custom_fields![fieldname];

	// Apply default for fields that don't have values yet
	if (!currentValue && currentValue !== "") {
		const field = props.customFields.find((f) => f.fieldname === fieldname);
		if (field) {
			const defaultValue = getFieldDefaultValue(field);
			if (defaultValue) {
				updateCustomFieldValue(fieldname, defaultValue);
				return defaultValue;
			}
		}
	}

	return currentValue || "";
};

const updateCustomFieldValue = (fieldname: string, value: any) => {
	ensureCustomFieldsExists();
	props.attendee.custom_fields![fieldname] = value;
};
</script>
