<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Badge } from "frappe-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"

import { startOpening } from "@/composables/useWorkspaceOpening"
import { currentTeam, selectPersonalTeam, upcomingEventsLabel } from "@/data/teams"
import { userResource } from "@/data/user"
import type { TeamOption } from "@/types"

// No team yet until the user first picks it: a click creates it.
const props = defineProps<{ team: TeamOption | null }>()

const router = useRouter()
const username = computed(() => userResource.data?.username)
const profileUrl = computed(() => `${window.location.host}/u/${username.value}`)
const pattern = {
	backgroundImage: bannerPattern("personal", {
		line: "var(--outline-gray-1)",
		surface: "transparent",
	}),
	maskImage: "linear-gradient(to top right, transparent 15%, black 85%)",
}

async function create() {
	await selectPersonalTeam()
	if (currentTeam.value?.is_personal) router.push(`/manage/communities/${currentTeam.value.name}`)
}

function open(event: MouseEvent) {
	if (!props.team) {
		event.preventDefault()
		return create()
	}
	// A modified click opens a new tab, leaving this page where it is.
	if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
	startOpening(__("Personal"))
}
</script>

<template>
	<router-link
		:to="team ? `/manage/communities/${team.name}` : $route.fullPath"
		class="relative flex flex-col gap-4 overflow-hidden rounded-5 border border-outline-gray-2 p-5 transition-[background-color,border-color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] hover:border-outline-gray-3 hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:focus-ring active:scale-[0.99] motion-reduce:active:scale-100"
		@click="open"
	>
		<div class="absolute inset-0" :style="pattern" aria-hidden="true" />

		<div class="relative flex items-start justify-between">
			<div class="grid size-14 place-items-center rounded-4 bg-surface-gray-2">
				<span class="lucide-calendar-heart size-6 text-ink-gray-8" aria-hidden="true" />
			</div>
			<Badge :label="__('Only you')">
				<template #prefix>
					<span class="lucide-lock size-3" aria-hidden="true" />
				</template>
			</Badge>
		</div>

		<div class="relative flex flex-col gap-1">
			<h3 class="text-lg font-semibold text-ink-gray-9">{{ __("Personal") }}</h3>
			<p class="text-sm text-ink-gray-5">
				{{ __("Your calendar") }} · {{ upcomingEventsLabel(team?.upcoming_event_count ?? 0) }}
			</p>
		</div>

		<p
			v-if="username"
			class="relative mt-auto flex items-center gap-1.5 pt-4 text-sm text-ink-gray-5"
		>
			<span class="lucide-calendar size-4 shrink-0" aria-hidden="true" />
			<span class="truncate">{{ profileUrl }}</span>
		</p>
	</router-link>
</template>
