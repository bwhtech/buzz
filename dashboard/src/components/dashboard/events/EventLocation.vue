<script setup lang="ts">
import { Button, Combobox } from "frappe-ui"
import { computed, ref, watch } from "vue"

import ZoomLogo from "@/components/common/ZoomLogo.vue"
import AddVenueDialog from "@/components/dashboard/events/AddVenueDialog.vue"
import { venues } from "@/data/venues"

// A reserved value rather than a venue name. Event Venue is autonamed by prompt, so a
// venue really could be called "Zoom" — the sentinel keeps the two apart.
const ZOOM = "__zoom__"

// A page that asks for the medium separately picks a venue and nothing else, so the
// Zoom option would be a second way to answer a question already answered.
const props = withDefaults(
	defineProps<{ team: string; disabled?: boolean; showVirtual?: boolean; error?: string }>(),
	{ showVirtual: true, error: "" },
)

const venue = defineModel<string>("venue", { default: "" })
// Zoom cannot be booked until the event exists, so this is the intent to act on at save.
const zoomMeeting = defineModel<boolean>("zoomMeeting", { default: false })

const isAdding = ref(false)
const suggestedName = ref("")
const isOpen = ref(false)
const query = ref("")

watch(
	() => props.team,
	(team) => team && venues.fetch({ team }),
	{ immediate: true },
)

const selected = computed({
	get: () => (zoomMeeting.value ? ZOOM : venue.value),
	set: (value: string | null) => {
		// The server derives `medium` from this, so it is not tracked here as well.
		zoomMeeting.value = value === ZOOM
		venue.value = value === ZOOM ? "" : (value ?? "")
	},
})

// Nothing answers to what they typed, so Add Manually is the only move left: it is
// pre-armed, and Enter takes it. Not while the list is still loading: an empty list is
// not an answer, and arming Enter on one adds a venue that already exists.
const unmatched = computed(() => {
	if (venues.loading) return false
	const text = query.value.trim().toLowerCase()
	return Boolean(text) && !(venues.data ?? []).some((row) => row.name.toLowerCase().includes(text))
})

function addManually() {
	isOpen.value = false
	suggestedName.value = query.value.trim()
	isAdding.value = true
}

function createZoomMeeting() {
	isOpen.value = false
	selected.value = ZOOM
}

// The Zoom row stays out of the list — the footer offers it. It comes back while
// selected, because the trigger reads its label from a matching option.
const zoomOption = { label: "Create Zoom meeting", value: ZOOM, icon: "lucide-video" }

const options = computed(() => [
	{
		group: "Venues",
		options: (venues.data ?? []).map((row) => ({
			label: row.name,
			description: row.address,
			value: row.name,
		})),
	},
	...(zoomMeeting.value ? [{ group: "Virtual", options: [zoomOption] }] : []),
])

async function onVenueCreated(name: string) {
	await venues.fetch({ team: props.team })
	selected.value = name
}
</script>

<template>
	<!-- Enter is prevented: its default action clicks whatever the dialog focuses as it
	 opens, which closes the dialog again. -->
	<Combobox
		v-model="selected"
		v-model:open="isOpen"
		v-model:query="query"
		:options="options"
		placeholder="Search venues, or add one"
		empty-text=""
		class="w-full"
		:loading="venues.loading"
		:disabled="disabled"
		:error="error"
		@keydown.enter.prevent="unmatched && addManually()"
	>
		<!-- Rows size the popover, and an address can be a long URL. Cap them near the
		 trigger width, minus the row's own padding, so the panel stays put. -->
		<template #item-label="{ item }">
			<div class="min-w-0 max-w-[calc(var(--reka-combobox-trigger-width)-3rem)]">
				<div class="truncate">{{ item.label }}</div>
				<div v-if="item.description" class="truncate text-p-sm text-ink-gray-5">
					{{ item.description }}
				</div>
			</div>
		</template>

		<template #footer>
			<div class="flex flex-col gap-1 border-t border-outline-gray-1 p-1">
				<Button
					class="w-full !justify-start"
					:class="unmatched && '!bg-surface-gray-3'"
					variant="ghost"
					icon-left="lucide-map-pin-plus"
					label="Add Manually"
					@click="addManually()"
				/>
				<Button
					v-if="showVirtual"
					class="w-full !justify-start"
					variant="ghost"
					label="Create Zoom Meeting"
					@click="createZoomMeeting()"
				>
					<template #prefix>
						<ZoomLogo class="size-4" color="var(--ink-gray-5)" />
					</template>
				</Button>
			</div>
		</template>
	</Combobox>

	<AddVenueDialog
		v-model="isAdding"
		v-model:suggested-name="suggestedName"
		:team="team"
		@created="onVenueCreated"
	/>
</template>
