<script setup lang="ts">
import { updateEvent } from "@/data/events";
import type { FrappeError } from "@/types";
import { nowInZone } from "@/utils/timeZones";
import { Button, Dialog, Switch, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ event: string; timeZone: string | null; closed: boolean }>();
const isOpen = defineModel<boolean>({ required: true });
const emit = defineEmits<{ saved: [] }>();

const accepting = ref(false);

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (updateEvent.error as FrappeError | null)?.message);

watch(isOpen, (open) => {
	if (!open) return;
	accepting.value = !props.closed;
	updateEvent.error = null;
});

async function confirm() {
	// There is no accept-registrations flag: closing means "closed as of right now", read
	// in the event's own timezone, and reopening clears the cutoff altogether.
	const registrations_close_at = accepting.value ? null : nowInZone(props.timeZone);

	await updateEvent.submit({
		doctype: "Buzz Event",
		name: props.event,
		fieldname: { registrations_close_at },
	});
	if (updateEvent.error) return;

	toast.success(accepting.value ? "Registration is open" : "Registration is closed");
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
				<span class="lucide-ticket-check size-5 text-ink-gray-7" />
			</span>

			<div class="space-y-2">
				<h2 class="text-xl font-semibold text-ink-gray-9">Registration</h2>
				<p class="text-base text-ink-gray-6">
					Close registration to stop accepting new guests, including anyone who's been
					invited.
				</p>
				<p class="text-base text-ink-gray-6">
					Ticket limits only apply while registration is open.
				</p>
			</div>

			<Switch v-model="accepting" label="Accept Registration" />

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
