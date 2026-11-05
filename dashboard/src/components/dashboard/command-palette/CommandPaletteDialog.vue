<script setup lang="ts">
import { KeyboardShortcut, useKeyboardShortcut } from "frappe-ui"
import {
	CommandPalette,
	CommandPaletteEmpty,
	CommandPaletteFooter,
	CommandPaletteGroup,
	CommandPaletteInput,
	CommandPaletteItem,
	CommandPaletteList,
	type CommandPaletteSelectEvent,
} from "frappe-ui/experimental"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { paletteOpen } from "./paletteOpen"
import { scopeLabel, type PaletteScope } from "./paletteRows"
import { usePaletteGroups } from "./usePaletteGroups"
import { usePaletteEvents } from "./usePaletteSearch"

const route = useRoute()
const router = useRouter()

const query = ref("")
const scope = ref<PaletteScope | null>(null)
const eventsCall = usePaletteEvents()
const events = computed(() => eventsCall.data?.events ?? [])
const currentEventId = computed(() => route.params.eventId as string | undefined)
const { groups, rowsById, searching, currentEvent, countSearch } = usePaletteGroups({
	query,
	scope,
	events,
	currentEventId,
})

useKeyboardShortcut({
	combo: "Mod+K",
	description: "Open command palette",
	allowInInput: true,
	handler: () => (paletteOpen.value = !paletteOpen.value),
})

// Refetched on every open, so a new or newly shared event is there next time.
watch(paletteOpen, (open) => {
	if (open) eventsCall.fetch()
	else scope.value = null
})

function select(id: unknown, event: CommandPaletteSelectEvent) {
	const row = rowsById.value.get(String(id))
	if (!row) return
	countSearch(row)
	if (row.keepOpen) event.preventDefault()
	if (row.run) row.run()
	else if (row.to) router.push(row.to)
}

function pushScope(id: unknown) {
	const row = rowsById.value.get(String(id))
	if (!row?.scope) return false
	scope.value = row.scope
	query.value = row.scopeQuery ?? ""
	return true
}

function popScope() {
	if (!scope.value) return false
	scope.value = scope.value.source ? { event: scope.value.event } : null
	return true
}

function onKeydown(event: KeyboardEvent, active: unknown) {
	const handled =
		(event.key === "Tab" && !event.shiftKey && pushScope(active)) ||
		(event.key === "Tab" && event.shiftKey && popScope()) ||
		(event.key === "Backspace" && !query.value && popScope()) ||
		(event.key === "Escape" && popScope())
	// Tab never leaves the field, even on a row it cannot push into.
	if (!handled && event.key !== "Tab") return
	event.preventDefault()
	// The dialog closes on an Escape it hears; this one only left the scope.
	event.stopPropagation()
}

const scopeName = computed(() => (scope.value ? scopeLabel(scope.value) : ""))

const emptyText = computed(() => {
	const where = scopeName.value || currentEvent.value?.title
	if (searching.value) return __("Searching…")
	if (query.value.trim().length < 2)
		return where ? __("Type at least two letters to search {0}", [where]) : __("No matches")
	return where
		? __('Nothing matches "{0}" in {1}', [query.value.trim(), where])
		: __('Nothing matches "{0}"', [query.value.trim()])
})
</script>

<template>
	<CommandPalette
		v-model:open="paletteOpen"
		v-model:query="query"
		:filterable="false"
		:title="__('Search')"
		@select="select"
	>
		<template #default="{ active }">
			<CommandPaletteInput
				:placeholder="
					scope
						? __('Search in {0}', [scopeName])
						: __('Search people, talks, sponsors, or type a command…')
				"
				@keydown="onKeydown($event, active)"
			>
				<template v-if="scope" #prefix>
					<span
						class="flex shrink-0 items-center gap-1 rounded-full bg-surface-gray-3 py-0.5 pl-2 pr-0.5 text-sm text-ink-gray-8"
					>
						{{ scopeName }}
						<button
							class="grid size-5 place-items-center rounded-full text-ink-gray-5 transition-transform duration-100 ease-out hover:bg-surface-gray-4 hover:text-ink-gray-8 active:scale-90"
							:aria-label="__('Clear scope')"
							@click="scope = null"
						>
							<span class="lucide-x size-3.5" />
						</button>
					</span>
				</template>
			</CommandPaletteInput>

			<CommandPaletteList>
				<CommandPaletteGroup
					v-for="group in groups"
					:key="group.label + group.rows[0]?.id"
					:label="group.label || undefined"
				>
					<CommandPaletteItem
						v-for="row in group.rows"
						:key="row.id"
						:value="row.id"
						:label="row.label"
					>
						<template #prefix>
							<span :class="[row.icon, 'mr-2 size-4 shrink-0 text-ink-gray-6']" />
						</template>
						<span class="truncate">{{ row.label }}</span>
						<span v-if="row.subtitle" class="ml-2 truncate text-ink-gray-5">{{
							row.subtitle
						}}</span>
						<template v-if="row.scope" #suffix="{ active: highlighted }">
							<span v-if="highlighted" class="flex items-center gap-1 text-sm text-ink-gray-5">
								{{ __("Search inside") }} <KeyboardShortcut combo="Tab" />
							</span>
						</template>
					</CommandPaletteItem>
				</CommandPaletteGroup>
			</CommandPaletteList>

			<CommandPaletteEmpty>
				{{ emptyText }}
			</CommandPaletteEmpty>

			<CommandPaletteFooter>
				<div class="flex items-center gap-4 text-sm text-ink-gray-5">
					<span class="flex items-center gap-1"
						><KeyboardShortcut combo="Enter" /> {{ __("Open") }}</span
					>
					<span v-if="scope" class="flex items-center gap-1">
						<KeyboardShortcut combo="Shift+Tab" /> {{ __("Back") }}
					</span>
				</div>
			</CommandPaletteFooter>
		</template>
	</CommandPalette>
</template>

<style>
/* Opened by keyboard many times a day, so it appears and leaves at once. */
.dialog-content:has([data-slot="command-palette"]),
body:has([data-slot="command-palette"]) .dialog-overlay {
	animation: none;
}
</style>
