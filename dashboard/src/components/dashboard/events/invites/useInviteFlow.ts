import { toast, useCall, useList } from "frappe-ui"
import { computed, nextTick, ref } from "vue"

import { useEventDoc } from "@/data/events"
import type { GuestInviteOutcome } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

import { guestCount, needsName, type TierOption } from "./invites"
import { useInviteSelection } from "./useInviteSelection"

export type Stage = "pick" | "review" | "message"
export const STAGES: Stage[] = ["pick", "review", "message"]

type InviteParams = {
	event: string
	invites: {
		email: string
		first_name: string | null
		last_name: string | null
		ticket_type: string
	}[]
	message?: string
}

export const stageTitle = (stage: Stage, count: number) =>
	({ pick: "Invite guests", review: `Review ${guestCount(count)}`, message: "Write the invite" })[
		stage
	]

/** One invite batch, shared by the desktop dialog and the phone page: who, which step, and sending. */
export function useInviteFlow(event: string, tiers: () => TierOption[], onDone: () => void) {
	const defaultTier = computed(() => tiers()[0]?.value ?? "")
	const selection = useInviteSelection(() => defaultTier.value)
	const stage = ref<Stage>("pick")
	const direction = ref<"forward" | "back">("forward")
	const message = ref("")
	const attempted = ref(false)
	const missingCount = computed(() => selection.selected.value.filter(needsName).length)

	const eventDoc = useEventDoc(() => event)
	// The team's other events, newest first; each one's guests load only when it is opened.
	const pastEvents = useList<{ name: string; title: string; start_date: string }>({
		doctype: "Buzz Event",
		fields: ["name", "title", "start_date"],
		filters: () => ({ team: eventDoc.doc?.team ?? "", name: ["!=", event] }),
		orderBy: "start_date desc",
		limit: 8,
	})

	const sendCall = useCall<GuestInviteOutcome[], InviteParams>({
		url: "/api/v2/method/buzz.api.booking.invites.send_invites",
		method: "POST",
		immediate: false,
	})
	const addCall = useCall<GuestInviteOutcome[], InviteParams>({
		url: "/api/v2/method/buzz.api.booking.invites.add_guests",
		method: "POST",
		immediate: false,
	})
	const busy = computed(() => sendCall.loading || addCall.loading)
	// Held here, not read off the calls, so a failed attempt's message clears on the next step.
	const error = ref("")

	function go(next: Stage) {
		error.value = ""
		direction.value = STAGES.indexOf(next) > STAGES.indexOf(stage.value) ? "forward" : "back"
		stage.value = next
	}

	const back = () => go(stage.value === "message" ? "review" : "pick")

	const toggle = (contact: { email: string }) =>
		selection.isSelected(contact.email)
			? selection.removeEmail(contact.email)
			: selection.add([contact])

	/** Books at once when everyone has a name; otherwise flags the rows and focuses the first. */
	async function addDirectly(container?: HTMLElement) {
		if (!missingCount.value) return submit(addCall)
		attempted.value = true
		await nextTick()
		const first = container?.querySelector<HTMLElement>("[data-missing]")
		first?.scrollIntoView({ block: "nearest" })
		first?.querySelector("input")?.focus()
	}

	const send = () => submit(sendCall, message.value)

	async function submit(call: typeof sendCall, note?: string) {
		const invites = selection.selected.value.map(
			({ email, first_name, last_name, ticket_type }) => ({
				email,
				first_name: first_name.trim() || null,
				last_name: last_name.trim() || null,
				ticket_type,
			}),
		)
		const outcomes = await call
			.submit({ event, invites, ...(note !== undefined && { message: note }) })
			.catch((failure: unknown) => {
				error.value = serverErrorMessage(failure)
				return null
			})
		if (!outcomes) return
		report(outcomes)
		onDone()
	}

	function reset() {
		error.value = ""
		stage.value = "pick"
		message.value = ""
		attempted.value = false
		selection.reset()
	}

	return {
		selection,
		defaultTier,
		stage,
		direction,
		message,
		attempted,
		missingCount,
		pastEvents,
		busy,
		error,
		go,
		back,
		toggle,
		addDirectly,
		send,
		reset,
	}
}

export type InviteFlow = ReturnType<typeof useInviteFlow>

function report(outcomes: GuestInviteOutcome[]) {
	const done = outcomes.filter(
		(outcome) => outcome.status === "invited" || outcome.status === "added",
	)
	const skipped = outcomes.length - done.length
	const verb = done[0]?.status === "added" ? "added" : "invited"
	const description = skipped
		? `${guestCount(skipped)} skipped: already registered or invited.`
		: undefined
	if (done.length) toast.success(`${guestCount(done.length)} ${verb}`, { description })
	else toast.info("Everyone on that list is already registered or invited")
}
