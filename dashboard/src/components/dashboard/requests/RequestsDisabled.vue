<script setup lang="ts">
import { Button } from "frappe-ui"

import EmptyState from "@/components/common/EmptyState.vue"
import type { RequestType } from "@/types"

const props = defineProps<{ type: RequestType; eventId: string }>()

const COPY = {
	Approval: {
		icon: "lucide-user-check",
		title: "Approvals aren’t enabled for this event",
		description:
			"Turn on registration approval first. Then every registration waits here until you accept it.",
	},
	Waitlist: {
		icon: "lucide-list-ordered",
		title: "The waitlist isn’t enabled for this event",
		description:
			"Turn on the waitlist first. Then people can queue up here once a ticket type with a seat limit sells out.",
	},
}
const copy = COPY[props.type]
</script>

<template>
	<EmptyState v-bind="copy">
		<Button
			variant="solid"
			label="Go to Registration"
			:route="`/manage/events/${eventId}/registrations`"
		/>
	</EmptyState>
</template>
