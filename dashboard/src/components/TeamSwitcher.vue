<script setup lang="ts">
import { Avatar, Badge, KeyboardShortcut, Popover } from "frappe-ui"
import { computed, ref } from "vue"

import { currentTeam, selectTeam, teams } from "@/data/teams"
import type { TeamOption } from "@/types"

const query = ref("")

const matchingTeams = computed(() =>
	teams.value.filter((team) =>
		team.team_name.toLowerCase().includes(query.value.trim().toLowerCase()),
	),
)

function switchTeam(team: TeamOption, closePanel: () => void) {
	selectTeam(team.name)
	closePanel()
}
</script>

<template>
	<Popover side="bottom" align="start" @close="query = ''">
		<template #trigger="{ open: isOpen }">
			<button
				class="flex h-10 w-full items-center gap-2 rounded-4 px-1.5 transition-colors duration-150 hover:bg-surface-gray-2 active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="{ 'bg-surface-gray-3': isOpen }"
			>
				<Avatar
					:image="currentTeam?.logo ?? undefined"
					:label="currentTeam?.team_name"
					size="lg"
					shape="square"
				/>
				<span class="flex-1 truncate text-left text-base text-ink-gray-8">
					{{ currentTeam?.team_name }}
				</span>
				<Badge v-if="currentTeam" theme="gray" variant="subtle">
					{{ currentTeam.team_role }}
				</Badge>
				<span class="lucide-chevrons-up-down size-4 shrink-0 text-ink-gray-5" />
			</button>
		</template>

		<template #default="{ close }">
			<div class="w-[22rem]">
				<div class="flex items-center gap-2 border-b px-3 py-2.5">
					<input
						v-model="query"
						aria-label="Find team"
						placeholder="Find team..."
						class="min-w-0 flex-1 bg-transparent text-base text-ink-gray-8 placeholder-ink-gray-4 focus:outline-none"
					/>
					<KeyboardShortcut bg combo="Esc" />
				</div>

				<div class="max-h-72 overflow-y-auto overscroll-contain p-1">
					<button
						v-for="team in matchingTeams"
						:key="team.name"
						class="flex h-9 w-full items-center gap-2 rounded-4 px-1.5 text-base text-ink-gray-8 transition-colors duration-150 hover:bg-surface-gray-2 active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
						@click="switchTeam(team, close)"
					>
						<Avatar
							:image="team.logo ?? undefined"
							:label="team.team_name"
							size="sm"
							shape="square"
						/>
						<span class="flex-1 truncate text-left">{{ team.team_name }}</span>
						<Badge theme="gray" variant="subtle">{{ team.team_role }}</Badge>
						<span
							v-if="team.name === currentTeam?.name"
							class="lucide-check size-4 shrink-0 text-ink-gray-7"
						/>
					</button>

					<div
						v-if="!matchingTeams.length"
						class="flex h-32 flex-col items-center justify-center gap-3 px-6 text-ink-gray-5"
					>
						<span
							class="lucide-users grid size-5 place-items-center rounded-5 border border-outline-gray-2"
						/>
						<p class="text-center text-sm">
							Teams you create and join appear here for quick context switching.
						</p>
					</div>
				</div>

				<button
					class="flex w-full items-center gap-3 border-t px-3 py-2.5 text-left transition-colors duration-150 hover:bg-surface-gray-2 active:bg-surface-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				>
					<span class="lucide-plus size-4 shrink-0 text-ink-gray-6" />
					<div class="min-w-0">
						<div class="text-base text-ink-gray-8">Create team</div>
						<div class="text-sm text-ink-gray-5">Collaborate with others in a shared workspace</div>
					</div>
				</button>
			</div>
		</template>
	</Popover>
</template>
