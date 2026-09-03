<script setup lang="ts">
import {
	Avatar,
	Button,
	Divider,
	Popover,
	Tooltip,
	sidebarCollapsedKey,
	useColorScheme,
} from "frappe-ui"
import { computed, inject } from "vue"

import { session } from "@/data/session"

const isCollapsed = inject(
	sidebarCollapsedKey,
	computed(() => false),
)

const { colorScheme, setColorScheme } = useColorScheme()

const themes = [
	{ value: "light", icon: "lucide-sun", label: "Light" },
	{ value: "dark", icon: "lucide-moon", label: "Dark" },
	{ value: "system", icon: "lucide-monitor", label: "System" },
] as const
</script>

<template>
	<Popover match-trigger-width side="top" align="start">
		<template #trigger="{ open: isOpen }">
			<button
				aria-label="Account menu"
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
					<span class="truncate text-base font-medium text-ink-gray-8">
						{{ session.fullName }}
					</span>
					<span class="truncate text-sm text-ink-gray-6">{{ session.user }}</span>
				</span>
				<span
					class="lucide-chevrons-up-down size-4 shrink-0 text-ink-gray-5 transition-opacity duration-150 ease-out"
					:class="{ 'w-0 overflow-hidden opacity-0': isCollapsed }"
				/>
			</button>
		</template>

		<template #default>
			<div class="p-2">
				<div class="flex flex-col px-1.5 py-1">
					<span class="truncate text-base text-ink-gray-8">{{ session.fullName }}</span>
					<span class="truncate text-sm text-ink-gray-5">{{ session.user }}</span>
				</div>

				<Divider class="my-2" />

				<Button size="sm" label="Settings" variant="ghost" class="w-full !justify-start" />

				<div class="flex h-8 items-center justify-between gap-2 px-1.5">
					<span class="text-base text-ink-gray-8 pl-0.5">Theme</span>
					<div class="flex items-center gap-1">
						<Button
							v-for="theme in themes"
							:key="theme.value"
							:variant="colorScheme === theme.value ? 'subtle' : 'ghost'"
							:icon="theme.icon"
							:label="theme.label"
							:tooltip="theme.label"
							@click="setColorScheme(theme.value)"
						/>
					</div>
				</div>

				<Divider class="my-2" />

				<Button
					size="sm"
					label="Log Out"
					variant="ghost"
					theme="red"
					class="w-full !justify-start"
					@click="session.logout.fetch()"
				/>
			</div>
		</template>
	</Popover>
</template>
