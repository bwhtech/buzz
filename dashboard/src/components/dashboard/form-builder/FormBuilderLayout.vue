<script setup lang="ts">
import { Button, TabButtons, toast, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import ActionSheet from "./ActionSheet.vue"
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

const SECTIONS = [
	{ label: "Build", value: "build", icon: "lucide-layout-list" },
	{ label: "Logic", value: "logic", icon: "lucide-workflow" },
	{ label: "Settings", value: "settings", icon: "lucide-settings-2" },
]
const TABS = SECTIONS.map(({ icon, ...option }) => ({ ...option, iconLeft: icon }))
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

// Registration lives on the booking page, so only other forms have a link of their own.
const link = computed(() => {
	const form = draft.value
	if (!form || ["Event Booking", "Event Booking Attendee"].includes(form.form_doctype)) return ""
	return `${window.location.origin}/b/${event.doc?.route ?? ""}/${form.route}`
})
const publishMenuOpen = ref(false)
const publishActions = computed(() => [
	...(link.value
		? [
				{
					label: "Copy link",
					icon: "lucide-link",
					onClick: async () => {
						await navigator.clipboard.writeText(link.value)
						toast.success("Link copied")
					},
				},
				{
					label: "Open form",
					icon: "lucide-external-link",
					onClick: () => window.open(link.value, "_blank"),
				},
			]
		: []),
	{
		label: "Unpublish",
		icon: "lucide-circle-pause",
		theme: "red" as const,
		onClick: () => publish(false),
	},
])

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
		<template v-if="isMobile">
			<header
				v-if="preview"
				class="grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b border-outline-gray-1 bg-surface-base py-2 pl-5 pr-3"
			>
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-[15px] font-semibold text-ink-gray-9">Preview</span>
					<span class="text-p-xs text-ink-gray-5">What people see · answers aren't saved</span>
				</div>
				<Button variant="subtle" size="lg" label="Done" @click="preview = false" />
			</header>
			<template v-else>
				<header
					class="grid shrink-0 grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-1 bg-surface-base pb-1.5 pl-1.5 pr-2.5 pt-1"
				>
					<Button
						variant="ghost"
						size="lg"
						icon="lucide-chevron-left"
						:label="`Back to ${section.label}`"
						:route="section.route"
					/>
					<div class="flex min-w-0 flex-col gap-0.5">
						<span class="truncate text-[15px] font-semibold text-ink-gray-9">{{
							draft?.title
						}}</span>
						<span class="flex items-center gap-1.5 whitespace-nowrap text-p-xs text-ink-gray-5">
							<span class="size-1.5 shrink-0 rounded-full" :class="status.dot" aria-hidden="true" />
							<span class="truncate">{{ status.label }} · {{ event.doc?.title }}</span>
						</span>
					</div>
					<div class="flex items-center gap-1">
						<Button
							v-if="tab === 'build'"
							variant="ghost"
							size="lg"
							icon="lucide-eye"
							label="Preview"
							@click="preview = true"
						/>
						<Button
							v-if="live && !dirty"
							variant="ghost"
							size="lg"
							icon="lucide-ellipsis"
							label="Publishing options"
							@click="publishMenuOpen = true"
						/>
						<Button
							v-else
							variant="solid"
							size="lg"
							label="Publish"
							:loading="saving"
							@click="publish()"
						/>
					</div>
				</header>
				<nav
					class="grid shrink-0 grid-cols-3 border-b border-outline-gray-1 bg-surface-base px-3"
					aria-label="Form builder sections"
				>
					<button
						v-for="section in SECTIONS"
						:key="section.value"
						type="button"
						class="relative flex h-11 items-center justify-center gap-1.5 text-p-base transition-colors duration-150"
						:class="tab === section.value ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5'"
						:aria-current="tab === section.value ? 'page' : undefined"
						@click="tab = section.value"
					>
						<span :class="[section.icon, 'size-[15px]']" aria-hidden="true" />
						{{ section.label }}
						<span
							class="absolute inset-x-[20%] -bottom-px h-0.5 rounded-full transition-colors duration-150"
							:class="tab === section.value ? 'bg-surface-gray-10' : 'bg-transparent'"
							aria-hidden="true"
						/>
					</button>
				</nav>
			</template>
			<ActionSheet v-model:open="publishMenuOpen" title="Form is live" :actions="publishActions" />
		</template>
		<header
			v-else
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
					<template v-if="event.doc">
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
						<span>{{ status.label }}</span>
					</span>
				</div>
			</div>

			<TabButtons v-model="tab" :options="TABS" />

			<div class="flex items-center justify-end gap-1.5">
				<template v-if="tab === 'build'">
					<Tooltip :text="preview ? 'Back to editing' : 'Preview'">
						<Button
							:variant="preview ? 'subtle' : 'ghost'"
							:icon="preview ? 'lucide-pencil' : 'lucide-eye'"
							:label="preview ? 'Back to editing' : 'Preview'"
							@click="preview = !preview"
						/>
					</Tooltip>
					<TabButtons v-model="device" :options="DEVICES" />
					<span class="mx-1 h-4 w-px bg-surface-gray-3" aria-hidden="true" />
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
