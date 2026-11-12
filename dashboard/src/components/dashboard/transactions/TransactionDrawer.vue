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
import BookingActivity from "@/components/dashboard/transactions/BookingActivity.vue"
import TransactionAmountsSection from "@/components/dashboard/transactions/TransactionAmountsSection.vue"
import TransactionBuyerSection from "@/components/dashboard/transactions/TransactionBuyerSection.vue"
import TransactionPaymentSection from "@/components/dashboard/transactions/TransactionPaymentSection.vue"
import TransactionRefundsSection from "@/components/dashboard/transactions/TransactionRefundsSection.vue"
import TransactionSourceSection from "@/components/dashboard/transactions/TransactionSourceSection.vue"
import TransactionTicketsSection from "@/components/dashboard/transactions/TransactionTicketsSection.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useMoney } from "@/composables/useMoney"
import type { TransactionDetail } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"
import { transactionStatus } from "@/utils/transactionStatus"

const props = defineProps<{
	event: string
	booking: string | null
	hasPrevious: boolean
	hasNext: boolean
	// download_invoice reads the booking itself, which takes guests access.
	canDownloadInvoice: boolean
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ previous: []; next: [] }>()

const copyToClipboard = useCopyToClipboard()

const detail = useCall<TransactionDetail, { event: string; booking: string }>({
	url: "/api/v2/method/buzz.api.transactions.get_transaction",
	immediate: false,
})

watch(
	() => props.booking,
	// The error shows from detail.error; submit() rejects as well.
	(booking) => booking && detail.submit({ event: props.event, booking }).catch(() => {}),
	{ immediate: true },
)

// Stepping keeps the previous booking's answer until the next one lands; it is not shown.
const transaction = computed(() =>
	detail.data?.name === props.booking ? (detail.data ?? null) : null,
)

const status = computed(() => (transaction.value ? transactionStatus(transaction.value) : null))

const money = useMoney()
const total = computed(() =>
	transaction.value
		? money(transaction.value.amounts.total_amount, transaction.value.currency)
		: "",
)

const byline = computed(() => {
	if (!transaction.value) return ""
	const { buyer, created_at } = transaction.value
	return `${buyer.name || buyer.email || "Unnamed buyer"} · ${dayjsLocal(created_at).format("D MMM YYYY, h:mm A")}`
})

const invoiceUrl = computed(() => {
	const booking = transaction.value
	if (!props.canDownloadInvoice || !booking?.buyer.invoice_requested) return undefined
	if (booking.payment_status === "Verification Pending") return undefined
	return `/api/v2/method/buzz.api.booking.download_invoice?booking_id=${encodeURIComponent(booking.name)}`
})
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
					<div class="flex items-center gap-1">
						<DrawerTitle class="font-mono text-base text-ink-gray-5">{{ booking }}</DrawerTitle>
						<Button
							v-if="booking"
							variant="ghost"
							size="sm"
							icon="lucide-copy"
							aria-label="Copy booking ID"
							@click="copyToClipboard(booking, 'Booking ID copied')"
						/>
					</div>
					<template v-if="transaction && status">
						<p class="text-3xl font-semibold tabular-nums text-ink-gray-9">{{ total }}</p>
						<Badge variant="subtle" size="md" :theme="status.theme" :label="status.label" />
					</template>
					<DrawerDescription class="text-base tabular-nums text-ink-gray-5">
						{{ byline }}
					</DrawerDescription>
				</header>

				<ErrorMessage
					v-if="detail.error && !detail.loading"
					:message="serverErrorMessage(detail.error)"
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
					<BookingActivity
						:key="transaction.name"
						:booking="transaction.name"
						:buyer-name="transaction.buyer.name"
						:buyer-email="transaction.buyer.email"
					/>
				</template>
			</div>

			<template v-if="invoiceUrl" #footer>
				<Button
					class="flex-1"
					size="md"
					variant="subtle"
					icon-left="lucide-download"
					label="Download invoice"
					:href="invoiceUrl"
				/>
			</template>
		</DrawerContent>
	</Drawer>
</template>
