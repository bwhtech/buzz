<script setup lang="ts">
import { Badge, Button, ErrorMessage, Skeleton, Tooltip, dayjsLocal, useCall } from "frappe-ui"
import { computed, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import TransactionAmountsSection from "@/components/dashboard/transactions/TransactionAmountsSection.vue"
import TransactionBuyerSection from "@/components/dashboard/transactions/TransactionBuyerSection.vue"
import TransactionPaymentSection from "@/components/dashboard/transactions/TransactionPaymentSection.vue"
import TransactionRefundsSection from "@/components/dashboard/transactions/TransactionRefundsSection.vue"
import TransactionSourceSection from "@/components/dashboard/transactions/TransactionSourceSection.vue"
import TransactionTicketsSection from "@/components/dashboard/transactions/TransactionTicketsSection.vue"
import type { FrappeError, TransactionDetail } from "@/types"
import { formatCurrency } from "@/utils/currency"
import { paymentStatusTheme, refundStatusTheme } from "@/utils/transactionStatus"

const props = defineProps<{
	event: string
	booking: string | null
	hasPrevious: boolean
	hasNext: boolean
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ previous: []; next: [] }>()

const detail = useCall<TransactionDetail, { event: string; booking: string }>({
	url: "/api/v2/method/buzz.api.transactions.get_transaction",
	immediate: false,
})

watch(
	() => props.booking,
	(booking) => booking && detail.submit({ event: props.event, booking }),
	{ immediate: true },
)

// Stepping keeps the previous booking's answer until the next one lands; it is not shown.
const transaction = computed(() =>
	detail.data?.name === props.booking ? (detail.data ?? null) : null,
)

const createdAt = computed(() =>
	transaction.value ? dayjsLocal(transaction.value.created_at) : null,
)

const total = computed(() =>
	transaction.value
		? formatCurrency(
				transaction.value.amounts.total_amount,
				transaction.value.currency ?? undefined,
			)
		: "",
)
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<div class="flex items-center gap-1 p-4 pb-0">
				<DrawerCloseButton label="Close transaction" />
				<div class="ml-auto flex items-center gap-1">
					<Tooltip text="Previous transaction">
						<Button
							variant="ghost"
							size="sm"
							icon="lucide-chevron-up"
							aria-label="Previous transaction"
							:disabled="!hasPrevious"
							@click="emit('previous')"
						/>
					</Tooltip>
					<Tooltip text="Next transaction">
						<Button
							variant="ghost"
							size="sm"
							icon="lucide-chevron-down"
							aria-label="Next transaction"
							:disabled="!hasNext"
							@click="emit('next')"
						/>
					</Tooltip>
				</div>
			</div>

			<div class="flex flex-1 flex-col gap-8 overflow-y-auto overscroll-contain p-4">
				<header class="space-y-2">
					<DrawerTitle class="font-mono text-base text-ink-gray-5">{{ booking }}</DrawerTitle>
					<template v-if="transaction">
						<p class="text-3xl font-semibold tabular-nums text-ink-gray-9">{{ total }}</p>
						<div class="flex flex-wrap items-center gap-1.5">
							<Badge
								v-if="transaction.payment_status"
								variant="subtle"
								:theme="paymentStatusTheme(transaction.payment_status)"
								:label="transaction.payment_status"
							/>
							<Badge
								v-if="transaction.refund_status"
								variant="subtle"
								:theme="refundStatusTheme(transaction.refund_status)"
								:label="transaction.refund_status"
							/>
						</div>
					</template>
					<DrawerDescription class="text-base text-ink-gray-5">
						<Tooltip v-if="createdAt" :text="createdAt.fromNow()">
							<span>{{ createdAt.format("D MMM YYYY, h:mm A") }}</span>
						</Tooltip>
					</DrawerDescription>
				</header>

				<ErrorMessage
					v-if="detail.error && !detail.loading"
					:message="(detail.error as FrappeError | null)?.message"
				/>

				<div v-else-if="!transaction" class="space-y-3">
					<Skeleton class="h-8 w-40 rounded-4" />
					<Skeleton v-for="row in 4" :key="row" class="h-5 w-full rounded-4" />
				</div>

				<template v-else>
					<TransactionPaymentSection :transaction="transaction" />
					<TransactionAmountsSection :transaction="transaction" />
					<TransactionTicketsSection
						v-if="transaction.tickets.length"
						:transaction="transaction"
						:event="event"
					/>
					<TransactionRefundsSection v-if="transaction.refunds.length" :transaction="transaction" />
					<TransactionBuyerSection :buyer="transaction.buyer" />
					<TransactionSourceSection
						v-if="transaction.utm.length || transaction.answers.length"
						:transaction="transaction"
					/>
				</template>
			</div>
		</DrawerContent>
	</Drawer>
</template>
