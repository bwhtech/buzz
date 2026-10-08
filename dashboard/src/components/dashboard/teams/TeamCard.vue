<script setup lang="ts">
import { Avatar } from "frappe-ui"
import { computed } from "vue"

import UserGroup from "@/components/common/UserGroup.vue"
import type { TeamOption } from "@/types"

const props = defineProps<{ team: TeamOption }>()

const upcomingEvents = computed(() => {
	const count = props.team.upcoming_event_count
	if (!count) return __("No upcoming events")
	return count === 1 ? __("1 upcoming event") : __("{0} upcoming events", [String(count)])
})
</script>

<template>
	<router-link
		:to="`/manage/teams/${team.name}`"
		class="flex flex-col gap-4 rounded-5 border border-outline-gray-2 p-5 transition-[background-color,border-color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] hover:border-outline-gray-3 hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:focus-ring active:scale-[0.99] motion-reduce:active:scale-100"
	>
		<Avatar shape="square" size="3xl" :image="team.logo ?? undefined" :label="team.team_name" />

		<div class="flex flex-col gap-1">
			<h3 class="truncate text-lg font-semibold text-ink-gray-9" :title="team.team_name">
				{{ team.team_name }}
			</h3>
			<p class="flex items-center gap-1.5 text-sm text-ink-gray-5">
				<span>{{ __(team.team_role) }}</span>
				<span class="text-ink-gray-4">·</span>
				<span>{{ upcomingEvents }}</span>
			</p>
			<p v-if="team.short_description" class="line-clamp-2 text-p-base text-ink-gray-6">
				{{ team.short_description }}
			</p>
		</div>

		<UserGroup class="mt-auto pt-4" :users="team.members" />
	</router-link>
</template>
