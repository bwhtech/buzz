<script setup lang="ts">
import { Button, ErrorMessage, toast, useDoc, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import type { AddOnItem, TicketTypeItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"
import { matches } from "@/utils/formDraft"
import { serverErrorMessage } from "@/utils/serverError"

import AddOnFields from "./AddOnFields.vue"
import {
	type AddOnValues,
	addOnDocValues,
	addOnError,
	addOnValuesOf,
	blankAddOnValues,
} from "./addOnForm"

const DEFAULT_CURRENCY = "INR"

const props = defineProps<{
	event: string
	// null opens the drawer on a new add-on.
	addOn: AddOnItem | null
	ticketTypes: TicketTypeItem[]
	paidEventsEnabled: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [] }>()

const isNew = computed(() => !props.addOn)
const creator = useNewDoc<Record<string, unknown>>("Ticket Add-on")
const addOnDoc = useDoc<Record<string, unknown> & { name: string }>({
	doctype: "Ticket Add-on",
	name: () => props.addOn?.name ?? "",
	immediate: false,
})
const enabledCurrencies = useEnabledCurrencies()

const draft = ref<AddOnValues>(blankAddOnValues(DEFAULT_CURRENCY))
const hasChanges = computed(
	() => isNew.value || !matches(draft.value, addOnValuesOf(props.addOn as AddOnItem)),
)
const validationError = computed(() => addOnError(draft.value))
// Shown only after a save attempt, then live until the drawer reopens.
const showValidationError = ref(false)
const serverError = ref("")
const shownError = computed(
	() => serverError.value || (showValidationError.value ? validationError.value : null),
)
const saving = computed(() => creator.loading || addOnDoc.setValue.loading)

function defaultCurrency() {
	const names = (enabledCurrencies.data ?? []).map((currency) => currency.name)
	return names.includes(DEFAULT_CURRENCY) ? DEFAULT_CURRENCY : (names[0] ?? DEFAULT_CURRENCY)
}

watch(open, (opened) => {
	if (!opened) return
	draft.value = props.addOn ? addOnValuesOf(props.addOn) : blankAddOnValues(defaultCurrency())
	showValidationError.value = false
	serverError.value = ""
	creator.reset()
})

async function submitValues(values: ReturnType<typeof addOnDocValues>) {
	if (!isNew.value) {
		await addOnDoc.setValue.submit(values).catch(() => null)
		return addOnDoc.setValue.error
	}
	Object.assign(creator.doc, { event: props.event, ...values })
	await creator.submit().catch(() => null)
	return creator.error
}

async function save() {
	showValidationError.value = true
	serverError.value = ""
	if (validationError.value || saving.value) return
	const error = await submitValues(addOnDocValues(draft.value, props.paidEventsEnabled))
	if (error) {
		serverError.value = serverErrorMessage(error) || "Could not save the add-on. Try again."
		return
	}
	toast.success(isNew.value ? "Add-on added" : "Add-on updated")
	emit("changed")
	open.value = false
}
</script>

<template>
	<SponsorshipDrawer
		v-model:open="open"
		:title="addOn?.title ?? 'New add-on'"
		:description="addOn ? formatWholePriceOrFree(addOn.price, addOn.currency) : ''"
	>
		<AddOnFields
			v-model="draft"
			:ticket-types="ticketTypes"
			:paid-events-enabled="paidEventsEnabled"
			:show-enabled="!isNew"
		/>

		<template v-if="hasChanges" #footer>
			<div class="flex w-full flex-wrap items-center justify-end gap-x-4 gap-y-2">
				<ErrorMessage class="text-right" :message="shownError ?? undefined" />
				<div class="flex justify-end gap-2 max-sm:w-full max-sm:[&>*]:flex-1">
					<Button size="md" label="Cancel" @click="open = false" />
					<Button
						size="md"
						variant="solid"
						:label="isNew ? 'Add add-on' : 'Save changes'"
						:loading="saving"
						@click="save"
					/>
				</div>
			</div>
		</template>
	</SponsorshipDrawer>
</template>
