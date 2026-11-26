<script setup lang="ts">
import { Button, ErrorMessage, toast, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useEnabledCurrencies } from "@/data/currencies"
import { useSetTicketTypeAccess } from "@/data/ticketTypes"
import type { TicketCategoryItem } from "@/types"
import { type TicketTypeAccess, accessChanged, withEventAccess } from "@/utils/approvalMode"
import { serverErrorMessage } from "@/utils/serverError"
import {
	type TicketTypeValues,
	blankTicketTypeValues,
	ticketTypeDocValues,
	ticketTypeError,
} from "@/utils/ticketTypeForm"

import TicketTypeFields from "./TicketTypeFields.vue"

const DEFAULT_CURRENCY = "INR"

const props = defineProps<{
	event: string
	// The category the ticket type is added to; empty for uncategorized.
	category: string
	categories: TicketCategoryItem[]
	access: TicketTypeAccess
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ created: []; categoryCreated: [] }>()

const creator = useNewDoc<Record<string, unknown> & { name?: string }>("Event Ticket Type")
const accessSetter = useSetTicketTypeAccess()
const enabledCurrencies = useEnabledCurrencies()

const blankValues = (category: string, currency: string) =>
	withEventAccess(blankTicketTypeValues(category, currency), props.access)
const draft = ref<TicketTypeValues>(blankValues("", DEFAULT_CURRENCY))
const validationError = computed(() => ticketTypeError(draft.value))
// Shown only after a create attempt, then live until the drawer reopens.
const showValidationError = ref(false)

function defaultCurrency() {
	const names = (enabledCurrencies.data ?? []).map((currency) => currency.name)
	return names.includes(DEFAULT_CURRENCY) ? DEFAULT_CURRENCY : (names[0] ?? DEFAULT_CURRENCY)
}

watch(open, (opened) => {
	if (!opened) return
	draft.value = blankValues(props.category, defaultCurrency())
	showValidationError.value = false
	creator.reset()
})

async function create() {
	showValidationError.value = true
	if (validationError.value || creator.loading) return
	Object.assign(creator.doc, { event: props.event, ...ticketTypeDocValues(draft.value) })
	const doc = await creator.submit().catch(() => null)
	if (creator.error) {
		toast.error(serverErrorMessage(creator.error))
		return
	}
	// The ticket type exists by now, so a failure here must not invite a second create.
	if (doc?.name && accessChanged(blankValues("", ""), draft.value))
		await accessSetter
			.save(String(doc.name), draft.value)
			.catch((error) =>
				toast.error(`Approval and waitlist were not saved. ${serverErrorMessage(error)}`),
			)
	toast.success("Ticket type added")
	emit("created")
	open.value = false
}
</script>

<template>
	<SponsorshipDrawer
		v-model:open="open"
		title="New ticket type"
		description=""
		:close-on-outside-click="false"
	>
		<TicketTypeFields
			v-model="draft"
			:categories="categories"
			hideable
			@category-created="emit('categoryCreated')"
		/>

		<template #footer>
			<div class="flex w-full flex-wrap items-center justify-end gap-x-4 gap-y-2">
				<ErrorMessage
					v-if="showValidationError"
					class="text-right"
					:message="validationError ?? undefined"
				/>
				<div class="flex justify-end gap-2 max-sm:w-full max-sm:[&>*]:flex-1">
					<Button size="md" label="Cancel" @click="open = false" />
					<Button
						size="md"
						variant="solid"
						label="Create"
						:loading="creator.loading"
						@click="create"
					/>
				</div>
			</div>
		</template>
	</SponsorshipDrawer>
</template>
