<script setup lang="ts">
import {
	Avatar,
	BottomSheet,
	Button,
	Dropdown,
	ItemListRow,
	TabButtons,
	Tooltip,
	sidebarCollapsedKey,
	useColorScheme,
	type DropdownOptions,
	type TabButtonValue,
} from "frappe-ui"
import { computed, inject, ref } from "vue"

import UserSettingsDialog from "@/components/UserSettingsDialog.vue"
import { session } from "@/data/session"

withDefaults(defineProps<{ variant?: "sidebar" | "sheet" }>(), { variant: "sidebar" })

const isCollapsed = inject(
	sidebarCollapsedKey,
	computed(() => false),
)

const { colorScheme, setColorScheme } = useColorScheme()

const settingsOpen = ref(false)
const sheetOpen = ref(false)

const NEW_ISSUE_URL = "https://github.com/bwhtech/buzz/issues/new"

const themes = [
	{ value: "light", icon: "lucide-sun", label: __("Light") },
	{ value: "dark", icon: "lucide-moon", label: __("Dark") },
	{ value: "system", icon: "lucide-monitor", label: __("System") },
] as const

const themeTabs = [...themes]
const setTheme = (value: TabButtonValue) =>
	setColorScheme(value as (typeof themes)[number]["value"])

const openSettings = () => (settingsOpen.value = true)
const reportIssue = () => window.open(NEW_ISSUE_URL, "_blank", "noopener")
const logOut = () => session.logout.fetch()
const logOutLabel = computed(() => (session.logout.loading ? __("Signing out…") : __("Log Out")))

// preventDefault keeps the menu open, so themes can be compared without reopening it.
const themeOptions = computed<DropdownOptions>(() =>
	themes.map((theme) => ({
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
				onClick: openSettings,
			},
			{
				label: __("Theme"),
				icon: "lucide-sun-moon",
				submenu: themeOptions.value,
			},
			{
				label: __("Report an Issue"),
				icon: "lucide-bug",
				onClick: reportIssue,
			},
		],
	},
	{
		group: "session",
		hideLabel: true,
		options: [
			{
				label: logOutLabel.value,
				icon: "lucide-log-out",
				theme: "red",
				disabled: session.logout.loading,
				onClick: logOut,
			},
		],
	},
])
</script>

<template>
	<template v-if="variant === 'sheet'">
		<Button
			variant="ghost"
			:aria-label="__('Account menu')"
			data-testid="account-menu"
			@click="sheetOpen = true"
		>
			<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="md" />
		</Button>

		<BottomSheet v-model:open="sheetOpen">
			<div class="flex items-center gap-3 px-5 pb-4">
				<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="2xl" />
				<div class="min-w-0">
					<p class="truncate text-lg-medium text-ink-gray-9">{{ session.fullName }}</p>
					<p class="truncate text-base text-ink-gray-6">{{ session.user }}</p>
				</div>
			</div>

			<div class="border-t border-outline-gray-1 p-2">
				<Button
					class="w-full !justify-start"
					variant="ghost"
					size="lg"
					icon-left="lucide-settings"
					:label="__('Settings')"
					@click="((sheetOpen = false), openSettings())"
				/>
				<ItemListRow size="lg">
					<template #prefix><span class="lucide-sun-moon size-5" aria-hidden="true" /></template>
					{{ __("Theme") }}
					<template #suffix>
						<TabButtons
							:model-value="colorScheme"
							:options="themeTabs"
							@update:model-value="setTheme"
						/>
					</template>
				</ItemListRow>
				<Button
					class="w-full !justify-start"
					variant="ghost"
					size="lg"
					icon-left="lucide-bug"
					:label="__('Report an Issue')"
					@click="reportIssue"
				/>
			</div>

			<div class="border-t border-outline-gray-1 p-2 pb-6">
				<Button
					class="w-full !justify-start"
					variant="ghost"
					theme="red"
					size="lg"
					icon-left="lucide-log-out"
					:label="logOutLabel"
					:loading="session.logout.loading"
					@click="logOut"
				/>
			</div>
		</BottomSheet>
	</template>

	<Dropdown v-else :options="menu" side="top" align="start" match-trigger-width>
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
