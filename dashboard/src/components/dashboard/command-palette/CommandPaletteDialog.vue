<script setup lang="ts">
import { Badge, KeyboardShortcut, useKeyboardShortcut } from "frappe-ui"
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
const { groups, rowsById } = usePaletteGroups({ query, scope, events, currentEventId })

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
		(event.key === "Backspace" && !query.value && popScope()) ||
		(event.key === "Escape" && popScope())
	if (!handled) return
	event.preventDefault()
	// The dialog closes on an Escape it hears; this one only left the scope.
	event.stopPropagation()
}

const canPush = (active: unknown) => Boolean(rowsById.value.get(String(active))?.scope)
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
				:placeholder="scope ? __('Search in {0}', [scopeLabel(scope)]) : __('Search or jump to…')"
				@keydown="onKeydown($event, active)"
			>
				<template v-if="scope" #prefix>
					<Badge :label="scopeLabel(scope)" theme="gray" size="md" class="shrink-0" />
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
							<span :class="[row.icon, 'size-4 shrink-0 text-ink-gray-6']" />
						</template>
						<span class="truncate">{{ row.label }}</span>
						<span v-if="row.subtitle" class="ml-2 truncate text-ink-gray-5">{{
							row.subtitle
						}}</span>
					</CommandPaletteItem>
				</CommandPaletteGroup>
			</CommandPaletteList>

			<CommandPaletteEmpty>
				{{ scope ? __("Type at least two letters to search") : __("No matches") }}
			</CommandPaletteEmpty>

			<CommandPaletteFooter>
				<div class="flex items-center gap-4 text-sm text-ink-gray-5">
					<span class="flex items-center gap-1"
						><KeyboardShortcut combo="Enter" /> {{ __("Open") }}</span
					>
					<span v-if="canPush(active)" class="flex items-center gap-1">
						<KeyboardShortcut combo="Tab" /> {{ __("Search inside") }}
					</span>
					<span v-if="scope" class="flex items-center gap-1">
						<KeyboardShortcut combo="Escape" /> {{ __("Back") }}
					</span>
				</div>
			</CommandPaletteFooter>
		</template>
	</CommandPalette>
</template>
