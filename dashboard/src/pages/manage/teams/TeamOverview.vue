<script setup lang="ts">
import { Avatar, Button, ErrorMessage, LoadingText } from "frappe-ui"
import { computed } from "vue"

import EventCard from "@/components/dashboard/events/EventCard.vue"
import TeamHero from "@/components/dashboard/teams/TeamHero.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useMyEvents } from "@/data/events"
import { currentTeam, useTeamOverview } from "@/data/teams"

const PREVIEW_LIMIT = 3
const AVATAR_LIMIT = 5

const teamOverview = useTeamOverview()

const team = computed(() => teamOverview.data)

const errorMessage = computed(() => teamOverview.error?.message)

const myEvents = useMyEvents()

// Reuses the feed the Events page already loads; only this team's rows are shown.
const upcoming = computed(() =>
	(myEvents.data?.upcoming || []).filter((event) => event.team === currentTeam.value?.name),
)

const preview = computed(() => upcoming.value.slice(0, PREVIEW_LIMIT))

// A large team would otherwise run the avatar row past the card.
const shownMembers = computed(() => (team.value?.members || []).slice(0, AVATAR_LIMIT))

const hiddenMemberCount = computed(() =>
	Math.max((team.value?.members.length || 0) - AVATAR_LIMIT, 0),
)
</script>

<template>
	<TeamPageHeader title="Home" />

	<div class="m-auto max-w-[1000px] w-full py-8 px-4 space-y-8">
		<LoadingText v-if="teamOverview.loading" text="Loading team…" />

		<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

		<template v-else-if="team">
			<TeamHero :team="team" />

			<div class="flex flex-col gap-4 md:flex-row">
				<section class="md:w-3/5 space-y-3">
					<h2 class="text-lg font-semibold text-ink-gray-8">Upcoming events</h2>

					<p v-if="!preview.length" class="text-base text-ink-gray-5">No upcoming events.</p>

					<!-- The list fades out to hint that the preview is cut short. -->
					<div v-else class="relative">
						<div class="space-y-3">
							<EventCard v-for="event in preview" :key="event.name" :event="event" show-date />
						</div>
						<div
							v-if="upcoming.length > PREVIEW_LIMIT"
							class="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-surface-elevation-1 to-transparent"
						/>
					</div>

					<Button
						variant="ghost"
						label="See all events"
						class="w-fit"
						:route="{ name: 'team-events' }"
					/>
				</section>

				<section class="md:w-2/5 h-fit space-y-3 rounded-8 bg-surface-gray-1 p-4">
					<h2 class="text-lg font-semibold text-ink-gray-8">
						Team members
						<span class="text-ink-gray-5">({{ team.members.length }})</span>
					</h2>

					<div class="flex -space-x-2">
						<Avatar
							v-for="member in shownMembers"
							:key="member.user"
							:image="member.user_image ?? undefined"
							:label="member.full_name ?? member.user"
							size="lg"
							class="border border-outline-gray-2"
						/>
						<Avatar v-if="hiddenMemberCount" size="lg" class="border border-outline-gray-2">
							<p class="text-sm">+{{ hiddenMemberCount }}</p>
						</Avatar>
					</div>

					<Button
						variant="ghost"
						label="Manage members"
						class="w-fit"
						:route="{ name: 'team-members' }"
					/>
				</section>
			</div>
		</template>
	</div>
</template>
