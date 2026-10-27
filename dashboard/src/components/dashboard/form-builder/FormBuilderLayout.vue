<script setup lang="ts">
import { Button, TabButtons, toast, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import { type FormBuilder, FORM_SECTIONS } from "./useFormBuilder"

// Registration edits two forms at once; the first one names the page and carries the publish state.
const props = defineProps<{ builders: FormBuilder[]; eventId: string }>()
const tab = defineModel<string>("tab", { required: true })
const device = defineModel<"desktop" | "mobile">("device", { required: true })
const preview = defineModel<boolean>("preview", { required: true })

const event = useEventDoc(() => props.eventId)
const main = computed(() => props.builders[0])
const draft = computed(() => main.value.draft.value)

const section = computed(() => {
	const { label, route } = FORM_SECTIONS[draft.value?.form_doctype ?? ""] ?? {
		label: "Settings",
		route: "event-settings",
	}
	return { label, route: { name: route, params: { eventId: props.eventId } } }
})

const isMobile = useIsMobile()

const TABS = computed(() =>
	[
		{ label: "Build", value: "build", icon: "lucide-layout-list" },
		{ label: "Logic", value: "logic", icon: "lucide-workflow" },
		{ label: "Settings", value: "settings", icon: "lucide-settings-2" },
	].map(({ icon, ...option }) =>
		isMobile.value ? { ...option, icon } : { ...option, iconLeft: icon },
	),
)
const DEVICES = [
	{ label: "Desktop", value: "desktop", icon: "lucide-monitor" },
	{ label: "Phone", value: "mobile", icon: "lucide-smartphone" },
]

const dirty = computed(() => props.builders.some((builder) => builder.dirty.value))
const saving = computed(() => props.builders.some((builder) => builder.form.setValue.loading))
const live = computed(() => !!main.value.form.doc?.publish)
const status = computed(() => {
	if (!live.value) return { label: "Draft", dot: "bg-surface-gray-4" }
	if (dirty.value) return { label: "Edited", dot: "bg-surface-amber-5" }
	return { label: "Live", dot: "bg-surface-green-3" }
})

// Saving is publishing: there are no drafts, so every save goes live.
async function publish(on = true) {
	if (draft.value) draft.value.publish = on ? 1 : 0
	try {
		for (const builder of props.builders) if (builder.dirty.value) await builder.save()
		toast.success(on ? "Form saved" : "Form unpublished")
	} catch (error) {
		toast.error((error as FrappeError).message || "Could not save the form")
	}
}
</script>

<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="grid h-12 shrink-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 border-b border-outline-gray-1 bg-surface-base px-2.5"
		>
			<div class="flex min-w-0 items-center gap-2">
				<Tooltip :text="`Back to ${section.label}`">
					<Button
						variant="ghost"
						icon="lucide-arrow-left"
						:label="`Back to ${section.label}`"
						:route="section.route"
					/>
				</Tooltip>
				<div class="flex min-w-0 items-center gap-2 whitespace-nowrap text-p-sm">
					<span class="truncate font-medium text-ink-gray-9">{{ draft?.title }}</span>
					<template v-if="!isMobile">
						<span class="text-ink-gray-3" aria-hidden="true">/</span>
						<span class="truncate text-ink-gray-5">{{ event.doc?.title }}</span>
					</template>
					<span
						class="ml-1.5 flex items-center gap-1.5 text-p-xs text-ink-gray-5"
						:title="status.label"
					>
						<span
							class="size-1.5 rounded-full transition-colors duration-200"
							:class="status.dot"
							aria-hidden="true"
						/>
						<span v-if="!isMobile">{{ status.label }}</span>
					</span>
				</div>
			</div>

			<TabButtons v-model="tab" :options="TABS" />

			<div class="flex items-center justify-end gap-1.5">
				<template v-if="!isMobile && tab === 'build'">
					<Tooltip :text="preview ? 'Back to editing' : 'Preview'">
						<Button
							:variant="preview ? 'subtle' : 'ghost'"
							:icon="preview ? 'lucide-pencil' : 'lucide-eye'"
							:label="preview ? 'Back to editing' : 'Preview'"
							@click="preview = !preview"
						/>
					</Tooltip>
					<TabButtons v-model="device" :options="DEVICES" />
					<span class="mx-1 h-4 w-px bg-outline-gray-2" aria-hidden="true" />
				</template>
				<Tooltip v-if="live && !dirty" text="Stop accepting submissions">
					<Button variant="ghost" label="Unpublish" :loading="saving" @click="publish(false)" />
				</Tooltip>
				<Button
					v-else
					variant="solid"
					:label="live ? 'Publish changes' : 'Publish'"
					:loading="saving"
					@click="publish()"
				/>
			</div>
		</header>
		<main class="min-h-0 flex-1 overflow-hidden bg-surface-base">
			<slot />
		</main>
	</div>
</template>
