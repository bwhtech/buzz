<script setup lang="ts">
import { DesktopShell, PageHeaderTarget, Sidebar, SidebarItem } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import ManagerSidebarHeader from "@/components/dashboard/ManagerSidebarHeader.vue"
import UserMenu from "@/components/UserMenu.vue"
import { useTeamAccess } from "@/composables/useTeamAccess"
import { eventDetail } from "@/data/events"
import { useMySponsorships } from "@/data/sponsorships"
import NotFound from "@/pages/NotFound.vue"

const route = useRoute()

const access = useTeamAccess()

// SidebarItem infers this from `to` on paper, but its `active` prop is declared
// type Boolean, so Vue casts the absent prop to false and the inference never runs.
const isActive = (to: string) => route.path === to

// Sponsorship is hidden until the user has an inquiry, the same rule the account
// page applies to its Sponsorships tab.
const sponsorships = useMySponsorships()

const mainItems = computed(() => {
	const destinations = [
		{ label: "Events", icon: "lucide-calendar-days", to: "/manage/events" },
		{ label: "Talk Proposals", icon: "lucide-mic", to: "/manage/proposals" },
	]

	if (sponsorships.data?.length) {
		destinations.push({
			label: "Sponsorship",
			icon: "lucide-handshake",
			to: "/manage/sponsorship",
		})
	}

	return destinations
})

// An event opens into the same shell with its own destinations.
const eventId = computed(() => route.params.eventId as string | undefined)

// Entering an event pushes the sidebar left, leaving it pulls back right.
const direction = ref<"forward" | "back">("forward")
watch(eventId, (id, previous) => {
	direction.value = id && !previous ? "forward" : "back"
})

const eventTitle = ref("")
watch(
	eventId,
	(id) => {
		eventTitle.value = ""
		if (!id) return
		// Drops a late response for an event the user has already left.
		eventDetail(id).promise?.then((event) => {
			if (eventId.value === id) eventTitle.value = event?.title ?? ""
		})
	},
	{ immediate: true },
)

const items = computed(() => {
	if (!eventId.value) return mainItems.value
	const event = `/manage/events/${eventId.value}`
	return [
		{ label: "Details", icon: "lucide-receipt-text", to: `${event}/details` },
		{ label: "Guests", icon: "lucide-users-round", to: `${event}/guests` },
		{ label: "Talks", icon: "lucide-presentation", to: `${event}/talks` },
	]
})
</script>

<template>
	<NotFound v-if="access === 'denied'" />

	<!-- scroll=false: the rounded panel below owns its own scroll. -->
	<DesktopShell v-else-if="access === 'granted'" :scroll="false">
		<template #sidebar>
			<Sidebar>
				<!-- px-1: puts the header mark on the item-icon centerline, in both states.
				     h-14 holds the height while both states overlap mid-transition. -->
				<div class="nav-stage relative h-14 shrink-0">
					<Transition :name="`nav-${direction}`">
						<div
							:key="eventId ? 'event' : 'root'"
							class="absolute inset-x-1 top-2 flex items-center"
						>
							<ManagerSidebarHeader :event-id="eventId" :event-title="eventTitle" />
						</div>
					</Transition>
				</div>

				<!-- One block, not per row: absolute rows would all collapse onto the
				     container's corner. my-2, not py-2: the leaving list anchors to the
				     padding box, so padding here would lift it out of line. -->
				<div class="nav-stage relative mx-2 my-2">
					<Transition :name="`nav-${direction}`">
						<div :key="eventId ? 'event' : 'root'" class="nav-list flex flex-col gap-0.5">
							<SidebarItem
								v-for="item in items"
								:key="item.label"
								:label="item.label"
								:icon="item.icon"
								:to="item.to"
								:active="isActive(item.to)"
							/>
						</div>
					</Transition>
				</div>

				<div class="mt-auto px-2 py-2">
					<UserMenu />
				</div>
			</Sidebar>
		</template>

		<div class="flex flex-col h-full min-h-0 bg-surface-sidebar py-2 pl-1">
			<div
				class="flex h-full flex-col overflow-hidden rounded-l-6 bg-surface-elevation-1 shadow-base"
			>
				<PageHeaderTarget />
				<div class="min-h-0 flex-1 overflow-y-auto">
					<router-view />
				</div>
			</div>
		</div>
	</DesktopShell>
</template>

<style scoped>
/* One vanishing point per stage, so header and list hinge off the same rail. */
.nav-stage {
	perspective: 700px;
}

.nav-forward-enter-active,
.nav-back-enter-active,
.nav-forward-leave-active,
.nav-back-leave-active {
	transform-origin: left center;
}

/* Opacity lands before the movement: a row still visible at the end of its slide
   reads as a ghost. */
.nav-forward-enter-active,
.nav-back-enter-active {
	transition:
		opacity 140ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

.nav-forward-leave-active,
.nav-back-leave-active {
	transition:
		opacity 100ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 140ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* Only the list leaves the flow; re-anchoring the header would shift it 4px. */
.nav-list.nav-forward-leave-active,
.nav-list.nav-back-leave-active {
	position: absolute;
	inset-inline: 0;
	top: 0;
}

.nav-forward-enter-from,
.nav-back-leave-to {
	opacity: 0;
	transform: translateX(10px) rotateY(-8deg);
}

.nav-forward-leave-to,
.nav-back-enter-from {
	opacity: 0;
	transform: translateX(-10px) rotateY(8deg);
}

@media (prefers-reduced-motion: reduce) {
	.nav-forward-enter-from,
	.nav-forward-leave-to,
	.nav-back-enter-from,
	.nav-back-leave-to {
		transform: none;
	}
}
</style>
