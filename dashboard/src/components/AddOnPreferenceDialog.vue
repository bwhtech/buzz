<template>
	<Dialog v-model="show" :title="__('Update Add-on Preferences')" size="lg">
		<div class="space-y-4">
			<p class="text-ink-gray-8">
				Update your add-on preferences for <strong>{{ ticket.attendee_name }}</strong>
			</p>

			<div v-if="addOnsWithOptions.length === 0" class="text-center py-4">
				<p class="text-ink-gray-6">No customizable add-ons found for this ticket.</p>
			</div>

			<div v-else class="space-y-4">
				<div v-for="addon in addOnsWithOptions" :key="addon.id" class="space-y-2">
					<label class="block text-sm-medium text-ink-gray-8">
						{{ __(addon.title ?? "") }}
					</label>
					<p class="text-xs text-ink-gray-6 mb-2">Current: {{ addon.value }}</p>
					<FormControl
						type="select"
						:options="addon.selectOptions"
						v-model="preferences[addon.id ?? '']"
						:placeholder="`Select ${(addon.title ?? '').toLowerCase()}`"
					/>
				</div>
			</div>
		</div>

		<template #actions="{ close }">
			<div class="flex space-x-2">
				<Button
					variant="solid"
					:loading="savePreferences.loading"
					:disabled="!hasChanges || addOnsWithOptions.length === 0"
					@click="handleSave"
				>
					Save Preferences
				</Button>
				<Button variant="outline" @click="close">Cancel</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import type { FrappeError, TicketAddOn } from "@/types";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { type PropType, computed, ref, watch } from "vue";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	ticket: {
		type: Object as PropType<{ add_ons?: TicketAddOn[]; attendee_name?: string }>,
		required: true,
	},
});

const emit = defineEmits(["update:modelValue", "success"]);

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const preferences = ref<Record<string, any>>({});

// Filter add-ons that have selectable options
const addOnsWithOptions = computed(() => {
	if (!props.ticket?.add_ons) return [];

	return props.ticket.add_ons
		.filter((addon: TicketAddOn) => addon.options && addon.options.length > 0)
		.map((addon: TicketAddOn) => ({
			...addon,
			selectOptions: (addon.options ?? []).map((option: string) => ({
				label: __(option),
				value: option,
			})),
		}));
});

// Check if user has made any changes
const hasChanges = computed(() => {
	return addOnsWithOptions.value.some((addon) => {
		const currentValue = preferences.value[addon.id ?? ""];
		return currentValue && currentValue !== addon.value;
	});
});

// Initialize preferences when dialog opens
watch(
	() => props.modelValue,
	(newValue) => {
		if (newValue && addOnsWithOptions.value.length > 0) {
			preferences.value = {};
			for (const addon of addOnsWithOptions.value) {
				preferences.value[addon.id ?? ""] = addon.value;
			}
		}
	},
	{ immediate: true }
);

const savePreferences = createResource({
	url: "buzz.api.change_add_on_preference",
	onSuccess: () => {
		toast.success("Add-on preferences updated successfully!");
		emit("success");
		show.value = false;
	},
	onError: (error: FrappeError) => {
		// Check if this is the specific error about change window closing
		if (error?.message?.includes("change window has closed")) {
			toast.error(
				"Add-on changes are not allowed at this time - the change window has closed as the event is approaching."
			);
		} else {
			toast.error("Failed to update preferences");
		}
		console.error("Error updating add-on preferences:", error);
	},
});

const handleSave = async () => {
	const changes = addOnsWithOptions.value.filter((addon) => {
		const newValue = preferences.value[addon.id ?? ""];
		return newValue && newValue !== addon.value;
	});

	if (changes.length === 0) {
		toast.warning("No changes to save");
		return;
	}

	// Save each changed preference
	for (const addon of changes) {
		const newValue = preferences.value[addon.id ?? ""];
		await savePreferences.submit({
			add_on_id: addon.id,
			new_value: newValue,
		});
	}
};
</script>
