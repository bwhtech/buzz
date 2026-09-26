<script setup lang="ts">
import { usePageMeta } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { useTeamAccess } from "@/composables/useTeamAccess"
import { useEventDoc } from "@/data/events"
import { useMySponsorships } from "@/data/sponsorships"
import ManagerDesktopShell from "@/layouts/ManagerDesktopShell.vue"
import ManagerMobileShell from "@/layouts/ManagerMobileShell.vue"
import NotFound from "@/pages/NotFound.vue"
import { managerNavigation } from "@/utils/managerNavigation"

const route = useRoute()
const access = useTeamAccess()
const isMobile = useIsMobile()
const sponsorships = useMySponsorships()

// An event opens into the same shell with its own destinations.
const eventId = computed(() => route.params.eventId as string | undefined)

// Keyed by the route param, so the doc follows the event the user is looking at. Shared
// through frappe-ui's document store, so the spaces reading the same event pay for one
// fetch between them.
const eventDoc = useEventDoc(() => eventId.value ?? "")
const eventTitle = computed(() => eventDoc.doc?.title ?? "")

usePageMeta(() => {
	const section = route.meta.title as string | undefined
	if (!section || !eventTitle.value) return null
	return { title: `${__(section)} | ${eventTitle.value}` }
})

const items = computed(() =>
	managerNavigation({
		eventId: eventId.value,
		creatingEvent: route.name === "create-event",
		hasSponsorships: Boolean(sponsorships.data?.length),
	}),
)
</script>

<template>
	<NotFound v-if="access === 'denied'" />
	<template v-else-if="access === 'granted'">
		<ManagerMobileShell v-if="isMobile" :items="items" :show-discover="!eventId" />
		<ManagerDesktopShell v-else :items="items" :event-id="eventId" :event-title="eventTitle" />
	</template>
</template>
