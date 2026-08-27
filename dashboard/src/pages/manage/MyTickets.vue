<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import PrintedTicket from "@/components/dashboard/tickets/PrintedTicket.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useMyTickets } from "@/data/tickets"
import type { TicketWithEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { type TimelineTab, inTab } from "@/utils/timelineTabs"

const tab = ref<TimelineTab>("upcoming")

const tickets = useMyTickets()

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
		heading="Tickets"
		noun="tickets"
		:months="months"
		:loading="tickets.loading"
		:error="tickets.error"
	>
		<template #default="{ item }">
			<PrintedTicket :ticket="item" />
		</template>
	</TimelineList>
</template>
