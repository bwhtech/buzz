<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import {
	Button,
	Icon,
	LoadingText,
	TabButtons,
	TextInput,
	dayjsLocal,
	toast,
	useCall,
} from "frappe-ui"
import { computed, ref, watch } from "vue"

import CheckInGuestRow from "@/components/checkin/CheckInGuestRow.vue"
import CheckInZoneSelect from "@/components/checkin/CheckInZoneSelect.vue"
import GuestCheckInDialog from "@/components/checkin/GuestCheckInDialog.vue"
import EmptyState from "@/components/common/EmptyState.vue"
import QRScanner from "@/components/QRScanner.vue"
import { useCheckInZone } from "@/composables/useCheckInZone"
import { useEventGuests } from "@/composables/useEventGuests"
import { useIsMobile } from "@/composables/useIsMobile"
import type { ListOrder } from "@/composables/useListQuery"
import {
	type ValidationResult,
	playSuccessBeep,
	useTicketValidation,
} from "@/composables/useTicketValidation"
import type { EventGuest, GuestZone, ZoneStatus } from "@/types"
import { formatPriceOrFree } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string }>()

const search = ref("")
// "1" and "0" narrow the list on the server; anything else is everyone.
const tab = ref("all")

// The zone drives the list itself, and the zones come back with the list.
const zones = ref<GuestZone[]>([])
const { selected: selectedZone, zone, defaultZone } = useCheckInZone(props.event, zones)

const { guests, loadMore, page, loadingFirstPage, loadingMore, searchPending } = useEventGuests(
	props.event,
	search,
	ref<ListOrder>("desc"),
	ref([]),
	{ url: "/api/v2/method/buzz.api.checkin.get_checkin_guests", checkedIn: tab, zone },
)
// Where the open guest stands at each zone; the row carries it, a check-in refreshes it.
const zoneStatuses = ref<ZoneStatus[]>([])

// Check-ins made here since the last fetch. A fetch carries the server's own count, which
// already includes them, so the tally starts over with every response.
const localCheckIns = ref(0)
// The search the shown rows belong to.
const loadedSearch = ref("")
watch(
	() => page.data,
	(data) => {
		if (data?.zones) zones.value = data.zones
		localCheckIns.value = 0
		loadedSearch.value = search.value.trim()
	},
)

const initialLoading = computed(() => !page.data && !page.error)
const reloading = computed(
	() => !initialLoading.value && (searchPending.value || loadingFirstPage.value),
)

const emptyState = computed(() => {
	if (loadedSearch.value)
		return {
			title: `No guests match “${loadedSearch.value}”`,
			description:
				tab.value === "all"
					? "Check the spelling, or search by email or ticket ID."
					: "Check the spelling, or look under All.",
			icon: "lucide-search-x",
		}
	const titles: Record<string, string> = {
		"1": "Nobody has checked in yet",
		"0": "Everyone is in",
	}
	return { title: titles[tab.value] ?? "No guests yet", icon: "lucide-users" }
})

const total = computed(() => page.data?.total ?? 0)
const checkedInCount = computed(() => (page.data?.checked_in ?? 0) + localCheckIns.value)

const tabs = computed(() => [
	{ label: "All", value: "all", count: total.value },
	{ label: "Checked in", value: "1", count: checkedInCount.value },
	{ label: "Not checked in", value: "0", count: total.value - checkedInCount.value },
])

const countOf = (value: string | number) =>
	new Intl.NumberFormat().format(tabs.value.find((option) => option.value === value)?.count ?? 0)

const startsAt = computed(() => {
	const data = page.data
	if (!data?.start_date) return ""
	const date = dayjsLocal(`${data.start_date}T${data.start_time || "00:00:00"}`)
	return date.format(data.start_time ? "ddd D MMM, h:mm A" : "ddd D MMM")
})

const selectedGuest = ref<EventGuest | null>(null)
const payment = ref<string | null>(null)
const guestOpen = ref(false)

const openGuest = (
	guest: EventGuest,
	paid: string | null = null,
	scannedStatuses?: ZoneStatus[],
) => {
	checkInCall.reset()
	undoCall.reset()
	selectedGuest.value = guest
	zoneStatuses.value = scannedStatuses ?? guest.zones
	payment.value = paid
	guestOpen.value = true
}

// Rows are patched in place rather than refetched, so the pages already scrolled through stay.
// Only a change in the zone the list shows touches its rows and tally.
const setCheckedIn = (ticket: string, at: string | null) => {
	if ((actionZone.value || defaultZone.value) !== (zone.value || defaultZone.value)) return
	for (const guest of [guests.value.find((row) => row.name === ticket), selectedGuest.value])
		if (guest?.name === ticket) guest.checked_in_at = at
	localCheckIns.value += at ? 1 : -1
}

const updateZones = (ticket: string, statuses: ZoneStatus[]) => {
	zoneStatuses.value = statuses
	const row = guests.value.find((guest) => guest.name === ticket)
	if (row) row.zones = statuses
}

interface CheckInResponse {
	message: string
	ticket: { id: string; check_in_time: string }
	zones: ZoneStatus[]
}

// One check-in at a time: the row or dialog that started it shows the spinner.
const busyTicket = ref<string | null>(null)

const checkInCall = useCall<CheckInResponse, { ticket_id: string; zone?: string }>({
	url: "/api/v2/method/buzz.api.checkin.checkin_ticket",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		busyTicket.value = null
		updateZones(data.ticket.id, data.zones)
		setCheckedIn(data.ticket.id, data.ticket.check_in_time)
		playSuccessBeep()
		toast.success(data.message)
		// Long enough to see the button turn into "Checked in", then out of the way.
		// In "Any zone" mode the dialog lists more zones to act on, so it stays.
		if (guestOpen.value && zone.value) setTimeout(() => (guestOpen.value = false), 600)
	},
	onError: (error) => {
		busyTicket.value = null
		// An open dialog shows the error itself; a row has nowhere else to say it.
		if (!guestOpen.value) toast.error(serverErrorMessage(error) || "Check-in failed")
	},
})

// A row in "Any zone" mode names its own zone; otherwise the selected zone applies.
const actionZone = ref("")

const zoneParams = (ticket: string, rowZone = "") => {
	actionZone.value = rowZone || zone.value
	return { ticket_id: ticket, ...(actionZone.value && { zone: actionZone.value }) }
}

const checkIn = (ticket: string, rowZone?: string) => {
	if (busyTicket.value) return
	busyTicket.value = ticket
	checkInCall.submit(zoneParams(ticket, rowZone))
}

// Undo lives only in the guest dialog, so its errors show there too.
const undoCall = useCall<CheckInResponse, { ticket_id: string; zone?: string }>({
	url: "/api/v2/method/buzz.api.checkin.undo_checkin",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		busyTicket.value = null
		updateZones(data.ticket.id, data.zones)
		setCheckedIn(data.ticket.id, null)
		toast.success(data.message)
	},
	onError: () => (busyTicket.value = null),
})

const undoCheckIn = (ticket: string, rowZone?: string) => {
	if (busyTicket.value) return
	busyTicket.value = ticket
	undoCall.submit(zoneParams(ticket, rowZone))
}

const stickySentinel = ref<HTMLElement | null>(null)
const isSticky = ref(false)
useIntersectionObserver(stickySentinel, ([entry]) => (isSticky.value = !entry?.isIntersecting))

const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})

const scanning = ref(false)
const isMobile = useIsMobile()
const { validationResult, scanZone } = useTicketValidation()
watch(zone, (value) => (scanZone.value = value), { immediate: true })

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
		zones: [],
	}

watch(validationResult, (result) => {
	if (!result?.ticket) return
	const paid = result.payment_details
	openGuest(
		guestFromScan({ ticket: result.ticket }),
		paid ? formatPriceOrFree(paid.amount, paid.currency) : null,
		result.zones ?? [],
	)
	validationResult.value = null
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
			<nav class="-mx-2 -mb-2 flex items-center justify-between gap-2">
				<Button
					variant="ghost"
					icon-left="lucide-arrow-left"
					label="Event dashboard"
					:route="{ name: 'event-guests', params: { eventId: event } }"
				/>
				<Button
					v-if="page.data?.route"
					variant="ghost"
					icon-right="lucide-arrow-up-right"
					label="Event page"
					:href="`/events/${page.data.route}`"
				/>
			</nav>

			<div ref="stickySentinel" aria-hidden="true" />
			<!-- The event is what the desk has to be sure of, so it carries the display type. -->
			<div
				class="sticky top-0 z-10 -mx-4 -my-3 space-y-5 border-b bg-surface-base/90 px-4 py-3 backdrop-blur-md backdrop-saturate-150 transition-colors duration-150 ease-out"
				:class="isSticky ? 'border-outline-gray-2' : 'border-transparent'"
			>
				<header class="flex flex-wrap items-end justify-between gap-4">
					<div class="min-w-0 flex-1 basis-56 space-y-2">
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
						v-if="!isMobile"
						size="lg"
						:icon-left="scanning ? 'lucide-x' : 'lucide-scan-barcode'"
						:label="scanning ? 'Close' : 'Scan'"
						class="ml-auto shrink-0 transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
						@click="scanning = !scanning"
					/>
				</header>

				<Transition name="shutter">
					<QRScanner v-if="scanning" :paused="guestOpen" />
				</Transition>

				<!-- Who and where: stacked on a phone; side by side from sm, the search taking three
				     parts and the zone one, never narrower than a zone name. -->
				<div class="flex flex-col gap-2 sm:flex-row">
					<TextInput
						v-model="search"
						class="sm:min-w-0 sm:flex-[3]"
						type="search"
						size="md"
						placeholder="Search by name, email or ticket ID"
						aria-label="Search guests"
					>
						<template #prefix>
							<Icon icon="lucide-search" class="size-4 text-ink-gray-5" />
						</template>
						<template #suffix>
							<LoadingText v-if="reloading && search.trim()" text="Searching" class="!text-sm" />
						</template>
					</TextInput>
					<CheckInZoneSelect
						v-model="selectedZone"
						:zones="zones"
						any-zone
						size="md"
						class="sm:min-w-32 sm:flex-1"
					/>
				</div>
			</div>

			<div class="-mx-4 overflow-x-auto px-4">
				<TabButtons v-model="tab" :options="tabs" class="w-max">
					<template #suffix="{ button }">
						<span class="tabular-nums text-ink-gray-5">{{ countOf(button.value) }}</span>
					</template>
				</TabButtons>
			</div>

			<p class="text-p-sm text-ink-gray-5">
				Tap <span class="font-medium text-ink-gray-7">Check in</span> as a guest arrives, or tap
				their name to see their ticket. <span class="font-medium text-ink-gray-7">Scan</span>
				reads the QR code on a ticket.
			</p>

			<ul v-if="initialLoading" class="flex flex-col gap-2" aria-busy="true">
				<li
					v-for="row in 6"
					:key="row"
					class="h-[62px] animate-pulse rounded-[14px] bg-surface-gray-1"
				/>
			</ul>

			<div
				v-else
				class="transition-opacity duration-150 ease-out motion-reduce:transition-none"
				:class="{ 'opacity-50': reloading }"
				:aria-busy="reloading"
			>
				<ul v-if="guests.length" class="flex flex-col gap-2">
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

				<EmptyState v-else v-bind="emptyState">
					<Button v-if="loadedSearch" label="Clear search" @click="search = ''" />
				</EmptyState>
			</div>

			<div ref="sentinel" aria-hidden="true" />

			<!-- On a phone Scan is the thumb's main job, so it floats where the thumb rests. -->
			<div
				v-if="isMobile"
				class="pointer-events-none fixed inset-x-4 bottom-[calc(1.5rem+env(safe-area-inset-bottom))] z-20 flex justify-center"
			>
				<Button
					class="pointer-events-auto shadow-lg transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97] motion-reduce:transition-none"
					variant="solid"
					size="lg"
					:icon-left="scanning ? 'lucide-x' : 'lucide-scan-barcode'"
					:label="scanning ? 'Close' : 'Scan'"
					@click="scanning = !scanning"
				/>
			</div>
		</template>

		<GuestCheckInDialog
			v-model:open="guestOpen"
			:guest="selectedGuest"
			:payment="payment"
			:busy="busyTicket === selectedGuest?.name"
			:error="serverErrorMessage(checkInCall.error || undoCall.error)"
			:zones="zoneStatuses"
			:zone="zone"
			@check-in="selectedGuest && checkIn(selectedGuest.name, $event)"
			@undo="selectedGuest && undoCheckIn(selectedGuest.name, $event)"
		/>
	</div>
</template>

<style scoped>
.shutter-enter-active {
	transition:
		grid-template-rows 350ms cubic-bezier(0.23, 1, 0.32, 1),
		clip-path 500ms cubic-bezier(0.23, 1, 0.32, 1);
}
.shutter-leave-active {
	transition:
		grid-template-rows 250ms ease-in,
		clip-path 200ms ease-in;
}
.shutter-enter-from,
.shutter-leave-to {
	grid-template-rows: 0fr;
	clip-path: circle(0% at 50% 50%);
}
@media (prefers-reduced-motion: reduce) {
	.shutter-enter-active,
	.shutter-leave-active {
		transition: none;
	}
}
</style>
