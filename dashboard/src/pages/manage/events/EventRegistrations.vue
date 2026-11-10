<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import RegistrationActions from "@/components/dashboard/events/RegistrationActions.vue"
import NewTicketTypeDrawer from "@/components/dashboard/ticket-types/NewTicketTypeDrawer.vue"
import TicketCategoryDialog from "@/components/dashboard/ticket-types/TicketCategoryDialog.vue"
import TicketTypeDrawer from "@/components/dashboard/ticket-types/TicketTypeDrawer.vue"
import TicketTypesSection from "@/components/dashboard/ticket-types/TicketTypesSection.vue"
import { useTicketTypeOrganizer } from "@/composables/useTicketTypeOrganizer"
import { useEventTicketTypes } from "@/data/ticketTypes"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError, TicketCategoryItem } from "@/types"

const eventId = useRoute().params.eventId as string

const page = useEventTicketTypes(eventId)

const organizer = useTicketTypeOrganizer(
	computed(() => page.data),
	() => page.reload(),
)

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

		<div v-else-if="page.data" class="space-y-8">
			<TicketTypesSection
				:page="page.data"
				:organizer="organizer"
				@open="selectedName = $event"
				@add="openNewDrawer"
				@add-category="openCategoryDialog(null)"
				@edit-category="openCategoryDialog"
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
				:requires-approval="page.data.requires_approval"
				:enable-waitlist="page.data.enable_waitlist"
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
		@created="page.reload()"
	/>
</template>
