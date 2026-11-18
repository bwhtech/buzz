<script setup lang="ts">
import { Avatar, Combobox } from "frappe-ui"
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
	<!-- A sentence at the top of the form, so the host is read before anything is typed:
	     events made under the wrong team are the mistake this guards against. -->
	<div v-if="selectedOption" class="space-y-2">
		<div
			class="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-lg font-semibold tracking-tight md:text-[22px]"
		>
			<span class="text-ink-gray-5">{{ __("New event for") }}</span>
			<Combobox
				v-model="selectedTeam"
				:options="options"
				:disabled="options.length < 2"
				:placeholder="__('Search teams')"
			>
				<template #trigger>
					<button
						type="button"
						class="host -my-0.5 inline-flex min-w-0 items-center gap-2 rounded-4 py-0.5 pl-0.5 pr-1.5 text-ink-gray-9 aria-expanded:bg-surface-gray-3 disabled:cursor-default"
						:disabled="options.length < 2"
					>
						<Avatar size="md" :image="selectedOption.image" :label="selectedOption.label" />
						<span class="truncate">{{ selectedOption.label }}</span>
						<span
							v-if="options.length > 1"
							class="lucide-chevron-down size-[18px] shrink-0 text-ink-gray-5"
							aria-hidden="true"
						/>
					</button>
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

<style scoped>
.host {
	text-decoration: underline dotted var(--outline-gray-4);
	text-decoration-thickness: 2px;
	text-underline-offset: 6px;
	transition:
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease;
}
.host:not(:disabled):active {
	transform: scale(0.97);
}
@media (hover: hover) and (pointer: fine) {
	.host:not(:disabled):hover {
		background: var(--surface-gray-2);
	}
}
@media (prefers-reduced-motion: reduce) {
	.host:active {
		transform: none;
	}
}
</style>
