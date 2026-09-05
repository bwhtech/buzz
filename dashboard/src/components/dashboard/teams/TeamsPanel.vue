<script setup lang="ts">
import { Avatar, FormControl, SettingsBody, SettingsHeader } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import UserGroup from "@/components/common/UserGroup.vue"
import ManageTeamPanel from "@/components/dashboard/teams/ManageTeamPanel.vue"
import { teams } from "@/data/teams"
import type { TeamOption } from "@/types"

const COLUMNS = "grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_1.5rem] items-center gap-4"

const search = ref("")
const managing = ref<TeamOption | null>(null)

const filtered = computed(() => {
	const query = search.value.trim().toLowerCase()
	return teams.value.filter((team) => team.team_name.toLowerCase().includes(query))
})
</script>

<template>
	<ManageTeamPanel
		v-if="managing"
		:team="managing.name"
		:team-name="managing.team_name"
		@back="managing = null"
	/>

	<template v-else>
		<SettingsHeader :title="__('Your Teams')" />

		<SettingsBody>
			<div class="flex flex-col gap-4 pt-6">
				<FormControl
					v-model="search"
					type="text"
					class="max-w-xs"
					:placeholder="__('Search teams')"
					:aria-label="__('Search teams')"
				>
					<template #prefix>
						<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</FormControl>

				<EmptyState v-if="!filtered.length" :title="__('No teams found')" />

				<div v-else>
					<div :class="COLUMNS" class="border-b pb-2 text-sm text-ink-gray-5">
						<span>{{ __("Team") }}</span>
						<span>{{ __("Members") }}</span>
					</div>

					<ul :aria-label="__('Your teams')">
						<li v-for="team in filtered" :key="team.name">
							<button
								type="button"
								:class="COLUMNS"
								class="w-full border-b py-3 text-left transition-colors duration-150 hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:focus-ring"
								@click="managing = team"
							>
								<div class="flex min-w-0 items-center gap-3">
									<Avatar
										shape="square"
										size="lg"
										:image="team.logo ?? undefined"
										:label="team.team_name"
									/>
									<span class="truncate text-base font-medium text-ink-gray-8">{{
										team.team_name
									}}</span>
								</div>

								<UserGroup :users="team.members" />

								<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
							</button>
						</li>
					</ul>
				</div>
			</div>
		</SettingsBody>
	</template>
</template>
