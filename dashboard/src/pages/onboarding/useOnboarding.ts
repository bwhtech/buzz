import { useCall } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import type { Availability } from "@/composables/useSlugAvailability"
import type { UserInfo } from "@/types"

export type Choice = "personal" | "community" | "attendee" | "team"
export type StepId = "profile" | "fork" | "invite" | "community" | "event" | "done"
export type Scene = "profile" | "personal" | "community" | "attendee" | "team" | "event" | "done"
export type Medium = "Online" | "In Person"

export type InvitedTeam = {
	name: string
	team_name: string
	logo: string | null
	team_role: string
	invited_by: string | null
	member_count: number
	upcoming_event_count: number
}
type SavedCommunity = {
	name: string
	team_name: string
	slug: string
	logo: string | null
	short_description: string | null
}
type DraftEvent = {
	name: string
	team: string
	title: string
	start_date: string
	start_time: string
	medium: Medium
	venue_name: string | null
}
type OnboardingState = {
	personal_teams_enabled: boolean
	communities_enabled: boolean
	invited_team: InvitedTeam | null
	community: SavedCommunity | null
	draft_event: DraftEvent | null
}

const stateCall = useCall<OnboardingState>({
	url: "/api/v2/method/buzz.api.onboarding.get_onboarding_state",
	immediate: false,
})
const personalTeamCall = useCall<string>({
	url: "/api/v2/method/buzz.api.teams.create_personal_team",
	method: "POST",
	immediate: false,
})
const communityCall = useCall<string, Record<string, unknown>>({
	url: "/api/v2/method/buzz.api.onboarding.save_community",
	method: "POST",
	immediate: false,
})
const eventCall = useCall<string, { event: Record<string, unknown> }>({
	url: "/api/v2/method/buzz.api.onboarding.save_first_event",
	method: "POST",
	immediate: false,
})
export const completeCall = useCall<null>({
	url: "/api/v2/method/buzz.api.onboarding.complete_onboarding",
	method: "POST",
	immediate: false,
})
const slugCall = useCall<Availability, { slug: string }>({
	url: "/api/v2/method/buzz.api.communities.check_community_slug",
	immediate: false,
})

export const checkCommunitySlug = (slug: string) => slugCall.submit({ slug })
export const personalTeamError = computed(() => personalTeamCall.error?.message)
export const communityError = computed(() => communityCall.error?.message)
export const eventError = computed(() => eventCall.error?.message)
export const loadError = computed(() => stateCall.error?.message)

export type Profile = {
	first_name: string
	last_name: string
	username: string
	user_image: string
}

export const profile = reactive<Profile>({
	first_name: "",
	last_name: "",
	username: "",
	user_image: "",
})
export const flow = reactive({
	choice: null as Choice | null,
	personalTeam: "",
	stepIndex: 0,
	direction: 1,
	eventSkipped: false,
	completed: false,
	community: {
		name: "",
		team_name: "",
		slug: "",
		savedSlug: "",
		slugEdited: false,
		logo: null as string | null,
		short_description: "",
	},
	event: {
		name: "",
		team: "",
		title: "",
		start_date: "",
		start_time: "",
		medium: "Online" as Medium,
		venue_name: "",
	},
})
export const state = ref<OnboardingState | null>(null)

// Email signup stores the whole name as the first name, so it is split at the first space.
function loadProfile(user: UserInfo | null | undefined) {
	const [first = "", ...rest] = (user?.first_name ?? "").split(" ")
	const splitName = !user?.last_name && rest.length
	Object.assign(profile, {
		first_name: splitName ? first : (user?.first_name ?? ""),
		last_name: splitName ? rest.join(" ") : (user?.last_name ?? ""),
		username: user?.username ?? "",
		user_image: user?.user_image ?? "",
	})
}

function loadCommunity(saved: SavedCommunity | null | undefined) {
	if (!saved) return
	Object.assign(flow.community, {
		name: saved.name,
		team_name: saved.team_name,
		slug: saved.slug,
		savedSlug: saved.slug,
		slugEdited: true,
		logo: saved.logo,
		short_description: saved.short_description ?? "",
	})
}

export async function loadOnboarding(user: UserInfo | null | undefined) {
	await stateCall.fetch()
	if (stateCall.error) return
	state.value = stateCall.data
	loadProfile(user)
	loadCommunity(stateCall.data?.community)
}

// Resolves false when the request failed; the call's own error holds the message.
export async function attempt(request: Promise<unknown>) {
	try {
		await request
		return true
	} catch {
		return false
	}
}

export const invitedTeam = computed(() => state.value?.invited_team ?? null)
export const fullName = computed(() =>
	[profile.first_name, profile.last_name].filter(Boolean).join(" "),
)

export const hostingOptions = computed<Choice[]>(() => {
	const options: Choice[] = []
	if (state.value?.personal_teams_enabled) options.push("personal")
	if (state.value?.communities_enabled) options.push("community")
	return options
})
export const forkOptions = computed<Choice[]>(() => [...hostingOptions.value, "attendee"])

// Before the fork is answered, progress assumes the first offered path.
export const effectiveChoice = computed<Choice>(
	() => flow.choice ?? (invitedTeam.value ? "team" : forkOptions.value[0]),
)

export const steps = computed<StepId[]>(() => {
	const choice = effectiveChoice.value
	const hosting = choice === "personal" || choice === "community"
	const askFork: StepId | null = invitedTeam.value
		? "invite"
		: hostingOptions.value.length
			? "fork"
			: null
	return [
		"profile",
		...(askFork ? [askFork] : []),
		...(choice === "community" ? ["community" as const] : []),
		...(hosting ? ["event" as const] : []),
		"done",
	]
})
export const currentStep = computed(() => steps.value[flow.stepIndex])

// A skipped community leaves nothing to show, so the all-set step treats it as attending.
export const outcome = computed<Choice>(() =>
	effectiveChoice.value === "community" && !flow.community.name
		? "attendee"
		: effectiveChoice.value,
)
export const hostTeam = computed(() =>
	effectiveChoice.value === "community" ? flow.community.name : flow.personalTeam,
)
export const hasDraft = computed(() => !flow.eventSkipped && Boolean(flow.event.name))

export const scene = computed<Scene>(() => {
	const step = currentStep.value
	if (step === "fork") return flow.choice ?? "profile"
	if (step === "invite") return effectiveChoice.value
	return step
})

export const previewAddress = computed(() => {
	const host = window.location.host
	if (scene.value === "community") return `${host}/community/${flow.community.slug || "…"}`
	if (scene.value === "event") return `${host}/events`
	if (scene.value === "attendee") return `${host}/b/account/tickets`
	if (scene.value === "team") return `${host}/b/manage`
	return `${host}/u/${profile.username || "…"}`
})

function prefillDraft() {
	const draft = state.value?.draft_event
	if (flow.event.name || !draft || draft.team !== hostTeam.value) return
	Object.assign(flow.event, {
		name: draft.name,
		team: draft.team,
		title: draft.title,
		start_date: draft.start_date,
		start_time: draft.start_time.slice(0, 5),
		medium: draft.medium,
		venue_name: draft.venue_name ?? "",
	})
}

export async function completeOnce() {
	if (flow.completed || completeCall.loading) return
	flow.completed = await attempt(completeCall.submit())
}

export function goTo(index: number) {
	const target = Math.max(0, Math.min(index, steps.value.length - 1))
	flow.direction = target >= flow.stepIndex ? 1 : -1
	flow.stepIndex = target
	if (currentStep.value === "event") prefillDraft()
	if (currentStep.value === "done") completeOnce()
}

export const next = () => goTo(flow.stepIndex + 1)
export const back = () => goTo(flow.stepIndex - 1)

export function skip() {
	if (currentStep.value === "community") return goTo(steps.value.length - 1)
	if (currentStep.value === "fork") flow.choice = "attendee"
	if (currentStep.value === "event") flow.eventSkipped = true
	next()
}

export async function savePersonalTeam() {
	if (effectiveChoice.value !== "personal") return true
	const created = await attempt(personalTeamCall.submit())
	if (created) flow.personalTeam = personalTeamCall.data ?? ""
	return created
}

export async function saveCommunity() {
	const { team_name, slug, logo, short_description } = flow.community
	const saved = await attempt(communityCall.submit({ team_name, slug, logo, short_description }))
	if (!saved) return false
	Object.assign(flow.community, { name: communityCall.data, savedSlug: slug })
	return true
}

export async function saveFirstEvent() {
	const { name, team, start_time, ...fields } = flow.event
	const event = {
		...fields,
		team: hostTeam.value,
		start_time: `${start_time}:00`,
		venue_name: fields.medium === "In Person" ? fields.venue_name : undefined,
		event: team === hostTeam.value ? name || undefined : undefined,
	}
	const saved = await attempt(eventCall.submit({ event }))
	if (!saved) return false
	Object.assign(flow.event, { name: eventCall.data, team: hostTeam.value })
	flow.eventSkipped = false
	return true
}
