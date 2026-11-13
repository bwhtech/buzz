<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import AddOnDrawer from "@/components/dashboard/add-ons/AddOnDrawer.vue"
import AddOnsSection from "@/components/dashboard/add-ons/AddOnsSection.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import RegistrationActions from "@/components/dashboard/events/RegistrationActions.vue"
import ApprovalModeCards from "@/components/dashboard/requests/ApprovalModeCards.vue"
import RequestSummaryCards from "@/components/dashboard/requests/RequestSummaryCards.vue"
import WaitlistSettings from "@/components/dashboard/requests/WaitlistSettings.vue"
import NewTicketTypeDrawer from "@/components/dashboard/ticket-types/NewTicketTypeDrawer.vue"
import TicketCategoryDialog from "@/components/dashboard/ticket-types/TicketCategoryDialog.vue"
import TicketTypeDrawer from "@/components/dashboard/ticket-types/TicketTypeDrawer.vue"
import TicketTypesSection from "@/components/dashboard/ticket-types/TicketTypesSection.vue"
import { useRegistrationRules } from "@/composables/useRegistrationRules"
import { useTicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import { useRequestCounts } from "@/data/requests"
import { useEventTicketTypes } from "@/data/ticketTypes"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError, TicketCategoryItem } from "@/types"

const eventId = useRoute().params.eventId as string

const page = useEventTicketTypes(eventId)

const organizer = useTicketTypeOrganizer(
	computed(() => page.data),
	() => page.reload(),
)

const rules = useRegistrationRules(eventId, page)
const counts = useRequestCounts(() => eventId)
const access = computed(() => ({
	mode: rules.mode.value,
	eventWaitlist: Boolean(page.data?.enable_waitlist),
}))

const newDrawerOpen = ref(false)
const addToCategory = ref("")

function openNewDrawer(category: string) {
	addToCategory.value = category
	newDrawerOpen.value = true
}

const categoryDialogOpen = ref(false)
const editedCategory = ref<TicketCategoryItem | null>(null)

function openCategoryDialog(category: TicketCategoryItem | null) {
	editedCategory.value = category
	categoryDialogOpen.value = true
}

// Held by name so a reload keeps the drawer pointing at fresh data.
const selectedName = ref<string | null>(null)

const selectedTicketType = computed(
	() => page.data?.ticket_types.find((row) => row.name === selectedName.value) ?? null,
)

const drawerOpen = computed<boolean>({
	get: () => selectedName.value !== null,
	set: (open) => !open && (selectedName.value = null),
})

const addOnDrawerOpen = ref(false)
// Empty while adding a new add-on.
const addOnName = ref("")
const selectedAddOn = computed(
	() => page.data?.add_ons.find((addOn) => addOn.name === addOnName.value) ?? null,
)

function openAddOnDrawer(name: string) {
	addOnName.value = name
	addOnDrawerOpen.value = true
}

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Registration" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<div v-if="page.loading && !page.data" class="space-y-3">
			<Skeleton class="h-6 w-24" />
			<Skeleton v-for="row in 2" :key="row" class="h-16 w-full rounded-4" />
		</div>

		<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

		<div v-else-if="page.data" class="space-y-10">
			<RequestSummaryCards v-if="page.data.can_write" :event="eventId" :counts="counts.data" />

			<TicketTypesSection
				:page="page.data"
				:organizer="organizer"
				@open="selectedName = $event"
				@add="openNewDrawer"
				@add-category="openCategoryDialog(null)"
				@edit-category="openCategoryDialog"
			/>

			<AddOnsSection :page="page.data" @open="openAddOnDrawer" @add="openAddOnDrawer('')" />

			<ApprovalModeCards
				:mode="rules.mode.value"
				:disabled="!page.data.can_write"
				@pick="rules.pickMode"
			/>

			<WaitlistSettings
				:enabled="page.data.enable_waitlist"
				:offer-hours="rules.offerHours.value"
				:disabled="!page.data.can_write"
				@toggle="rules.setWaitlist"
				@hours="rules.setOfferHours"
			/>
		</div>

		<template #sidebar>
			<RegistrationActions
				v-if="page.data"
				:event="eventId"
				:registration-link="page.data.registration_link"
				:registration-form="page.data.registration_form"
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
		:categories="page.data?.categories ?? []"
		:can-write="!!page.data?.can_write"
		:paid-events-enabled="!!page.data?.paid_events_enabled"
		:access="access"
		@changed="page.reload()"
	/>

	<AddOnDrawer
		v-model:open="addOnDrawerOpen"
		:event="eventId"
		:add-on="selectedAddOn"
		:ticket-types="page.data?.ticket_types ?? []"
		:paid-events-enabled="!!page.data?.paid_events_enabled"
		@changed="page.reload()"
	/>

	<TicketCategoryDialog
		v-model="categoryDialogOpen"
		:event="eventId"
		:category="editedCategory"
		@saved="page.reload()"
	/>

	<NewTicketTypeDrawer
		v-model:open="newDrawerOpen"
		:event="eventId"
		:category="addToCategory"
		:categories="page.data?.categories ?? []"
		:paid-events-enabled="!!page.data?.paid_events_enabled"
		:access="access"
		@created="page.reload()"
	/>
</template>
