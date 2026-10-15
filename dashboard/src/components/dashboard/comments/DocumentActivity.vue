<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed } from "vue"

import type { useDocumentActivity } from "@/composables/useDocumentActivity"

import ActivityEntryRow from "./ActivityEntry.vue"

const props = defineProps<{
	feed: ReturnType<typeof useDocumentActivity>
	names: Record<string, string>
	createdLabel: string
}>()

const entries = computed(() => props.feed.activity.data ?? [])
const hasNotes = computed(() =>
	entries.value.some((entry) => entry.kind === "comment" || entry.kind === "email"),
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
				:members="feed.members.data || []"
				:names="names"
				:created-label="createdLabel"
				:saving="feed.updating.loading"
				@update="(content) => feed.update(entry.name, content)"
				@delete="feed.remove(entry.name)"
			/>
		</ul>
		<p v-if="feed.activity.data && !hasNotes" class="text-sm text-pretty text-ink-gray-5">
			No notes yet. Only your team sees them; mention someone with @ to loop them in.
		</p>
	</div>
</template>
