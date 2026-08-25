<script setup lang="ts">
import EventLocation from "@/components/dashboard/events/EventLocation.vue";
import EventSchedule from "@/components/dashboard/events/EventSchedule.vue";
import { useTeamAccess } from "@/composables/useTeamAccess";
import { createEvent } from "@/data/events";
import { currentTeam } from "@/data/teams";
import NotFound from "@/pages/NotFound.vue";
import { bannerPattern } from "@/utils/eventBanner";
import { canCreateEvents } from "@/utils/teamRoles";
import { currentTimeZone } from "@/utils/timeZones";
import { refDebounced } from "@vueuse/core";
import type { FrappeError } from "@/types";
import { Alert, Button, ErrorMessage, FileUploader, toast, useTheme } from "frappe-ui";
import { Editor, EditorContent, RichTextKit } from "frappe-ui/editor";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const access = useTeamAccess();

// The server refuses anything below Manager, so the form is shown read-only rather than
// letting someone fill it in and lose the work to a 403 on save.
const canCreate = computed(() => canCreateEvents(currentTeam.value?.team_role));

// The picker is filtered to these, and the file that comes back is checked against the
// same list: `accept` is a hint the OS may ignore, and a drag-drop never consults it.
// Raster only — an SVG banner would be same-origin markup, which a banner has no need
// to be. Neither check is enforcement; the upload endpoint takes what it is given.
const BANNER_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

function validateBannerImage(file: File): string | void {
	if (!BANNER_IMAGE_TYPES.includes(file.type)) {
		return "Choose a PNG, JPEG, WebP or GIF image";
	}
}

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

// The pattern is seeded by the title, so the draft banner settles into the one the
// event keeps. Seeded off a debounced copy: a gradient cannot be transitioned, so
// re-seeding per keystroke would redraw the banner once per character while the
// organiser types. An untitled draft seeds on "Untitled" rather than the empty string,
// which would draw every new event the same.
const settledTitle = refDebounced(title, 250);

const banner = computed(() => ({
	backgroundImage: bannerPattern(settledTitle.value.trim() || "Untitled"),
}));

// True from the first keystroke until the debounce fires — and the pattern swaps on the
// same tick it turns false. So the blur is already up when the swap lands, and only
// falls away afterwards, which is what hides the change.
const isSettling = computed(() => title.value.trim() !== settledTitle.value.trim());

// About is optional: an event needs a name, when it runs, and where.
const canSave = computed(() =>
	Boolean(
		canCreate.value &&
			title.value.trim() &&
			startDate.value &&
			startTime.value &&
			endTime.value &&
			(venue.value || zoomMeeting.value)
	)
);

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (createEvent.error as FrappeError | null)?.message);

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
	router.push({ name: "team-events" });
}

// Reset per image, so a second upload fades in rather than snapping.
const bannerLoaded = ref(false);
watch(bannerImage, () => {
	bannerLoaded.value = false;
});
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

			<FileUploader
				:file-types="BANNER_IMAGE_TYPES"
				:validate-file="validateBannerImage"
				@success="(file: { file_url: string }) => (bannerImage = file.file_url)"
			>
				<template #default="{ openFileSelector, error: uploadError }">
					<!-- The whole banner is the hit area; the button inside stays the -->
					<!-- keyboard-reachable control, so its press must not fire twice. -->
					<div
						class="relative aspect-[3/1] overflow-hidden rounded-xl border border-outline-gray-2"
						:class="canCreate ? 'cursor-pointer' : 'cursor-default'"
						@click="canCreate && openFileSelector()"
					>
						<!-- The pattern gets a layer of its own so the blur below never
							 reaches the image or the button. Overscaled because blur samples
							 past the edges, which would otherwise go milky against the border.
							 A gradient cannot be interpolated, so blurring over the swap is
							 what hides it. -->
						<div
							class="absolute inset-0 scale-105 transition-[filter] duration-200 ease-out"
							:class="
								isSettling && !bannerImage
									? 'blur-[10px] motion-reduce:blur-none'
									: 'blur-0'
							"
							:style="banner"
							aria-hidden="true"
						/>

						<!-- Fades onto the pattern rather than replacing it outright. -->
						<!-- Absolute, like the pattern behind it: a static sibling would paint
							 under the positioned layer instead of over it. -->
						<img
							v-if="bannerImage"
							class="absolute inset-0 h-full w-full object-cover object-center transition-opacity duration-200 ease-out"
							:class="bannerLoaded ? 'opacity-100' : 'opacity-0'"
							:src="bannerImage"
							alt=""
							@load="bannerLoaded = true"
						/>

						<div class="absolute inset-0 grid place-items-center">
							<Button
								variant="subtle"
								icon-left="lucide-image-up"
								:label="bannerImage ? 'Change banner' : 'Add a banner'"
								:disabled="!canCreate"
								@click.stop="openFileSelector"
							/>
						</div>
					</div>

					<!-- The slot types its error as {}, so the message needs narrowing. -->
					<ErrorMessage v-if="uploadError" class="mt-2" :message="String(uploadError)" />
				</template>
			</FileUploader>

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
