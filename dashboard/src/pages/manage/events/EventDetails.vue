<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { Button, ErrorMessage, Textarea, toast } from "frappe-ui"
import { Editor, EditorContent, RichTextKit } from "frappe-ui/editor"
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue"
import { onBeforeRouteLeave, useRoute } from "vue-router"

import EventBanner from "@/components/dashboard/events/EventBanner.vue"
import EventDetailsSkeleton from "@/components/dashboard/events/EventDetailsSkeleton.vue"
import EventMedium from "@/components/dashboard/events/EventMedium.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import EventRoute from "@/components/dashboard/events/EventRoute.vue"
import EventSchedule from "@/components/dashboard/events/EventSchedule.vue"
import { eventDetail, updateEvent } from "@/data/events"
import type { EventDetail, FrappeError } from "@/types"
import { isEndBeforeStart } from "@/utils/eventDates"

const route = useRoute()
const eventId = route.params.eventId as string

const event = eventDetail(eventId)

// The form the page edits, and the copy it is compared against to know it is dirty.
const form = reactive(blank())
const saved = ref(JSON.stringify(blank()))

function blank() {
	return {
		title: "",
		route: "",
		short_description: "",
		about: "",
		banner_image: "",
		start_date: "",
		start_time: "",
		end_date: "",
		end_time: "",
		time_zone: "",
		medium: "In Person",
		venue: "",
		meeting_link: "",
	}
}

// Nulls all the way through the payload; the form works in empty strings so an untouched
// field compares equal to itself.
function fill(detail: EventDetail) {
	Object.assign(form, {
		title: detail.title ?? "",
		route: detail.route ?? "",
		short_description: detail.short_description ?? "",
		about: detail.about ?? "",
		banner_image: detail.banner_image ?? "",
		start_date: detail.start_date ?? "",
		start_time: detail.start_time ?? "",
		end_date: detail.end_date ?? "",
		end_time: detail.end_time ?? "",
		time_zone: detail.time_zone ?? "",
		medium: detail.medium || "In Person",
		venue: detail.venue?.name ?? "",
		meeting_link: detail.meeting_link ?? "",
	})
	// The editor rewrites its own HTML once it mounts, so the baseline is taken after
	// that settles — otherwise the page loads already dirty.
	nextTick().then(() => (saved.value = JSON.stringify(form)))
}

// A dirty form outranks the fetched document: the refetch after a save would otherwise
// drop anything typed while it was in flight.
watch(
	() => event.data,
	(detail) => detail && !isDirty.value && fill(detail),
)

const isDirty = computed(() => JSON.stringify(form) !== saved.value)

// The server refuses both of these, so the page should not spend a round trip finding out.
const routeTaken = ref(false)
const canSave = computed(
	() =>
		isDirty.value &&
		!routeTaken.value &&
		!isEndBeforeStart(form.start_date, form.end_date, form.start_time, form.end_time),
)

// Nothing here autosaves, so leaving with edits in hand has to be deliberate.
const LEAVE_WARNING = "You have unsaved changes. Leave without saving?"

function warnOnUnload(unload: BeforeUnloadEvent) {
	if (!isDirty.value) return
	unload.preventDefault()
}

onMounted(() => window.addEventListener("beforeunload", warnOnUnload))
onBeforeUnmount(() => window.removeEventListener("beforeunload", warnOnUnload))
onBeforeRouteLeave(() => !isDirty.value || window.confirm(LEAVE_WARNING))

// The page's own save takes the shortcut the browser would otherwise spend on saving the
// document — swallowed even with nothing to commit, so it never surprises mid-edit.
useEventListener(document, "keydown", (stroke: KeyboardEvent) => {
	if (stroke.key !== "s" || !(stroke.metaKey || stroke.ctrlKey) || stroke.altKey) return
	stroke.preventDefault()
	if (!stroke.repeat) save()
})

function discard() {
	if (event.data) fill(event.data)
}

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (updateEvent.error as FrappeError | null)?.messages?.join("\n"))

async function save() {
	if (!canSave.value || updateEvent.loading) return

	// A blank date or venue has to reach the server as null, not "".
	const fieldname = Object.fromEntries(
		Object.entries(form).map(([field, value]) => [field, value === "" ? null : value]),
	)
	const submitted = JSON.stringify(form)

	await updateEvent.submit({ doctype: "Buzz Event", name: eventId, fieldname })
	if (updateEvent.error) return

	// What the server now holds, not what the form holds — an edit made while the save
	// was in flight is still unsaved, and the baseline has to say so.
	saved.value = submitted
	// The header's modified badge and the route's open/copy links all read the fetched
	// document, so they stay wrong until it is refetched.
	await event.reload()
	toast.success("Event saved")
}
</script>

<template>
	<EventPageHeader :title="event.data?.title" section="Details" :modified="event.data?.modified">
		<!-- These appear mid-edit, so they arrive rather than pop. Exit is quicker than
			 entry: the save has already happened by then. -->
		<Transition
			enter-active-class="transition duration-150 ease-out motion-reduce:transition-none"
			enter-from-class="opacity-0 translate-y-1"
			leave-active-class="transition duration-100 ease-out motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<div v-if="isDirty" class="flex items-center gap-2">
				<Button label="Discard" @click="discard" />
				<Button
					variant="solid"
					label="Save"
					:disabled="!canSave"
					:loading="updateEvent.loading"
					@click="save"
				/>
			</div>
		</Transition>
	</EventPageHeader>

	<EventDetailsSkeleton v-if="!event.data" />

	<Transition
		enter-active-class="transition-opacity duration-200 ease-out motion-reduce:transition-none"
		enter-from-class="opacity-0"
	>
		<div v-if="event.data" class="m-auto w-full max-w-[800px] space-y-8 px-4 py-8">
			<ErrorMessage v-if="errorMessage" :message="errorMessage" />

			<EventBanner v-model="form.banner_image" :seed="form.title" />

			<div class="grid gap-8 md:grid-cols-5">
				<div class="space-y-8 md:col-span-3">
					<div class="space-y-2">
						<!-- Plain input on purpose: this is the page's headline, not a labelled field. -->
						<input
							v-model="form.title"
							aria-label="Event title"
							placeholder="Name your event"
							class="-mx-1 w-full rounded-4 bg-transparent px-1 text-4xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
						/>
						<!-- Ghost variant: no border, so it reads as a subtitle under the name. -->
						<Textarea
							v-model="form.short_description"
							variant="ghost"
							:rows="2"
							aria-label="Short description"
							placeholder="Add a small description"
							class="!border-0 resize-none !px-0 text-ink-gray-6 bg-transparent"
						/>
					</div>

					<section class="space-y-3">
						<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">About</h2>
						<!-- Editor is renderless, so EditorContent's root is the ProseMirror element
						 itself: the height and scrolling land on the editable area rather than on a
						 wrapper, and the whole box takes a click. -->
						<div
							class="rounded-6 border border-outline-gray-2 p-3 transition-colors duration-150 ease-out focus-within:border-outline-gray-4 motion-reduce:transition-none"
						>
							<Editor
								v-model="form.about"
								:extensions="[RichTextKit]"
								placeholder="What is this event about?"
							>
								<EditorContent
									class="prose-sm h-48 max-w-none overflow-y-auto text-ink-gray-8 focus:outline-none"
								/>
							</Editor>
						</div>
					</section>
				</div>

				<div class="space-y-8 md:col-span-2">
					<EventRoute
						v-model="form.route"
						v-model:taken="routeTaken"
						:event="eventId"
						:saved="event.data.route"
					/>

					<EventSchedule
						v-model:start-date="form.start_date"
						v-model:start-time="form.start_time"
						v-model:end-date="form.end_date"
						v-model:end-time="form.end_time"
						v-model:time-zone="form.time_zone"
					/>

					<section class="space-y-3">
						<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">Where</h2>
						<EventMedium
							v-model:medium="form.medium"
							v-model:venue="form.venue"
							v-model:meeting-link="form.meeting_link"
							:team="event.data.team || ''"
							:venue-address="event.data.venue?.address"
						/>
					</section>
				</div>
			</div>
		</div>
	</Transition>
</template>
