<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { Button, ErrorMessage, Skeleton, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import TicketTypeRow from "@/components/dashboard/ticket-types/TicketTypeRow.vue"
import { useEventTicketTypes, useSaveEventTicketTypes } from "@/data/ticketTypes"
import type { TicketTypeDraft, TicketTypeInput, TicketTypeItem } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const eventId = useRoute().params.eventId as string

const page = useEventTicketTypes(eventId)
const saveTicketTypes = useSaveEventTicketTypes()

const savedTicketTypes = ref<TicketTypeItem[]>([])
const drafts = ref<TicketTypeDraft[]>([])
const openKey = ref<string | null>(null)
let newTicketTypeCount = 0

const canWrite = computed(() => Boolean(page.data?.can_write))

const toDraft = (row: TicketTypeItem): TicketTypeDraft => ({ ...row, key: row.name })

const toInput = (draft: TicketTypeDraft): TicketTypeInput => ({
	name: draft.name,
	title: draft.title.trim(),
	price: draft.price,
	max_tickets_available: draft.max_tickets_available,
	auto_unpublish_after: draft.auto_unpublish_after || null,
	is_published: draft.is_published,
})

const isDirty = computed(
	() =>
		JSON.stringify(drafts.value.map(toInput)) !==
		JSON.stringify(savedTicketTypes.value.map(toDraft).map(toInput)),
)

const canSave = computed(
	() => isDirty.value && drafts.value.every((draft) => draft.title.trim() && draft.price >= 0),
)

function reset(rows: TicketTypeItem[]) {
	savedTicketTypes.value = rows
	drafts.value = rows.map(toDraft)
}

watch(
	() => page.data,
	(data) => data && !isDirty.value && reset(data.ticket_types),
	{ immediate: true },
)

function toggle(key: string) {
	openKey.value = openKey.value === key ? null : key
}

function addTicketType() {
	const key = `new-${++newTicketTypeCount}`
	drafts.value.push({
		key,
		name: null,
		title: "",
		price: 0,
		currency: "INR",
		max_tickets_available: 0,
		auto_unpublish_after: null,
		is_published: true,
		tickets_sold: 0,
	})
	openKey.value = key
}

function removeTicketType(key: string) {
	drafts.value = drafts.value.filter((draft) => draft.key !== key)
}

function discard() {
	reset(savedTicketTypes.value)
	openKey.value = null
}

async function save() {
	if (!canSave.value || saveTicketTypes.loading) return
	const result = await saveTicketTypes
		.submit({ event: eventId, ticket_types: drafts.value.map(toInput) })
		.catch(() => null)
	if (saveTicketTypes.error || !result) return
	reset(result.ticket_types)
	openKey.value = null
	toast.success("Tickets saved")
}

useEventListener(window, "beforeunload", (unload: BeforeUnloadEvent) => {
	if (isDirty.value) unload.preventDefault()
})

useEventListener(document, "keydown", (stroke: KeyboardEvent) => {
	if (stroke.key !== "s" || !(stroke.metaKey || stroke.ctrlKey) || stroke.altKey) return
	stroke.preventDefault()
	if (!stroke.repeat) save()
})

const errorMessage = computed(() => serverErrorMessage(saveTicketTypes.error || page.error))
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Tickets">
		<Button
			v-if="isDirty"
			variant="solid"
			label="Save tickets"
			:disabled="!canSave"
			:loading="saveTicketTypes.loading"
			@click="save"
		/>
		<template #leading>
			<Button v-if="isDirty" label="Discard" @click="discard" />
		</template>
	</EventPageHeader>

	<div class="m-auto w-full max-w-[720px] space-y-6 px-4 py-8">
		<EventArchivedAlert :event="eventId" />

		<div>
			<h2 class="text-xl font-semibold text-ink-gray-9">Tickets</h2>
			<p class="mt-1 text-p-base text-ink-gray-5">
				What people can buy for this event. Prices are in INR.
			</p>
		</div>

		<ErrorMessage v-if="errorMessage" :message="errorMessage" />

		<div v-if="page.loading && !page.data" class="space-y-2">
			<Skeleton v-for="row in 3" :key="row" class="h-16 w-full rounded-4" />
		</div>

		<div v-else-if="page.data" class="space-y-1">
			<TicketTypeRow
				v-for="(draft, index) in drafts"
				:key="draft.key"
				v-model:ticket-type="drafts[index]"
				:open="openKey === draft.key"
				:can-write="canWrite"
				@toggle="toggle(draft.key)"
				@remove="removeTicketType(draft.key)"
			/>
			<p v-if="!drafts.length" class="px-4 py-3 text-p-base text-ink-gray-5">
				No ticket types yet.
			</p>
			<Button
				v-if="canWrite"
				variant="ghost"
				icon-left="lucide-plus"
				label="Add ticket type"
				class="mt-2"
				@click="addTicketType"
			/>
		</div>
	</div>
</template>
