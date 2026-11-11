<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import type { RegistrationRequest } from "@/types"

const props = defineProps<{ freed: { ticketType: string; people: RegistrationRequest[] }[] }>()
const emit = defineEmits<{ letIn: [people: RegistrationRequest[]] }>()

const people = computed(() => props.freed.flatMap((entry) => entry.people))
const breakdown = computed(() =>
	props.freed.map((entry) => `${entry.people.length} on ${entry.ticketType}`).join(" · "),
)
</script>

<template>
	<div
		v-if="people.length"
		class="flex items-center gap-3.5 rounded-6 bg-surface-gray-2 px-4 py-3.5"
	>
		<span
			class="grid size-8 shrink-0 place-items-center rounded-4 bg-surface-base text-ink-gray-7 shadow-sm"
			aria-hidden="true"
		>
			<span class="lucide-armchair size-4" />
		</span>
		<div class="min-w-0 flex-1 space-y-0.5">
			<p class="text-base font-medium text-ink-gray-9">
				{{ people.length }} {{ people.length === 1 ? "seat has" : "seats have" }} freed up
			</p>
			<p class="text-sm text-ink-gray-5">{{ breakdown }}</p>
		</div>
		<Button variant="solid" :label="`Let in ${people.length}`" @click="emit('letIn', people)" />
	</div>
</template>
