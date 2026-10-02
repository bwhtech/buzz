<script setup lang="ts">
import { Button, DatePicker, FormControl, Switch } from "frappe-ui"
import { computed, ref } from "vue"

import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import type { TicketTypeDraft } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

const ticketType = defineModel<TicketTypeDraft>("ticketType", { required: true })
defineProps<{ open: boolean; canWrite: boolean }>()
const emit = defineEmits<{ toggle: []; remove: [] }>()

const showMoreOptions = ref(false)

const isSold = computed(() => ticketType.value.tickets_sold > 0)
const seats = computed(() => ticketType.value.max_tickets_available)

const priceLabel = computed(() =>
	ticketType.value.prices.map((row) => formatWholePriceOrFree(row.price, row.currency)).join(" · "),
)

const soldCurrencies = computed(() =>
	ticketType.value.prices.filter((row) => row.tickets_sold).map((row) => row.currency),
)

const soldLabel = computed(() =>
	seats.value
		? `${ticketType.value.tickets_sold} of ${seats.value} sold`
		: `${ticketType.value.tickets_sold} sold`,
)

const soldPercent = computed(() =>
	seats.value ? Math.min(100, (ticketType.value.tickets_sold / seats.value) * 100) : 0,
)

function update<Field extends keyof TicketTypeDraft>(field: Field, value: TicketTypeDraft[Field]) {
	ticketType.value = { ...ticketType.value, [field]: value }
}

function updateSeats(value: string | number) {
	update("max_tickets_available", Math.max(0, Math.floor(Number(value) || 0)))
}
</script>

<template>
	<div
		class="rounded-4 border transition-colors"
		:class="open ? 'border-outline-gray-2 bg-surface-white' : 'border-transparent'"
	>
		<button
			type="button"
			class="flex w-full items-center gap-4 rounded-4 px-4 py-3 text-left hover:bg-surface-gray-1"
			:aria-expanded="open"
			@click="emit('toggle')"
		>
			<div class="min-w-0 flex-1">
				<p class="truncate text-base font-medium text-ink-gray-9">
					{{ ticketType.title.trim() || "Untitled ticket" }}
				</p>
				<p class="mt-1 flex items-center gap-2 text-p-sm text-ink-gray-7">
					{{ priceLabel }}
					<span v-if="!ticketType.is_published" class="text-ink-gray-5">Hidden</span>
				</p>
			</div>
			<div class="w-36 shrink-0">
				<div v-if="seats" class="h-1 rounded-full bg-surface-gray-2">
					<div class="h-1 rounded-full bg-surface-gray-7" :style="{ width: `${soldPercent}%` }" />
				</div>
				<p class="mt-1.5 text-p-sm text-ink-gray-5">{{ soldLabel }}</p>
			</div>
			<span
				class="size-4 shrink-0 text-ink-gray-5"
				:class="open ? 'lucide-chevron-up' : 'lucide-chevron-down'"
				aria-hidden="true"
			/>
		</button>

		<div v-if="open" class="space-y-4 px-4 pb-4 pt-1">
			<div class="grid gap-3 sm:grid-cols-[1fr_7rem]">
				<FormControl
					label="Name"
					required
					placeholder="General admission"
					:model-value="ticketType.title"
					:disabled="!canWrite"
					@update:model-value="update('title', $event)"
				/>
				<FormControl
					type="number"
					label="Seats"
					placeholder="Unlimited"
					min="0"
					:model-value="seats || ''"
					:disabled="!canWrite"
					@update:model-value="updateSeats"
				/>
			</div>

			<div class="space-y-1.5">
				<PriceList
					:model-value="ticketType.prices"
					:locked-currencies="soldCurrencies"
					:disabled="!canWrite"
					@update:model-value="update('prices', $event)"
				/>
				<p v-if="soldCurrencies.length" class="text-p-xs text-ink-gray-5">
					A price is locked once tickets sell in its currency.
				</p>
			</div>

			<div>
				<Button
					variant="ghost"
					:icon-left="showMoreOptions ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					label="More options"
					@click="showMoreOptions = !showMoreOptions"
				/>
				<div v-if="showMoreOptions" class="mt-3 grid gap-4 sm:grid-cols-2">
					<DatePicker
						label="Stop selling on"
						description="Leave empty to sell until the event starts."
						placeholder="Select date"
						clearable
						:model-value="ticketType.auto_unpublish_after ?? ''"
						:disabled="!canWrite"
						@update:model-value="update('auto_unpublish_after', $event || null)"
					/>
					<Switch
						label="Show on booking page"
						description="Hidden ticket types can't be booked."
						:model-value="ticketType.is_published"
						:disabled="!canWrite"
						@update:model-value="update('is_published', $event)"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between gap-3 border-t border-outline-gray-1 pt-3">
				<p v-if="isSold" class="text-p-sm text-ink-gray-5">
					Tickets are sold, so this can't be deleted.
				</p>
				<Button
					v-else-if="canWrite"
					variant="ghost"
					theme="red"
					label="Delete ticket type"
					@click="emit('remove')"
				/>
				<span v-else />
				<Button label="Done" @click="emit('toggle')" />
			</div>
		</div>
	</div>
</template>
