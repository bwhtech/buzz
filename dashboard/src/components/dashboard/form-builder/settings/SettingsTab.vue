<script setup lang="ts">
import { Button, DateTimePicker, FormControl, Switch, Textarea, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { useEventDoc } from "@/data/events"

import type { BuzzFormDoc } from "../useFormBuilder"
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
			hasPage.value && { id: "submission", label: "After submit", icon: "lucide-send" },
			{ id: "access", label: "Access", icon: "lucide-lock-keyhole" },
			hasPage.value && { id: "preview", label: "Link preview", icon: "lucide-share-2" },
		].filter(Boolean) as { id: string; label: string; icon: string }[],
)

const event = useEventDoc(() => props.eventId)
const link = computed(
	() => `${window.location.origin}/b/${event.doc?.route ?? ""}/${form.value.route}`,
)

const toggle = (key: "publish" | "login_required") =>
	computed({
		get: () => !!form.value[key],
		set: (on: boolean) => (form.value[key] = on ? 1 : 0),
	})
const published = toggle("publish")
const loginRequired = toggle("login_required")

const scroller = ref<HTMLElement | null>(null)
function jump(id: string) {
	const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches
	scroller.value
		?.querySelector(`#settings-${id}`)
		?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" })
}

async function copyLink() {
	await navigator.clipboard.writeText(link.value)
	toast.success("Link copied")
}
</script>

<template>
	<div ref="scroller" class="h-full overflow-y-auto">
		<div class="mx-auto flex w-full max-w-[920px] gap-10 px-4 pb-24 pt-8 sm:px-7">
			<nav
				class="sticky top-8 hidden w-44 shrink-0 self-start md:block"
				aria-label="Settings sections"
			>
				<button
					v-for="section in SECTIONS"
					:key="section.id"
					type="button"
					class="flex w-full items-center gap-2 rounded-5 px-2 py-1.5 text-left text-p-sm text-ink-gray-7 [@media(hover:hover)]:hover:bg-surface-gray-2"
					@click="jump(section.id)"
				>
					<span :class="[section.icon, 'size-4 text-ink-gray-5']" aria-hidden="true" />
					{{ section.label }}
				</button>
			</nav>

			<div class="min-w-0 flex-1 space-y-6">
				<p
					v-if="isAttendeeForm"
					class="rounded-6 bg-surface-gray-2 px-4 py-3 text-p-sm text-ink-gray-6"
				>
					Attendee questions follow the registration form: it opens, closes and confirms bookings.
				</p>

				<SettingsSection id="settings-general" title="General">
					<FormControl
						v-model="form.title"
						label="Internal name"
						description="Only your team sees this name"
					/>
					<template v-if="hasPage">
						<div class="space-y-1.5">
							<FormControl v-model="form.route" label="Form link" :description="link" />
							<Button size="sm" icon-left="lucide-copy" label="Copy link" @click="copyLink" />
						</div>
						<Switch
							v-model="published"
							label="Accept submissions"
							description="Turn off to take the form offline"
						/>
					</template>
				</SettingsSection>

				<SettingsSection v-if="hasPage" id="settings-submission" title="After submit">
					<FormControl v-model="form.submit_label" label="Button label" placeholder="Submit" />
					<FormControl
						v-model="form.success_title"
						label="Confirmation title"
						placeholder="Thank you!"
					/>
					<Textarea
						v-model="form.success_message"
						label="Confirmation message"
						description="Markdown works here"
						:rows="4"
					/>
					<FormControl
						v-model="form.redirect_url"
						label="Redirect to"
						description="Send people to another page instead of the confirmation"
						placeholder="https://"
					/>
				</SettingsSection>

				<SettingsSection v-if="!isAttendeeForm" id="settings-access" title="Access">
					<div class="space-y-1.5">
						<span class="text-p-xs text-ink-gray-5">Close on</span>
						<DateTimePicker
							:model-value="form.auto_close_at ?? ''"
							placeholder="Stays open until you close it"
							@update:model-value="form.auto_close_at = $event || null"
						/>
						<p class="text-p-xs text-ink-gray-5">
							New submissions are turned away after this, in the event's time zone
						</p>
					</div>
					<Switch v-if="takesLogin" v-model="loginRequired" label="Require login" />
					<template v-if="hasPage">
						<FormControl
							v-model="form.closed_title"
							label="Closed title"
							placeholder="Submissions Closed"
						/>
						<Textarea v-model="form.closed_message" label="Closed message" :rows="2" />
					</template>
				</SettingsSection>

				<SettingsSection v-if="hasPage" id="settings-preview" title="Link preview">
					<FormControl
						v-model="form.meta_title"
						label="Title"
						:placeholder="`${form.title} · ${event.doc?.title ?? ''}`"
					/>
					<Textarea v-model="form.meta_description" label="Description" :rows="2" />
					<div class="rounded-6 p-3 ring-1 ring-outline-gray-2" aria-label="Preview">
						<p class="text-p-xs text-ink-gray-4">{{ link.replace(/^https?:\/\//, "") }}</p>
						<p class="text-p-sm font-medium text-ink-gray-9">
							{{ form.meta_title || `${form.title} · ${event.doc?.title ?? ""}` }}
						</p>
						<p class="line-clamp-2 text-p-sm text-ink-gray-6">
							{{ form.meta_description || form.description }}
						</p>
					</div>
				</SettingsSection>
			</div>
		</div>
	</div>
</template>
