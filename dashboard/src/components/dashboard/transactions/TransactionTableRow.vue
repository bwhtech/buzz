<script setup lang="ts">
import { Button, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useMoney } from "@/composables/useMoney"
import type { TransactionRow } from "@/types"
import { badgeDotClass } from "@/utils/badgeTheme"
import { transactionStatus, truncateMiddle } from "@/utils/transactionStatus"

const props = defineProps<{ transaction: TransactionRow; selected?: boolean }>()

const emit = defineEmits<{ open: [] }>()

const copyToClipboard = useCopyToClipboard()

const money = useMoney()

const createdAt = computed(() => dayjsLocal(props.transaction.created_at))
// A server clock a little ahead would otherwise read "in 2 minutes".
const createdAgo = computed(() =>
	createdAt.value.isAfter(dayjsLocal()) ? "just now" : createdAt.value.fromNow(),
)
// "Oct 23, 2:00am"; a booking from another year says which.
const createdOn = computed(() =>
	createdAt.value.format(
		createdAt.value.isSame(dayjsLocal(), "year") ? "MMM D, h:mma" : "MMM D YYYY, h:mma",
	),
)
const buyerName = computed(() => props.transaction.buyer_name || "Unnamed buyer")
const status = computed(() => transactionStatus(props.transaction))
</script>

<template>
	<tr
		class="group h-10 cursor-pointer text-base transition-colors duration-150 ease-out motion-reduce:transition-none"
		:class="selected ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
		:data-selected="selected"
		@click="emit('open')"
	>
		<td class="whitespace-nowrap px-3 font-mono text-sm text-ink-gray-7">
			{{ transaction.name }}
		</td>
		<td class="whitespace-nowrap px-3 text-right tabular-nums text-ink-gray-9">
			{{ money(transaction.total_amount, transaction.currency) }}
		</td>
		<td class="whitespace-nowrap px-3">
			<span class="flex max-w-48 items-center gap-2 text-ink-gray-7" :title="status.label">
				<span
					class="size-1.5 shrink-0 rounded-full"
					:class="badgeDotClass(status.theme)"
					aria-hidden="true"
				/>
				<span class="min-w-0 truncate">{{ status.label }}</span>
			</span>
		</td>
		<td class="min-w-48 max-w-64 px-3 py-2">
			<button
				type="button"
				class="block max-w-full rounded-1 text-left leading-snug [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
				:aria-label="`${buyerName}, booking ${transaction.name}`"
				@click.stop="emit('open')"
			>
				<span dir="auto" class="line-clamp-2 text-ink-gray-9" :title="buyerName">
					{{ buyerName }}
				</span>
				<span
					class="line-clamp-2 text-sm"
					:class="transaction.buyer_email ? 'text-ink-gray-5' : 'text-ink-gray-4'"
					:title="transaction.buyer_email ?? undefined"
				>
					{{ transaction.buyer_email || "No email" }}
				</span>
			</button>
		</td>
		<td class="whitespace-nowrap px-3">
			<div class="flex items-center gap-1">
				<span
					v-if="transaction.payment_id"
					class="font-mono text-sm text-ink-gray-7"
					:title="transaction.payment_id"
				>
					{{ truncateMiddle(transaction.payment_id) }}
				</span>
				<span v-else class="text-ink-gray-4">—</span>
				<Button
					v-if="transaction.payment_id"
					variant="ghost"
					size="sm"
					icon="lucide-copy"
					class="opacity-0 focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
					aria-label="Copy payment ID"
					@click.stop="copyToClipboard(transaction.payment_id, 'Payment ID copied')"
				/>
			</div>
			<span
				v-if="transaction.payment_method"
				class="block max-w-48 truncate text-sm text-ink-gray-5"
				:title="transaction.payment_method"
			>
				{{ transaction.payment_method }}
			</span>
		</td>
		<td class="whitespace-nowrap px-3 tabular-nums text-ink-gray-7">
			<Tooltip :text="createdAgo">
				<time :datetime="transaction.created_at">{{ createdOn }}</time>
			</Tooltip>
		</td>
	</tr>
</template>
