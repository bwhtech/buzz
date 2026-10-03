<script setup lang="ts">
import { Badge } from "frappe-ui"

import ListSection from "@/components/common/ListSection.vue"
import PaymentGatewayLogo from "@/components/PaymentGatewayLogo.vue"
import type { PaymentProviderItem } from "@/types"

defineProps<{ providers: PaymentProviderItem[] }>()
</script>

<template>
	<ListSection
		title="Payment Providers"
		description="Attendees and sponsors pick one of these when they pay. New events start with the site default."
		:empty="!providers.length"
		empty-title="No payment providers"
		empty-description="Ask a site admin to set a default payment provider."
		empty-icon="lucide-credit-card"
	>
		<ul class="flex flex-wrap gap-2">
			<li
				v-for="provider in providers"
				:key="provider.name"
				class="flex h-10 items-center gap-2.5 rounded-full border border-outline-gray-2 bg-surface-base pl-4"
				:class="provider.is_default ? 'pr-3' : 'pr-4'"
			>
				<PaymentGatewayLogo :gateway="provider.name" class="h-[18px]">
					<span class="font-mono text-sm text-ink-gray-8">{{ provider.name }}</span>
				</PaymentGatewayLogo>
				<Badge v-if="provider.is_default" theme="green" size="sm" label="Default" />
			</li>
		</ul>
	</ListSection>
</template>
