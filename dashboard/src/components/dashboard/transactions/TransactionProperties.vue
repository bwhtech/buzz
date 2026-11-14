<script setup lang="ts">
import { Avatar, Button, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { TransactionAnswer, TransactionDetail } from "@/types"

const props = defineProps<{ transaction: TransactionDetail; invoiceUrl?: string }>()

type Row = {
	label: string
	icon: string
	value?: string | null
	hint?: string | null
	extra?: string | null
	copyable?: boolean
	gatewayUrl?: string
}

const copy = useCopyToClipboard()

const answerValue = (answer: TransactionAnswer) =>
	answer.value === null || answer.value === undefined || answer.value === ""
		? null
		: String(answer.value)

function paymentRows(): Row[] {
	const { payments, payment_method, offline_payment_method } = props.transaction
	if (!payments.length)
		return [
			{
				label: "Paid with",
				icon: "lucide-wallet",
				value: offline_payment_method || payment_method,
			},
		]
	return payments.flatMap((payment) => [
		{
			label: "Paid with",
			icon: "lucide-wallet",
			value: payment.payment_gateway,
			hint: payment_method !== payment.payment_gateway ? payment_method : null,
		},
		{
			label: "Payment ID",
			icon: "lucide-hash",
			value: payment.payment_id,
			copyable: true,
			// Opens only for someone signed in to the team's Razorpay dashboard.
			gatewayUrl:
				payment.payment_id && payment.payment_gateway?.includes("Razorpay")
					? `https://dashboard.razorpay.com/app/payments/${payment.payment_id}`
					: undefined,
		},
		{ label: "Order ID", icon: "lucide-receipt", value: payment.order_id, copyable: true },
	])
}

function billingRows(): Row[] {
	const { buyer } = props.transaction
	if (!buyer.business_name && !buyer.tax_id) return []
	const address = [buyer.billing_address, buyer.billing_state].filter(Boolean).join("\n")
	return [
		{
			label: "Billing",
			icon: "lucide-building-2",
			value: buyer.business_name,
			hint: buyer.tax_id,
			extra: address,
		},
	]
}

// The Talk drawer's property list: one block, no heading, empty rows left out.
const rows = computed<Row[]>(() => {
	const { buyer, utm, answers } = props.transaction
	return [
		...(buyer.user && buyer.user !== buyer.email
			? [{ label: "Booked by", icon: "lucide-key-round", value: buyer.user }]
			: []),
		{ label: "Phone", icon: "lucide-phone", value: buyer.phone },
		...paymentRows(),
		...billingRows(),
		...utm.map((row) => ({
			label: row.utm_name ?? "Source",
			icon: "lucide-megaphone",
			value: row.value,
		})),
		...answers.map((answer) => ({
			label: answer.label || answer.fieldname || "Answer",
			icon: "lucide-text",
			value: answerValue(answer),
		})),
	].filter((row) => row.value)
})
</script>

<template>
	<dl class="space-y-0.5">
		<div class="flex min-h-8 items-center gap-3 py-1">
			<dt class="flex w-32 shrink-0 items-center gap-2 text-base text-ink-gray-5">
				<span class="lucide-user size-4 shrink-0" aria-hidden="true" />Buyer
			</dt>
			<dd class="flex min-w-0 flex-1 items-center gap-2">
				<Avatar size="xs" :label="transaction.buyer.name || transaction.buyer.email || '?'" />
				<span class="min-w-0 shrink truncate text-base text-ink-gray-8">
					{{ transaction.buyer.name || "Unnamed buyer" }}
				</span>
				<span v-if="transaction.buyer.email" class="min-w-0 truncate text-sm text-ink-gray-5">
					{{ transaction.buyer.email }}
				</span>
			</dd>
		</div>

		<div
			v-for="(row, index) in rows"
			:key="`${row.label}-${index}`"
			class="row flex min-h-8 items-start gap-3 py-1"
		>
			<dt class="flex w-32 shrink-0 items-center gap-2 py-0.5 text-base text-ink-gray-5">
				<span :class="row.icon" class="size-4 shrink-0" aria-hidden="true" />
				<span class="truncate">{{ row.label }}</span>
			</dt>
			<dd class="flex min-w-0 flex-1 items-start gap-1">
				<div class="min-w-0 flex-1 py-0.5">
					<p
						class="truncate text-ink-gray-8"
						:class="row.copyable ? 'font-mono text-sm leading-6' : 'text-base'"
						:title="row.value ?? undefined"
					>
						{{ row.value }}
						<span v-if="row.hint" class="font-sans text-sm text-ink-gray-5">· {{ row.hint }}</span>
					</p>
					<p v-if="row.extra" class="whitespace-pre-line text-sm text-ink-gray-5">
						{{ row.extra }}
					</p>
				</div>
				<template v-if="row.copyable && row.value">
					<Tooltip text="Copy">
						<Button
							class="row-action"
							variant="ghost"
							size="sm"
							icon="lucide-copy"
							:aria-label="`Copy ${row.label.toLowerCase()}`"
							@click="copy(row.value, `${row.label} copied`)"
						/>
					</Tooltip>
					<Tooltip v-if="row.gatewayUrl" text="Open in Razorpay">
						<Button
							class="row-action"
							variant="ghost"
							size="sm"
							icon="lucide-arrow-up-right"
							aria-label="Open in Razorpay"
							:href="row.gatewayUrl"
							target="_blank"
						/>
					</Tooltip>
				</template>
			</dd>
		</div>

		<div v-if="transaction.buyer.invoice_requested" class="flex min-h-8 items-center gap-3 py-1">
			<dt class="flex w-32 shrink-0 items-center gap-2 text-base text-ink-gray-5">
				<span class="lucide-file-text size-4 shrink-0" aria-hidden="true" />Invoice
			</dt>
			<dd class="flex flex-1 items-center gap-2">
				<span class="text-base text-ink-gray-8">Requested</span>
				<Button
					v-if="invoiceUrl"
					variant="ghost"
					size="sm"
					icon-left="lucide-download"
					label="Download"
					:href="invoiceUrl"
				/>
			</dd>
		</div>
	</dl>
</template>

<style scoped>
@media (hover: hover) and (pointer: fine) {
	.row-action {
		opacity: 0;
		transition: opacity 120ms ease;
	}

	.row:hover .row-action,
	.row-action:focus-visible {
		opacity: 1;
	}
}
</style>
