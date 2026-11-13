<script setup lang="ts">
import { Button } from "frappe-ui"

import ListSection from "@/components/common/ListSection.vue"
import PricedItemRow from "@/components/common/PricedItemRow.vue"
import type { AddOnItem, EventTicketTypes } from "@/types"
import { pluralize } from "@/utils/pluralize"

const props = defineProps<{ page: EventTicketTypes }>()
defineEmits<{ open: [name: string]; add: [] }>()

function scopeLabel(addOn: AddOnItem) {
	if (!addOn.ticket_types.length) return "All ticket types"
	return props.page.ticket_types
		.filter((ticketType) => addOn.ticket_types.includes(ticketType.name))
		.map((ticketType) => ticketType.title)
		.join(", ")
}

const optionsLabel = (addOn: AddOnItem) =>
	addOn.user_selects_option ? pluralize(addOn.options.length, "option") : ""
</script>

<template>
	<ListSection
		title="Add-ons"
		description="Extras a participant can pick with their ticket"
		:count="page.add_ons.length"
		:empty="!page.add_ons.length"
		empty-title="No add-ons yet"
		empty-description="Offer extras like lunch, merchandise or a workshop seat."
		empty-icon="lucide-package-plus"
		:empty-action="
			page.can_write
				? { label: 'Add add-on', iconLeft: 'lucide-plus', onClick: () => $emit('add') }
				: null
		"
	>
		<ul class="space-y-2">
			<li v-for="addOn in page.add_ons" :key="addOn.name">
				<PricedItemRow
					:title="addOn.title"
					:subtitle="scopeLabel(addOn)"
					:prices="[{ price: addOn.price, currency: addOn.currency }]"
					:usage-label="optionsLabel(addOn)"
					:badge="addOn.enabled ? null : { label: 'Disabled', theme: 'gray' }"
					:muted="!addOn.enabled"
					:disabled="!page.can_write"
					@click="$emit('open', addOn.name)"
				/>
			</li>
			<li v-if="page.can_write">
				<Button variant="ghost" icon-left="lucide-plus" label="Add add-on" @click="$emit('add')" />
			</li>
		</ul>
	</ListSection>
</template>
