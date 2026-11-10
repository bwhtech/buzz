<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Avatar } from "frappe-ui"
import { computed } from "vue"

import EventCard from "./EventCard.vue"
import {
	type Scene,
	effectiveChoice,
	flow,
	fullName,
	hasDraft,
	invitedTeam,
	profile,
} from "./useOnboarding"

const props = defineProps<{ scene: Scene }>()

const crowd = ["A", "B", "C", "D", "E"]
const fanned = ["first", "second"]
const card = computed(() => {
	if (props.scene !== "done") return props.scene
	return hasDraft.value ? "event" : effectiveChoice.value
})
const cover = (seed: string) => ({ backgroundImage: bannerPattern(seed) })

// Communities and the invited team share one card; only the data differs.
const group = computed(() => {
	if (card.value === "team" && invitedTeam.value)
		return {
			name: invitedTeam.value.team_name,
			logo: invitedTeam.value.logo,
			line: __("You're a {0} here", [invitedTeam.value.team_role]),
			footer: __("{0} members", [invitedTeam.value.member_count]),
		}
	if (card.value === "community")
		return {
			name: flow.community.team_name,
			logo: flow.community.logo,
			line: flow.community.short_description,
			footer: __("Members join here"),
		}
	return null
})
</script>

<template>
	<EventCard v-if="card === 'event'" />

	<div v-else-if="card === 'attendee'" class="relative w-full max-w-xs">
		<div
			class="stack-behind absolute inset-x-4 -bottom-2 h-full rounded-5 border border-outline-gray-2 bg-surface-elevation-1"
		/>
		<article
			class="relative flex overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
		>
			<div class="w-20 shrink-0" :style="cover(profile.username || 'tickets')" />
			<div class="flex flex-1 flex-col gap-1 p-4">
				<p class="text-base-semibold text-ink-gray-9">{{ __("Your tickets") }}</p>
				<p class="text-sm text-ink-gray-5">{{ __("Every booking in one place") }}</p>
				<p class="mt-2 text-sm text-ink-gray-7">{{ fullName }}</p>
			</div>
			<div
				class="flex w-16 items-center justify-center border-l border-dashed border-outline-gray-3"
			>
				<div class="grid grid-cols-3 gap-0.5">
					<span
						v-for="cell in 9"
						:key="cell"
						class="size-2 rounded-[2px]"
						:class="cell % 3 === 1 || cell === 5 ? 'bg-surface-gray-7' : 'bg-surface-gray-3'"
					/>
				</div>
			</div>
		</article>
	</div>

	<div v-else class="relative w-full max-w-xs">
		<template v-if="card === 'personal'">
			<div
				v-for="(seed, index) in fanned"
				:key="seed"
				class="fan absolute inset-x-6 top-0 h-24 rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
				:style="{ '--index': index, ...cover(`${profile.username}-${seed}`) }"
			/>
		</template>
		<article
			class="relative overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
		>
			<div
				class="h-20"
				:style="cover(group ? group.name || 'community' : profile.username || 'profile')"
			/>
			<div class="-mt-8 flex flex-col gap-3 p-5">
				<Avatar
					v-if="group"
					size="3xl"
					shape="square"
					:image="group.logo || undefined"
					:label="group.name || '?'"
					style="box-shadow: 0 0 0 4px var(--surface-white)"
				/>
				<Avatar
					v-else
					size="3xl"
					:image="profile.user_image || undefined"
					:label="fullName || '?'"
					style="box-shadow: 0 0 0 4px var(--surface-white)"
				/>
				<div class="flex flex-col gap-1">
					<p class="text-lg-semibold text-ink-gray-9">
						{{ group ? group.name || __("Your community") : fullName || __("Your name") }}
					</p>
					<p class="line-clamp-2 text-sm text-ink-gray-5">
						{{
							group ? group.line || __("A short description shows here.") : `@${profile.username}`
						}}
					</p>
				</div>
				<div v-if="group" class="flex items-center gap-2">
					<div class="flex -space-x-1.5">
						<Avatar
							v-for="(initial, index) in crowd"
							:key="initial"
							size="sm"
							:label="initial"
							class="member"
							:style="{ '--index': index, boxShadow: '0 0 0 2px var(--surface-white)' }"
						/>
					</div>
					<span class="text-sm text-ink-gray-5">{{ group.footer }}</span>
				</div>
				<p v-else class="text-sm text-ink-gray-5">
					{{
						card === "personal"
							? __("Your upcoming events show here")
							: __("Hosts and guests see this page")
					}}
				</p>
			</div>
		</article>
	</div>
</template>

<style scoped>
/* Upcoming events fan out from behind the profile card, one after the other. */
.fan {
	transform-origin: bottom center;
	animation: fan-out 420ms cubic-bezier(0.23, 1, 0.32, 1) both;
	animation-delay: calc(120ms + var(--index) * 70ms);
	--angle: calc(-7deg + var(--index) * 14deg);
	transform: translateY(-58px) rotate(var(--angle));
}
@keyframes fan-out {
	from {
		transform: translateY(0) rotate(0deg);
		opacity: 0;
	}
}
.member {
	animation: member-in 260ms cubic-bezier(0.23, 1, 0.32, 1) both;
	animation-delay: calc(140ms + var(--index) * 45ms);
}
@keyframes member-in {
	from {
		opacity: 0;
		transform: translateX(-6px) scale(0.9);
	}
}
.stack-behind {
	animation: stack-in 320ms cubic-bezier(0.23, 1, 0.32, 1) 120ms both;
	transform: translateY(8px) scale(0.96);
}
@keyframes stack-in {
	from {
		transform: translateY(0) scale(0.96);
		opacity: 0;
	}
}
@media (prefers-reduced-motion: reduce) {
	.fan,
	.member,
	.stack-behind {
		animation-name: none;
	}
}
</style>
