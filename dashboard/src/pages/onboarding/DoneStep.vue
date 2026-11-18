<script setup lang="ts">
import { Avatar, Button, ErrorMessage, Spinner } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"

import { selectTeam } from "@/data/teams"
import { resolveLoginRedirect } from "@/utils/loginRedirect"

import {
	completeCall,
	completeOnce,
	flow,
	fullName,
	hostTeam,
	invitedTeam,
	outcome,
	profile,
} from "./useOnboarding"

type Action = { label: string; description: string; icon: string; run: () => void }

const REDIRECT_SECONDS = 5
const route = useRoute()
// Hosts stay to pick their next step, so only attendees and invitees go back on their own.
const redirectTo = computed(() =>
	["personal", "community"].includes(outcome.value) ? undefined : route.query["redirect-to"],
)
const secondsLeft = ref(REDIRECT_SECONDS)
let timer: ReturnType<typeof setInterval> | undefined

function open(path: string, teamName?: string) {
	if (teamName) selectTeam(teamName)
	window.location.assign(path)
}

// The create page reads `team` to pick the team the user just set up.
const createEvent = computed<Action>(() => ({
	label: __("Create your first event"),
	description: __("Set the date, the place, and the tickets."),
	icon: "lucide-calendar-plus",
	run: () => open(`/b/manage/team/events/new?team=${encodeURIComponent(hostTeam.value)}`),
}))
const browseEvents: Action = {
	label: __("Browse events"),
	description: __("Find events to attend."),
	icon: "lucide-compass",
	run: () => open("/events"),
}

const actions = computed<Action[]>(() => {
	const team = invitedTeam.value
	if (outcome.value === "team" && team)
		return [
			{
				label: __("Open {0}", [team.team_name]),
				description: __("See the events and members of your team."),
				icon: "lucide-users",
				run: () => open("/b/manage", team.name),
			},
			browseEvents,
		]
	if (outcome.value === "personal")
		return [
			createEvent.value,
			{
				label: __("Go to dashboard"),
				description: __("See your events and settings."),
				icon: "lucide-layout-dashboard",
				run: () => open("/b/manage", hostTeam.value),
			},
		]
	if (outcome.value === "community")
		return [
			createEvent.value,
			{
				label: __("View community page"),
				description: __("See the page your members visit."),
				icon: "lucide-globe",
				run: () => open(`/community/${flow.community.slug}`),
			},
		]
	return [
		browseEvents,
		{
			label: __("My tickets"),
			description: __("See all your bookings in one place."),
			icon: "lucide-ticket",
			run: () => open("/b/manage/events"),
		},
	]
})

const summary = computed(() => {
	if (outcome.value === "attendee") return __("Your tickets and bookings live in one place now.")
	if (outcome.value === "team" && invitedTeam.value)
		return __("{0}'s events and members are waiting for you.", [invitedTeam.value.team_name])
	return __("Everything you set up is saved. Next, create your first event.")
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
		<div
			v-else
			class="flex w-full max-w-sm flex-col overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1"
		>
			<button
				v-for="(action, index) in actions"
				:key="action.label"
				type="button"
				class="action group flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-1 focus-visible:bg-surface-gray-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				:class="index > 0 && 'border-t border-outline-gray-1'"
				:disabled="!flow.completed"
				@click="action.run"
			>
				<span class="flex size-5 shrink-0 items-center justify-center text-ink-gray-6">
					<Spinner v-if="index === 0 && completeCall.loading" class="size-4" />
					<span v-else class="size-4" :class="action.icon" />
				</span>
				<span class="flex min-w-0 flex-1 flex-col gap-0.5">
					<span class="text-base-medium text-ink-gray-9">{{ action.label }}</span>
					<span class="text-sm text-ink-gray-5">{{ action.description }}</span>
				</span>
				<span class="chevron lucide-chevron-right size-4 shrink-0 text-ink-gray-4" />
			</button>
		</div>
	</div>
</template>

<style scoped>
.action {
	transition: background-color 150ms ease;
}
.action:not(:disabled):active {
	background-color: var(--surface-gray-2);
}
.chevron {
	transition:
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1),
		color 150ms ease;
}
@media (hover: hover) and (pointer: fine) {
	.action:not(:disabled):hover .chevron {
		transform: translateX(2px);
		color: var(--ink-gray-7);
	}
}
.action:focus-visible .chevron {
	transform: translateX(2px);
}
@media (prefers-reduced-motion: reduce) {
	.action,
	.chevron {
		transition: none;
	}
}
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
