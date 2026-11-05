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
import { ListboxGroupLabel } from "reka-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import HighlightFirstRow from "./HighlightFirstRow.vue"
import { paletteOpen } from "./paletteOpen"
import { scopeLabel, type PaletteScope } from "./paletteRows"
import { usePaletteGroups } from "./usePaletteGroups"
import { MIN_TERM_LENGTH, usePaletteEvents } from "./usePaletteSearch"

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
	if (!row?.scope || !canPushInto(row.scope)) return false
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

// The header row of the section already scoped to would push into itself.
function canPushInto(target?: PaletteScope) {
	if (!target) return false
	const current = scope.value
	return !(current?.event.name === target.event.name && current.source?.key === target.source?.key)
}

const rowIds = computed(() => [...rowsById.value.keys()].join())

const scopeName = computed(() => (scope.value ? scopeLabel(scope.value) : ""))

const emptyText = computed(() => {
	const where = scopeName.value || currentEvent.value?.title
	if (searching.value) return __("Searching…")
	if (eventsCall.data && !events.value.length)
		return __("Join or create an event to search its guests, talks and sponsors")
	if (query.value.trim().length < MIN_TERM_LENGTH)
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
					<!-- Capped, so a long event title never pushes the typed text out of view. -->
					<span
						class="flex min-w-0 max-w-[50%] shrink-0 items-center gap-1 rounded-full bg-surface-gray-3 py-0.5 pl-2 pr-0.5 text-sm text-ink-gray-8"
						:title="scopeName"
					>
						<span class="truncate">{{ scopeName }}</span>
						<button
							class="grid size-5 place-items-center rounded-full text-ink-gray-5 transition-transform duration-100 ease-out hover:bg-surface-gray-4 hover:text-ink-gray-8 active:scale-90"
							:aria-label="__('Clear scope')"
							@mousedown.prevent
							@click="scope = null"
						>
							<span class="lucide-x size-3.5" />
						</button>
					</span>
				</template>
			</CommandPaletteInput>

			<HighlightFirstRow :row-ids="rowIds" />
			<CommandPaletteList>
				<CommandPaletteGroup
					v-for="group in groups"
					:key="group.label + group.rows[0]?.id"
					:label="(!group.event && group.label) || undefined"
				>
					<ListboxGroupLabel
						v-if="group.event"
						as="div"
						class="mb-2.5 flex min-w-0 items-center gap-1.5 px-4.5 text-base leading-tighter text-ink-gray-5"
					>
						<span
							class="max-w-[60%] truncate rounded bg-surface-gray-2 px-1.5 py-0.5 text-sm text-ink-gray-7"
							:title="group.event"
							>{{ group.event }}</span
						>
						<span class="lucide-chevron-right size-3.5 shrink-0" />
						<span class="shrink-0">{{ group.label }}</span>
					</ListboxGroupLabel>
					<CommandPaletteItem
						v-for="row in group.rows"
						:key="row.id"
						:value="row.id"
						:label="row.label"
					>
						<template #prefix>
							<span :class="[row.icon, 'mr-2 size-4 shrink-0 text-ink-gray-6']" />
						</template>
						<!-- The name is capped so the subtitle, often what tells two rows apart, stays visible. -->
						<span class="flex min-w-0 items-baseline gap-2">
							<span
								:class="['truncate', row.subtitle && 'max-w-[65%] shrink-0']"
								:title="row.label"
								>{{ row.label }}</span
							>
							<span
								v-if="row.subtitle"
								class="min-w-0 truncate text-ink-gray-5"
								:title="row.subtitle"
								>{{ row.subtitle }}</span
							>
						</span>
						<template v-if="canPushInto(row.scope)" #suffix="{ active: highlighted }">
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
