<script setup lang="ts">
import {
	Button,
	DateTimePicker,
	Sidebar,
	SidebarItem,
	Switch,
	TabButtons,
	Textarea,
	TextInput,
	toast,
} from "frappe-ui"
import { computed, ref } from "vue"

import UrlField from "@/components/UrlField.vue"
import { useEventDoc } from "@/data/events"

import type { BuzzFormDoc } from "../useFormBuilder"
import FormStatus from "./FormStatus.vue"
import LinkPreview from "./LinkPreview.vue"
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

const FORM_KINDS: Record<string, { label: string; noun: string }> = {
	"Talk Proposal": { label: "Call for proposals", noun: "proposals" },
	"Event Booking": { label: "Registration", noun: "registrations" },
	"Event Booking Attendee": { label: "Registration", noun: "registrations" },
	"Sponsorship Enquiry": { label: "Sponsorship enquiry", noun: "enquiries" },
}
const kind = computed(
	() => FORM_KINDS[form.value.form_doctype] ?? { label: "Custom form", noun: "responses" },
)

const SECTIONS = computed(
	() =>
		[
			(hasPage.value || !isAttendeeForm.value) && {
				id: "sharing",
				label: "Sharing",
				icon: "lucide-link",
			},
			takesLogin.value && { id: "responses", label: "Responses", icon: "lucide-inbox" },
			hasPage.value && { id: "messages", label: "Messages", icon: "lucide-message-square" },
			hasPage.value && { id: "preview", label: "Link preview", icon: "lucide-share-2" },
		].filter(Boolean) as { id: string; label: string; icon: string }[],
)

const event = useEventDoc(() => props.eventId)
const linkPrefix = computed(() => `${window.location.host}/b/${event.doc?.route ?? ""}/`)
const link = computed(() => `${window.location.protocol}//${linkPrefix.value}${form.value.route}`)

const closeTime = computed(() =>
	form.value.auto_close_at
		? new Date(form.value.auto_close_at).toLocaleTimeString(undefined, {
				hour: "numeric",
				minute: "2-digit",
			})
		: "",
)

const loginRequired = computed({
	get: () => !!form.value.login_required,
	set: (on: boolean) => (form.value.login_required = on ? 1 : 0),
})

// A redirect replaces the confirmation, so the two are one choice.
const AFTER_SUBMIT = [
	{ label: "Show message", value: "message" },
	{ label: "Open website", value: "redirect" },
]
const redirecting = ref<boolean | null>(null)
const afterSubmit = computed({
	get: () => ((redirecting.value ?? !!form.value.redirect_url) ? "redirect" : "message"),
	set: (choice: string) => {
		redirecting.value = choice === "redirect"
		if (choice === "message") form.value.redirect_url = null
	},
})

// The nav follows the section scrolled to, and jumps to the one clicked.
const scroller = ref<HTMLElement | null>(null)
const active = ref(SECTIONS.value[0]?.id ?? "")
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
	active.value = passed.at(-1)?.id ?? SECTIONS.value[0]?.id ?? ""
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
			<div class="mx-auto flex max-w-[720px] flex-col gap-7 px-4 pb-[120px] pt-6 md:px-8 md:pt-8">
				<header>
					<h1 class="text-2xl font-semibold text-ink-gray-9">Settings</h1>
					<p class="mt-1 text-p-base text-ink-gray-5">{{ form.form_doctype }} · {{ kind.label }}</p>
				</header>

				<FormStatus :live="!!form.publish" :close-at="form.auto_close_at" :noun="kind.noun" />

				<SettingsSection
					v-if="SECTIONS.some((section) => section.id === 'sharing')"
					id="settings-sharing"
					title="Sharing"
				>
					<SettingsRow
						v-if="hasPage"
						title="Form link"
						:description="
							form.login_required
								? 'Signed-in people with this link can submit'
								: 'Anyone with this link can submit'
						"
						icon="lucide-link"
						tone="blue"
					>
						<template #below>
							<div class="flex items-center gap-1">
								<UrlField
									v-model="form.route"
									class="min-w-0 flex-1"
									:prefix="linkPrefix"
									label="Form link"
									variant="subtle"
									placeholder="your-form"
								/>
								<Button variant="ghost" icon="lucide-copy" label="Copy link" @click="copyLink" />
							</div>
						</template>
					</SettingsRow>
					<SettingsRow
						v-if="!isAttendeeForm"
						:title="`Stop accepting ${kind.noun} on`"
						:description="
							closeTime
								? `Closes automatically at ${closeTime}, in the event's time zone`
								: 'Leave empty to stay open until you unpublish'
						"
						icon="lucide-calendar-clock"
						tone="amber"
					>
						<DateTimePicker
							aria-label="Close date"
							:model-value="form.auto_close_at ?? ''"
							placeholder="Never"
							@update:model-value="form.auto_close_at = $event || null"
						/>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection v-if="takesLogin" id="settings-responses" title="Responses">
					<SettingsRow
						title="Require sign-in"
						description="Only signed-in people can submit"
						icon="lucide-lock"
						tone="violet"
					>
						<div class="flex sm:justify-end">
							<Switch aria-label="Require sign-in" v-model="loginRequired" />
						</div>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection v-if="hasPage" id="settings-messages" title="Messages">
					<SettingsRow
						title="Submit button text"
						description="Last button on the form"
						icon="lucide-mouse-pointer-click"
					>
						<TextInput
							aria-label="Submit button text"
							:model-value="form.submit_label ?? ''"
							@update:model-value="form.submit_label = $event"
							placeholder="Submit"
						/>
					</SettingsRow>
					<SettingsRow
						title="After submitting"
						description="What people see when they finish"
						icon="lucide-circle-check"
						tone="green"
					>
						<div class="flex sm:justify-end">
							<TabButtons v-model="afterSubmit" :options="AFTER_SUBMIT" />
						</div>
						<template #below>
							<div v-if="afterSubmit === 'message'" class="flex flex-col gap-3">
								<TextInput
									label="Title"
									:model-value="form.success_title ?? ''"
									@update:model-value="form.success_title = $event"
									placeholder="Thank you!"
								/>
								<Textarea
									label="Message"
									v-model="form.success_message"
									placeholder="Tell people what happens next. Markdown works here"
									:rows="3"
								/>
							</div>
							<TextInput
								v-else
								label="Website"
								:model-value="form.redirect_url ?? ''"
								@update:model-value="form.redirect_url = $event"
								placeholder="https://"
							/>
						</template>
					</SettingsRow>
					<SettingsRow
						title="When closed"
						description="What people see once the form stops taking submissions"
						icon="lucide-circle-slash"
						tone="amber"
					>
						<template #below>
							<div class="flex flex-col gap-3">
								<TextInput
									label="Title"
									:model-value="form.closed_title ?? ''"
									@update:model-value="form.closed_title = $event"
									placeholder="Submissions Closed"
								/>
								<Textarea
									label="Message"
									v-model="form.closed_message"
									placeholder="Explain why, or where to go instead"
									:rows="2"
								/>
							</div>
						</template>
					</SettingsRow>
				</SettingsSection>

				<SettingsSection
					v-if="hasPage"
					id="settings-preview"
					title="Link preview"
					description="How the form link looks when shared on WhatsApp, Slack or social"
				>
					<LinkPreview
						v-model="form"
						:event-title="event.doc?.title ?? ''"
						:event-description="event.doc?.short_description"
						:event-image="event.doc?.meta_image || event.doc?.og_image || event.doc?.banner_image"
					/>
				</SettingsSection>
			</div>
		</div>
	</div>
</template>
