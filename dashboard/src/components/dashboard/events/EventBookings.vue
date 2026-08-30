<script setup lang="ts">
import { Badge, Button, Spinner, dayjs } from "frappe-ui"
import { Accordion } from "frappe-ui/experimental"
import { computed, ref, toRef, watch } from "vue"

import { useMyBookingSummaries } from "@/data/bookings"
import { session } from "@/data/session"
import { formatCurrency } from "@/utils/currency"

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

const money = (amount: number) => formatCurrency(amount, booking.value?.currency)

const isPaid = computed(() => booking.value?.payment_status === "Paid")

const statusTheme = computed(() => {
	if (isPaid.value) return "green"
	return booking.value?.status === "Rejected" ? "red" : "amber"
})

/** Only the lines this booking has — a free booking states no tax or discount. */
const totalLines = computed(() => {
	const row = booking.value
	if (!row) return []
	const lines = [{ label: "Subtotal", value: money(row.net_amount), strong: false }]
	if (row.discount_amount)
		lines.push({
			label: row.coupon_code ? `Discount · ${row.coupon_code}` : "Discount",
			value: `− ${money(row.discount_amount)}`,
			strong: false,
		})
	if (row.tax_amount)
		lines.push({
			label: row.tax_percentage
				? `${row.tax_label || "Tax"} (${row.tax_percentage}%)`
				: row.tax_label || "Tax",
			value: money(row.tax_amount),
			strong: false,
		})
	lines.push({
		label: "Total",
		value: row.total_amount ? money(row.total_amount) : "Free",
		strong: true,
	})
	return lines
})

const bookedOn = computed(() =>
	booking.value ? dayjs(booking.value.booked_on).format("D MMM, HH:mm") : "",
)

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

					<div class="flex flex-col gap-5 rounded-lg bg-surface-gray-1 p-4">
						<div>
							<p class="text-p-xs uppercase tracking-wide text-ink-gray-5">
								{{ isPaid ? "Amount paid" : "Amount due" }}
							</p>
							<div class="mt-1 flex items-center justify-between gap-3">
								<span class="font-mono text-3xl font-semibold tabular-nums text-ink-gray-9">
									{{ booking.total_amount ? money(booking.total_amount) : "Free" }}
								</span>
								<Badge :theme="statusTheme" variant="subtle" size="lg">
									<template v-if="isPaid" #prefix>
										<span class="lucide-check size-3" aria-hidden="true" />
									</template>
									{{ isPaid ? "Paid" : booking.payment_status }}
								</Badge>
							</div>
						</div>

						<div
							v-if="booking.payment_method"
							class="flex items-center gap-3 rounded-lg border border-dashed border-outline-gray-2 px-3 py-2 text-p-base text-ink-gray-7"
						>
							<span class="lucide-circle-dollar-sign size-5 shrink-0" aria-hidden="true" />
							<span>
								{{ booking.payment_method }}
								<template v-if="booking.is_offline"> · collected offline</template>
							</span>
						</div>

						<div>
							<p class="text-p-xs uppercase tracking-wide text-ink-gray-5">Breakdown</p>
							<ul
								class="mt-2 flex flex-col divide-y divide-outline-gray-1 border-t border-outline-gray-1"
							>
								<li v-for="(line, index) in booking.lines" :key="index" class="py-2">
									<div class="flex items-baseline justify-between gap-3">
										<p class="min-w-0 truncate text-p-base text-ink-gray-8">
											{{ line.label }}
											<span class="text-ink-gray-5">× {{ line.quantity }}</span>
										</p>
										<span class="shrink-0 font-mono text-p-base tabular-nums text-ink-gray-8">
											{{ money(line.amount) }}
										</span>
									</div>
									<div
										v-for="(addOn, addOnIndex) in line.add_ons"
										:key="addOnIndex"
										class="flex items-baseline justify-between gap-3 pl-4 text-ink-gray-6"
									>
										<p class="min-w-0 truncate text-p-sm">
											↳ {{ addOn.label }}
											<span class="text-ink-gray-5">× {{ addOn.quantity }}</span>
										</p>
										<span class="shrink-0 font-mono text-p-sm tabular-nums">{{
											money(addOn.amount)
										}}</span>
									</div>
								</li>
							</ul>
						</div>

						<dl class="flex flex-col gap-1 border-t border-outline-gray-1 pt-3">
							<div v-for="line in totalLines" :key="line.label" class="flex justify-between gap-3">
								<dt
									:class="
										line.strong ? 'text-p-base text-ink-gray-8' : 'text-p-base text-ink-gray-5'
									"
								>
									{{ line.label }}
								</dt>
								<dd
									class="font-mono tabular-nums"
									:class="
										line.strong
											? 'text-p-base font-medium text-ink-gray-9'
											: 'text-p-base text-ink-gray-7'
									"
								>
									{{ line.value }}
								</dd>
							</div>
						</dl>
					</div>

					<div class="flex items-center gap-2">
						<span
							class="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-p-sm uppercase text-ink-gray-7"
						>
							{{ session.user?.slice(0, 1) }}
						</span>
						<div class="min-w-0">
							<p class="truncate text-p-base text-ink-gray-8">{{ session.user }}</p>
							<p class="text-p-sm text-ink-gray-5">Booked this on {{ bookedOn }}</p>
						</div>
					</div>
				</div>
			</template>
		</Accordion>
	</div>
</template>
