<template>
	<div v-if="isDateField(field.fieldtype)" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
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
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
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
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
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
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
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

	<div v-else-if="isTextareaField(field.fieldtype)" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
		</label>
		<Textarea
			:model-value="modelValue"
			@update:model-value="$emit('update:modelValue', $event)"
			:placeholder="getFieldPlaceholder(field)"
			:required="!!field.mandatory"
			variant="outline"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Rating'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
		</label>
		<Rating
			:model-value="Math.round((modelValue || 0) * 5)"
			@update:model-value="$emit('update:modelValue', $event / 5)"
		/>
	</div>

	<div v-else-if="field.fieldtype === 'Attach Image'" class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(field.label) }}
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
		</label>
		<div v-if="modelValue" class="relative inline-block">
			<img :src="modelValue" class="h-16 w-16 rounded object-cover border" />
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
			<span v-if="field.mandatory" class="text-ink-red-4">*</span>
		</label>
		<div v-if="modelValue" class="flex items-center gap-2">
			<a
				:href="modelValue"
				target="_blank"
				class="text-sm text-ink-blue-3 underline truncate max-w-xs"
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
import PhoneInput from "@/components/PhoneInput.vue";
import {
	type FrappeField,
	getFieldOptions,
	getFieldPlaceholder,
	getFormControlType,
	isDateField,
	isDateTimeField,
	isTextareaField,
} from "@/composables/useCustomFields";
import {
	Button,
	DatePicker,
	DateTimePicker,
	FileUploader,
	TimePicker,
	MultiSelect,
	Rating,
	Textarea,
} from "frappe-ui";
import { computed, type PropType } from "vue";
import LucideX from "~icons/lucide/x";

const props = defineProps({
	field: {
		type: Object as PropType<FrappeField>,
		required: true,
	},
});

const model = defineModel();
const multiSelectOptions = computed(() => getFieldOptions(props.field));
const checkboxValue = computed(() => model.value === 1 || model.value === "1");

const multiSelectProxy = computed({
	get() {
		if (!model.value) return [];
		return Array.isArray(model.value) ? model.value : String(model.value).split(",");
	},
	set(val) {
		if (!val || val.length === 0) {
			model.value = "";
		} else {
			const values = val.map((item) => item.value || item);
			model.value = values.join(",");
		}
	},
});

const linkFieldOptions = computed(() => {
	if (!props.field.link_options) return [];
	return props.field.link_options.map((option) => ({
		label: option.label,
		value: option.value,
	}));
});

function validateImageFile(file: File) {
	const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"];
	if (!validTypes.includes(file.type)) {
		return __("Please upload a valid image file (JPEG, PNG, GIF, WebP, SVG)");
	}
}
</script>
