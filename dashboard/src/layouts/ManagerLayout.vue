<script setup lang="ts">
import { StorageSerializers, useStorage } from "@vueuse/core"
import {
	DesktopShell,
	PageHeaderTarget,
	Sidebar,
	SidebarCollapseToggle,
	SidebarItem,
} from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import ManagerSidebarHeader from "@/components/dashboard/ManagerSidebarHeader.vue"
import { useTeamAccess } from "@/composables/useTeamAccess"
import { eventDetail } from "@/data/events"
import { useMySponsorships } from "@/data/sponsorships"
import NotFound from "@/pages/NotFound.vue"

// `null` keeps the sidebar's own rule: collapsed below `sm`, until the toggle overrides it.
const collapsed = useStorage<boolean | null>("buzz-sidebar-collapsed", null, undefined, {
	serializer: StorageSerializers.boolean,
})
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

const eventTitle = ref("")
watch(
	eventId,
	(id) => {
		eventTitle.value = ""
		if (!id) return
		// The user can hop between events faster than a fetch returns, so a late
		// response for the event that was left has to be dropped.
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
			<Sidebar v-model:collapsed="collapsed">
				<!-- px-1: puts the header mark on the item-icon centerline, in both states. -->
				<div class="flex shrink-0 items-center px-1 pt-2">
					<ManagerSidebarHeader :event-id="eventId" :event-title="eventTitle" />
				</div>

				<div class="flex flex-col gap-0.5 mx-2 py-2">
					<SidebarItem
						v-for="item in items"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:to="item.to"
						:active="isActive(item.to)"
					/>
				</div>

				<div class="mt-auto px-2 py-2">
					<SidebarCollapseToggle />
				</div>
			</Sidebar>
		</template>

		<div class="flex flex-col h-full min-h-0 bg-surface-sidebar py-2 pl-2">
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
