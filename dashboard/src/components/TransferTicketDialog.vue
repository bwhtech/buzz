<template>
	<Dialog v-model="isOpen">
		<template #body-title>
			<h3 class="text-xl font-semibold text-ink-gray-9">Transfer Ticket</h3>
		</template>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-ink-gray-7">
					Transfer this ticket to a new attendee. The new attendee will receive the
					updated ticket information.
				</p>

				<FormControl
					type="text"
					label="New Attendee Name"
					placeholder="Enter full name"
					v-model="transferForm.name"
					:required="true"
				/>

				<FormControl
					type="email"
					label="New Attendee Email"
					placeholder="Enter email address"
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
					:disabled="!transferForm.name || !transferForm.email"
				>
					Transfer Ticket
				</Button>
				<Button variant="outline" @click="close"> Cancel </Button>
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
	name: "",
	email: "",
});

// Transfer ticket resource
const transferResource = createResource({
	url: "buzz.api.transfer_ticket",
	onSuccess: () => {
		toast.success("Ticket transferred successfully!");
		isOpen.value = false;
		resetTransferForm();
		emit("success");
	},
	onError: (error: FrappeError) => {
		toast.error(`Failed to transfer ticket: ${error.message}`);
	},
});

const handleTransferTicket = () => {
	if (!props.ticket || !transferForm.value.name || !transferForm.value.email) {
		toast.error("Please fill in all required fields");
		return;
	}

	transferResource.submit({
		ticket_id: props.ticket.name,
		new_name: transferForm.value.name,
		new_email: transferForm.value.email,
	});
};

const resetTransferForm = () => {
	transferForm.value = {
		name: "",
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
