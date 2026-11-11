<script setup lang="ts">
import { computed } from "vue"

import type { RequestCounts } from "@/types"
import { pluralize } from "@/utils/pluralize"

const props = defineProps<{ event: string; counts: RequestCounts | null }>()

const seatsFree = computed(() =>
	Object.values(props.counts?.seats_free ?? {}).reduce((total, seats) => total + seats, 0),
)

const cards = computed(() => [
	{
		label: "Waiting for review",
		value: props.counts?.pending ?? 0,
		hint: "Review requests",
		to: `/manage/events/${props.event}/approvals`,
		dot: Boolean(props.counts?.pending),
	},
	{
		label: "On waitlist",
		value: props.counts?.waiting ?? 0,
		hint: seatsFree.value ? `${pluralize(seatsFree.value, "seat")} freed` : "Open waitlist",
		to: `/manage/events/${props.event}/waitlist`,
		dot: false,
	},
])
</script>

<template>
	<div class="grid gap-3 sm:grid-cols-2">
		<RouterLink
			v-for="card in cards"
			:key="card.label"
			:to="card.to"
			class="flex flex-col gap-1.5 rounded-6 border border-outline-gray-2 px-4 py-4 transition-[border-color,box-shadow] duration-150 ease-out hover:border-outline-gray-3 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
		>
			<span class="flex items-center gap-1.5 text-sm text-ink-gray-5">
				<span v-if="card.dot" class="size-1.5 rounded-full bg-surface-amber-6" aria-hidden="true" />
				{{ card.label }}
			</span>
			<span class="text-2xl font-semibold tabular-nums text-ink-gray-9">{{ card.value }}</span>
			<span class="flex items-center gap-1 text-sm text-ink-gray-6">
				{{ card.hint }}
				<span class="lucide-arrow-right size-3.5" aria-hidden="true" />
			</span>
		</RouterLink>
	</div>
</template>
