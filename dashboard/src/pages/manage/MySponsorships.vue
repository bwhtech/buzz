<script setup lang="ts">
import { useRouteQuery } from "@vueuse/router"
import { dayjs } from "frappe-ui"
import { computed } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import MyEnquiryCard from "@/components/dashboard/sponsorships/mine/MyEnquiryCard.vue"
import MyEnquiryDrawer from "@/components/dashboard/sponsorships/mine/MyEnquiryDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useDrawerSelection } from "@/composables/useDrawerSelection"
import { useOpenFromQuery } from "@/composables/useOpenFromQuery"
import { usePaymentSuccess } from "@/composables/usePaymentSuccess"
import { useMySponsorships } from "@/data/sponsorships"
import type { SponsorshipWithEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { inTab, useTimelineTabQuery } from "@/utils/timelineTabs"

const tab = useTimelineTabQuery()

const mySponsorships = useMySponsorships()

const drawer = useDrawerSelection<SponsorshipWithEvent>()

// An enquiry whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(mySponsorships.data || []).filter((enquiry): enquiry is SponsorshipWithEvent =>
		Boolean(enquiry.start_date && enquiry.event_title),
	),
)

// Plain dayjs: these are date-only values, and dayjsLocal shifts them a day back.
const months = computed(() =>
	groupEventsByMonth(inTab(dated.value, tab.value, dayjs().format("YYYY-MM-DD"))),
)

// The open drawer holds the row it was handed, so point it at the refreshed one.
async function refresh() {
	await mySponsorships.reload()
	const fresh = dated.value.find((enquiry) => enquiry.name === drawer.selected.value?.name)
	if (fresh) drawer.selected.value = fresh
}

// Back from the payment page: celebrate only once the enquiry is actually paid. The
// parameter is dropped in the same tick as ?enquiry=, so the two land in one replace.
const success = useRouteQuery<string | null>("success", null)
const payment = usePaymentSuccess({ checkOnMount: false, cleanupUrl: false })

function openFromLink(enquiry: SponsorshipWithEvent) {
	drawer.show(enquiry)
	if (success.value === "true" && enquiry.status === "Paid") payment.triggerSuccessFlow()
	success.value = null
}

useOpenFromQuery(
	"enquiry",
	(id) => dated.value.find((enquiry) => enquiry.name === id),
	openFromLink,
)

const emptyDescription = computed(() =>
	tab.value === "upcoming"
		? "Sponsorship enquiries you file for events will show up here."
		: "Enquiries you filed for past events will show up here.",
)
</script>

<template>
	<CreateEventHeader title="Sponsorship" />

	<TimelineList
		v-model:tab="tab"
		heading="Sponsorship"
		icon="lucide-handshake"
		noun="enquiries"
		:months="months"
		:loading="mySponsorships.loading"
		:error="mySponsorships.error"
	>
		<template #empty-state>
			<EmptyState
				:title="`No ${tab} enquiries`"
				:description="emptyDescription"
				icon="lucide-handshake"
			/>
		</template>

		<template #default="{ item }">
			<MyEnquiryCard :enquiry="item" @open="drawer.show(item)" />
		</template>
	</TimelineList>

	<MyEnquiryDrawer
		v-model:open="drawer.open.value"
		:enquiry="drawer.selected.value"
		:payment-received="payment.showSuccessMessage.value"
		@changed="refresh"
	/>
</template>
