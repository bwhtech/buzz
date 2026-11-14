<script setup lang="ts">
import { Button, ErrorMessage, Skeleton, Tooltip, dayjsLocal, useCall } from "frappe-ui"
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
import TransactionProperties from "@/components/dashboard/transactions/TransactionProperties.vue"
import TransactionRefundsSection from "@/components/dashboard/transactions/TransactionRefundsSection.vue"
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
	// download_invoice and download_tickets read the booking itself, which takes guests access.
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
const STATUS_DOTS: Record<string, string> = {
	green: "bg-surface-green-3",
	amber: "bg-surface-amber-3",
	red: "bg-surface-red-5",
	blue: "bg-surface-blue-3",
}

const money = useMoney()
const total = computed(() =>
	transaction.value
		? money(transaction.value.amounts.total_amount, transaction.value.currency)
		: "",
)
const bookedAt = computed(() =>
	transaction.value ? dayjsLocal(transaction.value.created_at).format("D MMM YYYY, h:mm A") : "",
)

const invoiceAvailable = computed(() => {
	const booking = transaction.value
	return Boolean(
		props.canDownloadInvoice &&
		booking?.buyer.invoice_requested &&
		booking.payment_status !== "Verification Pending",
	)
})
const invoiceUrl = computed(() =>
	invoiceAvailable.value && transaction.value
		? `/api/v2/method/buzz.api.booking.download_invoice?booking_id=${encodeURIComponent(transaction.value.name)}`
		: undefined,
)
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<div class="flex items-center gap-1 px-5 pt-4">
				<DrawerCloseButton label="Close transaction" />
				<DrawerTitle class="ml-1 text-lg font-semibold text-ink-gray-9"
					>Transaction details</DrawerTitle
				>
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

			<ErrorMessage
				v-if="detail.error && !detail.loading"
				class="mx-6 mt-5"
				:message="serverErrorMessage(detail.error)"
			/>

			<div v-else-if="!transaction || !status" class="space-y-3 px-6 pt-5">
				<Skeleton class="h-5 w-20 rounded-4" />
				<Skeleton class="h-9 w-44 rounded-4" />
				<Skeleton v-for="row in 4" :key="row" class="h-5 w-full rounded-4" />
			</div>

			<BookingActivity
				v-else
				:key="transaction.name"
				:transaction="transaction"
				:can-attach-invoice="invoiceAvailable"
			>
				<header class="space-y-2 pt-3">
					<p class="flex items-center gap-2 text-base text-ink-gray-7">
						<span
							class="size-2 rounded-full"
							:class="STATUS_DOTS[status.theme] ?? 'bg-surface-gray-4'"
							aria-hidden="true"
						/>
						{{ status.label }}
					</p>
					<p class="text-4xl font-semibold tabular-nums tracking-tight text-ink-gray-9">
						{{ total }}
					</p>
					<DrawerDescription class="flex items-center gap-1.5 text-base text-ink-gray-5">
						<button
							type="button"
							class="copy-id cursor-copy font-mono text-sm uppercase tracking-wider hover:text-ink-gray-7"
							:aria-label="`Copy booking ID ${transaction.name}`"
							@click="copyToClipboard(transaction.name, 'Booking ID copied')"
						>
							#{{ transaction.name }}
						</button>
						<span aria-hidden="true">·</span>
						<span class="tabular-nums">Booked {{ bookedAt }}</span>
					</DrawerDescription>
				</header>

				<TransactionProperties :transaction="transaction" :invoice-url="invoiceUrl" />
				<TransactionAmountsSection :transaction="transaction" />
				<TransactionTicketsSection
					v-if="transaction.tickets.length"
					:transaction="transaction"
					:event="event"
					:can-download-all="canDownloadInvoice"
				/>
				<TransactionRefundsSection v-if="transaction.refunds.length" :transaction="transaction" />
			</BookingActivity>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
.copy-id {
	transition:
		color 160ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

.copy-id:active {
	transform: scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
	.copy-id:active {
		transform: none;
	}
}
</style>
