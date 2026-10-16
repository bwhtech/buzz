<template>
	<header class="sticky top-0 z-20 border-b border-outline-gray-1 bg-surface-base">
		<div
			class="mx-auto grid h-14 max-w-6xl grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-4 px-6"
		>
			<div class="flex">
				<Button variant="ghost" :label="__('Back to event')" @click="backToEvent">
					<template #prefix><LucideArrowLeft class="size-4" /></template>
				</Button>
			</div>
			<div class="flex min-w-0 flex-col items-center gap-px text-center">
				<span class="max-w-full truncate text-base font-semibold text-ink-gray-9">
					{{ __(eventDetails.title) }}
				</span>
				<span v-if="subtitle" class="max-w-full truncate text-xs text-ink-gray-5">{{
					subtitle
				}}</span>
			</div>
			<div class="flex items-center justify-end gap-3">
				<span
					v-if="secondsLeft"
					role="timer"
					:aria-label="__('Tickets held for {0}', [clock])"
					class="flex items-center gap-1.5 text-p-sm tabular-nums text-ink-gray-6"
				>
					<LucideTimer class="size-3.5" />
					{{ clock }}
				</span>
				<Button
					variant="ghost"
					:tooltip="__('Toggle theme')"
					:aria-label="__('Toggle theme')"
					@click="toggleTheme"
				>
					<template #icon><LucideMoon class="size-4" /></template>
				</Button>
			</div>
		</div>
	</header>
</template>

<script setup lang="ts">
import { Button, resolvedColorScheme, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import LucideArrowLeft from "~icons/lucide/arrow-left"
import LucideMoon from "~icons/lucide/moon"
import LucideTimer from "~icons/lucide/timer"

import { eventPath } from "@/utils/eventUrl"

import { useEventDateLabels } from "./useEventDateLabels"

const props = defineProps<{
	eventDetails: Record<string, any>
	eventRoute: string
	secondsLeft: number | null
}>()

const { setColorScheme } = useColorScheme()

const { dateLabel, venueLabel } = useEventDateLabels(() => props.eventDetails)
const subtitle = computed(() => [dateLabel.value, venueLabel.value].filter(Boolean).join(" · "))
const clock = computed(() => {
	const seconds = props.secondsLeft ?? 0
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
})

// The event page is served outside the SPA's /b base.
const backToEvent = () => window.location.assign(eventPath(props.eventRoute))
const toggleTheme = () => setColorScheme(resolvedColorScheme() === "dark" ? "light" : "dark")
</script>
