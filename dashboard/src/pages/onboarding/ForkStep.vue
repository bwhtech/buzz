<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import ForkIllustration from "./ForkIllustration.vue"
import {
	type Choice,
	flow,
	forkOptions,
	hostingOptions,
	personalTeamError,
	savePersonalTeam,
} from "./useOnboarding"

type Tile = { value: Choice; title: string; line: string; example: string }

function tileFor(choice: Choice): Tile {
	if (choice === "personal")
		return {
			value: choice,
			title: __("Host as myself"),
			line: __("Run events under your own name and profile."),
			example: __("Priya's weekend pottery workshops"),
		}
	if (choice === "community")
		return {
			value: choice,
			title: __("Create a community"),
			line: __("A shared page for a group that hosts together."),
			example: __("Bangalore JS Meetup"),
		}
	return {
		value: choice,
		title: __("Skip, I'm just attending"),
		line: __("Find events and keep your tickets in one place."),
		example: __("You can start hosting any time"),
	}
}

const tiles = computed(() => forkOptions.value.map(tileFor))
const isWide = (choice: Choice) => choice === "attendee" || hostingOptions.value.length === 1

defineExpose({
	canContinue: () => Boolean(flow.choice),
	save: savePersonalTeam,
})
</script>

<template>
	<div class="flex flex-col gap-4">
		<div class="grid gap-3 sm:grid-cols-2" role="radiogroup">
			<div
				v-for="tile in tiles"
				:key="tile.value"
				tabindex="0"
				role="radio"
				:aria-checked="flow.choice === tile.value"
				class="fork-card flex cursor-pointer flex-col overflow-hidden rounded-5 border bg-surface-elevation-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="[
					isWide(tile.value) && 'sm:col-span-2 sm:flex-row',
					flow.choice === tile.value
						? 'border-outline-gray-9 ring-1 ring-outline-gray-9'
						: 'border-outline-gray-2 hover:border-outline-gray-3',
				]"
				@click="flow.choice = tile.value"
				@keydown.space.self.prevent="flow.choice = tile.value"
			>
				<ForkIllustration
					:kind="tile.value"
					:active="flow.choice === tile.value"
					:class="isWide(tile.value) ? 'sm:h-auto sm:w-48 sm:shrink-0' : 'h-36'"
				/>
				<span
					class="flex flex-1 flex-col gap-1.5 p-5"
					:class="{ 'sm:justify-center': isWide(tile.value) }"
				>
					<span class="text-lg-semibold text-ink-gray-9">{{ tile.title }}</span>
					<span class="text-base text-ink-gray-6">{{ tile.line }}</span>
					<span class="text-sm text-ink-gray-4">{{ __("e.g. {0}", [tile.example]) }}</span>
				</span>
			</div>
		</div>
		<ErrorMessage :message="personalTeamError" />
	</div>
</template>

<style scoped>
.fork-card {
	transition:
		transform 160ms ease-out,
		border-color 150ms ease;
}
.fork-card:active {
	transform: scale(0.985);
}
</style>
