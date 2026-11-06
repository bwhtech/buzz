<template>
	<div v-if="isDateField(field.fieldtype)" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<DatePicker
			:model-value="modelValue"
			@update:model-value="$emit('update:modelValue', $event)"
			:placeholder="getFieldPlaceholder(field)"
		/>
	</div>

	<div v-else-if="isDateTimeField(field.fieldtype)" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<DateTimePicker
			:model-value="modelValue"
			@update:model-value="$emit('update:modelValue', $event)"
			:placeholder="getFieldPlaceholder(field)"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Time'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<TimePicker
			:model-value="modelValue"
			@update:model-value="$emit('update:modelValue', $event)"
			:placeholder="getFieldPlaceholder(field)"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Multi Select'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<MultiSelect
			:options="multiSelectOptions"
			v-model="multiSelectProxy"
			:placeholder="getFieldPlaceholder(field)"
		/>
	</div>

	<FormControl
		v-else-if="field.fieldtype === 'Check'"
		type="checkbox"
		:model-value="checkboxValue"
		@update:model-value="$emit('update:modelValue', $event ? 1 : 0)"
		:label="__(field.label)"
	/>

	<PhoneInput
		v-else-if="field.fieldtype === 'Phone'"
		:model-value="modelValue"
		@update:model-value="$emit('update:modelValue', $event)"
		:label="field.label"
		:required="!!field.mandatory"
		:placeholder="getFieldPlaceholder(field)"
	/>

	<FormControl
		v-else-if="field.fieldtype === 'Link'"
		:model-value="modelValue"
		@update:model-value="$emit('update:modelValue', $event)"
		:label="__(field.label)"
		type="select"
		:options="linkFieldOptions"
		:required="!!field.mandatory"
		:placeholder="getFieldPlaceholder(field)"
	/>

	<div v-else-if="field.fieldtype === 'Small Text'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<Textarea
			:model-value="modelValue"
			@update:model-value="$emit('update:modelValue', $event)"
			:placeholder="getFieldPlaceholder(field)"
			:required="!!field.mandatory"
			variant="outline"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Text Editor'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<RichTextFieldInput v-model="model" :placeholder="getFieldPlaceholder(field)" />
	</div>

	<div v-else-if="field.fieldtype === 'Rating'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<Rating
			:model-value="Math.round((modelValue || 0) * 5)"
			size="md"
			@update:model-value="$emit('update:modelValue', $event / 5)"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Attach Image'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<div v-if="modelValue" class="relative inline-block">
			<img :src="modelValue" class="h-16 w-16 rounded-4 object-cover border" />
			<Button
				variant="subtle"
				theme="gray"
				:label="__('Remove image')"
				:title="__('Remove image')"
				class="absolute -right-1.5 -top-1.5 !h-5 !w-5 !min-w-0 !rounded-full !p-0"
				@click="$emit('update:modelValue', '')"
			>
				<LucideX class="h-3 w-3" />
			</Button>
		</div>
		<FileUploader
			v-else
			@success="(file: { file_url: string }) => $emit('update:modelValue', file.file_url)"
			:validateFile="validateImageFile"
		>
			<template #default="{ openFileSelector }">
				<Button variant="outline" @click="openFileSelector">
					{{ __("Upload Image") }}
				</Button>
			</template>
		</FileUploader>
	</div>

	<div v-else-if="field.fieldtype === 'Attach'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-8">*</span>
		</label>
		<div v-if="modelValue" class="flex items-center gap-2">
			<a
				:href="modelValue"
				target="_blank"
				class="text-sm text-ink-blue-6 underline truncate max-w-xs"
			>
				{{ modelValue.split("/").pop() }}
			</a>
			<Button variant="ghost" size="sm" @click="$emit('update:modelValue', '')">
				{{ __("Remove") }}
			</Button>
		</div>
		<FileUploader
			v-else
			@success="(file: { file_url: string }) => $emit('update:modelValue', file.file_url)"
		>
			<template #default="{ openFileSelector }">
				<Button variant="outline" @click="openFileSelector">
					{{ __("Upload File") }}
				</Button>
			</template>
		</FileUploader>
	</div>

	<h3 v-else-if="field.fieldtype === 'Heading'" class="pt-2 text-lg font-semibold text-ink-gray-9">
		{{ __(field.label) }}
	</h3>

	<div
		v-else-if="field.fieldtype === 'Paragraph'"
		class="prose prose-sm max-w-none text-ink-gray-7"
		v-html="field.description"
	/>

	<hr v-else-if="field.fieldtype === 'Divider'" class="border-outline-gray-2" />

	<!-- Steps are split out by the form; anywhere else a page break draws nothing. -->
	<template v-else-if="field.fieldtype === 'Page Break'" />

	<RadioGroup
		v-else-if="field.fieldtype === 'Radio'"
		:model-value="modelValue"
		@update:model-value="$emit('update:modelValue', $event)"
		:label="__(field.label)"
		:required="!!field.mandatory"
	>
		<Radio
			v-for="option in getFieldOptions(field)"
			:key="option.value"
			:value="option.value"
			:label="option.label"
		/>
	</RadioGroup>

	<FormControl
		v-else
		:model-value="modelValue"
		@update:model-value="$emit('update:modelValue', $event)"
		:label="__(field.label)"
		:type="getFormControlType(field.fieldtype, field.options as string)"
		:options="getFieldOptions(field)"
		:required="!!field.mandatory"
		:placeholder="getFieldPlaceholder(field)"
	/>
</template>

<script setup lang="ts">
import {
	Button,
	DatePicker,
	DateTimePicker,
	FileUploader,
	TimePicker,
	MultiSelect,
	Radio,
	RadioGroup,
	Rating,
	Textarea,
} from "frappe-ui"
import { computed, defineAsyncComponent, type PropType } from "vue"
import LucideX from "~icons/lucide/x"

import PhoneInput from "@/components/PhoneInput.vue"
import {
	type FrappeField,
	getFieldOptions,
	getFieldPlaceholder,
	getFormControlType,
	isDateField,
	isDateTimeField,
} from "@/composables/useCustomFields"

// Loaded only for a form that has a rich text question: the editor is the app's largest chunk.
const RichTextFieldInput = defineAsyncComponent(() => import("@/components/RichTextFieldInput.vue"))

const props = defineProps({
	field: {
		type: Object as PropType<FrappeField>,
		required: true,
	},
})

// Frappe field values are heterogeneous (string, number, comma-joined multi-select),
// and the template binds this straight into components that expect a string.
const model = defineModel<any>()
const multiSelectOptions = computed(() => getFieldOptions(props.field))
const checkboxValue = computed(() => model.value === 1 || model.value === "1")

const multiSelectProxy = computed({
	get() {
		if (!model.value) return []
		return Array.isArray(model.value) ? model.value : String(model.value).split(",")
	},
	set(val) {
		// The server takes a Multi Select answer as a list.
		model.value = (val ?? []).map((item) => item.value || item)
	},
})

const linkFieldOptions = computed(() => {
	if (!props.field.link_options) return []
	return props.field.link_options.map((option) => ({
		label: option.label,
		value: option.value,
	}))
})

function validateImageFile(file: File) {
	const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"]
	if (!validTypes.includes(file.type)) {
		return __("Please upload a valid image file (JPEG, PNG, GIF, WebP, SVG)")
	}
}
</script>
