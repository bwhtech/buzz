<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { Button, Dialog, Icon, TabButtons, TextInput, dayjsLocal } from "frappe-ui"
import { computed, ref, watch } from "vue"

import GuestCheckInDialog from "@/components/checkin/GuestCheckInDialog.vue"
import EmptyState from "@/components/common/EmptyState.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import EventGuestSkeleton from "@/components/dashboard/events/EventGuestSkeleton.vue"
import QRScanner from "@/components/QRScanner.vue"
import { useEventGuests } from "@/composables/useEventGuests"
import type { ListOrder } from "@/composables/useListQuery"
import { type ValidationResult, useTicketValidation } from "@/composables/useTicketValidation"
import type { EventGuest } from "@/types"
import { formatPriceOrFree } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string }>()

const search = ref("")
// "1" and "0" narrow the list on the server; anything else is everyone.
const tab = ref("all")

const { guests, loadMore, page, loadingFirstPage, loadingMore } = useEventGuests(
	props.event,
	search,
	ref<ListOrder>("desc"),
	ref([]),
	{ url: "/api/v2/method/buzz.api.checkin.get_checkin_guests", checkedIn: tab },
)

// Check-ins made here since the last fetch. A fetch carries the server's own count, which
// already includes them, so the tally starts over with every response.
const localCheckIns = ref(0)
watch(
	() => page.data,
	() => (localCheckIns.value = 0),
)

const total = computed(() => page.data?.total ?? 0)
const checkedInCount = computed(() => (page.data?.checked_in ?? 0) + localCheckIns.value)

const tabs = computed(() => [
	{ label: "All", value: "all", count: total.value },
	{ label: "Checked in", value: "1", count: checkedInCount.value },
	{ label: "Not checked in", value: "0", count: total.value - checkedInCount.value },
])

const countOf = (value: string | number) =>
	tabs.value.find((option) => option.value === value)?.count

const startsAt = computed(() => {
	const data = page.data
	if (!data?.start_date) return ""
	const date = dayjsLocal(`${data.start_date}T${data.start_time || "00:00:00"}`)
	return date.format(data.start_time ? "D MMM, h:mm A" : "D MMM")
})

const selectedGuest = ref<EventGuest | null>(null)
const payment = ref<string | null>(null)
const guestOpen = ref(false)

const openGuest = (guest: EventGuest, paid: string | null = null) => {
	selectedGuest.value = guest
	payment.value = paid
	guestOpen.value = true
}

// Rows are patched in place rather than refetched, so the pages already scrolled through stay.
const markCheckedIn = (ticket: string, at: string) => {
	const row = guests.value.find((guest) => guest.name === ticket)
	if (row) row.checked_in_at = at
	localCheckIns.value += 1
}

const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})

// Scanning: a valid ticket swaps the camera for the guest, and closing the guest goes
// back to the camera, so a queue is worked without reaching for the Scan button each time.
const scanning = ref(false)
const resumeScan = ref(false)
const { validationResult } = useTicketValidation()

const guestFromScan = ({ ticket }: Required<Pick<ValidationResult, "ticket">>): EventGuest =>
	guests.value.find((guest) => guest.name === ticket.id) ?? {
		name: ticket.id,
		attendee_name: ticket.attendee_name,
		attendee_email: ticket.attendee_email,
		ticket_type: ticket.ticket_type,
		registered_at: null,
		add_ons: ticket.add_ons.map((addOn) => ({
			title: addOn.add_on_title || addOn.add_on,
			value: addOn.value ?? null,
		})),
	}

watch(validationResult, (result) => {
	if (!result?.ticket) return
	const paid = result.payment_details
	scanning.value = false
	resumeScan.value = true
	openGuest(
		guestFromScan({ ticket: result.ticket }),
		paid ? formatPriceOrFree(paid.amount, paid.currency) : null,
	)
	validationResult.value = null
})

watch(guestOpen, (open) => {
	if (open || !resumeScan.value) return
	resumeScan.value = false
	scanning.value = true
})
</script>

<template>
	<div class="mx-auto w-full max-w-3xl space-y-4 p-4 max-md:pb-24">
		<EmptyState
			v-if="page.error"
			title="Access denied"
			:description="serverErrorMessage(page.error)"
			icon="lucide-shield-x"
		/>

		<template v-else>
			<header class="flex items-start justify-between gap-4">
				<div class="min-w-0">
					<h1 class="truncate text-xl font-semibold text-ink-gray-9">
						{{ page.data?.title || "Check in" }}
					</h1>
					<p class="truncate text-base text-ink-gray-5">
						{{ [startsAt, page.data?.venue].filter(Boolean).join(" · ") }}
					</p>
				</div>
				<Button size="md" icon-left="lucide-scan-line" label="Scan" @click="scanning = true" />
			</header>

			<TextInput
				v-model="search"
				type="search"
				size="md"
				placeholder="Search for a guest…"
				aria-label="Search for a guest"
			>
				<template #prefix>
					<Icon name="lucide-search" class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>

			<TabButtons v-model="tab" variant="underline" :options="tabs">
				<template #suffix="{ button }">
					<span class="tabular-nums text-ink-gray-5">{{ countOf(button.value) }}</span>
				</template>
			</TabButtons>

			<ul
				v-if="loadingFirstPage"
				class="divide-y divide-outline-gray-1 overflow-hidden rounded-7 border border-outline-gray-2"
			>
				<EventGuestSkeleton :rows="6" />
			</ul>

			<ul
				v-else-if="guests.length"
				class="divide-y divide-outline-gray-1 overflow-hidden rounded-7 border border-outline-gray-2"
			>
				<EventGuestItem
					v-for="guest in guests"
					:key="guest.name"
					:guest="guest"
					:selected="guestOpen && guest.name === selectedGuest?.name"
					@open="openGuest(guest)"
				/>
				<EventGuestSkeleton v-if="loadingMore" :rows="3" />
			</ul>

			<EmptyState
				v-else-if="search.trim()"
				title="No matching guests"
				:description="`Nobody here matches “${search.trim()}”.`"
				icon="lucide-search-x"
			/>
			<EmptyState
				v-else
				:title="tab === '1' ? 'Nobody has checked in yet' : 'No guests here'"
				icon="lucide-users"
			/>

			<div ref="sentinel" aria-hidden="true" />
		</template>

		<Dialog v-model:open="scanning" title="Scan ticket" size="md">
			<QRScanner />
		</Dialog>

		<GuestCheckInDialog
			v-model:open="guestOpen"
			:guest="selectedGuest"
			:payment="payment"
			@checked-in="markCheckedIn"
		/>
	</div>
</template>
