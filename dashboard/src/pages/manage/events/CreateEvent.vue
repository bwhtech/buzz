<script setup lang="ts">
import EventBanner from "@/components/dashboard/events/EventBanner.vue";
import EventLocation from "@/components/dashboard/events/EventLocation.vue";
import EventSchedule from "@/components/dashboard/events/EventSchedule.vue";
import { useTeamAccess } from "@/composables/useTeamAccess";
import { createEvent } from "@/data/events";
import { currentTeam } from "@/data/teams";
import NotFound from "@/pages/NotFound.vue";
import { isEndBeforeStart } from "@/utils/eventDates";
import { canCreateEvents } from "@/utils/teamRoles";
import { currentTimeZone } from "@/utils/timeZones";
import type { FrappeError } from "@/types";
import { Alert, Button, ErrorMessage, toast, useTheme } from "frappe-ui";
import { Editor, EditorContent, RichTextKit } from "frappe-ui/editor";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const access = useTeamAccess();

// The server refuses anything below Manager, so the form is shown read-only rather than
// letting someone fill it in and lose the work to a 403 on save.
const canCreate = computed(() => canCreateEvents(currentTeam.value?.team_role));

const { currentTheme, setTheme, getSystemTheme } = useTheme();
// `system` resolves against the OS, so the icon shows what is on screen rather than
// what was picked — and the toggle sets the opposite outright instead of stepping
// through `system`, which would look like a no-op when the OS is already dark.
const isDark = computed(
	() => (currentTheme.value === "system" ? getSystemTheme() : currentTheme.value) === "dark"
);

const title = ref("");
const about = ref("");
const bannerImage = ref("");
const startDate = ref("");
const startTime = ref("");
const endDate = ref("");
const endTime = ref("");
// The organiser's own zone is the safe opening guess; they change it if the event is
// somewhere else.
const timeZone = ref(currentTimeZone());

const venue = ref("");
// The Zoom meeting can only be booked once the event exists, so save has to act on this.
const zoomMeeting = ref(false);

// About is optional: an event needs a name, when it runs, and where.
const canSave = computed(() =>
	Boolean(
		canCreate.value &&
			title.value.trim() &&
			startDate.value &&
			startTime.value &&
			endTime.value &&
			!isEndBeforeStart(startDate.value, endDate.value, startTime.value, endTime.value) &&
			(venue.value || zoomMeeting.value)
	)
);

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() =>
	(createEvent.error as FrappeError | null)?.messages?.join("\n")
);

async function save() {
	if (!canSave.value) return;

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
	});
	if (createEvent.error) return;

	toast.success(`${createEvent.data?.title} created`);
	router.push({ name: "event-details", params: { eventId: createEvent.data?.name } });
}
</script>

<template>
	<NotFound v-if="access === 'denied'" />

	<!-- Nothing renders until the team resolves, so the page would otherwise pop in. -->
	<Transition
		v-else
		enter-active-class="transition-opacity duration-150 ease-out motion-reduce:transition-none"
		enter-from-class="opacity-0"
	>
		<div v-if="access === 'granted'" class="m-auto max-w-[800px] w-full py-8 px-4 space-y-8">
			<header class="space-y-4">
				<div class="flex items-center justify-between">
					<Button
						variant="ghost"
						icon-left="lucide-arrow-left"
						label="Back"
						class="-ml-2"
						:route="{ name: 'team-events' }"
					/>

					<Button
						variant="ghost"
						:icon="isDark ? 'lucide-sun' : 'lucide-moon'"
						:label="isDark ? 'Switch to light theme' : 'Switch to dark theme'"
						@click="setTheme(isDark ? 'light' : 'dark')"
					/>
				</div>

				<div class="flex items-center justify-between gap-4">
					<h1 class="text-2xl font-semibold text-ink-gray-9">Create event</h1>
					<Button
						variant="solid"
						label="Create event"
						:disabled="!canSave"
						:loading="createEvent.loading"
						@click="save"
					/>
				</div>

				<ErrorMessage v-if="errorMessage" :message="errorMessage" />
			</header>

			<Alert
				v-if="!canCreate"
				theme="yellow"
				title="You cannot create events"
				description="Ask an admin to make you a Manager to create events."
				:dismissible="false"
			/>

			<EventBanner v-model="bannerImage" :seed="title" :disabled="!canCreate" />

			<!-- Plain input on purpose: this is the page's headline, not a labelled field. -->
			<input
				v-model="title"
				aria-label="Event title"
				placeholder="Name your event"
				:disabled="!canCreate"
				class="w-full bg-transparent text-4xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none disabled:text-ink-gray-5"
			/>

			<div class="grid gap-8 md:grid-cols-5">
				<section class="space-y-3 md:col-span-3">
					<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
						About
					</h2>
					<!-- Editor is renderless, so EditorContent's root is the ProseMirror element
					 itself: the height and scrolling land on the editable area rather than on a
					 wrapper, and the whole box takes a click. -->
					<div class="rounded-lg border border-outline-gray-2 p-3">
						<Editor
							v-model="about"
							:extensions="[RichTextKit]"
							placeholder="What is this event about?"
							:editable="canCreate"
						>
							<EditorContent
								class="prose-sm h-48 max-w-none overflow-y-auto text-ink-gray-8 focus:outline-none"
							/>
						</Editor>
					</div>
				</section>

				<div class="space-y-8 md:col-span-2">
					<section class="space-y-3">
						<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
							When
						</h2>
						<EventSchedule
							:disabled="!canCreate"
							v-model:start-date="startDate"
							v-model:start-time="startTime"
							v-model:end-date="endDate"
							v-model:end-time="endTime"
							v-model:time-zone="timeZone"
						/>
					</section>

					<section class="space-y-8">
						<label class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
							Where
						</label>
						<EventLocation
							v-model:venue="venue"
							v-model:zoom-meeting="zoomMeeting"
							:team="currentTeam?.name ?? ''"
							:disabled="!canCreate"
						/>
					</section>
				</div>
			</div>
		</div>
	</Transition>
</template>
