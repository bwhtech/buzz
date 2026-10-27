<script setup lang="ts">
import { computed } from "vue"

import { wallClockDate, wallClockIn } from "@/utils/timeZones"

// `closeAt` is on the event's clock, as the server compares it.
const props = defineProps<{
	live: boolean
	closeAt?: string | null
	timeZone?: string | null
	noun: string
}>()

const DAY = 24 * 60 * 60 * 1000
const formatDate = (date: Date) =>
	date.toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" })

const STATES = {
	open: {
		box: "bg-surface-green-1 ring-outline-green-2",
		dot: "bg-surface-green-3",
		title: "text-ink-green-7",
	},
	closed: {
		box: "bg-surface-amber-1 ring-outline-amber-2",
		dot: "bg-surface-amber-5",
		title: "text-ink-amber-7",
	},
	draft: {
		box: "bg-surface-gray-2 ring-outline-gray-2",
		dot: "bg-surface-gray-5",
		title: "text-ink-gray-8",
	},
}

const status = computed(() => {
	const close = props.closeAt ? wallClockDate(props.closeAt) : null
	const now = wallClockDate(wallClockIn(props.timeZone))
	if (!props.live)
		return {
			state: "draft" as const,
			title: "Not published",
			detail: `Publish from the top bar to start accepting ${props.noun}`,
		}
	if (close && close <= now)
		return {
			state: "closed" as const,
			title: "Closed",
			detail: `Stopped accepting ${props.noun} on ${formatDate(close)}`,
		}
	return {
		state: "open" as const,
		title: `Accepting ${props.noun}`,
		detail: openDetail(close, now),
	}
})

function openDetail(close: Date | null, now: Date) {
	if (!close) return "Open until you unpublish it"
	const days = Math.ceil((close.getTime() - now.getTime()) / DAY)
	const left = days <= 1 ? "last day" : `${days} days left`
	return `Closes on ${formatDate(close)} · ${left}`
}
</script>

<template>
	<div
		class="flex items-center gap-3 rounded-5 px-4 py-3.5 ring-1 ring-inset"
		:class="STATES[status.state].box"
		role="status"
	>
		<span
			class="size-2.5 shrink-0 rounded-full"
			:class="STATES[status.state].dot"
			aria-hidden="true"
		/>
		<div class="min-w-0">
			<p class="text-p-base font-semibold" :class="STATES[status.state].title">
				{{ status.title }}
			</p>
			<p class="mt-0.5 text-p-sm text-ink-gray-6">{{ status.detail }}</p>
		</div>
	</div>
</template>
