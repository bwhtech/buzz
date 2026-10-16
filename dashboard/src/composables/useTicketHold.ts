import { useEventListener, useIntervalFn, useSessionStorage } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { type Ref, computed, onUnmounted, ref, watch } from "vue"

import type { TicketHold } from "@/types"

const HOLD_URL = "/api/v2/method/buzz.api.booking.hold_tickets"
const RELEASE_URL = "/api/v2/method/buzz.api.booking.release_hold"
const RESIZE_DELAY_MS = 400

/**
 * Holds the tickets a booking form has picked, keyed per browser tab. The server owns the
 * expiry; the form shows the countdown and releases the hold when the person leaves.
 * `quantities` maps ticket type name to count, for ticket types with a limit only.
 */
export function holdTokenKey(eventRoute: string) {
	return `ticket-hold-${eventRoute}`
}

export function useTicketHold(
	eventRoute: string,
	eventId: Ref<string | null>,
	quantities: Ref<Record<string, number>>,
) {
	const holdToken = useSessionStorage<string | null>(holdTokenKey(eventRoute), null)
	const deadline = ref<number | null>(null)
	const now = ref(Date.now())
	let keepOnLeave = false
	let resizeTimer: ReturnType<typeof setTimeout> | undefined

	const holdCall = useCall<TicketHold, Record<string, unknown>>({
		url: HOLD_URL,
		method: "POST",
		immediate: false,
	})

	const secondsLeft = computed(() =>
		deadline.value === null ? null : Math.max(0, Math.ceil((deadline.value - now.value) / 1000)),
	)
	const expired = computed(() => secondsLeft.value === 0)

	async function hold() {
		if (!eventId.value || (!holdToken.value && !Object.keys(quantities.value).length)) return
		const data = await holdCall
			.submit({ event: eventId.value, quantities: quantities.value, hold_token: holdToken.value })
			.catch(() => null)
		if (!data) return
		holdToken.value = data.hold_token
		deadline.value =
			data.expires_in_seconds === null ? null : Date.now() + data.expires_in_seconds * 1000
	}

	function scheduleHold() {
		clearTimeout(resizeTimer)
		resizeTimer = setTimeout(hold, RESIZE_DELAY_MS)
	}

	// The server renews a lapsed token, and keeps the expiry of one that is still live.
	function holdAgain() {
		hold()
	}

	// Called once the booking is placed: the server ends the hold, and a paid booking still
	// needs it while the person is away on the payment page.
	function keepHold() {
		keepOnLeave = true
	}

	function release() {
		clearTimeout(resizeTimer)
		if (keepOnLeave || !holdToken.value) return
		// keepalive lets the request finish after the page is gone.
		fetch(RELEASE_URL, {
			method: "POST",
			keepalive: true,
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": (window as unknown as { csrf_token?: string }).csrf_token ?? "",
			},
			body: JSON.stringify({ hold_token: holdToken.value }),
		})
		holdToken.value = null
		deadline.value = null
	}

	// The booking data poll rebuilds the ticket types, which recomputes equal quantities.
	watch(
		() => JSON.stringify(quantities.value),
		() => !expired.value && scheduleHold(),
		{ immediate: true },
	)
	useIntervalFn(() => {
		now.value = Date.now()
	}, 1000)
	useEventListener(window, "pagehide", release)
	// A page restored from the back-forward cache lost its hold on pagehide.
	useEventListener(window, "pageshow", (event: PageTransitionEvent) => event.persisted && hold())
	onUnmounted(release)

	return {
		holdToken,
		secondsLeft,
		expired,
		holdError: computed(() => holdCall.error),
		holdAgain,
		keepHold,
	}
}
