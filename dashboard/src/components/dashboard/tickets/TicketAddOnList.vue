<script setup lang="ts">
import { Badge } from "frappe-ui"

import type { TicketAddOnDetail } from "@/types"

defineProps<{ addOns: TicketAddOnDetail[] }>()
</script>

<template>
	<div v-if="addOns.length" class="flex flex-col gap-2 px-4 pb-4">
		<h3 class="text-p-xs uppercase tracking-wide text-ink-gray-5">Add-ons</h3>
		<div class="flex flex-wrap gap-2">
			<Badge v-for="addOn in addOns" :key="addOn.id" variant="subtle" size="lg">
				{{ addOn.title }}
				<!-- Only a selectable add-on carries a chosen value worth stating. -->
				<span v-if="addOn.value" class="text-ink-gray-5">&nbsp;× {{ addOn.value }}</span>
			</Badge>
		</div>
	</div>
</template>
