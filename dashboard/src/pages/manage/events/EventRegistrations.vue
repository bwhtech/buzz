<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { Button, ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import ListSection from "@/components/common/ListSection.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import RegistrationActions from "@/components/dashboard/events/RegistrationActions.vue"
import AddPricedItemDialog from "@/components/dashboard/sponsorships/AddPricedItemDialog.vue"
import TaxSettings from "@/components/dashboard/ticket-types/TaxSettings.vue"
import TicketTypeDrawer from "@/components/dashboard/ticket-types/TicketTypeDrawer.vue"
import TicketTypeList from "@/components/dashboard/ticket-types/TicketTypeList.vue"
import { useTaxSettingsForm } from "@/composables/useTaxSettingsForm"
import { useEventTicketTypes } from "@/data/ticketTypes"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const eventId = useRoute().params.eventId as string

const page = useEventTicketTypes(eventId)

const taxForm = useTaxSettingsForm(
	eventId,
	computed(() => page.data ?? undefined),
	() => page.reload(),
)

// The page's own save takes the shortcut, as on the Details page.
useEventListener(document, "keydown", (stroke: KeyboardEvent) => {
	if (stroke.key !== "s" || !(stroke.metaKey || stroke.ctrlKey) || stroke.altKey) return
	stroke.preventDefault()
	if (!stroke.repeat) taxForm.save()
})

const addDialogOpen = ref(false)

const addAction = computed(() =>
	page.data?.can_write
		? {
				label: "Add",
				variant: "outline" as const,
				iconLeft: "lucide-plus",
				onClick: () => (addDialogOpen.value = true),
			}
		: null,
)

// Held by name so a reload keeps the drawer pointing at fresh data.
const selectedName = ref<string | null>(null)

const selectedTicketType = computed(
	() => page.data?.ticket_types.find((row) => row.name === selectedName.value) ?? null,
)

const drawerOpen = computed<boolean>({
	get: () => selectedName.value !== null,
	set: (open) => !open && (selectedName.value = null),
})

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Registration">
		<Transition
			enter-active-class="transition duration-150 ease-out motion-reduce:transition-none"
			enter-from-class="opacity-0 translate-y-1"
			leave-active-class="transition duration-100 ease-out motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<Button
				v-if="taxForm.isDirty.value"
				variant="solid"
				label="Save"
				:loading="taxForm.update.loading"
				@click="taxForm.save"
			/>
		</Transition>

		<template #leading>
			<Button v-if="taxForm.isDirty.value" label="Discard" @click="taxForm.discard" />
		</template>
	</EventPageHeader>

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<div v-if="page.loading && !page.data" class="space-y-3">
			<Skeleton class="h-6 w-24" />
			<Skeleton v-for="row in 2" :key="row" class="h-16 w-full rounded-4" />
		</div>

		<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

		<div v-else-if="page.data" class="space-y-8">
			<ListSection
				title="Ticket Types"
				description="Types of tickets that a participant can buy for this event"
				:count="page.data.ticket_types.length"
				:action="addAction"
				:empty="!page.data.ticket_types.length"
				empty-title="No ticket types yet"
				empty-description="Add one so people can register."
				empty-icon="lucide-ticket"
			>
				<TicketTypeList
					:ticket-types="page.data.ticket_types"
					:can-write="page.data.can_write"
					@open="selectedName = $event"
				/>
			</ListSection>

			<TaxSettings
				:event="eventId"
				:form="taxForm"
				:can-write="page.data.can_write"
				:has-tax-details="page.data.team_has_tax_details"
				:can-edit-team="page.data.can_edit_team"
				@tax-details-added="page.reload()"
			/>
		</div>

		<template #sidebar>
			<RegistrationActions
				v-if="page.data"
				:event="eventId"
				:registration-link="page.data.registration_link"
				:closed="page.data.registrations_closed"
				:can-write="page.data.can_write"
				:allow-guest-booking="page.data.allow_guest_booking"
				:guest-verification-method="page.data.guest_verification_method"
				@changed="page.reload()"
			/>
		</template>
	</PageWithSidebar>

	<TicketTypeDrawer
		v-model:open="drawerOpen"
		:event="eventId"
		:ticket-type="selectedTicketType"
		:can-write="!!page.data?.can_write"
		@changed="page.reload()"
	/>

	<AddPricedItemDialog
		v-model="addDialogOpen"
		:event="eventId"
		doctype="Event Ticket Type"
		item-label="Ticket Type"
		placeholder="General admission"
		@saved="page.reload()"
	/>
</template>
