<script setup lang="ts">
import DetailRow from "@/components/common/DetailRow.vue"
import TransactionSection from "@/components/dashboard/transactions/TransactionSection.vue"
import type { TransactionBuyer } from "@/types"

defineProps<{ buyer: TransactionBuyer }>()
</script>

<template>
	<TransactionSection title="Buyer & billing">
		<dl class="space-y-3 text-base">
			<DetailRow label="Name" :value="buyer.name" />
			<DetailRow label="Email" :value="buyer.email" />
			<DetailRow label="Phone" :value="buyer.phone" />
			<DetailRow label="Account" :value="buyer.user" />
			<template v-if="buyer.invoice_requested || buyer.business_name || buyer.tax_id">
				<DetailRow label="Business" :value="buyer.business_name" />
				<DetailRow label="Tax ID" :value="buyer.tax_id" />
				<DetailRow label="State" :value="buyer.billing_state" />
				<DetailRow label="Address">
					<span v-if="buyer.billing_address" class="whitespace-pre-line">
						{{ buyer.billing_address }}
					</span>
					<span v-else class="text-ink-gray-5">—</span>
				</DetailRow>
				<DetailRow
					label="Invoice"
					:value="buyer.invoice_requested ? 'Requested' : 'Not requested'"
				/>
			</template>
		</dl>
	</TransactionSection>
</template>
