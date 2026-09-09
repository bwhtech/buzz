<script setup lang="ts">
import { useTextareaAutosize } from "@vueuse/core"
import { Alert, Button, ErrorMessage, toast } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
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

// The server refuses anything below Manager, so the form is shown read-only rather than
// letting someone fill it in and lose the work to a 403 on save.
const canCreate = computed(() => canCreateEvents(currentTeam.value?.team_role))

const title = ref("")

// A title wraps rather than scrolling out of sight, so the box grows with it.
const titleField = ref<HTMLTextAreaElement>()
useTextareaAutosize({ element: titleField, watch: title })
const about = ref("")
const bannerImage = ref("")

const opening = defaultSchedule()
const startDate = ref(opening.startDate)
const startTime = ref(opening.startTime)
const endDate = ref(opening.endDate)
const endTime = ref(opening.endTime)
// The organiser's own zone is the safe opening guess; they change it if the event is
// somewhere else.
const timeZone = ref(currentTimeZone())

const venue = ref("")
// The Zoom meeting can only be booked once the event exists, so save has to act on this.
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

// The time zone and the opening slot come pre-filled, so they say nothing about whether
// the organiser has started — only a schedule moved off those defaults does.
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

// Set once the event exists: the form is no longer worth keeping, and the redirect that
// follows must not be challenged.
const created = ref(false)

// Nothing here autosaves, so leaving with a draft in hand has to be deliberate.
const LEAVE_WARNING = "You have unsaved changes. Leave without saving?"

function warnOnUnload(unload: BeforeUnloadEvent) {
	if (isDirty.value && !created.value) unload.preventDefault()
}

onMounted(() => window.addEventListener("beforeunload", warnOnUnload))
onBeforeUnmount(() => window.removeEventListener("beforeunload", warnOnUnload))
onBeforeRouteLeave(() => !isDirty.value || created.value || window.confirm(LEAVE_WARNING))

// Nothing is marked wrong until the organiser has asked to save; before that the
// checklist reads as a plan, not as four errors about work they have not started.
const saveAttempted = ref(false)

const missingItems = computed(() => checklist.value.filter((item) => !item.done))

function iconColor(item: ChecklistItem) {
	if (item.done) return "text-ink-green-7"
	return saveAttempted.value ? "text-ink-red-7" : "text-ink-gray-6"
}

// Combobox draws its own error region, so Where says what it is missing in place.
const locationError = computed(() =>
	saveAttempted.value && !venue.value && !zoomMeeting.value
		? "Pick a venue, or create a Zoom meeting"
		: "",
)

// "a, b, and c" — the toast has to name the fields, since the checklist may be scrolled
// out of view and never reaches assistive tech on its own.
const listFormat = new Intl.ListFormat("en", { style: "long", type: "conjunction" })

// The checklist is a summary; the fields themselves have to show which one is meant.
function focusFirstMissing() {
	const target = document.getElementById(missingItems.value[0]?.field ?? "")
	// A full-page smooth scroll is exactly the motion a vestibular user turns off.
	const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches
	target?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" })
	const focusable = target?.matches("input, button")
		? target
		: target?.querySelector("input, button")
	;(focusable as HTMLElement | null)?.focus({ preventScroll: true })
}

// The button stays live and the checklist says what is still missing, rather than
// leaving the organiser to guess what would enable it.
async function save() {
	if (!canCreate.value) {
		toast.error(MANAGER_REQUIRED)
		return
	}
	saveAttempted.value = true
	if (!isDraftComplete(draft.value)) {
		// Labels are sentence-cased for the list, which reads as one sentence.
		const names = missingItems.value.map((item) => item.label.toLowerCase())
		toast.error(`Add ${listFormat.format(names)}`)
		focusFirstMissing()
		return
	}

	await createEvent.submit({
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
	})
	if (createEvent.error) return

	created.value = true
	toast.success(`${createEvent.data?.title} created`)
	router.push({ name: "event-details", params: { eventId: createEvent.data?.name } })
}
</script>

<template>
	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-8">
		<header class="space-y-4">
			<div class="flex items-center justify-between gap-4">
				<h1 class="text-2xl font-semibold text-ink-gray-9">Create event</h1>
				<!-- Enabled even when incomplete, so the click can say what is missing. No
				 aria-disabled: that reads as disabled to assistive tech and blocks the very
				 click that explains the state. The checklist is named instead. -->
				<Button
					variant="solid"
					label="Create"
					:loading="createEvent.loading"
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

		<!-- Plain input on purpose: this is the page's headline, not a labelled field. -->
		<!-- A textarea rather than an input so a long name wraps; Enter is swallowed
		 since a title has no second line of its own. -->
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
				<!-- Editor is renderless, so EditorContent's root is the ProseMirror element
				 itself: the height and scrolling land on the editable area rather than on a
				 wrapper, and the whole box takes a click. -->
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
		<!-- The colour rides on the icon alone: the label stays at full contrast, so the
		 row still reads when the two hues do not. -->
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
					<!-- A row turning green is the only reward in this flow; a hard cut spends it. -->
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
</template>
