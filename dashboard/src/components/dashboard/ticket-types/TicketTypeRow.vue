<script setup lang="ts">
import PricedItemRow from "@/components/common/PricedItemRow.vue"
import type { TicketTypeItem } from "@/types"
import { salesLabel, seatsLabel, soldPercent, ticketTypeBadge } from "@/utils/ticketTypeLabels"

defineProps<{ ticketType: TicketTypeItem; subtitle?: string; disabled?: boolean }>()
</script>

<template>
	<PricedItemRow
		:title="ticketType.title"
		:subtitle="subtitle ?? salesLabel(ticketType)"
		:prices="ticketType.prices"
		:usage-label="seatsLabel(ticketType)"
		:usage-percent="soldPercent(ticketType)"
		:badge="ticketTypeBadge(ticketType)"
		:muted="!ticketType.is_published"
		:disabled="disabled"
	/>
</template>
