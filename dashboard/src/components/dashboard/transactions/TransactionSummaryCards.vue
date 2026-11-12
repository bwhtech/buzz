<script setup lang="ts">
import { ErrorMessage, useCall } from "frappe-ui"
import { NumberCard } from "frappe-ui/charts"
import { computed } from "vue"

import type { FrappeError, TransactionSummary } from "@/types"
import { transactionSummaryCards } from "@/utils/transactionSummary"

const props = defineProps<{ event: string }>()

const CARD = "!rounded-5 !border-outline-gray-2 !bg-surface-base"

const summary = useCall<TransactionSummary, { event: string }>({
	url: "/api/v2/method/buzz.api.transactions.get_transaction_summary",
	params: () => ({ event: props.event }),
})

const sets = computed(() => (summary.data ? transactionSummaryCards(summary.data) : []))
const showCurrency = computed(() => sets.value.length > 1)
</script>

<template>
	<section aria-label="Overview" class="space-y-6">
		<div v-if="summary.loading && !summary.data" class="grid gap-2 sm:grid-cols-3">
			<NumberCard v-for="card in 3" :key="card" :class="CARD" title="" :value="null" loading />
		</div>

		<ErrorMessage
			v-else-if="summary.error"
			:message="(summary.error as FrappeError | null)?.message"
		/>

		<div v-for="set in sets" :key="set.currency" class="space-y-2">
			<h2 v-if="showCurrency" class="text-sm font-medium text-ink-gray-5">{{ set.currency }}</h2>
			<div class="grid gap-2 sm:grid-cols-3">
				<NumberCard
					v-for="card in set.cards"
					:key="card.title"
					:class="CARD"
					:title="card.title"
					:value="card.value"
					:delta-caption="card.caption"
				/>
			</div>
			<p class="text-sm text-ink-gray-5">{{ set.footnote }}</p>
		</div>
	</section>
</template>
