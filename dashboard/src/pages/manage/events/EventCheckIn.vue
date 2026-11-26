<script setup lang="ts">
import { ErrorMessage, useCall } from "frappe-ui"
import { NumberCard } from "frappe-ui/charts"
import { useRoute, useRouter } from "vue-router"

import CheckInZoneCards from "@/components/dashboard/events/checkin-zones/CheckInZoneCards.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import QuickActionTile from "@/components/dashboard/events/QuickActionTile.vue"
import { useCanWriteEvent, useEventAccess } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { EventGuests, FrappeError } from "@/types"

const eventId = useRoute().params.eventId as string
const router = useRouter()

// One guest row is enough: the page needs the totals and per-zone counts, not the list.
const summary = useCall<EventGuests, { event: string; limit: number }>({
	url: "/api/v2/method/buzz.api.events.get_event_guests",
	params: { event: eventId, limit: 1 },
})
const canWrite = useCanWriteEvent(eventId)
const access = useEventAccess(() => eventId)
access.fetch()

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<EventPageHeader :title="summary.data?.title" section="Check-in" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<NumberCard
			class="!rounded-5 !border-outline-gray-2 !bg-surface-base sm:max-w-xs"
			:title="__('Checked in')"
			:value="summary.data ? (summary.data.checked_in_any_zone ?? 0) : null"
			:target="summary.data?.total ?? 0"
			:loading="summary.loading && !summary.data"
		/>
		<ErrorMessage :message="message(summary.error)" />

		<section class="space-y-3">
			<div>
				<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Check-in zones") }}</h2>
				<p class="mt-1 text-p-base text-ink-gray-5">
					{{ __("Areas of the venue guests are checked in to, such as entry, workshops or lunch") }}
				</p>
			</div>
			<CheckInZoneCards
				:event="eventId"
				:stats="summary.data?.zones ?? []"
				:read-only="!canWrite.data?.has_permission"
				@changed="summary.reload()"
			/>
		</section>

		<template v-if="access.data?.guests === 'Edit'" #sidebar>
			<h3 class="text-p-sm font-medium text-ink-gray-5">{{ __("Quick actions") }}</h3>
			<QuickActionTile
				icon="lucide-scan-line"
				:title="__('Check in guests')"
				:subtitle="__('Scan tickets or search by name')"
				tone="green"
				@click="router.push({ name: 'check-in', params: { eventName: eventId } })"
			/>
		</template>
	</PageWithSidebar>
</template>
