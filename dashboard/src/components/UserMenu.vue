<script setup lang="ts">
import {
	Avatar,
	Dropdown,
	KeyboardShortcut,
	Tooltip,
	sidebarCollapsedKey,
	useColorScheme,
	type DropdownOptions,
} from "frappe-ui"
import { computed, h, inject, ref } from "vue"

import UserSettingsDialog from "@/components/UserSettingsDialog.vue"
import { session } from "@/data/session"

const isCollapsed = inject(
	sidebarCollapsedKey,
	computed(() => false),
)

const { colorScheme, setColorScheme } = useColorScheme()

const settingsOpen = ref(false)

const NEW_ISSUE_URL = "https://github.com/bwhtech/buzz/issues/new"

// preventDefault keeps the menu open, so themes can be compared without reopening it.
const themeOptions = computed<DropdownOptions>(() =>
	(
		[
			{ value: "light", icon: "lucide-sun", label: __("Light") },
			{ value: "dark", icon: "lucide-moon", label: __("Dark") },
			{ value: "system", icon: "lucide-monitor", label: __("System") },
		] as const
	).map((theme) => ({
		label: theme.label,
		icon: theme.icon,
		selected: colorScheme.value === theme.value,
		onClick: (event: Event) => {
			event.preventDefault()
			setColorScheme(theme.value)
		},
	})),
)

const menu = computed<DropdownOptions>(() => [
	{
		group: "settings",
		hideLabel: true,
		options: [
			{
				label: __("Settings"),
				icon: "lucide-settings",
				onClick: () => (settingsOpen.value = true),
				slots: { suffix: () => h(KeyboardShortcut, { combo: "G+S", bg: true }) },
			},
			{
				label: __("Theme"),
				icon: "lucide-sun-moon",
				submenu: themeOptions.value,
			},
			{
				label: __("Report an Issue"),
				icon: "lucide-bug",
				onClick: () => window.open(NEW_ISSUE_URL, "_blank", "noopener"),
			},
		],
	},
	{
		group: "session",
		hideLabel: true,
		options: [
			{
				label: session.logout.loading ? __("Signing out…") : __("Log Out"),
				icon: "lucide-log-out",
				theme: "red",
				disabled: session.logout.loading,
				onClick: () => session.logout.fetch(),
			},
		],
	},
])
</script>

<template>
	<Dropdown :options="menu" side="top" align="start" match-trigger-width>
		<template #default="{ open: isOpen }">
			<button
				data-testid="account-menu"
				class="flex h-12 w-full items-center gap-2 rounded-4 px-1.5 transition-[background-color,transform] duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98] focus-visible:outline-none focus-visible:focus-ring"
				:class="{ 'bg-surface-gray-2': isOpen }"
			>
				<Tooltip :text="session.fullName" side="right" :disabled="!isCollapsed">
					<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
				</Tooltip>
				<span
					class="flex min-w-0 flex-col text-left transition-opacity duration-150 ease-out"
					:class="isCollapsed ? 'w-0 flex-none overflow-hidden opacity-0' : 'flex-1 opacity-100'"
				>
					<span :title="session.fullName" class="truncate text-base font-medium text-ink-gray-8">
						{{ session.fullName }}
					</span>
					<span :title="session.user" class="truncate text-sm text-ink-gray-6">
						{{ session.user }}
					</span>
				</span>
				<!-- Names the control without replacing the name the button already shows. -->
				<span class="sr-only">{{ __("Account menu") }}</span>
				<span
					class="lucide-chevrons-up-down size-4 shrink-0 text-ink-gray-5 transition-opacity duration-150 ease-out"
					:class="{ 'w-0 overflow-hidden opacity-0': isCollapsed }"
				/>
			</button>
		</template>
	</Dropdown>

	<UserSettingsDialog v-model:open="settingsOpen" />
</template>
