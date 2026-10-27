<script setup lang="ts">
import { Breadcrumbs, Button, TabButtons, toast } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import type { FormBuilder } from "./useFormBuilder"

const props = defineProps<{ builder: FormBuilder; eventId: string }>()
const tab = defineModel<string>("tab", { required: true })

// Where each form type lives in the event workspace, so the crumb leads back there.
const SECTIONS: Record<string, { label: string; route: string }> = {
	"Talk Proposal": { label: "Talks", route: "event-talks" },
	"Sponsorship Enquiry": { label: "Sponsorships", route: "event-sponsorships" },
	"Event Booking": { label: "Registrations", route: "event-registrations" },
	"Event Booking Attendee": { label: "Registrations", route: "event-registrations" },
}

const event = useEventDoc(() => props.eventId)
const draft = computed(() => props.builder.draft.value)

const crumbs = computed(() => {
	const section = SECTIONS[draft.value?.form_doctype ?? ""] ?? {
		label: "Settings",
		route: "event-settings",
	}
	return [
		{ label: event.doc?.title || "Event" },
		{ label: section.label, route: { name: section.route, params: { eventId: props.eventId } } },
		{ label: draft.value?.title || "Form" },
	]
})

const TABS = [
	{ label: "Build", value: "build", iconLeft: "lucide-layout-list" },
	{ label: "Logic", value: "logic", iconLeft: "lucide-workflow" },
	{ label: "Settings", value: "settings", iconLeft: "lucide-settings-2" },
]

const saving = computed(() => props.builder.form.setValue.loading)

async function save() {
	try {
		await props.builder.save()
		toast.success("Form saved")
	} catch (error) {
		toast.error((error as FrappeError).message || "Could not save the form")
	}
}
</script>

<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="flex h-12 shrink-0 items-center gap-3 border-b border-outline-gray-1 bg-surface-base px-4"
		>
			<Breadcrumbs class="min-w-0 flex-1" :items="crumbs" />
			<TabButtons v-model="tab" :options="TABS" />
			<div class="flex flex-1 justify-end">
				<Button
					variant="solid"
					label="Save"
					:disabled="!builder.dirty.value"
					:loading="saving"
					@click="save"
				/>
			</div>
		</header>
		<main class="min-h-0 flex-1 overflow-y-auto bg-surface-gray-1">
			<slot />
		</main>
	</div>
</template>
