<template>
	<div>
		<div class="w-8 mx-auto" v-if="formDataResource.loading">
			<Spinner />
		</div>

		<div v-else-if="submitted" class="text-center">
			<div class="bg-surface-green-1 border border-outline-green-1 rounded-lg p-8">
				<LucideCheckCircle class="w-16 h-16 text-ink-green-2 mx-auto mb-4" />
				<h2 class="text-ink-green-3 font-semibold text-xl mb-2">
					{{ formData?.success_title }}
				</h2>
				<div
					v-if="renderedSuccessMessage"
					class="prose prose-sm max-w-none text-ink-green-2"
					v-html="renderedSuccessMessage"
				></div>
				<p v-else class="text-ink-green-2">
					{{ __("Your submission has been received.") }}
				</p>
			</div>
		</div>

		<LoginRequired
			v-else-if="loginRequired"
			:message="__('Please log in to submit this form.')"
		/>

		<div v-else-if="formData?.closed" class="text-center">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-lg p-8">
				<LucideAlertCircle class="w-16 h-16 text-ink-amber-3 mx-auto mb-4" />
				<h2 class="text-ink-amber-3 font-semibold text-xl mb-2">
					{{ formData.closed_title }}
				</h2>
				<p class="text-ink-amber-2">
					{{ formData.closed_message }}
				</p>
			</div>
		</div>

		<div v-else-if="formData">
			<EventDetailsHeader :event-details="formData.event" />

			<form
				class="bg-surface-white border border-outline-gray-1 rounded-lg p-6"
				@submit.prevent="handleSubmit"
			>
				<h1 class="text-ink-gray-9 font-bold text-2xl mb-6">
					{{ formData.form_title }}
				</h1>

				<div class="space-y-6">
					<FormFieldSections :fields="formData.form_fields">
						<template #field="{ field }">
							<div v-if="field.fieldtype === 'Table'" class="space-y-2">
								<label class="text-xs text-ink-gray-5 block">
									{{ __(field.label) }}
								</label>
								<div v-if="tableData[field.fieldname]?.length" class="space-y-2">
									<div
										v-for="(row, idx) in tableData[field.fieldname]"
										:key="idx"
										class="flex items-center justify-between gap-2 border border-outline-gray-2 rounded-md px-3 py-2"
									>
										<span class="text-sm text-ink-gray-7 min-w-0 truncate">
											{{ getTableRowSummary(row) }}
										</span>
										<div class="flex gap-1 shrink-0">
											<Button
												variant="ghost"
												size="sm"
												@click="editTableRow(field, idx)"
											>
												{{ __("Edit") }}
											</Button>
											<Button
												variant="ghost"
												size="sm"
												@click="removeTableRow(field.fieldname, idx)"
											>
												{{ __("Remove") }}
											</Button>
										</div>
									</div>
								</div>
								<Button variant="outline" size="sm" @click="addTableRow(field)">
									{{ __("Add {0}", [__(field.label)]) }}
								</Button>
							</div>

							<CustomFieldInput
								v-else
								:field="normalizeField(field)"
								:model-value="formValues[field.fieldname]"
								@update:model-value="formValues[field.fieldname] = $event"
							/>
						</template>
					</FormFieldSections>

					<CustomFieldsSection
						v-if="formData.custom_fields?.length"
						:custom-fields="formData.custom_fields"
						v-model="customFieldValues"
						:show-title="false"
					/>
				</div>

				<Button
					variant="solid"
					size="lg"
					class="w-full mt-6"
					:loading="submitResource.loading"
					type="submit"
				>
					{{ __("Submit") }}
				</Button>
			</form>
		</div>

		<div v-else-if="loadError" class="text-center">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-lg p-8">
				<LucideAlertCircle class="w-16 h-16 text-ink-amber-3 mx-auto mb-4" />
				<h2 class="text-ink-amber-3 font-semibold text-xl mb-2">
					{{ __("Not Found") }}
				</h2>
				<p class="text-ink-amber-2">
					{{ loadError }}
				</p>
			</div>
		</div>

		<Dialog v-model="tableDialog.open" :title="tableDialog.title">
			<form @submit.prevent="saveTableRow">
				<div class="space-y-4">
					<template v-for="childField in tableDialog.fields" :key="childField.fieldname">
						<CustomFieldInput
							:field="normalizeField(childField)"
							:model-value="tableDialog.rowData[childField.fieldname]"
							@update:model-value="
								tableDialog.rowData[childField.fieldname] = $event
							"
						/>
					</template>
				</div>
				<Button variant="solid" type="submit" class="mt-4">
					{{ tableDialog.editIndex !== null ? __("Update") : __("Add") }}
				</Button>
			</form>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import CustomFieldInput from "@/components/CustomFieldInput.vue";
import CustomFieldsSection from "@/components/CustomFieldsSection.vue";
import EventDetailsHeader from "@/components/EventDetailsHeader.vue";
import FormFieldSections from "@/components/FormFieldSections.vue";
import LoginRequired from "@/components/LoginRequired.vue";
import type { FrappeError } from "@/types";
import { Button, Dialog, Spinner, createResource, toast } from "frappe-ui";
import { marked } from "marked";
import { computed, reactive, ref } from "vue";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideCheckCircle from "~icons/lucide/check-circle";

interface FormFieldDef {
	fieldname: string;
	fieldtype: string;
	label: string;
	options?: any;
	reqd?: number | boolean;
	mandatory?: number | boolean;
	default?: any;
	default_value?: any;
	placeholder?: string;
	link_options?: any;
	child_fields?: FormFieldDef[];
	[key: string]: any;
}

interface CustomFormData {
	success_message?: string;
	form_title?: string;
	form_fields?: FormFieldDef[];
	custom_fields?: FormFieldDef[];
	event?: Record<string, any>;
	closed?: boolean;
	closed_title?: string;
	closed_message?: string;
	[key: string]: any;
}

const props = defineProps({
	eventRoute: {
		type: String,
		required: true,
	},
	formRoute: {
		type: String,
		required: true,
	},
});

const formData = ref<CustomFormData | null>(null);
const formValues = reactive<Record<string, any>>({});
const customFieldValues = ref<Record<string, any>>({});
const submitted = ref(false);
const loginRequired = ref(false);
const loadError = ref<string | null>(null);

const tableData = reactive<Record<string, any[]>>({});
const tableDialog = reactive({
	open: false,
	title: "",
	fieldname: "",
	fields: [] as FormFieldDef[],
	rowData: {} as Record<string, any>,
	editIndex: null as number | null,
});

const renderedSuccessMessage = computed(() => {
	const msg = formData.value?.success_message;
	if (!msg) return "";
	return marked(msg);
});

function normalizeField(field: FormFieldDef) {
	return {
		fieldname: field.fieldname,
		fieldtype: field.fieldtype,
		label: field.label,
		options: field.options,
		mandatory: field.reqd || field.mandatory,
		placeholder: field.placeholder || "",
		default_value: field.default || field.default_value,
		link_options: field.link_options,
	};
}

function getTableRowSummary(row: Record<string, any>) {
	const values = Object.values(row).filter((v) => v && typeof v === "string");
	return values.slice(0, 3).join(" — ") || __("(empty)");
}

function addTableRow(field: FormFieldDef) {
	if (!tableData[field.fieldname]) tableData[field.fieldname] = [];

	tableDialog.open = true;
	tableDialog.title = __("Add {0}", [__(field.label)]);
	tableDialog.fieldname = field.fieldname;
	tableDialog.fields = field.child_fields || [];
	tableDialog.rowData = {};
	tableDialog.editIndex = null;
}

function editTableRow(field: FormFieldDef, idx: number) {
	tableDialog.open = true;
	tableDialog.title = __("Edit {0}", [__(field.label)]);
	tableDialog.fieldname = field.fieldname;
	tableDialog.fields = field.child_fields || [];
	tableDialog.rowData = { ...tableData[field.fieldname][idx] };
	tableDialog.editIndex = idx;
}

function removeTableRow(fieldname: string, idx: number) {
	tableData[fieldname].splice(idx, 1);
}

function saveTableRow() {
	const fieldname = tableDialog.fieldname;
	if (!tableData[fieldname]) tableData[fieldname] = [];

	if (tableDialog.editIndex !== null) {
		tableData[fieldname][tableDialog.editIndex] = { ...tableDialog.rowData };
	} else {
		tableData[fieldname].push({ ...tableDialog.rowData });
	}
	tableDialog.open = false;
}

const formDataResource = createResource({
	url: "buzz.api.forms.get_custom_form_data",
	params: {
		event_route: props.eventRoute,
		form_route: props.formRoute,
	},
	auto: true,
	onSuccess: (data: CustomFormData) => {
		formData.value = data;
		for (const field of data.form_fields || []) {
			if (field.default) {
				formValues[field.fieldname] = field.default;
			}
		}
	},
	onError: (err: FrappeError) => {
		if (err.exc_type === "AuthenticationError") {
			loginRequired.value = true;
			return;
		}
		loadError.value = err.messages?.[0] || __("Form not found");
	},
});

const submitResource = createResource({
	url: "buzz.api.forms.submit_custom_form",
	onSuccess: () => {
		submitted.value = true;
	},
	onError: (err: FrappeError) => {
		const msg = err.messages?.[0] || __("Failed to submit form");
		toast.error(msg.replace(/<[^>]*>/g, ""));
	},
});

function handleSubmit() {
	for (const field of formData.value?.form_fields || []) {
		if (field.fieldtype === "Table" && field.reqd && !tableData[field.fieldname]?.length) {
			toast.error(__("Please add at least one {0}", [__(field.label)]));
			return;
		}
	}

	for (const field of formData.value?.custom_fields || []) {
		if (!field.mandatory) continue;
		const val = customFieldValues.value[field.fieldname];
		const isEmpty = !val || val === "0" || val === 0;
		if (isEmpty) {
			toast.error(__("{0} is required", [__(field.label)]));
			return;
		}
	}

	const data = { ...formValues };
	for (const [fieldname, rows] of Object.entries(tableData)) {
		if (rows.length) {
			data[fieldname] = rows;
		}
	}

	submitResource.submit({
		event_route: props.eventRoute,
		form_route: props.formRoute,
		data,
		custom_fields_data: customFieldValues.value,
	});
}
</script>
