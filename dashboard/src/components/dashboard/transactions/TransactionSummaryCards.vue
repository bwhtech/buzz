<script setup lang="ts">
import { Button, ErrorMessage, TabButtons, dayjsLocal, useCall } from "frappe-ui"
import { NumberCard } from "frappe-ui/charts"
import { computed, ref } from "vue"

import PaymentMethodMix from "@/components/dashboard/transactions/PaymentMethodMix.vue"
import { devTransactionSummary } from "@/components/dashboard/transactions/transactionFixtures"
import { useMoney } from "@/composables/useMoney"
import type { TransactionSummary } from "@/types"
import { pluralize } from "@/utils/pluralize"
import { serverErrorMessage } from "@/utils/serverError"
import {
	type Period,
	currenciesByVolume,
	paymentMethodShares,
	pendingFor,
	percentChange,
	periodStats,
	summaryFootnote,
} from "@/utils/transactionSummary"

const props = defineProps<{ event: string }>()

const emit = defineEmits<{ reviewPending: [] }>()

const CARD = "!rounded-5 !border-outline-gray-2 !bg-surface-base"

const PERIODS = [
	{ label: "7D", value: "7d" },
	{ label: "30D", value: "30d" },
	{ label: "All", value: "all" },
]
const PERIOD_CAPTIONS: Record<Period, string> = {
	"7d": "vs previous 7 days",
	"30d": "vs previous 30 days",
	all: "",
}

const money = useMoney()

const summary = useCall<TransactionSummary, { event: string }>({
	url: "/api/v2/method/buzz.api.transactions.get_transaction_summary",
	params: () => ({ event: props.event }),
	transform: devTransactionSummary,
})

const currencies = computed(() => (summary.data ? currenciesByVolume(summary.data) : []))
const picked = ref<string | null>(null)
// An event with no paid bookings has no currency yet; its cards read zero.
const currency = computed(() =>
	picked.value && currencies.value.includes(picked.value)
		? picked.value
		: (currencies.value[0] ?? ""),
)
const currencyOptions = computed(() =>
	currencies.value.map((code) => ({ label: code, value: code })),
)
const period = ref<Period>("all")

const stats = computed(() =>
	summary.data
		? periodStats(summary.data, currency.value, period.value, dayjsLocal().format("YYYY-MM-DD"))
		: null,
)
const amount = (value: number) => (currency.value ? money(value, currency.value) : "0")
const tickets = computed(
	() => summary.data?.currencies.find((row) => row.currency === currency.value)?.tickets ?? 0,
)

const revenueCaption = computed(() =>
	period.value === "all"
		? `${amount(stats.value?.refunded ?? 0)} refunded`
		: PERIOD_CAPTIONS[period.value],
)
const bookingsCaption = computed(() =>
	period.value === "all" ? pluralize(tickets.value, "ticket") : PERIOD_CAPTIONS[period.value],
)
const bookingsDelta = computed(() =>
	stats.value?.previousBookings == null
		? null
		: stats.value.bookings - stats.value.previousBookings,
)

const methods = computed(() =>
	summary.data ? paymentMethodShares(summary.data, currency.value) : [],
)
const pending = computed(() => (summary.data ? pendingFor(summary.data, currency.value) : null))
const footnote = computed(() =>
	summary.data ? summaryFootnote(summary.data, currency.value, money) : "",
)
</script>

<template>
	<section aria-labelledby="transactions-overview" class="space-y-3">
		<div class="flex min-h-7 flex-wrap items-center justify-between gap-3">
			<h2 id="transactions-overview" class="text-lg font-semibold text-ink-gray-9">Overview</h2>
			<div class="flex items-center gap-2">
				<TabButtons
					v-if="currencies.length > 1"
					:options="currencyOptions"
					:model-value="currency"
					@update:model-value="picked = String($event)"
				/>
				<TabButtons v-model="period" :options="PERIODS" />
			</div>
		</div>

		<ErrorMessage
			v-if="summary.error && !summary.data"
			:message="serverErrorMessage(summary.error)"
		/>

		<div v-else class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
			<NumberCard
				:class="CARD"
				class="sm:col-span-2"
				title="Net revenue"
				:loading="!stats"
				:value="stats ? amount(stats.net) : null"
				:delta="stats ? percentChange(stats.net, stats.previousNet) : null"
				delta-suffix="%"
				:delta-caption="revenueCaption"
				:sparkline="stats?.net ? { data: stats.netRunning } : undefined"
			/>
			<PaymentMethodMix
				:class="CARD"
				class="sm:col-span-2 lg:col-span-1 lg:row-span-2"
				:methods="methods"
				:currency="currency"
				:loading="!stats"
			/>
			<NumberCard
				:class="CARD"
				title="Paid bookings"
				:loading="!stats"
				:value="stats ? stats.bookings.toLocaleString() : null"
				:delta="bookingsDelta"
				:delta-caption="bookingsCaption"
				:sparkline="stats?.bookings ? { data: stats.bookingBars, type: 'bar' } : undefined"
			/>
			<NumberCard
				:class="CARD"
				title="Average order"
				:loading="!stats"
				:value="stats ? amount(stats.averageOrder) : null"
				delta-caption="per paid booking, before refunds"
			/>
		</div>

		<div
			v-if="pending"
			class="flex items-center gap-3 rounded-5 bg-surface-amber-1 py-2 pl-3 pr-2 text-p-sm text-ink-amber-8"
		>
			<span class="lucide-hourglass size-4 shrink-0" aria-hidden="true" />
			<span class="min-w-0 flex-1">
				{{ pluralize(pending.bookings, "booking") }} worth {{ amount(pending.amount) }}
				{{ pending.bookings === 1 ? "is" : "are" }} awaiting payment verification.
			</span>
			<Button variant="ghost" size="sm" label="Review" @click="emit('reviewPending')" />
		</div>

		<p v-if="footnote" class="text-sm text-ink-gray-5">{{ footnote }}</p>
	</section>
</template>
