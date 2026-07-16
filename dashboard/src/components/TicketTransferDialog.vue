<template>
	<Dialog v-model="isOpen">
		<template #body-title>
			<h3 class="text-xl font-semibold text-ink-gray-9">{{ __("Transfer Ticket") }}</h3>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-ink-gray-7">
					{{
						__(
							"Transfer this ticket to a new attendee. The new attendee will receive the updated ticket information."
						)
					}}
				</p>

				<FormControl
					type="text"
					:label="__('First Name')"
					:placeholder="__('Enter first name')"
					v-model="transferForm.first_name"
					:required="true"
				/>

				<FormControl
					type="text"
					:label="__('Last Name')"
					:placeholder="__('Enter last name')"
					v-model="transferForm.last_name"
				/>

				<FormControl
					type="email"
					:label="__('New Attendee Email')"
					:placeholder="__('Enter email address')"
					v-model="transferForm.email"
					:required="true"
				/>
			</div>
		</template>
		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					@click="handleTransferTicket"
					:loading="transferResource.loading"
					:disabled="!transferForm.first_name || !transferForm.email"
				>
					{{ __("Transfer Ticket") }}
				</Button>
				<Button variant="outline" @click="close"> {{ __("Cancel") }} </Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	ticket: {
		type: Object,
		default: null,
	},
});

const emit = defineEmits(["update:modelValue", "success"]);

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const transferForm = ref({
	first_name: "",
	last_name: "",
	email: "",
});

// Transfer ticket resource
const transferResource = createResource({
	url: "buzz.api.transfer_ticket",
	onSuccess: () => {
		toast.success(__("Ticket transferred successfully!"));
		isOpen.value = false;
		resetTransferForm();
		emit("success");
	},
	onError: (error: FrappeError) => {
		toast.error(`${__("Failed to transfer ticket")}: ${error.message}`);
	},
});

const handleTransferTicket = () => {
	if (!props.ticket || !transferForm.value.first_name || !transferForm.value.email) {
		toast.error(__("Please fill in all required fields"));
		return;
	}

	transferResource.submit({
		ticket_id: props.ticket.name,
		new_first_name: transferForm.value.first_name,
		new_last_name: transferForm.value.last_name || "",
		new_email: transferForm.value.email,
	});
};

const resetTransferForm = () => {
	transferForm.value = {
		first_name: "",
		last_name: "",
		email: "",
	};
};

// Reset form when dialog is closed
watch(isOpen, (newValue) => {
	if (!newValue) {
		resetTransferForm();
	}
});
</script>
