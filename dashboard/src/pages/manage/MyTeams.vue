<script setup lang="ts">
import { Icon, Skeleton } from "frappe-ui"
import { computed } from "vue"

import SectionHeader from "@/components/common/SectionHeader.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import TeamCard from "@/components/dashboard/teams/TeamCard.vue"
import { teams, teamsLoaded } from "@/data/teams"

const sections = computed(() =>
	[
		{ title: "Communities", teams: teams.value.filter((team) => team.is_a_community) },
		{ title: "Teams", teams: teams.value.filter((team) => !team.is_a_community) },
	].filter((section) => section.teams.length),
)
</script>

<template>
	<CreateEventHeader title="Teams" />

	<div class="m-auto w-full max-w-[800px] space-y-8 p-4 max-md:pb-24">
		<header class="hidden items-center gap-3 md:flex">
			<div class="rounded-4 bg-surface-gray-3 p-2">
				<Icon name="lucide-users" class="size-6" />
			</div>
			<h1 class="text-4xl font-semibold">Teams</h1>
		</header>

		<div
			v-if="!teamsLoaded"
			class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
			aria-busy="true"
		>
			<span class="sr-only">Loading teams…</span>
			<Skeleton v-for="card in 3" :key="card" class="h-48 rounded-5" />
		</div>

		<template v-else>
			<section v-for="section in sections" :key="section.title" class="space-y-4">
				<SectionHeader :title="__(section.title)" :count="section.teams.length" />
				<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
					<TeamCard
						v-for="(team, index) in section.teams"
						:key="team.name"
						:team="team"
						class="fade-up-in [animation-duration:200ms] [animation-timing-function:cubic-bezier(0.23,1,0.32,1)]"
						:style="{ animationDelay: `${index * 40}ms` }"
					/>
				</div>
			</section>
		</template>
	</div>
</template>
