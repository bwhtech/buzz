<template>
	<Dialog v-model="isOpen" :options="{ size: '3xl' }">
		<template #body-title>
			<h3 class="text-xl font-semibold text-ink-gray-9">
				{{ eventTalkId ? __("Edit Talk") : __("Edit Proposal") }}
			</h3>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					type="text"
					:label="__('Title')"
					:placeholder="__('Enter proposal title')"
					v-model="editForm.title"
					:required="true"
				/>

				<div>
					<label class="block text-sm font-medium text-ink-gray-7 mb-2">
						{{ __("Description") }}
					</label>
					<TextEditor
						:fixedMenu="true"
						:content="editForm.description"
						:placeholder="__('Enter proposal description...')"
						@change="(val) => (editForm.description = val)"
						editorClass="prose-sm max-w-none py-2 px-3 min-h-[12rem] border-outline-gray-2 hover:border-outline-gray-3 rounded-b-md bg-surface-gray-3"
					/>
				</div>

				<FormControl
					v-if="!eventTalkId"
					type="tel"
					:label="__('Phone (optional)')"
					:placeholder="__('Enter phone number')"
					v-model="editForm.phone"
				/>
			</div>
		</template>
		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					@click="handleSave"
					:loading="updateResource.loading"
					:disabled="!editForm.title"
				>
					{{ __("Save Changes") }}
				</Button>
				<Button variant="outline" @click="close">
					{{ __("Cancel") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { Button, Dialog, FormControl, TextEditor, createResource, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps({
	open: {
		type: Boolean,
		default: false,
	},
	proposalId: {
		type: String,
		required: true,
	},
	eventTalkId: {
		type: String,
		default: null,
	},
	initialData: {
		type: Object,
		default: () => ({ title: "", description: "", phone: "" }),
	},
});

const emit = defineEmits(["update:open", "updated"]);

const isOpen = computed({
	get: () => props.open,
	set: (value) => emit("update:open", value),
});

const editForm = ref({
	title: "",
	description: "",
	phone: "",
});

// Update resource using frappe.client.set_value
const updateResource = createResource({
	url: "frappe.client.set_value",
	onSuccess: () => {
		const message = props.eventTalkId
			? __("Talk updated successfully")
			: __("Proposal updated successfully");
		toast.success(message);
		isOpen.value = false;
		emit("updated");
	},
	onError: (error: FrappeError) => {
		const message = props.eventTalkId
			? __("Failed to update talk")
			: __("Failed to update proposal");
		toast.error(error.messages?.[0] || message);
	},
});

const handleSave = () => {
	if (!editForm.value.title) {
		toast.error(__("Title is required"));
		return;
	}

	// If eventTalkId is provided, update the Event Talk doctype
	// Otherwise, update the Talk Proposal doctype
	if (props.eventTalkId) {
		updateResource.submit({
			doctype: "Event Talk",
			name: props.eventTalkId,
			fieldname: {
				title: editForm.value.title,
				description: editForm.value.description,
			},
		});
	} else {
		updateResource.submit({
			doctype: "Talk Proposal",
			name: props.proposalId,
			fieldname: {
				title: editForm.value.title,
				description: editForm.value.description,
				phone: editForm.value.phone || "",
			},
		});
	}
};

// Initialize form with initial data when dialog opens
watch(
	() => props.open,
	(newValue) => {
		if (newValue) {
			editForm.value = {
				title: props.initialData.title || "",
				description: props.initialData.description || "",
				phone: props.initialData.phone || "",
			};
		}
	},
	{ immediate: true }
);

// Also watch for initialData changes
watch(
	() => props.initialData,
	(newData) => {
		if (props.open && newData) {
			editForm.value = {
				title: newData.title || "",
				description: newData.description || "",
				phone: newData.phone || "",
			};
		}
	},
	{ deep: true }
);
</script>
