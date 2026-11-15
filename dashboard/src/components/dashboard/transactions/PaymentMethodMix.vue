<script setup lang="ts">
import { Skeleton } from "frappe-ui"
import { ChartCard } from "frappe-ui/charts"
import { computed } from "vue"

import { useMoney } from "@/composables/useMoney"
import type { MethodShare } from "@/utils/transactionSummary"

const props = defineProps<{ methods: MethodShare[]; currency: string; loading?: boolean }>()

const money = useMoney()

// Gray steps rather than hues: a payment method is a category, not a state.
const SHADES = ["bg-surface-gray-9", "bg-surface-gray-6", "bg-surface-gray-4", "bg-surface-gray-3"]
const shade = (index: number) => SHADES[Math.min(index, SHADES.length - 1)]

const total = computed(() => props.methods.reduce((sum, method) => sum + method.amount, 0))
const amount = (value: number) => money(value, props.currency)
</script>

<template>
	<ChartCard>
		<div class="flex flex-col gap-1.5">
			<div class="flex items-center justify-between gap-3 text-sm text-ink-gray-5">
				<span>Payment methods</span>
				<span>Collected, all time</span>
			</div>

			<Skeleton v-if="loading" class="my-1 h-7 w-28 rounded-4" />
			<p v-else class="truncate text-3xl-semibold tabular-nums text-ink-gray-9">
				{{ amount(total) }}
			</p>

			<div class="mt-3 flex h-2 gap-0.5 overflow-hidden rounded-full bg-surface-gray-2">
				<div
					v-for="(method, index) in methods"
					:key="method.method"
					class="first:rounded-l-full last:rounded-r-full"
					:class="shade(index)"
					:style="{ width: `${method.percent}%` }"
					:title="`${method.method}: ${amount(method.amount)}`"
				/>
			</div>

			<ol class="mt-3 flex flex-col gap-2 text-base">
				<li
					v-for="(method, index) in methods"
					:key="method.method"
					class="flex min-w-0 items-center gap-2"
				>
					<span class="w-3 shrink-0 text-sm tabular-nums text-ink-gray-4">{{ index + 1 }}</span>
					<span class="size-2 shrink-0 rounded-full" :class="shade(index)" aria-hidden="true" />
					<span class="min-w-0 flex-1 truncate text-ink-gray-8" :title="method.method">
						{{ method.method }}
					</span>
					<span class="shrink-0 tabular-nums text-ink-gray-9">{{ amount(method.amount) }}</span>
					<span class="w-10 shrink-0 text-right text-sm tabular-nums text-ink-gray-5">
						{{ Math.round(method.percent) }}%
					</span>
				</li>
				<li v-if="!loading && !methods.length" class="text-sm text-ink-gray-5">No payments yet</li>
			</ol>
		</div>
	</ChartCard>
</template>
