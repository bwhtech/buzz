<script setup lang="ts">
// The search side of the location dialog: one place or several, the results, adding a place
// by hand and the Zoom option. The desktop dialog floats it over the map, the phone sheet docks it.
import { Button, ScrollArea, TabButtons, TextInput } from "frappe-ui"
import { DialogClose, DialogTitle } from "reka-ui"
import { computed, ref } from "vue"

import ZoomLogo from "@/components/common/ZoomLogo.vue"
import LocationResults from "@/components/dashboard/events/location/LocationResults.vue"
import ManualVenueForm from "@/components/dashboard/events/location/ManualVenueForm.vue"
import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import type { LocationSelection } from "@/components/dashboard/events/location/useLocationSelection"

const props = defineProps<{
	picker: LocationPicker
	selection: LocationSelection
	title: string
	canPickZoom: boolean
	showHeader?: boolean
}>()
const emit = defineEmits<{ picked: [venue: string]; zoom: [] }>()

const MODES = [
	{ label: "Single", value: "single" },
	{ label: "Multiple", value: "multiple" },
]

const isAddingManually = ref(false)
const mode = computed({
	get: () => (props.selection.isMultiple ? "multiple" : "single"),
	set: (value) => props.selection.setMultiple(value === "multiple"),
})

// A place added by hand joins the list, or is the location when there is only one.
function savedManually(venue: string) {
	isAddingManually.value = false
	if (props.selection.isMultiple) props.selection.add(venue)
	else emit("picked", venue)
}
</script>

<template>
	<div class="flex min-h-0 flex-col">
		<div v-if="showHeader" class="flex items-center gap-2 pb-2.5 pl-4 pr-3 pt-3.5">
			<DialogTitle class="flex-1 text-lg font-semibold text-ink-gray-9">
				{{ isAddingManually ? "Add venue manually" : title }}
			</DialogTitle>
			<DialogClose as-child>
				<Button variant="ghost" icon="lucide-x" aria-label="Close" />
			</DialogClose>
		</div>

		<ManualVenueForm
			v-if="isAddingManually"
			class="min-h-0 flex-1 overflow-y-auto px-4 pb-4"
			:picker="picker"
			:suggested-name="picker.query.trim()"
			@saved="savedManually"
			@cancel="isAddingManually = false"
		/>
		<template v-else>
			<div class="flex flex-col gap-2 px-3 pb-1">
				<TabButtons v-model="mode" :options="MODES" fluid />
				<TextInput
					v-model="picker.query"
					placeholder="Search a venue or a place"
					autofocus
					@keydown.enter.prevent="picker.isUnmatched && (isAddingManually = true)"
				>
					<template #prefix>
						<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</TextInput>
			</div>
			<ScrollArea class="min-h-0 flex-1">
				<LocationResults
					class="p-1.5 transition-opacity duration-150 ease-out"
					:class="selection.isSaving && 'pointer-events-none opacity-60'"
					:picker="picker"
					:active-key="selection.isMultiple ? undefined : selection.preview?.key"
					:selected="selection.isMultiple ? selection.selected : undefined"
					@venue="selection.pickVenue"
					@place="selection.pickPlace"
					@manual="isAddingManually = true"
					@hover="selection.hovered = $event"
				/>
			</ScrollArea>
			<ErrorMessage class="px-4 pb-2" :message="picker.error" />
			<div class="flex gap-1 border-t border-outline-gray-1 px-2 py-2">
				<Button
					variant="ghost"
					icon-left="lucide-map-pin-plus"
					label="Add manually"
					@click="isAddingManually = true"
				/>
				<Button
					v-if="canPickZoom && !selection.isMultiple"
					variant="ghost"
					label="Zoom meeting"
					@click="$emit('zoom')"
				>
					<template #prefix>
						<ZoomLogo class="size-4" color="var(--ink-gray-5)" />
					</template>
				</Button>
			</div>
		</template>
		<slot />
	</div>
</template>
