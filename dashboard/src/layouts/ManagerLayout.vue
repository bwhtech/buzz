<script setup lang="ts">
import TeamSwitcher from "@/components/TeamSwitcher.vue";
import UserMenu from "@/components/UserMenu.vue";
import { useTeamAccess } from "@/composables/useTeamAccess";
import NotFound from "@/pages/NotFound.vue";
import { DesktopShell, PageHeaderTarget, Sidebar, SidebarItem, SidebarLabel } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

const collapsed = ref(false);
const route = useRoute();

const access = useTeamAccess();

// SidebarItem infers this from `to` on paper, but its `active` prop is declared
// type Boolean, so Vue casts the absent prop to false and the inference never runs.
const isActive = (to: string) => route.path === to;

const personalItems = [
	{ label: "My Events", icon: "lucide-calendar-days", to: "/manage/events" },
	{ label: "My Tickets", icon: "lucide-ticket", to: "/manage/tickets" },
	{ label: "Talk Proposals", icon: "lucide-file-text", to: "/manage/proposals" },
	{ label: "Sponsorship", icon: "lucide-handshake", to: "/manage/sponsorship" },
];

// Team-scoped destinations read the active team from data/teams rather than the path,
// so they are fixed and need no team loaded to render.
const teamItems = [
	{ label: "Overview", icon: "lucide-layout-dashboard", to: "/manage/team/overview" },
	{ label: "Events", icon: "lucide-calendar-days", to: "/manage/team/events" },
	{ label: "Members", icon: "lucide-users-round", to: "/manage/team/members" },
];

// An event opens into the same shell with its own destinations in place of the
// personal and team ones.
const eventId = computed(() => route.params.eventId as string | undefined);

const eventItems = computed(() => [
	{ label: "Back", icon: "lucide-arrow-left", to: "/" },
	{
		label: "Details",
		icon: "lucide-receipt-text",
		to: `/manage/events/${eventId.value}/details`,
	},
	{
		label: "Guests",
		icon: "lucide-users-round",
		to: `/manage/events/${eventId.value}/guests`,
	},
	{
		label: "Talks",
		icon: "lucide-presentation",
		to: `/manage/events/${eventId.value}/talks`,
	},
]);
</script>

<template>
	<NotFound v-if="access === 'denied'" />

	<!-- scroll=false: the rounded panel below owns its own scroll. -->
	<DesktopShell v-else-if="access === 'granted'" :scroll="false">
		<template #sidebar>
			<Sidebar v-model:collapsed="collapsed">
				<div class="flex h-12 shrink-0 items-center px-1">
					<TeamSwitcher />
				</div>

				<div v-if="eventId" class="flex flex-col mx-2 py-2">
					<SidebarItem
						v-for="item in eventItems"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:to="item.to"
						:active="isActive(item.to)"
					/>
				</div>

				<div v-else class="flex flex-col mx-2 py-2">
					<SidebarItem
						v-for="item in personalItems"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:to="item.to"
						:active="isActive(item.to)"
					/>

					<SidebarLabel divider class="mt-3 px-2">Team</SidebarLabel>
					<SidebarItem
						v-for="item in teamItems"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:to="item.to"
						:active="isActive(item.to)"
					/>
				</div>

				<div class="mt-auto px-2 py-2">
					<UserMenu />
				</div>
			</Sidebar>
		</template>

		<div class="h-full min-h-0 bg-surface-sidebar py-2 pl-2">
			<div
				class="flex h-full flex-col overflow-hidden rounded-l-lg bg-surface-elevation-1 shadow-base"
			>
				<PageHeaderTarget />
				<div class="min-h-0 flex-1 overflow-y-auto">
					<router-view />
				</div>
			</div>
		</div>
	</DesktopShell>
</template>
