<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Avatar, Button, ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import {
	type Choice,
	effectiveChoice,
	flow,
	hostingOptions,
	invitedTeam,
	personalTeamError,
	savePersonalTeam,
} from "./useOnboarding"

const team = invitedTeam
const teamSelected = computed(() => effectiveChoice.value === "team")
const ownSpaceButtons = computed(() =>
	hostingOptions.value.map((value) => ({
		value,
		label: value === "personal" ? __("Host as myself") : __("Create a community"),
		icon: value === "personal" ? "lucide-user" : "lucide-users",
	})),
)

// Pressing a chosen option again goes back to the team.
function toggle(choice: Choice) {
	flow.choice = flow.choice === choice ? "team" : choice
}

defineExpose({ canContinue: () => true, save: savePersonalTeam })
</script>

<template>
	<div v-if="team" class="flex flex-col gap-5">
		<div class="flex flex-col gap-3">
			<div v-if="team.invited_by" class="byline flex items-center gap-2.5">
				<Avatar size="md" :label="team.invited_by" />
				<p class="text-base text-ink-gray-6">
					<span class="font-semibold text-ink-gray-9">{{ team.invited_by }}</span>
					{{ __("invited you to join") }}
				</p>
			</div>
			<div
				role="button"
				tabindex="0"
				:aria-pressed="teamSelected"
				class="cursor-pointer overflow-hidden rounded-5 border bg-surface-elevation-1 text-left transition-[border-color,box-shadow,transform] duration-150 ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-outline-gray-8 active:scale-[0.985] motion-reduce:transform-none"
				:class="
					teamSelected
						? 'border-outline-gray-9 ring-1 ring-outline-gray-9'
						: 'border-outline-gray-2 hover:border-outline-gray-3'
				"
				@click="flow.choice = 'team'"
				@keydown.enter.self.prevent="flow.choice = 'team'"
				@keydown.space.self.prevent="flow.choice = 'team'"
			>
				<div class="h-16" :style="{ backgroundImage: bannerPattern(team.team_name) }" />
				<div class="-mt-6 flex items-end justify-between gap-3 px-4">
					<Avatar
						size="2xl"
						shape="square"
						:image="team.logo || undefined"
						:label="team.team_name"
						style="box-shadow: 0 0 0 4px var(--surface-white)"
					/>
					<span
						class="mb-1 rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs font-medium text-ink-gray-7"
					>
						{{ team.team_role }}
					</span>
				</div>
				<div class="flex flex-col gap-0.5 p-4 pt-3">
					<p class="text-lg-semibold text-ink-gray-9">{{ team.team_name }}</p>
					<p class="text-sm text-ink-gray-5">
						{{
							__("{0} members · {1} upcoming events", [
								team.member_count,
								team.upcoming_event_count,
							])
						}}
					</p>
				</div>
			</div>
		</div>

		<div v-if="ownSpaceButtons.length" class="flex flex-col gap-3 rounded-5 bg-surface-gray-1 p-4">
			<div class="flex flex-col gap-0.5">
				<p class="text-sm-medium text-ink-gray-7">{{ __("Want your own space too?") }}</p>
				<p class="text-sm text-ink-gray-5">
					{{ __("Run events outside {0}. Your team access stays the same.", [team.team_name]) }}
				</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<Button
					v-for="option in ownSpaceButtons"
					:key="option.value"
					:variant="flow.choice === option.value ? 'subtle' : 'outline'"
					:icon-left="option.icon"
					:label="option.label"
					:aria-pressed="flow.choice === option.value"
					@click="toggle(option.value)"
				/>
			</div>
		</div>
		<ErrorMessage :message="personalTeamError" />
	</div>
</template>

<style scoped>
.byline {
	animation: byline-rise 260ms cubic-bezier(0.23, 1, 0.32, 1) both;
}
@keyframes byline-rise {
	from {
		opacity: 0;
		transform: translateY(4px);
	}
}
@media (prefers-reduced-motion: reduce) {
	.byline {
		animation: none;
	}
}
</style>
