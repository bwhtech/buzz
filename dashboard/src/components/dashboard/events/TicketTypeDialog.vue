<script setup lang="ts">
import { useCurrencies } from "@/data/tickets";
import type { TicketType } from "@/types";
import { Button, Dialog, FormControl, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

// The list on the page owns the insert, so creating a tier refreshes it for free.
const props = defineProps<{
	event: string;
	insert: (doc: Partial<TicketType> & Record<string, unknown>) => Promise<unknown>;
}>();
const isOpen = defineModel<boolean>({ required: true });

const currencies = useCurrencies();

const title = ref("");
// Held as typed rather than as numbers: an empty capacity means unlimited, and an
// empty price is a field nobody filled in — neither survives a cast to 0.
const price = ref("");
const currency = ref("INR");
const capacity = ref("");
const showErrors = ref(false);
const saving = ref(false);
const failure = ref("");

const currencyOptions = computed(() => currencies.data?.map((row) => row.name) ?? ["INR"]);

const problem = computed(() => {
	if (!title.value.trim()) return "A ticket type needs a title.";
	if (price.value === "") return "A ticket type needs a price. Enter 0 to make it free.";
	if (capacity.value !== "" && Number(capacity.value) < 1)
		return "Leave the capacity empty for unlimited tickets.";
	return "";
});

watch(isOpen, (open) => {
	if (!open) return;
	title.value = "";
	price.value = "";
	currency.value = "INR";
	capacity.value = "";
	showErrors.value = false;
	failure.value = "";
});

async function submit() {
	showErrors.value = true;
	if (problem.value) return;

	saving.value = true;
	failure.value = "";
	try {
		await props.insert({
			event: props.event,
			title: title.value.trim(),
			price: Number(price.value),
			currency: currency.value,
			// The doctype spells unlimited as 0.
			max_tickets_available: capacity.value === "" ? 0 : Number(capacity.value),
		});
	} catch (error) {
		failure.value = (error as Error).message;
		return;
	} finally {
		saving.value = false;
	}

	toast.success(`${title.value.trim()} added`);
	isOpen.value = false;
}
</script>

<template>
	<Dialog v-model="isOpen" title="New ticket type">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl
				v-model="title"
				label="Title"
				placeholder="Early Bird"
				autocomplete="off"
				required
			/>

			<div class="grid grid-cols-[1fr_auto] gap-3">
				<FormControl
					v-model="price"
					type="number"
					min="0"
					label="Price"
					placeholder="0"
					required
				/>
				<FormControl
					v-model="currency"
					type="select"
					label="Currency"
					:options="currencyOptions"
				/>
			</div>

			<FormControl
				v-model="capacity"
				type="number"
				min="1"
				label="Ticket capacity"
				placeholder="Unlimited"
			/>

			<p v-if="showErrors && problem" class="text-sm text-ink-red-4">{{ problem }}</p>
			<ErrorMessage v-else-if="failure" :message="failure" />

			<!-- type=button: inside a form, a submit button would run `submit` twice — once on
				 click, once on the form's own submit — and the second insert collides with the
				 tier the first one just created. -->
			<Button
				type="button"
				variant="solid"
				label="Create ticket type"
				class="w-full"
				:loading="saving"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>

<style scoped>
/* The stepper arrows crowd a field that is typed into, not nudged. */
:deep(input[type="number"]) {
	appearance: textfield;
}

:deep(input[type="number"]::-webkit-inner-spin-button),
:deep(input[type="number"]::-webkit-outer-spin-button) {
	appearance: none;
	margin: 0;
}
</style>
