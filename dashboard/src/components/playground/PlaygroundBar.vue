<script setup lang="ts">
import { Button, Dropdown, toast, useCall } from "frappe-ui"
import { onBeforeUnmount, ref } from "vue"

import { useSocket } from "@/socket"

import PlaygroundChecklist from "./PlaygroundChecklist.vue"
import PlaygroundInbox from "./PlaygroundInbox.vue"

const playground = window.playground
const inboxOpen = ref(false)
const hasNewEmail = ref(false)

const redirect = {
	onSuccess: (data: { redirect_to: string }) => window.location.assign(data.redirect_to),
}
const switchPersona = useCall<{ redirect_to: string }, { persona: string }>({
	url: "/api/v2/method/buzz.api.playground.switch_persona",
	method: "POST",
	immediate: false,
	...redirect,
})
const reset = useCall<{ redirect_to: string }>({
	url: "/api/v2/method/buzz.api.playground.reset",
	method: "POST",
	immediate: false,
	...redirect,
})

const personas = [
	{ label: __("Organizer"), persona: "organizer" },
	{ label: __("Attendee"), persona: "attendee" },
	{ label: __("Front desk"), persona: "front_desk" },
].map(({ label, persona }) => ({ label, onClick: () => switchPersona.submit({ persona }) }))

function openInbox() {
	hasNewEmail.value = false
	inboxOpen.value = true
}

const socket = useSocket()
const onEmail = () => {
	hasNewEmail.value = true
	toast.info(__("New email in your playground inbox"))
}
socket?.on("playground_email", onEmail)
onBeforeUnmount(() => socket?.off("playground_email", onEmail))
</script>

<template>
	<!-- Phones: left-aligned above the bottom tab bar, beside the floating create button. -->
	<div
		class="fixed bottom-20 left-4 z-50 flex items-center gap-1 rounded-full border border-outline-gray-2 bg-surface-elevation-2 p-1 shadow-xl sm:bottom-4 sm:left-1/2 sm:-translate-x-1/2 sm:pl-4"
	>
		<span class="hidden whitespace-nowrap text-sm text-ink-gray-7 sm:inline">
			{{ __("Playground · resets in {0}h", [playground?.hours_left]) }}
		</span>
		<Button variant="ghost" icon-left="lucide-inbox" :aria-label="__('Inbox')" @click="openInbox">
			<span class="hidden sm:inline">{{ __("Inbox") }}</span>
			<span v-if="hasNewEmail" class="size-2 rounded-full bg-surface-red-5" />
		</Button>
		<Dropdown :options="personas">
			<Button
				variant="ghost"
				icon-left="lucide-user-round"
				:aria-label="__('View as')"
				:loading="switchPersona.loading"
			>
				<span class="hidden sm:inline">{{ __("View as") }}</span>
			</Button>
		</Dropdown>
		<Button
			variant="ghost"
			icon-left="lucide-rotate-ccw"
			:aria-label="__('Reset')"
			:loading="reset.loading"
			@click="reset.submit()"
		>
			<span class="hidden sm:inline">{{ __("Reset") }}</span>
		</Button>
		<Button
			v-if="playground?.signup_url"
			variant="solid"
			class="rounded-full"
			:href="playground.signup_url"
		>
			<span class="sm:hidden">{{ __("Sign up") }}</span>
			<span class="hidden sm:inline">{{ __("Create your real account") }}</span>
		</Button>
	</div>
	<PlaygroundInbox v-model="inboxOpen" />
	<!-- Outside the bar: its translate would anchor this fixed card to the bar. -->
	<PlaygroundChecklist />
</template>
