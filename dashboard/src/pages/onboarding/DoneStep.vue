<script setup lang="ts">
import { Avatar, Button, ErrorMessage } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"

import { selectTeam } from "@/data/teams"
import { resolveLoginRedirect } from "@/utils/loginRedirect"

import {
	completeCall,
	completeOnce,
	flow,
	fullName,
	hasDraft,
	hostTeam,
	invitedTeam,
	outcome,
	profile,
} from "./useOnboarding"

type Action = { label: string; run: () => void }

const REDIRECT_SECONDS = 5
const route = useRoute()
const redirectTo = computed(() => route.query["redirect-to"])
const secondsLeft = ref(REDIRECT_SECONDS)
let timer: ReturnType<typeof setInterval> | undefined

function open(path: string, teamName?: string) {
	if (teamName) selectTeam(teamName)
	window.location.assign(path)
}

const eventAction = computed<Action>(() =>
	hasDraft.value
		? {
				label: __("Open event draft"),
				run: () => open(`/b/manage/events/${flow.event.name}`, hostTeam.value),
			}
		: {
				label: __("Create event"),
				run: () => open("/b/manage/team/events/new", hostTeam.value),
			},
)
const browseEvents: Action = { label: __("Browse events"), run: () => open("/events") }

const actions = computed<Action[]>(() => {
	const team = invitedTeam.value
	if (outcome.value === "team" && team)
		return [
			{ label: __("Open {0}", [team.team_name]), run: () => open("/b/manage", team.name) },
			browseEvents,
		]
	if (outcome.value === "personal")
		return [
			eventAction.value,
			{ label: __("Go to dashboard"), run: () => open("/b/manage", hostTeam.value) },
		]
	if (outcome.value === "community")
		return [
			eventAction.value,
			{ label: __("View community page"), run: () => open(`/community/${flow.community.slug}`) },
		]
	return [browseEvents, { label: __("My tickets"), run: () => open("/b/account/tickets") }]
})

const summary = computed(() => {
	if (outcome.value === "attendee") return __("Your tickets and bookings live in one place now.")
	if (outcome.value === "team" && invitedTeam.value)
		return __("{0}'s events and members are waiting for you.", [invitedTeam.value.team_name])
	return __("Everything you set up is saved. Pick up where you left off.")
})

function redirectNow() {
	clearInterval(timer)
	window.location.replace(resolveLoginRedirect(redirectTo.value, window.location.origin))
}

function startCountdown() {
	timer = setInterval(() => {
		secondsLeft.value -= 1
		if (secondsLeft.value <= 0) redirectNow()
	}, 1000)
}

watch(
	() => flow.completed,
	(completed) => completed && redirectTo.value && startCountdown(),
	{ immediate: true },
)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
	<div class="flex flex-col items-center gap-6 text-center">
		<Avatar size="3xl" :image="profile.user_image || undefined" :label="fullName || '?'" />
		<div class="flex flex-col gap-1.5">
			<h2 class="text-2xl-semibold text-ink-gray-9">
				{{ __("You're all set, {0}", [profile.first_name]) }}
			</h2>
			<p class="text-base text-ink-gray-6">{{ summary }}</p>
		</div>

		<div v-if="completeCall.error" class="flex flex-col items-center gap-3">
			<ErrorMessage :message="completeCall.error.message" />
			<Button variant="subtle" :label="__('Try again')" @click="completeOnce" />
		</div>
		<div v-else-if="redirectTo" class="flex w-full max-w-sm flex-col items-center gap-3">
			<p class="sr-only" role="status">
				{{ __("Taking you back in {0} seconds", [REDIRECT_SECONDS]) }}
			</p>
			<p class="text-sm text-ink-gray-6" aria-live="off">
				{{ __("Taking you back in {0}s", [secondsLeft]) }}
			</p>
			<div class="h-0.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
				<div
					v-if="flow.completed"
					class="countdown h-full w-full bg-surface-gray-9"
					:style="{ animationDuration: `${REDIRECT_SECONDS}s` }"
				/>
			</div>
			<Button
				variant="solid"
				:label="__('Go now')"
				:disabled="!flow.completed"
				@click="redirectNow"
			/>
		</div>
		<div v-else class="flex flex-wrap justify-center gap-2">
			<Button
				variant="solid"
				:label="actions[0].label"
				:loading="completeCall.loading"
				:disabled="!flow.completed"
				@click="actions[0].run"
			/>
			<Button
				variant="subtle"
				:label="actions[1].label"
				:disabled="!flow.completed"
				@click="actions[1].run"
			/>
		</div>
	</div>
</template>

<style scoped>
.countdown {
	transform-origin: left;
	animation: countdown linear forwards;
}
@keyframes countdown {
	to {
		transform: scaleX(0);
	}
}
</style>
