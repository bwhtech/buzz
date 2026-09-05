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
	<Transition name="view" mode="out-in">
		<ManageTeamPanel
			v-if="managing"
			:team="managing.name"
			:team-name="managing.team_name"
			@back="managing = null"
		/>

		<div v-else class="flex min-h-0 flex-1 flex-col">
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
									class="group w-full border-b py-3 text-left transition-[background-color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-surface-gray-1 active:scale-[0.99] focus-visible:outline-none focus-visible:focus-ring motion-reduce:active:scale-100"
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

									<span
										class="lucide-chevron-right size-4 text-ink-gray-5 transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:translate-x-0.5 motion-reduce:group-hover:translate-x-0"
										aria-hidden="true"
									/>
								</button>
							</li>
						</ul>
					</div>
				</div>
			</SettingsBody>
		</div>
	</Transition>
</template>

<style scoped>
.view-enter-active,
.view-leave-active {
	transition:
		opacity 120ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}

.view-enter-from {
	opacity: 0;
	transform: translateX(4px);
}

.view-leave-to {
	opacity: 0;
	transform: translateX(-4px);
}

@media (prefers-reduced-motion: reduce) {
	.view-enter-from,
	.view-leave-to {
		transform: none;
	}
}
</style>
