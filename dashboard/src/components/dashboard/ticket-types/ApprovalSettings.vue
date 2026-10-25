<script setup lang="ts">
import { Switch } from "frappe-ui"

import SectionHeader from "@/components/common/SectionHeader.vue"
import type { EventTicketTypes } from "@/types"

defineProps<{ page: EventTicketTypes; hasPricedTickets: boolean }>()
const emit = defineEmits<{ change: [enabled: boolean] }>()
</script>

<template>
	<section class="space-y-3">
		<SectionHeader title="Approval" />
		<Switch
			:model-value="page.requires_approval"
			padded
			label="Require approval for all tickets"
			:description="
				hasPricedTickets
					? 'Approval only works with free tickets.'
					: 'Guests send a request and you approve or decline it from the Guests page.'
			"
			:disabled="!page.can_write || (hasPricedTickets && !page.requires_approval)"
			@update:model-value="emit('change', $event)"
		/>
	</section>
</template>
