import type { StepKey } from "../setupSteps"
import MiniDates from "./MiniDates.vue"
import MiniLink from "./MiniLink.vue"
import MiniLocation from "./MiniLocation.vue"
import MiniPage from "./MiniPage.vue"
import MiniPayments from "./MiniPayments.vue"
import MiniQuestions from "./MiniQuestions.vue"
import MiniTalks from "./MiniTalks.vue"
import MiniTeam from "./MiniTeam.vue"
import MiniTickets from "./MiniTickets.vue"

export const MINIATURES: Record<StepKey, unknown> = {
	dates: MiniDates,
	location: MiniLocation,
	link: MiniLink,
	tickets: MiniTickets,
	page: MiniPage,
	payments: MiniPayments,
	questions: MiniQuestions,
	team: MiniTeam,
	talks: MiniTalks,
}
