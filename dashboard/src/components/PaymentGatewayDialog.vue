<template>
	<Dialog
		v-model="isOpen"
		:options="{
			title: __('Select Payment Method'),
			size: 'md',
		}"
	>
		<template #body-content>
			<div class="space-y-3">
				<div
					v-for="gateway in paymentGateways"
					:key="gateway"
					class="border border-outline-gray-2 rounded-lg p-4 cursor-pointer transition-all hover:border-outline-gray-3 hover:bg-surface-gray-1"
					:class="{
						'border-outline-gray-4 bg-surface-gray-2': selectedGateway === gateway,
					}"
					@click="selectedGateway = gateway"
				>
					<div class="flex items-center space-x-3">
						<input
							type="radio"
							:checked="selectedGateway === gateway"
							@change="selectedGateway = gateway"
							class="text-ink-gray-6"
						/>
						<div>
							<h3 class="font-semibold text-ink-gray-9">{{ gateway }}</h3>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end space-x-3">
				<Button variant="ghost" @click="closeDialog">{{ __("Cancel") }}</Button>
				<Button variant="solid" :disabled="!selectedGateway" @click="proceedToPayment">
					{{ __("Proceed to Pay") }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog } from "frappe-ui";
import { computed, type PropType, ref, watch } from "vue";

const props = defineProps({
	open: {
		type: Boolean,
		default: false,
	},
	paymentGateways: {
		type: Array as PropType<any[]>,
		required: true,
	},
});

const emit = defineEmits(["update:open", "gateway-selected"]);

const isOpen = computed({
	get: () => props.open,
	set: (val) => emit("update:open", val),
});

const selectedGateway = ref<any>(null);

// Reset selection when dialog opens
watch(
	() => props.open,
	(newVal) => {
		if (newVal) {
			selectedGateway.value = null;
		}
	}
);

const closeDialog = () => {
	isOpen.value = false;
	selectedGateway.value = null;
};

const proceedToPayment = () => {
	if (!selectedGateway.value) return;
	emit("gateway-selected", selectedGateway.value);
	closeDialog();
};
</script>
