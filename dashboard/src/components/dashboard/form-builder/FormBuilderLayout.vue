<script setup lang="ts">
import { Breadcrumbs, Button, TabButtons, toast } from "frappe-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import { type FormBuilder, FORM_SECTIONS } from "./useFormBuilder"

// Registration edits two forms at once; the first one names the page.
const props = defineProps<{ builders: FormBuilder[]; eventId: string }>()
const tab = defineModel<string>("tab", { required: true })

const event = useEventDoc(() => props.eventId)
const draft = computed(() => props.builders[0].draft.value)

const section = computed(() => {
	const { label, route } = FORM_SECTIONS[draft.value?.form_doctype ?? ""] ?? {
		label: "Settings",
		route: "event-settings",
	}
	return { label, route: { name: route, params: { eventId: props.eventId } } }
})

const crumbs = computed(() => [
	{ label: event.doc?.title || "Event" },
	section.value,
	{ label: draft.value?.title || "Form" },
])

const isMobile = useIsMobile()

// On a phone the tabs keep only their icons, with the label as their accessible name.
const TABS = computed(() =>
	[
		{ label: "Build", value: "build", icon: "lucide-layout-list" },
		{ label: "Logic", value: "logic", icon: "lucide-workflow" },
		{ label: "Settings", value: "settings", icon: "lucide-settings-2" },
	].map(({ icon, ...option }) =>
		isMobile.value ? { ...option, icon } : { ...option, iconLeft: icon },
	),
)

const dirty = computed(() => props.builders.some((builder) => builder.dirty.value))
const saving = computed(() => props.builders.some((builder) => builder.form.setValue.loading))

async function save() {
	try {
		for (const builder of props.builders) if (builder.dirty.value) await builder.save()
		toast.success("Form saved")
	} catch (error) {
		toast.error((error as FrappeError).message || "Could not save the form")
	}
}
</script>

<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-base px-2 sm:gap-3 sm:px-4"
		>
			<div class="flex min-w-0 flex-1 items-center gap-1">
				<Button
					variant="ghost"
					icon="lucide-arrow-left"
					:label="`Back to ${section.label}`"
					:route="section.route"
				/>
				<Breadcrumbs v-if="!isMobile" class="min-w-0" :items="crumbs" />
				<span v-else class="truncate text-p-base font-medium text-ink-gray-9">{{
					draft?.title
				}}</span>
			</div>
			<TabButtons v-model="tab" :options="TABS" />
			<div class="flex justify-end sm:flex-1">
				<Button variant="solid" label="Save" :disabled="!dirty" :loading="saving" @click="save" />
			</div>
		</header>
		<main class="min-h-0 flex-1 overflow-hidden bg-surface-gray-1">
			<slot />
		</main>
	</div>
</template>
