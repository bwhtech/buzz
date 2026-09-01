<script setup lang="ts">
import { Divider } from "frappe-ui"
import { Accordion } from "frappe-ui/experimental"

import BookingSummary from "@/components/dashboard/events/BookingSummary.vue"
import { useBookingSummary } from "@/data/bookings"

// Fetched per booking rather than off the viewer's own bookings: the receipt behind a
// ticket somebody else paid for is still theirs to read.
const props = defineProps<{ booking: string }>()

const summary = useBookingSummary(() => props.booking)

const accordionItems = [{ value: "booking", title: "Booking Details" }]
</script>

<template>
	<template v-if="summary.data">
		<Accordion :items="accordionItems">
			<template #item-content>
				<BookingSummary :booking="summary.data" show-id />
			</template>
		</Accordion>
	</template>
</template>
