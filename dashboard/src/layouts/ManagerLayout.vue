<script setup lang="ts">
import TeamSwitcher from "@/components/TeamSwitcher.vue";
import UserMenu from "@/components/UserMenu.vue";
import { isTeamMember } from "@/data/teams";
import NotFound from "@/pages/NotFound.vue";
import { DesktopShell, Sidebar, SidebarItem, SidebarLabel } from "frappe-ui";
import { ref } from "vue";

const isMember = ref<boolean | null>(null);
isTeamMember().then((member) => {
	isMember.value = member;
});

const collapsed = ref(false);
const active = ref("Calendar");

const personalItems = [
	{ label: "Calendar", icon: "lucide-calendar-days" },
	{ label: "My Tickets", icon: "lucide-ticket" },
	{ label: "Talk Proposals", icon: "lucide-file-text" },
	{ label: "Sponsorship", icon: "lucide-handshake" },
];

const teamItems = [
	{ label: "Overview", icon: "lucide-layout-dashboard" },
	{ label: "Registrations", icon: "lucide-users" },
	{ label: "Sponsors", icon: "lucide-badge-dollar-sign" },
	{ label: "More", icon: "lucide-ellipsis" },
];
</script>

<template>
	<NotFound v-if="isMember === false" />

	<DesktopShell v-else-if="isMember">
		<template #sidebar>
			<Sidebar v-model:collapsed="collapsed">
				<div class="flex h-12 shrink-0 items-center px-1">
					<TeamSwitcher />
				</div>

				<div class="flex flex-col mx-2 py-2">
					<SidebarItem
						v-for="item in personalItems"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:active="active === item.label"
						@click="active = item.label"
					/>

					<SidebarLabel divider class="mt-3 px-2">Team</SidebarLabel>
					<SidebarItem
						v-for="item in teamItems"
						:key="item.label"
						:label="item.label"
						:icon="item.icon"
						:active="active === item.label"
						@click="active = item.label"
					/>
				</div>

				<div class="mt-auto px-2 py-2">
					<UserMenu />
				</div>
			</Sidebar>
		</template>

		<div class="h-[calc(100vh-1rem)] bg-surface-sidebar py-2 pl-2">
			<div class="h-full rounded-l-lg bg-surface-elevation-1 shadow-base overflow-y-auto">
				<router-view />
			</div>
		</div>
	</DesktopShell>
</template>
