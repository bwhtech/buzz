<script setup lang="ts">
import { Button, Spinner } from "frappe-ui"
import { Accordion } from "frappe-ui/experimental"
import { computed, ref, toRef, watch } from "vue"

import BookingSummary from "@/components/dashboard/events/BookingSummary.vue"
import { useMyBookingSummaries } from "@/data/bookings"

const props = defineProps<{ event: string }>()

const event = toRef(props, "event")
const summaries = useMyBookingSummaries(() => event.value)

const bookings = computed(() => summaries.data ?? [])

const selected = ref<string | null>(null)

// The first booking is shown by default, and a booking that disappears cannot stay selected.
watch(
	bookings,
	(list) => {
		const names = list.map((booking) => booking.name)
		if (!selected.value || !names.includes(selected.value)) selected.value = names[0] ?? null
	},
	{ immediate: true },
)

const booking = computed(() => bookings.value.find((row) => row.name === selected.value) ?? null)

const accordionItems = [{ value: "booking", title: "Booking Details" }]
</script>

<template>
	<div class="px-4 pb-4">
		<Accordion :items="accordionItems">
			<template #item-content>
				<Spinner v-if="summaries.loading" class="size-4" />

				<p v-else-if="!booking" class="text-p-base text-ink-gray-5">
					No booking of yours for this event.
				</p>

				<div v-else class="flex flex-col gap-5">
					<!-- One chip per booking; a person can book the same event more than once. -->
					<div v-if="bookings.length > 1" class="flex flex-wrap gap-2">
						<Button
							v-for="row in bookings"
							:key="row.name"
							size="sm"
							:variant="row.name === selected ? 'solid' : 'subtle'"
							@click="selected = row.name"
						>
							<span class="font-mono">#{{ row.name }}</span>
						</Button>
					</div>

					<BookingSummary :booking="booking" :show-id="bookings.length < 2" />
				</div>
			</template>
		</Accordion>
	</div>
</template>
