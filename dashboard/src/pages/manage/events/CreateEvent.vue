<script setup lang="ts">
import { Alert, Button, ErrorMessage, toast } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router"

import ProgressStatus from "@/components/common/ProgressStatus.vue"
import AnnounceLaterTile from "@/components/dashboard/events/create/AnnounceLaterTile.vue"
import CreateEventFooter from "@/components/dashboard/events/create/CreateEventFooter.vue"
import CreateEventHeader from "@/components/dashboard/events/create/CreateEventHeader.vue"
import EventScheduleField from "@/components/dashboard/events/create/EventScheduleField.vue"
import EventTitleField from "@/components/dashboard/events/create/EventTitleField.vue"
import EventTeamSelect from "@/components/dashboard/events/EventTeamSelect.vue"
import EventLocationField from "@/components/dashboard/events/location/EventLocationField.vue"
import { useQueryParamRecord } from "@/composables/useQueryParamRecord"
import { createEvent } from "@/data/events"
import { currentTeam, selectTeam, teams, teamsLoaded } from "@/data/teams"
import { defaultSchedule } from "@/utils/eventDates"
import { eventDraftChecklist, isDraftComplete } from "@/utils/eventValidation"
import { resolveLoginRedirect } from "@/utils/loginRedirect"
import { serverErrorMessage } from "@/utils/serverError"
import { canCreateEvents } from "@/utils/teamRoles"
import { currentTimeZone } from "@/utils/timeZones"

const MANAGER_REQUIRED = "Ask an admin to make you a Manager to create events."

const route = useRoute()
const router = useRouter()

const canCreate = computed(() => canCreateEvents(currentTeam.value?.team_role))
// `?team=<name>` picks the team to create under, as onboarding links do.
useQueryParamRecord(
	"team",
	() => (teamsLoaded.value ? teams.value : undefined),
	(team) => selectTeam(team.name),
)

const title = ref("")

// The date can be announced later, so the form opens without one.
const opening = { startDate: "", startTime: "", endDate: "", endTime: "" }
const schedule = reactive({ ...opening, timeZone: currentTimeZone() })
const hasSchedule = computed(() => Boolean(schedule.startDate))

const clearSchedule = () => Object.assign(schedule, opening)

// Starts from the next free hour and opens the picker, so setting a date is one click.
async function setSchedule() {
	Object.assign(schedule, defaultSchedule())
	await nextTick()
	document.getElementById("event-schedule-start")?.click()
}

const venue = ref("")
const zoomMeeting = ref(false)

const draft = computed(() => ({
	title: title.value,
	startDate: schedule.startDate,
	startTime: schedule.startTime,
	endDate: schedule.endDate,
	endTime: schedule.endTime,
}))

const checklist = computed(() => eventDraftChecklist(draft.value))

const errorMessage = computed(() => serverErrorMessage(createEvent.error))

const isDirty = computed(() =>
	Boolean(
		title.value ||
		venue.value ||
		zoomMeeting.value ||
		schedule.startDate !== opening.startDate ||
		schedule.startTime !== opening.startTime ||
		schedule.endDate !== opening.endDate ||
		schedule.endTime !== opening.endTime,
	),
)

// True from the first step until the redirect lands, so the steps play past the response
// and the leave guard stays quiet for a redirect the page asked for.
const submitting = ref(false)

// Local to the sequence: the resource keeps its error for the form's message long after
// the panel is done with it, and the panel has to start clean on every attempt.
const failed = ref(false)

const CREATION_STEPS = [
	"Saving the details",
	"Setting the schedule",
	"Booking the venue",
	"Opening the guest list",
]
// The page that sent us here, such as a community calendar, gets the organiser back on cancel.
const redirectTo = computed(() => {
	const target = route.query["redirect-to"]
	return typeof target === "string" ? target : ""
})
const finalStep = "Opening event page"
const FAILED_STEP = "Failed to create event"
const STEP_DURATION = 600

const step = ref("")

function wait(milliseconds: number) {
	return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

// Walks the steps at a fixed pace whatever the save is doing, so the panel reads as
// progress rather than as a spinner with captions.
async function walkSteps() {
	for (const next of CREATION_STEPS) {
		if (createEvent.error) return
		step.value = next
		await wait(STEP_DURATION)
	}
}

const LEAVE_WARNING = "You have unsaved changes. Leave without saving?"

function warnOnUnload(unload: BeforeUnloadEvent) {
	if (isDirty.value && !submitting.value) unload.preventDefault()
}

onMounted(() => window.addEventListener("beforeunload", warnOnUnload))
onBeforeUnmount(() => window.removeEventListener("beforeunload", warnOnUnload))
onBeforeRouteLeave(() => !isDirty.value || submitting.value || window.confirm(LEAVE_WARNING))

const saveAttempted = ref(false)

const missingItems = computed(() => checklist.value.filter((item) => !item.done))
const isMissing = (field: string) =>
	saveAttempted.value && missingItems.value.some((item) => item.field === field)
const labelTone = (fields: string[]) =>
	fields.some(isMissing) ? "text-ink-red-7" : "text-ink-gray-6"
const SCHEDULE_FIELDS = ["event-schedule-start", "event-schedule-end"]

// One list of what is missing, shown beside whichever Create is on screen.
const showMissing = ref(false)
const footerVisible = ref(false)
const headerMissing = computed({
	get: () => showMissing.value && !footerVisible.value,
	set: (open: boolean) => (showMissing.value = open),
})
const footerMissing = computed({
	get: () => showMissing.value && footerVisible.value,
	set: (open: boolean) => (showMissing.value = open),
})

function focusFirstMissing() {
	const target = document.getElementById(missingItems.value[0]?.field ?? "")
	const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches
	target?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" })
	const focusable = target?.matches("input, button, textarea")
		? target
		: target?.querySelector("input, button, textarea")
	;(focusable as HTMLElement | null)?.focus({ preventScroll: true })
}

async function save() {
	// The button is disabled through both, but a keyboard repeat outruns the re-render.
	if (submitting.value) return
	if (!canCreate.value) {
		toast.error(MANAGER_REQUIRED)
		return
	}
	saveAttempted.value = true
	if (!isDraftComplete(draft.value)) {
		showMissing.value = true
		focusFirstMissing()
		return
	}
	showMissing.value = false

	submitting.value = true
	failed.value = false
	// Steps and save run together: whichever finishes first waits for the other. Settled,
	// not all: the panel reads the recorded error, whether or not the save also rejects.
	await Promise.allSettled([
		createEvent.submit({
			event: {
				team: currentTeam.value?.name,
				title: title.value.trim(),
				start_date: schedule.startDate || null,
				start_time: schedule.startTime || null,
				end_date: schedule.endDate || null,
				end_time: schedule.endTime || null,
				time_zone: schedule.timeZone || null,
				venue: venue.value || null,
				zoom_meeting: zoomMeeting.value,
			},
		}),
		walkSteps(),
	])
	if (createEvent.error) {
		// The panel says how it ended before it hands the form back with the message.
		failed.value = true
		step.value = FAILED_STEP
		toast.error(errorMessage.value || FAILED_STEP)
		await wait(STEP_DURATION * 2)
		submitting.value = false
		return
	}

	step.value = finalStep
	toast.success(`${createEvent.data?.title} created`)
	await wait(STEP_DURATION)
	// Someone who walked off mid-save meant it; the toast already says the event exists.
	if (router.currentRoute.value.name !== "create-event") return
	router.push({ name: "event-overview", params: { eventId: createEvent.data?.name } })
}

function close() {
	if (redirectTo.value) return goBack(redirectTo.value)
	router.push({ name: "events" })
}

// A dashboard page stays in the SPA; a public page, such as a community's, is a full load.
function goBack(path: string) {
	const base = router.options.history.base
	if (path.startsWith(`${base}/`)) return router.push(path.slice(base.length))
	window.location.assign(resolveLoginRedirect(path, window.location.origin))
}
</script>

<template>
	<div class="flex min-h-full flex-col bg-surface-base">
		<CreateEventHeader
			v-model:show-missing="headerMissing"
			class="sticky top-0 z-30"
			:missing="missingItems"
			:loading="submitting"
			:create-hidden="footerVisible || submitting"
			@create="save"
			@close="close"
		/>

		<Transition
			mode="out-in"
			enter-active-class="transition-opacity duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			leave-active-class="transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			enter-from-class="opacity-0"
			leave-to-class="opacity-0"
		>
			<div
				v-if="!submitting"
				class="mx-auto flex w-full max-w-[720px] flex-col gap-6 px-4 pb-28 pt-6 md:gap-7 md:px-6 md:pt-10"
			>
				<EventTeamSelect />
				<ErrorMessage v-if="errorMessage" :message="errorMessage" />

				<Alert
					v-if="!canCreate"
					theme="amber"
					title="You cannot create events"
					:description="MANAGER_REQUIRED"
					:dismissible="false"
				/>

				<EventTitleField
					v-model="title"
					:disabled="!canCreate"
					:invalid="isMissing('event-title')"
				/>

				<section>
					<div class="mb-2 flex h-6 items-center justify-between">
						<h2 class="text-sm font-medium" :class="labelTone(SCHEDULE_FIELDS)">
							{{ __("When") }}
							<span class="font-normal text-ink-gray-4">· {{ __("Optional") }}</span>
						</h2>
						<Button
							v-if="hasSchedule"
							variant="ghost"
							size="sm"
							:label="__('Announce later')"
							:disabled="!canCreate"
							@click="clearSchedule"
						/>
					</div>
					<EventScheduleField v-if="hasSchedule" :schedule="schedule" :disabled="!canCreate" />
					<AnnounceLaterTile
						v-else
						icon="lucide-calendar-clock"
						:title="__('Date to be announced')"
						:action-label="__('Set date')"
						:disabled="!canCreate"
						@action="setSchedule"
					/>
				</section>

				<section id="event-location">
					<h2 class="mb-2 text-sm font-medium text-ink-gray-6">
						{{ __("Where") }}
						<span class="font-normal text-ink-gray-4">· {{ __("Optional") }}</span>
					</h2>
					<EventLocationField
						v-model:venue="venue"
						v-model:zoom-meeting="zoomMeeting"
						:team="currentTeam?.name ?? ''"
						:disabled="!canCreate"
					>
						<template #empty="{ open }">
							<AnnounceLaterTile
								icon="lucide-map-pin"
								:title="__('Venue to be announced')"
								:action-label="__('Add location')"
								:disabled="!canCreate"
								@action="open"
							/>
						</template>
					</EventLocationField>
				</section>

				<CreateEventFooter
					v-model:show-missing="footerMissing"
					v-model:visible="footerVisible"
					:missing="missingItems"
					:loading="submitting"
					@create="save"
				/>
			</div>

			<ProgressStatus v-else class="py-16" :text="step" :failed="failed" delayed />
		</Transition>
	</div>
</template>
