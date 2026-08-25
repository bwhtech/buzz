<script setup lang="ts">
import AddVenueDialog from "@/components/dashboard/events/AddVenueDialog.vue";
import { venues } from "@/data/venues";
import { Combobox } from "frappe-ui";
import { computed, ref, watch } from "vue";

// A reserved value rather than a venue name. Event Venue is autonamed by prompt, so a
// venue really could be called "Zoom" — the sentinel keeps the two apart.
const ZOOM = "__zoom__";

const props = defineProps<{ team: string; disabled?: boolean }>();

const venue = defineModel<string>("venue", { default: "" });
// Zoom cannot be booked until the event exists, so this is the intent to act on at save.
const zoomMeeting = defineModel<boolean>("zoomMeeting", { default: false });

const isAdding = ref(false);
const suggestedName = ref("");

watch(
	() => props.team,
	(team) => team && venues.fetch({ team }),
	{ immediate: true }
);

const selected = computed({
	get: () => (zoomMeeting.value ? ZOOM : venue.value),
	set: (value: string | null) => {
		// The server derives `medium` from this, so it is not tracked here as well.
		zoomMeeting.value = value === ZOOM;
		venue.value = value === ZOOM ? "" : value ?? "";
	},
});

const options = computed(() => [
	{
		group: "Venues",
		options: (venues.data ?? []).map((row) => ({
			label: row.name,
			description: row.address,
			value: row.name,
		})),
	},
	{
		group: "Virtual",
		options: [
			{ label: "Create Zoom meeting", value: ZOOM, icon: "lucide-video" },
			{
				type: "custom" as const,
				key: "add-venue",
				label: "Add venue",
				icon: "lucide-plus",
				// Only worth offering once they have typed a name nothing answers to.
				condition: ({ query }: { query: string }) =>
					Boolean(query.trim()) &&
					!(venues.data ?? []).some(
						(row) => row.name.toLowerCase() === query.trim().toLowerCase()
					),
				onClick: ({ query }: { query: string }) => {
					suggestedName.value = query.trim();
					isAdding.value = true;
				},
			},
		],
	},
]);

async function onVenueCreated(name: string) {
	await venues.fetch({ team: props.team });
	selected.value = name;
}
</script>

<template>
	<Combobox
		v-model="selected"
		:options="options"
		placeholder="Search venues, or add one"
		class="w-full mt-2"
		:disabled="disabled"
	/>

	<AddVenueDialog
		v-model="isAdding"
		v-model:suggested-name="suggestedName"
		:team="team"
		@created="onVenueCreated"
	/>
</template>
