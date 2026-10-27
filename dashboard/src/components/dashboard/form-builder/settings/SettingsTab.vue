<script setup lang="ts">
import { Badge, Button, DateTimePicker, Switch, Textarea, TextInput, toast } from "frappe-ui"
import { computed, ref } from "vue"

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

const FORM_TYPES: Record<string, string> = {
	"Talk Proposal": "Call for proposals",
	"Event Booking": "Registration",
	"Event Booking Attendee": "Registration",
	"Sponsorship Enquiry": "Sponsorship enquiry",
	"Event Feedback": "Feedback",
}
const formType = computed(() => FORM_TYPES[form.value.form_doctype] ?? "Custom form")

const SECTIONS = computed(
	() =>
		[
			{ id: "general", label: "General", icon: "lucide-settings-2" },
			hasPage.value && { id: "submission", label: "After submit", icon: "lucide-send" },
			!isAttendeeForm.value && { id: "access", label: "Access", icon: "lucide-lock-keyhole" },
			hasPage.value && { id: "preview", label: "Link preview", icon: "lucide-share-2" },
		].filter(Boolean) as { id: string; label: string; icon: string }[],
)

const event = useEventDoc(() => props.eventId)
const link = computed(
	() => `${window.location.origin}/b/${event.doc?.route ?? ""}/${form.value.route}`,
)
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
function onScroll() {
	const top = scroller.value!.getBoundingClientRect().top + 40
	const passed = SECTIONS.value.filter(
		(section) =>
			document.getElementById(`settings-${section.id}`)!.getBoundingClientRect().top <= top,
	)
	active.value = passed.at(-1)?.id ?? "general"
}

function jump(id: string) {
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
		<nav
			class="hidden w-[220px] shrink-0 flex-col gap-0.5 border-r border-outline-gray-1 px-3 py-5 md:flex"
			aria-label="Settings sections"
		>
			<button
				v-for="section in SECTIONS"
				:key="section.id"
				type="button"
				class="flex h-8 w-full items-center gap-2 rounded-5 px-2 text-left text-p-sm transition-colors duration-150"
				:class="
					active === section.id
						? 'bg-surface-base text-ink-gray-9 shadow-sm ring-1 ring-outline-gray-2'
						: 'text-ink-gray-7 [@media(hover:hover)]:hover:bg-surface-gray-2'
				"
				:aria-current="active === section.id ? 'true' : undefined"
				@click="jump(section.id)"
			>
				<span :class="[section.icon, 'size-4 text-ink-gray-6']" aria-hidden="true" />
				{{ section.label }}
			</button>
		</nav>

		<div ref="scroller" class="min-w-0 flex-1 overflow-y-auto" @scroll.passive="onScroll">
			<div
				class="mx-auto flex max-w-[720px] flex-col gap-6 px-4 pb-[120px] pt-5 md:gap-9 md:px-8 md:pt-7"
			>
				<SettingsSection id="settings-general" title="General">
					<SettingsRow
						title="Form type"
						:description="
							isAttendeeForm
								? 'Attendee questions follow the registration form: it opens, closes and confirms bookings'
								: 'What this form collects for the event'
						"
					>
						<div class="flex sm:justify-end">
							<Badge theme="green" variant="subtle" size="lg" :label="formType" />
						</div>
					</SettingsRow>
					<SettingsRow title="Internal name" description="Only your team sees this name">
						<TextInput aria-label="Internal name" v-model="form.title" />
					</SettingsRow>
					<SettingsRow
						v-if="hasPage"
						title="Form link"
						description="Share this to invite people directly"
					>
						<div class="flex items-center gap-1">
							<TextInput aria-label="Form link" v-model="form.route" class="flex-1">
								<template #prefix><span class="lucide-link size-4 text-ink-gray-5" /></template>
							</TextInput>
							<Button variant="ghost" icon="lucide-copy" label="Copy link" @click="copyLink" />
						</div>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection v-if="hasPage" id="settings-submission" title="After submit">
					<SettingsRow title="Button label" description="Shown at the end of the form">
						<TextInput
							aria-label="Button label"
							:model-value="form.submit_label ?? ''"
							@update:model-value="form.submit_label = $event"
							placeholder="Submit"
						/>
					</SettingsRow>
					<SettingsRow
						title="Confirmation title"
						description="The heading people see after submitting"
					>
						<TextInput
							aria-label="Confirmation title"
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
						title="Redirect to"
						description="Send people to another page instead of the confirmation"
					>
						<TextInput
							aria-label="Redirect to"
							:model-value="form.redirect_url ?? ''"
							@update:model-value="form.redirect_url = $event"
							placeholder="https://"
						/>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection v-if="!isAttendeeForm" id="settings-access" title="Access">
					<SettingsRow
						title="Close on"
						description="New submissions are turned away after this, in the event's time zone"
					>
						<DateTimePicker
							aria-label="Close on"
							:model-value="form.auto_close_at ?? ''"
							placeholder="Stays open"
							@update:model-value="form.auto_close_at = $event || null"
						/>
					</SettingsRow>
					<SettingsRow
						v-if="takesLogin"
						title="Require login"
						description="Only signed-in people can submit"
					>
						<div class="flex sm:justify-end">
							<Switch aria-label="Require login" v-model="loginRequired" />
						</div>
					</SettingsRow>
					<template v-if="hasPage">
						<SettingsRow
							title="Closed title"
							description="The heading people see once the form closes"
						>
							<TextInput
								aria-label="Closed title"
								:model-value="form.closed_title ?? ''"
								@update:model-value="form.closed_title = $event"
								placeholder="Submissions Closed"
							/>
						</SettingsRow>
						<SettingsRow
							title="Closed message"
							description="Explain why, or where to go instead"
							stacked
						>
							<Textarea aria-label="Closed message" v-model="form.closed_message" :rows="2" />
						</SettingsRow>
					</template>
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
								label="Title"
								:placeholder="previewTitle"
							/>
							<Textarea v-model="form.meta_description" label="Description" :rows="3" />
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
