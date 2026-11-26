<script setup lang="ts">
import { useNow } from "@vueuse/core"
import { Avatar, Button, Tooltip, dayjsLocal, useDoc } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { useEventDoc } from "@/data/events"
import { editedAgo } from "@/utils/dateLabels"
import { eventPath } from "@/utils/eventUrl"

// The right side every event page header shares: when the event was last edited, a
// link to its public page, and the team that owns it. A page that saves the event
// passes its own `modified` so the time moves on save.
const props = withDefaults(
	defineProps<{ modified?: string | null; buttonSize?: "sm" | "md" | "lg" }>(),
	{ modified: null, buttonSize: "sm" },
)

type TeamDoc = { name: string; team_name: string; logo: string | null }
type HeaderEventDoc = { route?: string; team?: string; modified?: string }

const route = useRoute()
const event = useEventDoc(() => route.params.eventId as string)
const doc = computed(() => event.doc as HeaderEventDoc | null)
const team = useDoc<TeamDoc>({ doctype: "Buzz Team", name: () => doc.value?.team || "" })

// Shown as one group once the team is known too: the team sits rightmost, so arriving
// late would push everything else left.
const ready = computed(() => Boolean(doc.value && (!doc.value.team || team.doc || team.error)))

const now = useNow({ interval: 60_000 })
const modified = computed(() => props.modified ?? doc.value?.modified ?? null)
const editedLabel = computed(() => (modified.value ? editedAgo(modified.value, now.value) : ""))
const editedExact = computed(() =>
	modified.value ? dayjsLocal(modified.value).format("D MMM YYYY, h:mm A") : "",
)
const eventPage = computed(() => (doc.value?.route ? eventPath(doc.value.route) : undefined))
const teamRoute = computed(() =>
	team.doc ? { name: "team-calendar", params: { teamId: team.doc.name } } : undefined,
)
</script>

<template>
	<div v-if="ready" class="header-actions flex items-center gap-1.5">
		<Tooltip v-if="modified" :text="`Last edited on ${editedExact}`">
			<span class="px-1 text-sm tabular-nums text-ink-gray-4">Edited {{ editedLabel }}</span>
		</Tooltip>
		<Button
			v-if="eventPage"
			variant="ghost"
			:size="buttonSize"
			:link="eventPage"
			icon-right="lucide-arrow-up-right"
			label="View event"
		/>
		<Button v-if="team.doc" variant="subtle" :size="buttonSize" :route="teamRoute" class="!pl-1.5">
			<template #prefix>
				<Avatar
					:image="team.doc.logo ?? undefined"
					:label="team.doc.team_name"
					size="xs"
					shape="square"
				/>
			</template>
			<span class="text-ink-gray-7">{{ team.doc.team_name }}</span>
		</Button>
	</div>
</template>

<style scoped>
.header-actions {
	transition: opacity 150ms cubic-bezier(0.23, 1, 0.32, 1);
}
@starting-style {
	.header-actions {
		opacity: 0;
	}
}
</style>
