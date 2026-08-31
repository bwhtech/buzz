<script setup lang="ts">
import { useRouteQuery } from "@vueuse/router"
import { dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import TicketDrawer from "@/components/dashboard/tickets/TicketDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useMyTickets } from "@/data/tickets"
import type { TicketWithEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { type TimelineTab, inTab } from "@/utils/timelineTabs"

// In the URL, so the tab survives a reload and a shared link lands on the same view.
const tab = useRouteQuery<TimelineTab>("tab", "upcoming")

const tickets = useMyTickets()

// Held past the close so the drawer keeps its contents while it animates out.
const selected = ref<TicketWithEvent | null>(null)
const drawerOpen = ref(false)

function openTicket(ticket: TicketWithEvent) {
	selected.value = ticket
	drawerOpen.value = true
}

// A ticket whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(tickets.data || []).filter((ticket): ticket is TicketWithEvent =>
		Boolean(ticket.start_date && ticket.event_title),
	),
)

// Plain dayjs: these are date-only values, and dayjsLocal shifts them a day back.
const months = computed(() =>
	groupEventsByMonth(inTab(dated.value, tab.value, dayjs().format("YYYY-MM-DD"))),
)
</script>

<template>
	<TimelineList
		v-model:tab="tab"
		heading="My Tickets"
		icon="lucide-ticket"
		noun="tickets"
		:months="months"
		:loading="tickets.loading"
		:error="tickets.error"
	>
		<template #default="{ item }">
			<PrintedTicket :ticket="item" :banner-image="item.banner_image" @open="openTicket(item)" />
		</template>
	</TimelineList>

	<TicketDrawer v-model:open="drawerOpen" :ticket="selected" />
</template>
