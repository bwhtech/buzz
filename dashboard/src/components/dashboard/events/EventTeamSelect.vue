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

// The host as a row of chips, so the other teams are in view and the default reads as a
// choice rather than a fact: events made under the wrong team are the mistake this guards.
const VISIBLE_CHIPS = 3

const options = computed(() =>
	eventTeamOptions(teams.value, {
		personalTeamsEnabled,
		personalLabel: __("{0} (You)", [session.fullName]),
	}).map(({ value, label }) => {
		const team = teams.value.find((row) => row.name === value)
		const isPersonal = value === NEW_PERSONAL_TEAM || Boolean(team?.is_personal)
		return {
			value,
			label,
			isPersonal,
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

// A team picked from the search joins the chips, so the choice stays on screen.
const chips = computed(() => {
	const head = options.value.slice(0, VISIBLE_CHIPS)
	const picked = selectedOption.value
	return picked && !head.includes(picked) ? [...head, picked] : head
})
const otherOptions = computed(() => options.value.filter((option) => !chips.value.includes(option)))
const searchPick = computed({
	get: () => null,
	set: (value: string | null) => value && (selectedTeam.value = value),
})

// Someone with no team came here to host, and Personal is all they can host as.
watchEffect(() => {
	if (teamsLoaded.value && !teams.value.length && personalTeamsEnabled) selectPersonalTeam()
})
</script>

<template>
	<section v-if="selectedOption" class="space-y-2">
		<h2 class="text-sm font-medium text-ink-gray-6">{{ __("Host") }}</h2>
		<div class="flex flex-wrap gap-2">
			<Button
				v-for="option in chips"
				:key="option.value"
				size="md"
				class="max-w-full rounded-full"
				:variant="option.value === selectedTeam ? 'solid' : 'subtle'"
				:aria-pressed="option.value === selectedTeam"
				@click="selectedTeam = option.value"
			>
				<template #prefix>
					<Avatar size="xs" :image="option.image" :label="option.label" />
				</template>
				<span class="inline-block max-w-48 truncate align-bottom" :title="option.label">
					{{ option.label }}
				</span>
			</Button>
			<Combobox
				v-if="otherOptions.length"
				v-model="searchPick"
				:options="otherOptions"
				:placeholder="__('Search teams')"
			>
				<template #trigger>
					<Button
						size="md"
						variant="outline"
						icon-left="lucide-plus"
						class="rounded-full border-dashed"
						:label="__('{0} more', [otherOptions.length])"
					/>
				</template>
				<template #item-prefix="{ item }">
					<Avatar shape="square" size="md" :image="item.image" :label="item.label" />
				</template>
			</Combobox>
		</div>
		<p class="text-p-sm text-ink-gray-5">
			{{
				selectedOption.isPersonal
					? __("Hosted by you. It shows on your profile and only you can edit it.")
					: __("Hosted by {0}. Its members can manage this event.", [selectedOption.label])
			}}
		</p>
	</section>
</template>
