<script setup lang="ts">
import TeamSwitcher from "@/components/TeamSwitcher.vue";
import UserMenu from "@/components/UserMenu.vue";
import { DesktopShell, Sidebar, SidebarItem, SidebarLabel } from "frappe-ui";
import { ref } from "vue";

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
	<DesktopShell>
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
			<div
				class="flex h-[calc(100vh-1rem)] flex-col items-center justify-center gap-4 rounded-l-lg bg-surface-elevation-1 shadow-base"
			>
				<svg
					viewBox="0 0 64 64"
					fill="none"
					stroke="currentColor"
					stroke-width="2.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-16 text-ink-gray-4"
					aria-hidden="true"
				>
					<path d="M14 22v34M50 22v34" />
					<rect x="8" y="24" width="48" height="12" rx="2" />
					<rect x="8" y="42" width="48" height="12" rx="2" />
					<path
						d="M20 24 12 36M34 24 26 36M48 24 40 36M20 42 12 54M34 42 26 54M48 42 40 54"
					/>
					<path d="M32 8v14" />
				</svg>

				<div class="text-center">
					<p class="text-lg font-medium text-ink-gray-7">Work in progress</p>
					<p class="mt-1 text-base text-ink-gray-5">This page is still being built.</p>
				</div>
			</div>
		</div>
	</DesktopShell>
</template>
