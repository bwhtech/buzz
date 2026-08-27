<script setup lang="ts">
import { Button, FormControl, toast } from "frappe-ui"
import { computed } from "vue"

import EventLocation from "@/components/dashboard/events/EventLocation.vue"
import { venues } from "@/data/venues"

// The two values Buzz Event's `medium` select takes.
const IN_PERSON = "In Person"
const ONLINE = "Online"

const props = defineProps<{ team: string; venueAddress?: string | null }>()

const medium = defineModel<string>("medium", { default: IN_PERSON })
const venue = defineModel<string>("venue", { default: "" })
const meetingLink = defineModel<string>("meetingLink", { default: "" })

const isOnline = computed(() => medium.value === ONLINE)

const options = [
	{ label: "In person", icon: "lucide-map-pin", value: IN_PERSON },
	{ label: "Virtual", icon: "lucide-video", value: ONLINE },
]

// The picker knows the address of a venue chosen in this session; the one loaded with
// the event is only known to the payload until that list arrives.
const address = computed(() => {
	const picked = (venues.data ?? []).find((row) => row.name === venue.value)
	return picked?.address || props.venueAddress || ""
})

// The hidden field is dropped here as well as on the server: the calendar invite and the
// booking page both read `venue` without consulting `medium`, so a leftover one shows an
// address the event no longer has.
function pick(value: string) {
	medium.value = value
	if (value === ONLINE) venue.value = ""
	else meetingLink.value = ""
}

async function copyLink() {
	await navigator.clipboard.writeText(meetingLink.value)
	toast.success("Link copied")
}
</script>

<template>
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-2 gap-2">
			<Button
				v-for="option in options"
				:key="option.value"
				:variant="medium === option.value ? 'subtle' : 'ghost'"
				:icon-left="option.icon"
				:label="option.label"
				:aria-pressed="medium === option.value"
				class="w-full"
				@click="pick(option.value)"
			/>
		</div>

		<template v-if="isOnline">
			<div class="flex items-end gap-2">
				<FormControl
					v-model="meetingLink"
					class="flex-1"
					type="url"
					label="Meeting link"
					placeholder="https://…"
				/>
				<Button
					icon="lucide-copy"
					label="Copy meeting link"
					:disabled="!meetingLink"
					@click="copyLink"
				/>
			</div>
		</template>

		<template v-else>
			<EventLocation v-model:venue="venue" :team="team" :show-virtual="false" />
			<p v-if="address" class="text-base text-ink-gray-5">{{ address }}</p>
		</template>
	</div>
</template>
