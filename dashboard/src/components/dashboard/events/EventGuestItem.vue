<script setup lang="ts">
import { Avatar, Badge } from "frappe-ui"

import type { EventGuest } from "@/types"

const props = defineProps<{ guest: EventGuest }>()

// A ticket can be issued before anyone is named on it, so the email is the fallback
// and the row never renders blank.
const name = props.guest.attendee_name || props.guest.attendee_email || "Unnamed guest"
</script>

<template>
	<li class="flex items-center gap-3 px-4 py-3">
		<Avatar :label="name" size="lg" />

		<!-- Name and email on one line: the email is how you tell two Harshes apart, so it
			 belongs beside the name rather than under it. -->
		<div class="flex min-w-0 flex-1 items-baseline gap-2">
			<span class="shrink-0 truncate text-base font-medium text-ink-gray-8">{{ name }}</span>
			<span v-if="guest.attendee_email" class="truncate text-base text-ink-gray-5">
				{{ guest.attendee_email }}
			</span>
		</div>

		<div class="flex shrink-0 items-center gap-1.5">
			<Badge
				v-for="addOn in guest.add_ons"
				:key="addOn.title"
				theme="blue"
				variant="subtle"
				:label="addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title"
			/>
			<Badge v-if="guest.ticket_type" variant="outline" :label="guest.ticket_type" />
		</div>
	</li>
</template>
