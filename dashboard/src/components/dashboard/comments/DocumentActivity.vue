<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { useDocumentActivity } from "@/composables/useDocumentActivity"

import ActivityEntryRow from "./ActivityEntry.vue"

const props = defineProps<{
	feed: ReturnType<typeof useDocumentActivity>
	names: Record<string, string>
	createdLabel: string
}>()

const entries = computed(() => props.feed.activity.data ?? [])
// Only the latest email each way opens; earlier ones in the thread fold to a line.
const openEmails = computed(() => {
	const emails = entries.value.filter((entry) => entry.kind === "email")
	const latest = (received: boolean) =>
		emails.filter((entry) => entry.received === received).at(-1)?.name
	return new Set([latest(true), latest(false)])
})
// What the timeline opened with shows at once; only entries added while it is open
// animate in.
const loadedNames = ref<Set<string> | null>(null)
watch(
	entries,
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
		<ul v-if="entries.length">
			<ActivityEntryRow
				v-for="(entry, index) in entries"
				:key="entry.name"
				:entry="entry"
				:last="index === entries.length - 1"
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
			v-if="feed.activity.data && !feed.noteCount.value"
			class="text-sm text-pretty text-ink-gray-5"
		>
			No notes yet. Only your team sees them; mention someone with @ to loop them in.
		</p>
	</div>
</template>
