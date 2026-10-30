<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import type { LogicRule } from "@/utils/formLogic"

import { setTicketTypes, ticketTypesOf } from "../logic/ticketTypeRule"

const props = defineProps<{
	rules: LogicRule[]
	fieldname: string
	ensureFieldname: () => string
	ticketTypes: { value: string; label: string }[]
}>()

const chosen = computed(() => ticketTypesOf(props.rules, props.fieldname))

function toggle(ticketType: string) {
	const next = chosen.value.includes(ticketType)
		? chosen.value.filter((value) => value !== ticketType)
		: [...chosen.value, ticketType]
	setTicketTypes(props.rules, props.ensureFieldname(), next)
}
</script>

<template>
	<div class="space-y-1.5">
		<span class="text-p-xs text-ink-gray-5">Ask for</span>
		<div class="flex flex-wrap gap-1.5">
			<Button
				size="sm"
				:variant="chosen.length ? 'subtle' : 'solid'"
				label="All tickets"
				@click="setTicketTypes(rules, fieldname, [])"
			/>
			<Button
				v-for="ticketType in ticketTypes"
				:key="ticketType.value"
				size="sm"
				:variant="chosen.includes(String(ticketType.value)) ? 'solid' : 'subtle'"
				:label="ticketType.label"
				@click="toggle(String(ticketType.value))"
			/>
		</div>
	</div>
</template>
