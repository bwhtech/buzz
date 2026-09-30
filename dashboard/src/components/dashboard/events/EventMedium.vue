<script setup lang="ts">
import { Button, Dialog, type DialogAction, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import EventLocationField from "@/components/dashboard/events/location/EventLocationField.vue"
import VirtualMeetingOptions from "@/components/dashboard/events/VirtualMeetingOptions.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { convertEvent, convertToZoomMeeting } from "@/data/events"
import { serverErrorMessage } from "@/utils/serverError"

// The two values Buzz Event's `medium` select takes.
const IN_PERSON = "In Person"
const ONLINE = "Online"

type Call = { error: unknown }

const props = defineProps<{ event: string; team: string; medium: string }>()
const emit = defineEmits<{ converted: [] }>()

const venue = defineModel<string>("venue", { default: "" })
const meetingLink = defineModel<string>("meetingLink", { default: "" })

const isOnline = computed(() => props.medium === ONLINE)
const isDialogOpen = ref(false)
const isConverting = ref(false)
const newLink = ref("")
const choice = ref<"link" | "zoom">("link")
const zoomAvailable = Boolean(window.zoom_available)

watch(isDialogOpen, (open) => {
	if (!open) return
	newLink.value = ""
	choice.value = "link"
})

// Converting saves on its own, apart from the page's Save, so the page is told to take
// the new location once the server has it.
// `submit` settles even when the server refuses, so the failure is read off the call.
function convert(call: Call, request: Promise<unknown>, loading: string, success: string) {
	isDialogOpen.value = false
	isConverting.value = true
	const done = request
		.then(() => {
			if (call.error) throw call.error
			emit("converted")
		})
		.finally(() => (isConverting.value = false))
	toast.promise(done, { loading, success, error: (error: unknown) => serverErrorMessage(error) })
}

function convertToVirtual() {
	if (choice.value === "zoom") {
		const request = convertToZoomMeeting.submit({ event: props.event })
		return convert(
			convertToZoomMeeting,
			request,
			"Creating a Zoom meeting…",
			"The event is now on Zoom",
		)
	}
	const request = convertEvent.submit({
		name: props.event,
		medium: ONLINE,
		meeting_link: newLink.value.trim(),
	})
	convert(convertEvent, request, "Converting to a virtual event…", "The event is now virtual")
}

const actions = computed<DialogAction[]>(() => [
	{ label: "Cancel" },
	{
		label: "Convert",
		variant: "solid",
		disabled: choice.value === "link" && !newLink.value.trim(),
		onClick: convertToVirtual,
	},
])

function convertToInPerson() {
	const request = convertEvent.submit({ name: props.event, medium: IN_PERSON })
	convert(convertEvent, request, "Converting to an in-person event…", "The event is now in person")
}

const copyToClipboard = useCopyToClipboard()

const copyLink = () => copyToClipboard(meetingLink.value, "Meeting link copied")
</script>

<template>
	<div class="flex flex-col gap-3">
		<!-- The two answers are different heights, so the swap moves the column. Opacity
			 only, and out before in: a height animation here would cost more than it hides. -->
		<Transition
			mode="out-in"
			enter-active-class="transition-opacity duration-100 ease-out motion-reduce:transition-none"
			enter-from-class="opacity-0"
			leave-active-class="transition-opacity duration-75 ease-out motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<div v-if="isOnline" class="flex items-end gap-2">
				<FormControl
					v-model="meetingLink"
					class="flex-1"
					type="url"
					label="Meeting link"
					placeholder="https://…"
				/>
				<Button
					icon="lucide-copy"
					label="Copy meeting link"
					:disabled="!meetingLink"
					@click="copyLink"
				/>
			</div>

			<EventLocationField v-else v-model:venue="venue" :team="team" :show-zoom="false" />
		</Transition>

		<p class="text-p-sm text-ink-gray-5">
			{{ isOnline ? "Meeting in person?" : "Hosting online?" }}
			<button
				type="button"
				class="text-ink-gray-7 underline underline-offset-2 hover:text-ink-gray-9 disabled:opacity-50"
				:disabled="isConverting"
				@click="isOnline ? convertToInPerson() : (isDialogOpen = true)"
			>
				{{ isOnline ? "Convert to an in-person event" : "Convert to a virtual event" }}
			</button>
		</p>

		<Dialog v-model="isDialogOpen" title="Convert to a virtual event" :actions="actions">
			<div class="space-y-3">
				<p class="text-p-base text-ink-gray-7">Guests join online, and the venue is removed.</p>
				<VirtualMeetingOptions
					v-if="zoomAvailable"
					v-model:choice="choice"
					v-model:link="newLink"
				/>
				<FormControl
					v-else
					v-model="newLink"
					type="url"
					label="Meeting link"
					placeholder="https://…"
				/>
			</div>
		</Dialog>
	</div>
</template>
