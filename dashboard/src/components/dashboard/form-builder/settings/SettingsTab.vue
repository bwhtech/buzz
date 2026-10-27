<script setup lang="ts">
import {
	Button,
	DateTimePicker,
	Sidebar,
	SidebarItem,
	Switch,
	Textarea,
	TextInput,
	toast,
} from "frappe-ui"
import { computed, ref } from "vue"

import UrlField from "@/components/UrlField.vue"
import { useEventDoc } from "@/data/events"

import type { BuzzFormDoc } from "../useFormBuilder"
import SettingsRow from "./SettingsRow.vue"
import SettingsSection from "./SettingsSection.vue"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{ eventId: string }>()

// Registration is served by the booking page, so its forms have no link or messages of their own.
const REGISTRATION = ["Event Booking", "Event Booking Attendee"]
const hasPage = computed(() => !REGISTRATION.includes(form.value.form_doctype))
const isAttendeeForm = computed(() => form.value.form_doctype === "Event Booking Attendee")
const takesLogin = computed(
	() => hasPage.value && form.value.form_doctype !== "Sponsorship Enquiry",
)

const SECTIONS = computed(
	() =>
		[
			{ id: "general", label: "General", icon: "lucide-settings-2" },
			!isAttendeeForm.value && { id: "submissions", label: "Submissions", icon: "lucide-inbox" },
			hasPage.value && { id: "confirmation", label: "Confirmation", icon: "lucide-circle-check" },
			hasPage.value && { id: "preview", label: "Link preview", icon: "lucide-share-2" },
		].filter(Boolean) as { id: string; label: string; icon: string }[],
)

const event = useEventDoc(() => props.eventId)
const linkPrefix = computed(() => `${window.location.host}/b/${event.doc?.route ?? ""}/`)
const link = computed(() => `${window.location.protocol}//${linkPrefix.value}${form.value.route}`)
const previewTitle = computed(
	() => form.value.meta_title || `${form.value.title} · ${event.doc?.title ?? ""}`,
)

const loginRequired = computed({
	get: () => !!form.value.login_required,
	set: (on: boolean) => (form.value.login_required = on ? 1 : 0),
})

// The nav follows the section scrolled to, and jumps to the one clicked.
const scroller = ref<HTMLElement | null>(null)
const active = ref("general")
// A clicked section stays highlighted while its jump scrolls, and when the page is too short
// to scroll it to the top; the reader's own scrolling hands the highlight back.
let jumping = false
const stopJumping = () => (jumping = false)

function onScroll() {
	if (jumping) return
	const top = scroller.value!.getBoundingClientRect().top + 40
	const passed = SECTIONS.value.filter(
		(section) =>
			document.getElementById(`settings-${section.id}`)!.getBoundingClientRect().top <= top,
	)
	active.value = passed.at(-1)?.id ?? "general"
}

function jump(id: string) {
	active.value = id
	jumping = true
	scroller.value!.addEventListener("scrollend", stopJumping, { once: true })
	const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches
	document
		.getElementById(`settings-${id}`)
		?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" })
}

async function copyLink() {
	await navigator.clipboard.writeText(link.value)
	toast.success("Link copied")
}
</script>

<template>
	<div class="flex h-full min-h-0 bg-surface-base">
		<div class="hidden md:flex">
			<Sidebar :collapsible="false" width="220px" aria-label="Settings sections">
				<div class="flex-1 overflow-y-auto px-2 py-3">
					<SidebarItem
						v-for="section in SECTIONS"
						:key="section.id"
						:label="section.label"
						:icon="section.icon"
						:active="active === section.id"
						@click="jump(section.id)"
					/>
				</div>
			</Sidebar>
		</div>

		<div
			ref="scroller"
			class="min-w-0 flex-1 overflow-y-auto"
			@scroll.passive="onScroll"
			@wheel.passive="stopJumping"
			@touchstart.passive="stopJumping"
			@keydown="stopJumping"
		>
			<div
				class="mx-auto flex max-w-[720px] flex-col gap-6 px-4 pb-[120px] pt-5 md:gap-9 md:px-8 md:pt-7"
			>
				<SettingsSection id="settings-general" title="General">
					<SettingsRow title="Title" description="Shown at the top of the form">
						<TextInput aria-label="Title" v-model="form.title" />
					</SettingsRow>
					<SettingsRow
						v-if="hasPage"
						title="Link"
						description="The end of the form's web address. Share it to invite people"
					>
						<div class="flex items-start gap-1">
							<UrlField
								v-model="form.route"
								class="min-w-0 flex-1"
								:prefix="linkPrefix"
								label="Form link"
								variant="subtle"
								placeholder="your-form"
							/>
							<Button
								class="mt-1.5"
								variant="ghost"
								icon="lucide-copy"
								label="Copy link"
								@click="copyLink"
							/>
						</div>
					</SettingsRow>
					<SettingsRow
						v-if="hasPage"
						title="Submit button text"
						description="The button at the end of the form"
					>
						<TextInput
							aria-label="Submit button text"
							:model-value="form.submit_label ?? ''"
							@update:model-value="form.submit_label = $event"
							placeholder="Submit"
						/>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection v-if="!isAttendeeForm" id="settings-submissions" title="Submissions">
					<SettingsRow
						title="Close date"
						description="Stop taking submissions after this, in the event's time zone"
					>
						<DateTimePicker
							aria-label="Close date"
							:model-value="form.auto_close_at ?? ''"
							placeholder="Never"
							@update:model-value="form.auto_close_at = $event || null"
						/>
					</SettingsRow>
					<SettingsRow
						v-if="takesLogin"
						title="Require sign-in"
						description="Only signed-in people can submit"
					>
						<div class="flex sm:justify-end">
							<Switch aria-label="Require sign-in" v-model="loginRequired" />
						</div>
					</SettingsRow>
					<template v-if="hasPage">
						<SettingsRow
							title="Closed form heading"
							description="What people see once the form stops taking submissions"
						>
							<TextInput
								aria-label="Closed form heading"
								:model-value="form.closed_title ?? ''"
								@update:model-value="form.closed_title = $event"
								placeholder="Submissions Closed"
							/>
						</SettingsRow>
						<SettingsRow
							title="Closed form message"
							description="Explain why, or where to go instead"
							stacked
						>
							<Textarea aria-label="Closed form message" v-model="form.closed_message" :rows="2" />
						</SettingsRow>
					</template>
				</SettingsSection>

				<SettingsSection v-if="hasPage" id="settings-confirmation" title="Confirmation">
					<SettingsRow title="Confirmation heading" description="What people see after they submit">
						<TextInput
							aria-label="Confirmation heading"
							:model-value="form.success_title ?? ''"
							@update:model-value="form.success_title = $event"
							placeholder="Thank you!"
						/>
					</SettingsRow>
					<SettingsRow
						title="Confirmation message"
						description="Tell people what happens next. Markdown works here"
						stacked
					>
						<Textarea aria-label="Confirmation message" v-model="form.success_message" :rows="3" />
					</SettingsRow>
					<SettingsRow
						title="Redirect URL"
						description="Send people to this page after they submit, instead of the confirmation"
					>
						<TextInput
							aria-label="Redirect URL"
							:model-value="form.redirect_url ?? ''"
							@update:model-value="form.redirect_url = $event"
							placeholder="https://"
						/>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection
					v-if="hasPage"
					id="settings-preview"
					title="Link preview"
					description="How the form link looks when shared on WhatsApp, Slack or social"
				>
					<div class="mt-3 grid gap-6 sm:grid-cols-[minmax(0,1fr)_260px] sm:items-start">
						<div class="flex flex-col gap-3.5">
							<TextInput
								:model-value="form.meta_title ?? ''"
								@update:model-value="form.meta_title = $event"
								label="Preview title"
								:placeholder="previewTitle"
							/>
							<Textarea
								v-model="form.meta_description"
								label="Preview description"
								:placeholder="form.description || ''"
								:rows="3"
							/>
						</div>
						<div
							class="overflow-hidden rounded-5 ring-1 ring-inset ring-outline-gray-2"
							aria-label="Preview"
						>
							<div
								class="flex h-[120px] flex-col items-center justify-center gap-1.5 bg-surface-gray-2 text-p-xs text-ink-gray-5"
							>
								<span class="lucide-image size-[18px]" aria-hidden="true" />
								Uses the event cover
							</div>
							<div class="flex flex-col gap-0.5 px-3 py-2.5">
								<span class="truncate text-[11px] text-ink-gray-5">{{
									link.replace(/^https?:\/\//, "")
								}}</span>
								<span class="text-p-sm font-semibold text-ink-gray-9">{{ previewTitle }}</span>
								<span class="line-clamp-2 text-p-xs text-ink-gray-6">
									{{ form.meta_description || form.description }}
								</span>
							</div>
						</div>
					</div>
				</SettingsSection>
			</div>
		</div>
	</div>
</template>
