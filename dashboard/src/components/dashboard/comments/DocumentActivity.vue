<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { activityFilters, type useDocumentActivity } from "@/composables/useDocumentActivity"
import type { BadgeTheme } from "@/utils/badgeTheme"

import ActivityEntryRow from "./ActivityEntry.vue"

const props = defineProps<{
	feed: ReturnType<typeof useDocumentActivity>
	names: Record<string, string>
	createdLabel: string
	changeTheme?: (value: string) => BadgeTheme
}>()

const allEntries = computed(() => props.feed.activity.data ?? [])
const entries = computed(() => props.feed.entries.value)
const filterLabel = computed(
	() => activityFilters.find((option) => option.value === props.feed.filter.value)?.label,
)
// Only the latest email each way opens; earlier ones in the thread fold to a line.
const openEmails = computed(() => {
	const emails = allEntries.value.filter((entry) => entry.kind === "email")
	const latest = (received: boolean) =>
		emails.filter((entry) => entry.received === received).at(-1)?.name
	return new Set([latest(true), latest(false)])
})
// What the timeline opened with shows at once; only entries added while it is open
// animate in.
const loadedNames = ref<Set<string> | null>(null)
watch(
	allEntries,
	(list) => {
		if (props.feed.activity.data && !loadedNames.value)
			loadedNames.value = new Set(list.map((entry) => entry.name))
	},
	{ immediate: true },
)
</script>

<template>
	<div class="space-y-5">
		<Skeleton v-if="feed.activity.loading && !feed.activity.data" class="h-16 w-full rounded-4" />
		<ErrorMessage :message="feed.activity.error || feed.updating.error || feed.deleting.error" />
		<ul v-if="entries.length" class="flex flex-col gap-[18px]">
			<ActivityEntryRow
				v-for="entry in entries"
				:key="entry.name"
				:entry="entry"
				:change-theme="changeTheme"
				:fresh="Boolean(loadedNames && !loadedNames.has(entry.name))"
				:folded="entry.kind === 'email' && !openEmails.has(entry.name)"
				:members="feed.members.data || []"
				:names="names"
				:created-label="createdLabel"
				:saving="feed.updating.loading"
				@update="(content) => feed.update(entry.name, content)"
				@delete="feed.remove(entry.name)"
			/>
		</ul>
		<p
			v-if="feed.activity.data && feed.filter.value !== 'all' && !entries.length"
			class="text-sm text-ink-gray-5"
		>
			No {{ filterLabel?.toLowerCase() }} yet.
		</p>
		<p
			v-else-if="feed.activity.data && feed.filter.value === 'all' && !feed.noteCount.value"
			class="text-sm text-pretty text-ink-gray-5"
		>
			No notes yet. Only your team sees them; mention someone with @ to loop them in.
		</p>
	</div>
</template>
