<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { Button, Dialog, Icon, TabButtons, TextInput, dayjsLocal, toast, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import CheckInGuestRow from "@/components/checkin/CheckInGuestRow.vue"
import GuestCheckInDialog from "@/components/checkin/GuestCheckInDialog.vue"
import EmptyState from "@/components/common/EmptyState.vue"
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
	return date.format(data.start_time ? "ddd D MMM, h:mm A" : "ddd D MMM")
})

const selectedGuest = ref<EventGuest | null>(null)
const payment = ref<string | null>(null)
const guestOpen = ref(false)

const openGuest = (guest: EventGuest, paid: string | null = null) => {
	checkInCall.reset()
	undoCall.reset()
	selectedGuest.value = guest
	payment.value = paid
	guestOpen.value = true
}

// Rows are patched in place rather than refetched, so the pages already scrolled through stay.
const setCheckedIn = (ticket: string, at: string | null) => {
	for (const guest of [guests.value.find((row) => row.name === ticket), selectedGuest.value])
		if (guest?.name === ticket) guest.checked_in_at = at
	localCheckIns.value += at ? 1 : -1
}

interface CheckInResponse {
	message: string
	ticket: { id: string; check_in_time: string }
}

// One check-in at a time: the row or dialog that started it shows the spinner.
const busyTicket = ref<string | null>(null)

const checkInCall = useCall<CheckInResponse, { ticket_id: string }>({
	url: "/api/v2/method/buzz.api.checkin.checkin_ticket",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		busyTicket.value = null
		setCheckedIn(data.ticket.id, data.ticket.check_in_time)
		toast.success(data.message)
		// Long enough to see the button turn into "Checked in", then out of the way.
		if (guestOpen.value) setTimeout(() => (guestOpen.value = false), 600)
	},
	onError: (error) => {
		busyTicket.value = null
		// An open dialog shows the error itself; a row has nowhere else to say it.
		if (!guestOpen.value) toast.error(serverErrorMessage(error) || "Check-in failed")
	},
})

const checkIn = (ticket: string) => {
	if (busyTicket.value) return
	busyTicket.value = ticket
	checkInCall.submit({ ticket_id: ticket })
}

// Undo lives only in the guest dialog, so its errors show there too.
const undoCall = useCall<CheckInResponse, { ticket_id: string }>({
	url: "/api/v2/method/buzz.api.checkin.undo_checkin",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		busyTicket.value = null
		setCheckedIn(data.ticket.id, null)
		toast.success(data.message)
	},
	onError: () => (busyTicket.value = null),
})

const undoCheckIn = (ticket: string) => {
	if (busyTicket.value) return
	busyTicket.value = ticket
	undoCall.submit({ ticket_id: ticket })
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
	<div class="space-y-5 pb-24">
		<EmptyState
			v-if="page.error"
			title="Access denied"
			:description="serverErrorMessage(page.error)"
			icon="lucide-shield-x"
		/>

		<template v-else>
			<!-- The event is what the desk has to be sure of, so it carries the display type. -->
			<header class="flex items-end justify-between gap-4">
				<div class="min-w-0 space-y-2">
					<p class="text-sm font-medium uppercase tracking-wider text-ink-gray-5">Check-in</p>
					<h1
						v-if="page.data"
						class="line-clamp-2 font-display text-[2.75rem] uppercase leading-[0.95] text-ink-gray-9 md:text-[3.5rem]"
					>
						{{ page.data.title }}
					</h1>
					<div v-else class="h-12 w-64 max-w-full animate-pulse rounded-4 bg-surface-gray-2" />
					<p class="truncate text-base text-ink-gray-5">
						{{ [startsAt, page.data?.venue].filter(Boolean).join(" · ") }}
					</p>
				</div>
				<Button
					size="lg"
					icon-left="lucide-scan-line"
					label="Scan"
					class="shrink-0 transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
					@click="scanning = true"
				/>
			</header>

			<TextInput
				v-model="search"
				type="search"
				size="md"
				placeholder="Search by name or email"
				aria-label="Search guests"
			>
				<template #prefix>
					<Icon name="lucide-search" class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>

			<TabButtons v-model="tab" :options="tabs">
				<template #suffix="{ button }">
					<span class="tabular-nums text-ink-gray-5">{{ countOf(button.value) }}</span>
				</template>
			</TabButtons>

			<p class="text-p-sm text-ink-gray-5">
				Tap <span class="font-medium text-ink-gray-7">Check in</span> as a guest arrives, or tap
				their name to see their ticket. <span class="font-medium text-ink-gray-7">Scan</span>
				reads the QR code on a ticket.
			</p>

			<ul v-if="loadingFirstPage" class="flex flex-col gap-2" aria-busy="true">
				<li
					v-for="row in 6"
					:key="row"
					class="h-[62px] animate-pulse rounded-[14px] bg-surface-gray-1"
				/>
			</ul>

			<ul v-else-if="guests.length" class="flex flex-col gap-2">
				<CheckInGuestRow
					v-for="guest in guests"
					:key="guest.name"
					:guest="guest"
					:busy="busyTicket === guest.name && !guestOpen"
					@open="openGuest(guest)"
					@check-in="checkIn(guest.name)"
				/>
				<li v-if="loadingMore" class="h-[62px] animate-pulse rounded-[14px] bg-surface-gray-1" />
			</ul>

			<EmptyState
				v-else-if="search.trim()"
				title="No matching guests"
				:description="`Nobody here matches “${search.trim()}”.`"
				icon="lucide-search-x"
			/>
			<EmptyState
				v-else
				:title="
					tab === '1'
						? 'Nobody has checked in yet'
						: tab === '0'
							? 'Everyone is in'
							: 'No guests yet'
				"
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
			:busy="busyTicket === selectedGuest?.name"
			:error="serverErrorMessage(checkInCall.error || undoCall.error)"
			@check-in="selectedGuest && checkIn(selectedGuest.name)"
			@undo="selectedGuest && undoCheckIn(selectedGuest.name)"
		/>
	</div>
</template>
