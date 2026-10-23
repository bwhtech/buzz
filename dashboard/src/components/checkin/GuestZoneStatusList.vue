<script setup lang="ts">
import { Button, dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import type { ZoneStatus } from "@/types"

const props = defineProps<{
	zones: ZoneStatus[]
	// The zone being checked into; empty lists every zone with its own action.
	zone: string
	busy?: boolean
}>()

const emit = defineEmits<{ checkIn: [zone: string]; undo: [zone: string] }>()

const pendingZone = ref("")

const act = (action: "checkIn" | "undo", zone: string) => {
	pendingZone.value = zone
	if (action === "undo") emit("undo", zone)
	else emit("checkIn", zone)
}

const time = (at: string) => dayjsLocal(at).format("h:mm A")

const rows = computed(() =>
	props.zone
		? props.zones.filter((row) => row.name !== props.zone && row.checked_in_at)
		: props.zones,
)
</script>

<template>
	<ul v-if="rows.length" class="flex flex-col gap-2">
		<li
			v-for="row in rows"
			:key="row.name"
			class="flex min-h-10 items-center justify-between gap-3 rounded-5 border border-outline-gray-2 px-3 py-1.5"
		>
			<span class="min-w-0 truncate text-base text-ink-gray-8">{{ row.title }}</span>
			<template v-if="zone">
				<span class="text-sm text-ink-green-7">Checked in {{ time(row.checked_in_at!) }}</span>
			</template>
			<span v-else-if="!row.allowed" class="text-sm text-ink-gray-4">Not allowed</span>
			<div v-else-if="row.checked_in_at" class="flex items-center gap-2">
				<span class="text-sm text-ink-green-7">Checked in {{ time(row.checked_in_at) }}</span>
				<Button
					variant="ghost"
					icon="lucide-undo-2"
					aria-label="Undo check-in"
					:loading="busy && pendingZone === row.name"
					:disabled="busy"
					@click="act('undo', row.name)"
				/>
			</div>
			<Button
				v-else
				variant="solid"
				theme="green"
				label="Check in"
				:loading="busy && pendingZone === row.name"
				:disabled="busy"
				@click="act('checkIn', row.name)"
			/>
		</li>
	</ul>
</template>
