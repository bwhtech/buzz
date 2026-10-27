<template>
	<div>
		<div class="w-8 mx-auto" v-if="formDataResource.loading">
			<Spinner />
		</div>

		<div v-else-if="submitted" class="text-center">
			<div class="bg-surface-green-1 border border-outline-green-1 rounded-6 p-8">
				<LucideCheckCircle class="w-16 h-16 text-ink-green-6 mx-auto mb-4" />
				<h2 class="text-ink-green-6 text-2xl-semibold mb-2">
					{{ formData?.success_title }}
				</h2>
				<div
					v-if="renderedSuccessMessage"
					class="prose prose-sm max-w-none text-ink-green-6"
					v-html="renderedSuccessMessage"
				></div>
				<p v-else class="text-ink-green-6">
					{{ __("Your submission has been received.") }}
				</p>
				<p v-if="enquiryId && !session.isLoggedIn" class="text-ink-green-6 mt-3">
					{{ __("We'll be in touch at the email address you gave us.") }}
				</p>
				<Button
					v-if="enquiryId && session.isLoggedIn"
					class="mt-4"
					:route="`/account/sponsorships/${enquiryId}`"
				>
					{{ __("View your enquiry") }}
				</Button>
			</div>
		</div>

		<LoginRequired v-else-if="loginRequired" :message="__('Please log in to submit this form.')" />

		<div v-else-if="formData?.closed" class="text-center">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-6 p-8">
				<LucideAlertCircle class="w-16 h-16 text-ink-amber-6 mx-auto mb-4" />
				<h2 class="text-ink-amber-6 text-2xl-semibold mb-2">
					{{ formData.closed_title }}
				</h2>
				<p class="text-ink-amber-5">
					{{ formData.closed_message }}
				</p>
			</div>
		</div>

		<div v-else-if="formData">
			<EventDetailsHeader :event-details="formData.event" />

			<form
				class="bg-surface-base border border-outline-gray-1 rounded-6 p-6"
				@submit.prevent="handleSubmit"
			>
				<h1
					class="text-ink-gray-9 text-3xl-bold"
					:class="formData.form_description ? 'mb-2' : 'mb-6'"
				>
					{{ formData.form_title }}
				</h1>
				<p v-if="formData.form_description" class="mb-6 text-p-base text-ink-gray-6">
					{{ formData.form_description }}
				</p>

				<div v-if="steps.length > 1" class="mb-6 space-y-2">
					<div class="flex gap-1" aria-hidden="true">
						<span
							v-for="(_, index) in steps"
							:key="index"
							class="h-1 flex-1 rounded-full transition-colors duration-200"
							:class="index <= step ? 'bg-surface-gray-7' : 'bg-surface-gray-3'"
						/>
					</div>
					<p class="text-p-sm text-ink-gray-5">
						{{ __("Step {0} of {1}", [step + 1, steps.length]) }}
						<template v-if="steps[step].title"> · {{ __(steps[step].title) }}</template>
					</p>
				</div>

				<FormGrid :fields="steps[step].fields">
					<template #default="{ field }">
						<div v-if="field.fieldtype === 'Table'" class="space-y-2">
							<label class="text-xs text-ink-gray-5 block">
								{{ __(field.label) }}
							</label>
							<div v-if="tableData[field.fieldname]?.length" class="space-y-2">
								<div
									v-for="(row, idx) in tableData[field.fieldname]"
									:key="idx"
									class="flex items-center justify-between gap-2 border border-outline-gray-2 rounded-5 px-3 py-2"
								>
									<span class="text-sm text-ink-gray-7 min-w-0 truncate">
										{{ getTableRowSummary(row) }}
									</span>
									<div class="flex gap-1 shrink-0">
										<Button variant="ghost" size="sm" @click="editTableRow(field, idx)">
											{{ __("Edit") }}
										</Button>
										<Button variant="ghost" size="sm" @click="removeTableRow(field.fieldname, idx)">
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
							v-else-if="field.isQuestion"
							:field="field"
							:model-value="customFieldValues[field.fieldname]"
							@update:model-value="customFieldValues[field.fieldname] = $event"
						/>
						<CustomFieldInput
							v-else
							:field="normalizeField(field)"
							:model-value="formValues[field.fieldname]"
							@update:model-value="formValues[field.fieldname] = $event"
						/>
					</template>
				</FormGrid>

				<div class="mt-6 flex gap-2">
					<Button v-if="step > 0" size="lg" @click="step--">
						{{ __("Back") }}
					</Button>
					<Button
						variant="solid"
						size="lg"
						class="flex-1"
						:loading="submitResource.loading"
						type="submit"
					>
						{{ isLastStep ? __(formData.submit_label || "Submit") : __("Next") }}
					</Button>
				</div>
			</form>
		</div>

		<div v-else-if="loadError" class="text-center">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-6 p-8">
				<LucideAlertCircle class="w-16 h-16 text-ink-amber-6 mx-auto mb-4" />
				<h2 class="text-ink-amber-6 text-2xl-semibold mb-2">
					{{ __("Not Found") }}
				</h2>
				<p class="text-ink-amber-5">
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
							@update:model-value="tableDialog.rowData[childField.fieldname] = $event"
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
import { Button, Dialog, Spinner, toast, useCall, usePageMeta } from "frappe-ui"
import { marked } from "marked"
import { computed, reactive, ref } from "vue"
import LucideAlertCircle from "~icons/lucide/alert-circle"
import LucideCheckCircle from "~icons/lucide/check-circle"

import CustomFieldInput from "@/components/CustomFieldInput.vue"
import EventDetailsHeader from "@/components/EventDetailsHeader.vue"
import FormGrid from "@/components/FormGrid.vue"
import LoginRequired from "@/components/LoginRequired.vue"
import { type FrappeField, getFieldDefaultValue } from "@/composables/useCustomFields"
import { session } from "@/data/session"
import type { FrappeError } from "@/types"
import { applyLogic, type LogicRule } from "@/utils/formLogic"

interface FormFieldDef {
	fieldname: string
	fieldtype: string
	label: string
	options?: any
	reqd?: number | boolean
	mandatory?: number | boolean
	default?: any
	default_value?: any
	placeholder?: string
	link_options?: any
	child_fields?: FormFieldDef[]
	order?: number
	isQuestion?: boolean
	[key: string]: any
}

interface CustomFormData {
	success_message?: string
	form_title?: string
	form_fields?: FormFieldDef[]
	custom_fields?: FormFieldDef[]
	logic_rules?: LogicRule[]
	event?: Record<string, any>
	closed?: boolean
	closed_title?: string
	closed_message?: string
	[key: string]: any
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
})

const formData = ref<CustomFormData | null>(null)

usePageMeta(() => {
	const eventTitle = formData.value?.event?.title
	const formTitle = formData.value?.form_title
	return eventTitle && formTitle ? { title: `${formTitle} | ${eventTitle}` } : null
})

const formValues = reactive<Record<string, any>>({})
const customFieldValues = ref<Record<string, any>>({})
const submitted = ref(false)
const enquiryId = ref<string | null>(null)
const loginRequired = ref(false)
const loadError = ref<string | null>(null)

const tableData = reactive<Record<string, any[]>>({})
const tableDialog = reactive({
	open: false,
	title: "",
	fieldname: "",
	fields: [] as FormFieldDef[],
	rowData: {} as Record<string, any>,
	editIndex: null as number | null,
})

const renderedSuccessMessage = computed(() => {
	const msg = formData.value?.success_message
	if (!msg) return ""
	return marked(msg)
})

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
	}
}

function getTableRowSummary(row: Record<string, any>) {
	const values = Object.values(row).filter((v) => v && typeof v === "string")
	return values.slice(0, 3).join(" — ") || __("(empty)")
}

function addTableRow(field: FormFieldDef) {
	if (!tableData[field.fieldname]) tableData[field.fieldname] = []

	tableDialog.open = true
	tableDialog.title = __("Add {0}", [__(field.label)])
	tableDialog.fieldname = field.fieldname
	tableDialog.fields = field.child_fields || []
	tableDialog.rowData = {}
	tableDialog.editIndex = null
}

function editTableRow(field: FormFieldDef, idx: number) {
	tableDialog.open = true
	tableDialog.title = __("Edit {0}", [__(field.label)])
	tableDialog.fieldname = field.fieldname
	tableDialog.fields = field.child_fields || []
	tableDialog.rowData = { ...tableData[field.fieldname][idx] }
	tableDialog.editIndex = idx
}

function removeTableRow(fieldname: string, idx: number) {
	tableData[fieldname].splice(idx, 1)
}

function saveTableRow() {
	const fieldname = tableDialog.fieldname
	if (!tableData[fieldname]) tableData[fieldname] = []

	if (tableDialog.editIndex !== null) {
		tableData[fieldname][tableDialog.editIndex] = { ...tableDialog.rowData }
	} else {
		tableData[fieldname].push({ ...tableDialog.rowData })
	}
	tableDialog.open = false
}

const formDataResource = useCall<CustomFormData, { event_route: string; form_route: string }>({
	url: "/api/v2/method/buzz.api.forms.get_custom_form_data",
	params: {
		event_route: props.eventRoute,
		form_route: props.formRoute,
	},
	onSuccess: (data: CustomFormData) => {
		formData.value = data
		for (const field of data.form_fields || []) {
			if (field.default) {
				formValues[field.fieldname] = field.default
			}
		}
		for (const field of data.custom_fields || []) {
			const value = getFieldDefaultValue(field as FrappeField)
			if (value) customFieldValues.value[field.fieldname] = value
		}
	},
	onError: (error: Error) => {
		const err = error as FrappeError
		if (err.type === "LoginRequired" || err.exc_type === "LoginRequired") {
			loginRequired.value = true
			return
		}
		loadError.value = err.message || __("Form not found")
	},
})

const submitResource = useCall<string | null, Record<string, any>>({
	url: computed(
		() =>
			`/api/v2/method/${formData.value?.submission_method || "buzz.api.forms.submit_custom_form"}`,
	),
	method: "POST",
	immediate: false,
	onSuccess: (name) => {
		enquiryId.value = name || null
		submitted.value = true
	},
	onError: (error: Error) => {
		const err = error as FrappeError
		const msg = err.message || __("Failed to submit form")
		toast.error(msg.replace(/<[^>]*>/g, ""))
	},
})

// Upload fields render no native input, so the browser cannot enforce required on them.
function isAttachField(field: FormFieldDef) {
	return field.fieldtype === "Attach" || field.fieldtype === "Attach Image"
}

// The form's own fields and its questions, in the order the organiser set.
// Questions the rules hide drop out, and each shown one carries its effective mandatory flag.
const items = computed(() => {
	const shown = applyLogic(
		formData.value?.custom_fields || [],
		formData.value?.logic_rules || [],
		formValues,
		customFieldValues.value,
	)
	return [
		...(formData.value?.form_fields || []).map((field) => ({ ...field, isQuestion: false })),
		...shown.map((field) => ({ ...field, isQuestion: true })),
	].toSorted((a, b) => (a.order ?? 0) - (b.order ?? 0))
})

// Page breaks split the form into steps.
const steps = computed(() => {
	const groups: { title: string; fields: FormFieldDef[] }[] = [{ title: "", fields: [] }]
	for (const field of items.value) {
		if (field.fieldtype === "Page Break") groups.push({ title: field.label, fields: [] })
		else groups[groups.length - 1].fields.push(field)
	}
	return groups
})
const step = ref(0)
const isLastStep = computed(() => step.value >= steps.value.length - 1)

// The browser has already checked this step's required inputs before submit fires.
function handleSubmit() {
	if (!isLastStep.value) {
		step.value++
		window.scrollTo({ top: 0 })
		return
	}
	for (const field of formData.value?.form_fields || []) {
		if (field.fieldtype === "Table" && field.reqd && !tableData[field.fieldname]?.length) {
			toast.error(__("Please add at least one {0}", [__(field.label)]))
			return
		}
		if (isAttachField(field) && field.reqd && !formValues[field.fieldname]) {
			toast.error(__("{0} is required", [__(field.label)]))
			return
		}
	}

	for (const field of items.value) {
		if (!field.isQuestion || !field.mandatory) continue
		const val = customFieldValues.value[field.fieldname]
		const isEmpty = val == null || val === "" || (Array.isArray(val) && val.length === 0)
		if (isEmpty) {
			step.value = steps.value.findIndex((group) =>
				group.fields.some((item) => item.isQuestion && item.fieldname === field.fieldname),
			)
			toast.error(__("{0} is required", [__(field.label)]))
			return
		}
	}

	const data = { ...formValues }
	for (const [fieldname, rows] of Object.entries(tableData)) {
		if (rows.length) {
			data[fieldname] = rows
		}
	}

	submitResource.submit({
		event_route: props.eventRoute,
		form_route: props.formRoute,
		data,
		// A hidden question's answer is dropped by the server too; it is not sent at all.
		custom_fields_data: Object.fromEntries(
			items.value
				.filter((field) => field.isQuestion && field.fieldname in customFieldValues.value)
				.map((field) => [field.fieldname, customFieldValues.value[field.fieldname]]),
		),
	})
}
</script>
