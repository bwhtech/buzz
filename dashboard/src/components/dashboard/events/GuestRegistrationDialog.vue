<script setup lang="ts">
import { updateEvent } from "@/data/events";
import type { FrappeError } from "@/types";
import { Button, Dialog, FormControl, Switch, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ event: string; allowed: boolean; verification: string | null }>();
const isOpen = defineModel<boolean>({ required: true });
const emit = defineEmits<{ saved: [] }>();

const allowing = ref(false);
const verifying = ref(false);
const method = ref("Email OTP");

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (updateEvent.error as FrappeError | null)?.message);

watch(isOpen, (open) => {
	if (!open) return;
	allowing.value = props.allowed;
	// "None" is the stored way of saying nobody is verified, so it is not a method.
	verifying.value = Boolean(props.verification) && props.verification !== "None";
	method.value = verifying.value ? props.verification! : "Email OTP";
	updateEvent.error = null;
});

async function confirm() {
	await updateEvent.submit({
		doctype: "Buzz Event",
		name: props.event,
		fieldname: {
			allow_guest_booking: Number(allowing.value),
			guest_verification_method: verifying.value ? method.value : "None",
		},
	});
	if (updateEvent.error) return;

	toast.success(allowing.value ? "Guest registration is on" : "Guest registration is off");
	emit("saved");
	isOpen.value = false;
}
</script>

<template>
	<Dialog v-model="isOpen">
		<div class="space-y-4">
			<span
				class="grid size-11 place-items-center rounded-full bg-surface-gray-2"
				aria-hidden="true"
			>
				<span class="lucide-hat-glasses size-5 text-ink-gray-7" />
			</span>

			<div class="space-y-2">
				<h2 class="text-xl font-semibold text-ink-gray-9">Guest Registration</h2>
				<p class="text-base text-ink-gray-6">
					Let visitors register without an account. Turn it off and everyone has to sign
					in first.
				</p>
			</div>

			<Switch v-model="allowing" label="Allow Guest Registration" />

			<template v-if="allowing">
				<Switch v-model="verifying" label="Verify Guests" />

				<FormControl
					v-if="verifying"
					v-model="method"
					type="select"
					label="Verify by"
					:options="['Email OTP', 'Phone OTP']"
				/>
			</template>

			<ErrorMessage v-if="errorMessage" :message="errorMessage" />

			<Button
				variant="solid"
				label="Confirm"
				class="w-full"
				:loading="updateEvent.loading"
				@click="confirm"
			/>
		</div>
	</Dialog>
</template>
