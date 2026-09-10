<script setup lang="ts">
import { useTextareaAutosize } from "@vueuse/core"
import { Alert, Button, ErrorMessage, LoadingIndicator, toast } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { TextMorph } from "torph/vue"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { onBeforeRouteLeave, useRouter } from "vue-router"

import EventBanner from "@/components/dashboard/events/EventBanner.vue"
import EventLocation from "@/components/dashboard/events/EventLocation.vue"
import EventSchedule from "@/components/dashboard/events/EventSchedule.vue"
import { createEvent } from "@/data/events"
import { currentTeam } from "@/data/teams"
import type { FrappeError } from "@/types"
import { defaultSchedule } from "@/utils/eventDates"
import type { ChecklistItem } from "@/utils/eventValidation"
import { eventDraftChecklist, isDraftComplete } from "@/utils/eventValidation"
import { richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"
import { canCreateEvents } from "@/utils/teamRoles"
import { currentTimeZone } from "@/utils/timeZones"

const MANAGER_REQUIRED = "Ask an admin to make you a Manager to create events."

const router = useRouter()

const canCreate = computed(() => canCreateEvents(currentTeam.value?.team_role))

const title = ref("")

const titleField = ref<HTMLTextAreaElement>()
useTextareaAutosize({ element: titleField, watch: title })
const about = ref("")
const bannerImage = ref("")

const opening = defaultSchedule()
const startDate = ref(opening.startDate)
const startTime = ref(opening.startTime)
const endDate = ref(opening.endDate)
const endTime = ref(opening.endTime)
const timeZone = ref(currentTimeZone())

const venue = ref("")
const zoomMeeting = ref(false)

const draft = computed(() => ({
	title: title.value,
	startDate: startDate.value,
	startTime: startTime.value,
	endDate: endDate.value,
	endTime: endTime.value,
	venue: venue.value,
	zoomMeeting: zoomMeeting.value,
}))

const checklist = computed(() => eventDraftChecklist(draft.value))

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (createEvent.error as FrappeError | null)?.messages?.join("\n"))

const isDirty = computed(() =>
	Boolean(
		title.value ||
		about.value ||
		bannerImage.value ||
		venue.value ||
		zoomMeeting.value ||
		startDate.value !== opening.startDate ||
		startTime.value !== opening.startTime ||
		endDate.value !== opening.endDate ||
		endTime.value !== opening.endTime,
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
const FINAL_STEP = "Opening event page"
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

function iconColor(item: ChecklistItem) {
	if (item.done) return "text-ink-green-7"
	return saveAttempted.value ? "text-ink-red-7" : "text-ink-gray-6"
}

const locationError = computed(() =>
	saveAttempted.value && !venue.value && !zoomMeeting.value
		? "Pick a venue, or create a Zoom meeting"
		: "",
)

const listFormat = new Intl.ListFormat("en", { style: "long", type: "conjunction" })

function focusFirstMissing() {
	const target = document.getElementById(missingItems.value[0]?.field ?? "")
	const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches
	target?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" })
	const focusable = target?.matches("input, button")
		? target
		: target?.querySelector("input, button")
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
		const names = missingItems.value.map((item) => item.label.toLowerCase())
		toast.error(`Add ${listFormat.format(names)}`)
		focusFirstMissing()
		return
	}

	submitting.value = true
	failed.value = false
	// Steps and save run together: whichever finishes first waits for the other. Settled,
	// not all: createResource rejects as well as recording the error, and the record is
	// what the panel reads.
	await Promise.allSettled([
		createEvent.submit({
			event: {
				team: currentTeam.value?.name,
				title: title.value.trim(),
				start_date: startDate.value,
				start_time: startTime.value,
				end_date: endDate.value || null,
				end_time: endTime.value,
				about: about.value || null,
				banner_image: bannerImage.value || null,
				time_zone: timeZone.value || null,
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

	step.value = FINAL_STEP
	toast.success(`${createEvent.data?.title} created`)
	await wait(STEP_DURATION)
	// Someone who walked off mid-save meant it; the toast already says the event exists.
	if (router.currentRoute.value.name !== "create-event") return
	router.push({ name: "event-details", params: { eventId: createEvent.data?.name } })
}
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4">
		<Transition
			mode="out-in"
			enter-active-class="transition-opacity duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			leave-active-class="transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			enter-from-class="opacity-0"
			leave-to-class="opacity-0"
		>
			<div v-if="!submitting" class="space-y-8">
				<header class="space-y-4">
					<div class="flex items-center justify-between gap-4">
						<h1 class="text-2xl font-semibold text-ink-gray-9">Create event</h1>
						<!-- Never disabled, and never aria-disabled: the click is what explains
						 what is missing. Held busy past the response, or the page it just saved
						 takes a second click. -->
						<Button
							variant="solid"
							size="lg"
							label="Create"
							:loading="submitting"
							aria-describedby="event-requirements"
							@click="save"
						/>
					</div>

					<ErrorMessage v-if="errorMessage" :message="errorMessage" />
				</header>

				<Alert
					v-if="!canCreate"
					theme="amber"
					title="You cannot create events"
					:description="MANAGER_REQUIRED"
					:dismissible="false"
				/>

				<EventBanner v-model="bannerImage" :seed="title" :disabled="!canCreate" />

				<textarea
					id="event-title"
					ref="titleField"
					v-model="title"
					rows="1"
					aria-label="Event title"
					placeholder="Name your event"
					:disabled="!canCreate"
					:aria-invalid="saveAttempted && !title.trim()"
					class="w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-4xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none disabled:text-ink-gray-5 aria-invalid:placeholder:text-ink-red-4"
					@keydown.enter.prevent
				/>

				<div class="grid gap-8 md:grid-cols-5">
					<section class="space-y-3 md:col-span-3">
						<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">About</h2>
						<div class="overflow-hidden rounded-6 border border-outline-gray-2">
							<Editor
								v-model="about"
								:extensions="richTextExtensions"
								placeholder="What is this event about?"
								:editable="canCreate"
							>
								<EditorFixedMenu
									:items="richTextToolbar"
									class="overflow-x-auto border-b border-outline-gray-2 px-2 py-1"
								/>
								<EditorContent
									class="prose-sm h-48 max-w-none overflow-y-auto p-3 text-ink-gray-8 focus:outline-none"
								/>
							</Editor>
						</div>
					</section>

					<div class="space-y-8 md:col-span-2">
						<EventSchedule
							:disabled="!canCreate"
							v-model:start-date="startDate"
							v-model:start-time="startTime"
							v-model:end-date="endDate"
							v-model:end-time="endTime"
							v-model:time-zone="timeZone"
						/>

						<section id="event-location" class="space-y-1.5">
							<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">Where</h2>
							<EventLocation
								v-model:venue="venue"
								v-model:zoom-meeting="zoomMeeting"
								:team="currentTeam?.name ?? ''"
								:disabled="!canCreate"
								:error="locationError"
							/>
						</section>
					</div>
				</div>
				<section id="event-requirements" class="space-y-3 rounded-6 bg-surface-gray-1/90 p-4">
					<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
						{{ missingItems.length ? "Still needed" : "Ready to create" }}
					</h2>

					<ul class="space-y-2" aria-live="polite">
						<li
							v-for="item in checklist"
							:key="item.label"
							class="flex items-center gap-2 text-base text-ink-gray-8"
						>
							<span
								class="size-4 shrink-0 transition-colors duration-150 ease-out motion-reduce:transition-none"
								:class="[item.done ? 'lucide-check' : 'lucide-x', iconColor(item)]"
								aria-hidden="true"
							/>
							<span>{{ item.label }}</span>
							<span class="sr-only">{{ item.done ? "done" : "missing" }}</span>
						</li>
					</ul>
				</section>
			</div>

			<div v-else class="flex items-center justify-center gap-3 py-24">
				<span v-if="failed" class="lucide-circle-x size-6 text-ink-red-6" aria-hidden="true" />
				<LoadingIndicator v-else class="size-6 text-ink-gray-7" />
				<TextMorph
					:text="step"
					class="text-base"
					:class="failed ? 'text-ink-red-6' : 'text-ink-gray-7'"
				/>
			</div>
		</Transition>
	</div>
</template>
