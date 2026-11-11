<script setup lang="ts">
import { usePageMeta } from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { finishOpening, openingTeam } from "@/composables/useWorkspaceOpening"
import { useEventAccess, useEventDoc } from "@/data/events"
import { useRequestCounts } from "@/data/requests"
import { useMySponsorships } from "@/data/sponsorships"
import { loadTeams, selectTeam, teamLabel, teams, teamsLoaded } from "@/data/teams"
import ManagerDesktopShell from "@/layouts/ManagerDesktopShell.vue"
import ManagerMobileShell from "@/layouts/ManagerMobileShell.vue"
import NotFound from "@/pages/NotFound.vue"
import { managerNavigation, type Workspace } from "@/utils/managerNavigation"

const route = useRoute()
const isMobile = useIsMobile()
const sponsorships = useMySponsorships()

loadTeams()

// An event opens into the same shell with its own destinations.
const eventId = computed(() => route.params.eventId as string | undefined)

// Keyed by the route param, so the doc follows the event the user is looking at. Shared
// through frappe-ui's document store, so the spaces reading the same event pay for one
// fetch between them.
const eventDoc = useEventDoc(() => eventId.value ?? "")
const eventTitle = computed(() => eventDoc.doc?.title ?? "")

// Per section: a collaborator sees only the destinations they were granted.
const eventAccess = useEventAccess(() => eventId.value ?? "")
watch(eventId, (id) => id && eventAccess.fetch(), { immediate: true })

// Only someone who can act on requests may count them.
const requestCounts = useRequestCounts(() =>
	eventId.value && eventAccess.data?.guests === "Edit" ? eventId.value : "",
)

// A team opens the same way; its name and logo are already in the teams list.
const teamId = computed(() => route.params.teamId as string | undefined)
const team = computed(() => teams.value.find((option) => option.name === teamId.value))
// The server refuses a non-member too; this keeps them off the page.
const teamDenied = computed(() => Boolean(teamId.value && teamsLoaded.value && !team.value))
watch(teamDenied, (denied) => denied && finishOpening())
// Create Event files the event under the current team, so opening a team makes it current.
watch(team, (opened) => opened && selectTeam(opened.name), { immediate: true })

const workspace = computed((): Workspace | undefined => {
	if (eventId.value)
		return {
			title: eventTitle.value,
			subtitle: "Event Workspace",
			back: { label: "Back to events", to: "/manage/events" },
			icon: "lucide-box",
		}
	if (teamId.value)
		return {
			title: team.value ? teamLabel(team.value) : "",
			subtitle: team.value?.is_personal ? "Personal Calendar" : "Community Workspace",
			back: { label: "Back to communities", to: "/manage/communities" },
			image: team.value?.logo,
		}
	return undefined
})

usePageMeta(() => {
	const section = route.meta.title as string | undefined
	if (!section || !workspace.value?.title) return null
	return { title: `${__(section)} | ${workspace.value.title}` }
})

// The sidebar empties while a workspace opens, so the old destinations don't linger.
const items = computed(() =>
	openingTeam.value || (eventId.value && !eventAccess.data)
		? []
		: managerNavigation({
				eventId: eventId.value,
				teamId: teamId.value,
				creatingEvent: route.name === "create-event",
				hasSponsorships: Boolean(sponsorships.data?.length),
				access: eventAccess.data,
				requestCounts: requestCounts.data,
			}),
)
</script>

<template>
	<NotFound v-if="teamDenied" />
	<ManagerMobileShell v-else-if="isMobile" :items="items" :show-discover="!workspace" />
	<ManagerDesktopShell v-else :items="items" :workspace="workspace" />
</template>
