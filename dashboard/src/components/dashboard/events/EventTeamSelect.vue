<script setup lang="ts">
import { Avatar, Button, Combobox } from "frappe-ui"
import { computed, watchEffect } from "vue"

import { session } from "@/data/session"
import {
	currentTeam,
	personalTeamsEnabled,
	selectPersonalTeam,
	selectTeam,
	teams,
	teamsLoaded,
} from "@/data/teams"
import { NEW_PERSONAL_TEAM, eventTeamOptions } from "@/utils/eventTeamOptions"

const options = computed(() =>
	eventTeamOptions(teams.value, {
		personalTeamsEnabled,
		personalLabel: __("{0} (You)", [session.fullName]),
	}).map(({ value, label }) => {
		const team = teams.value.find((row) => row.name === value)
		const isPersonal = value === NEW_PERSONAL_TEAM || Boolean(team?.is_personal)
		const memberCount = team?.members.length ?? 0
		return {
			value,
			label,
			description: isPersonal
				? session.user
				: memberCount === 1
					? __("1 member")
					: __("{0} members", [memberCount]),
			image: (isPersonal ? session.userImage : team?.logo) ?? undefined,
		}
	}),
)

const selectedTeam = computed({
	get: () => currentTeam.value?.name ?? null,
	set: (value) =>
		value === NEW_PERSONAL_TEAM ? selectPersonalTeam() : value && selectTeam(String(value)),
})
const selectedOption = computed(() =>
	options.value.find((option) => option.value === selectedTeam.value),
)

// Someone with no team came here to host, and Personal is all they can host as.
watchEffect(() => {
	if (teamsLoaded.value && !teams.value.length && personalTeamsEnabled) selectPersonalTeam()
})
</script>

<template>
	<div v-if="selectedOption" class="space-y-2">
		<div class="flex items-center gap-3">
			<span class="text-base text-ink-gray-5">{{ __("Hosted by") }}</span>
			<Combobox
				v-model="selectedTeam"
				:options="options"
				:disabled="options.length < 2"
				:placeholder="__('Search teams')"
			>
				<template #trigger>
					<Button
						variant="outline"
						class="rounded-full transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
						:label="selectedOption.label"
					>
						<template #prefix>
							<Avatar size="sm" :image="selectedOption.image" :label="selectedOption.label" />
						</template>
						<template v-if="options.length > 1" #suffix>
							<span class="lucide-chevron-down size-4 text-ink-gray-5" aria-hidden="true" />
						</template>
					</Button>
				</template>
				<template #item-prefix="{ item }">
					<Avatar shape="square" size="md" :image="item.image" :label="item.label" />
				</template>
			</Combobox>
		</div>
		<p v-if="currentTeam?.is_personal" class="text-p-sm text-ink-gray-5">
			{{ __("Shows on your profile. Only you can edit it") }}
		</p>
	</div>
</template>
