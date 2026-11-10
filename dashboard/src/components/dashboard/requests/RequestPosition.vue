<script setup lang="ts">
import { dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { RegistrationRequest } from "@/types"
import { pluralize } from "@/utils/pluralize"

const props = defineProps<{
	request: RegistrationRequest
	statusLabel: string
	waiting: boolean
	ticketType: string
	seatsFree: number
}>()

const joined = computed(() => `joined ${dayjsLocal(props.request.requested_at).fromNow()}`)
const seats = computed(() =>
	props.seatsFree ? `${pluralize(props.seatsFree, "seat")} free right now` : "No seats free yet",
)
</script>

<template>
	<div class="flex items-center gap-4 rounded-6 border border-outline-gray-2 p-4">
		<span
			class="min-w-12 text-4xl font-semibold tabular-nums"
			:class="waiting && request.position ? 'text-ink-gray-9' : 'text-ink-gray-4'"
		>
			{{ waiting && request.position ? `#${request.position}` : "—" }}
		</span>
		<div class="min-w-0 space-y-0.5">
			<p class="text-base font-medium text-ink-gray-9">
				{{ waiting ? `in line for ${ticketType}` : statusLabel }}
			</p>
			<p class="text-sm text-ink-gray-5">{{ waiting ? `${seats} · ${joined}` : joined }}</p>
		</div>
	</div>
</template>
