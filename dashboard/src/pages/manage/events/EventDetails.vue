<script setup lang="ts">
import EventBanner from "@/components/dashboard/events/EventBanner.vue";
import EventMedium from "@/components/dashboard/events/EventMedium.vue";
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue";
import EventRoute from "@/components/dashboard/events/EventRoute.vue";
import EventSchedule from "@/components/dashboard/events/EventSchedule.vue";
import { eventDetail, updateEvent } from "@/data/events";
import type { EventDetail, FrappeError } from "@/types";
import { Button, ErrorMessage, Textarea, toast } from "frappe-ui";
import { Editor, EditorContent, RichTextKit } from "frappe-ui/editor";
import { computed, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = route.params.eventId as string;

const event = eventDetail(eventId);

// The form the page edits, and the copy it is compared against to know it is dirty.
const form = reactive(blank());
const saved = ref(JSON.stringify(blank()));

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
	};
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
	});
	saved.value = JSON.stringify(form);
}

watch(
	() => event.data,
	(detail) => detail && fill(detail)
);

const isDirty = computed(() => JSON.stringify(form) !== saved.value);

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() =>
	(updateEvent.error as FrappeError | null)?.messages?.join("\n")
);

async function save() {
	// A blank date or venue has to reach the server as null, not "".
	const fieldname = Object.fromEntries(
		Object.entries(form).map(([field, value]) => [field, value === "" ? null : value])
	);

	await updateEvent.submit({ doctype: "Buzz Event", name: eventId, fieldname });
	if (updateEvent.error) return;

	saved.value = JSON.stringify(form);
	toast.success("Event saved");
}
</script>

<template>
	<EventPageHeader :title="event.data?.title" section="Details">
		<Button
			v-if="isDirty"
			variant="solid"
			label="Save"
			:loading="updateEvent.loading"
			@click="save"
		/>
	</EventPageHeader>

	<div v-if="event.data" class="m-auto max-w-[800px] w-full py-8 px-4 space-y-8">
		<ErrorMessage v-if="errorMessage" :message="errorMessage" />

		<EventBanner v-model="form.banner_image" :seed="form.title" />

		<div class="space-y-2">
			<div class="flex items-start justify-between gap-4">
				<!-- Plain input on purpose: this is the page's headline, not a labelled field. -->
				<input
					v-model="form.title"
					aria-label="Event title"
					placeholder="Name your event"
					class="min-w-0 flex-1 bg-transparent text-4xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none"
				/>
				<EventRoute
					v-model="form.route"
					:event="eventId"
					:saved="event.data.route"
					class="shrink-0"
				/>
			</div>
			<!-- Ghost variant: no border, so it reads as a subtitle under the name. -->
			<Textarea
				v-model="form.short_description"
				variant="ghost"
				:rows="2"
				aria-label="Short description"
				placeholder="Add a small description"
				class="!border-0 resize-none px-0 text-ink-gray-6 bg-transparent"
			/>
		</div>

		<div class="grid gap-8 md:grid-cols-5">
			<section class="space-y-3 md:col-span-3">
				<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">About</h2>
				<!-- Editor is renderless, so EditorContent's root is the ProseMirror element
					 itself: the height and scrolling land on the editable area rather than on a
					 wrapper, and the whole box takes a click. -->
				<div class="rounded-lg border border-outline-gray-2 p-3">
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

			<div class="space-y-8 md:col-span-2">
				<section class="space-y-3">
					<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
						When
					</h2>
					<EventSchedule
						v-model:start-date="form.start_date"
						v-model:start-time="form.start_time"
						v-model:end-date="form.end_date"
						v-model:end-time="form.end_time"
						v-model:time-zone="form.time_zone"
					/>
				</section>

				<section class="space-y-3">
					<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
						Where
					</h2>
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
</template>
