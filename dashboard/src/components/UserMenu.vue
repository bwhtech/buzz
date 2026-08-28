<script setup lang="ts">
import { Avatar, Button, Divider, Popover, useColorScheme } from "frappe-ui"

import { session } from "@/data/session"

const { colorScheme, setColorScheme } = useColorScheme()

const themes = [
	{ value: "light", icon: "lucide-sun", label: "Light" },
	{ value: "dark", icon: "lucide-moon", label: "Dark" },
	{ value: "system", icon: "lucide-monitor", label: "System" },
] as const
</script>

<template>
	<Popover match-trigger-width side="bottom" align="start">
		<template #trigger="{ open: isOpen }">
			<button
				aria-label="Account"
				class="group flex h-10 w-full items-center gap-2 rounded-4 px-1.5 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="{ 'bg-surface-gray-2': isOpen }"
			>
				<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
				<span class="flex-1 truncate text-left text-base text-ink-gray-8">
					{{ session.fullName }}
				</span>
				<span
					class="grid size-6 shrink-0 place-items-center rounded-4 transition-colors duration-150 group-hover:bg-surface-gray-3"
					:class="{ 'bg-surface-gray-3': isOpen }"
				>
					<span class="lucide-ellipsis size-4 text-ink-gray-6" />
				</span>
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
