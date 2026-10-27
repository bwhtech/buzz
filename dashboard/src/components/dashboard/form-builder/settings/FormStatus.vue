<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{ live: boolean; closeAt?: string | null; noun: string }>()

const DAY = 24 * 60 * 60 * 1000
const formatDate = (date: Date) =>
	date.toLocaleDateString(undefined, { day: "numeric", month: "short" })

const STYLES = {
	open: "bg-surface-green-1 ring-outline-green-2",
	closed: "bg-surface-amber-1 ring-outline-amber-2",
	draft: "bg-surface-gray-2 ring-outline-gray-2",
}
const DOTS = {
	open: "bg-surface-green-3",
	closed: "bg-surface-amber-5",
	draft: "bg-surface-gray-5",
}
const TITLES = { open: "text-ink-green-7", closed: "text-ink-amber-7", draft: "text-ink-gray-8" }

const status = computed(() => {
	const close = props.closeAt ? new Date(props.closeAt) : null
	if (!props.live)
		return {
			state: "draft" as const,
			title: "Not published",
			detail: `Publish from the top bar to start accepting ${props.noun}`,
		}
	if (close && close.getTime() <= Date.now())
		return {
			state: "closed" as const,
			title: "Closed",
			detail: `Stopped accepting ${props.noun} on ${formatDate(close)}`,
		}
	return { state: "open" as const, title: `Accepting ${props.noun}`, detail: openDetail(close) }
})

function openDetail(close: Date | null) {
	if (!close) return "Open until you unpublish it"
	const days = Math.ceil((close.getTime() - Date.now()) / DAY)
	const left = days <= 1 ? "last day" : `${days} days left`
	return `Closes on ${formatDate(close)} · ${left}`
}
</script>

<template>
	<div
		class="flex items-center gap-3 rounded-5 px-4 py-3.5 ring-1 ring-inset"
		:class="STYLES[status.state]"
		role="status"
	>
		<span class="size-2.5 shrink-0 rounded-full" :class="DOTS[status.state]" aria-hidden="true" />
		<div class="min-w-0">
			<p class="text-p-base font-semibold" :class="TITLES[status.state]">{{ status.title }}</p>
			<p class="mt-0.5 text-p-sm text-ink-gray-6">{{ status.detail }}</p>
		</div>
	</div>
</template>
