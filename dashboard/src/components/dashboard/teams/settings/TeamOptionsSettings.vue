<script setup lang="ts">
import { Switch, Tooltip } from "frappe-ui"
import { computed } from "vue"

import type { TeamSettings } from "@/composables/useTeamSettings"
import { isPersonalTeam } from "@/data/teams"

const props = defineProps<{ settings: TeamSettings }>()

const isPersonal = computed(() => isPersonalTeam(props.settings.overview.data!.name))
const description = computed(() => {
	if (isPersonal.value) return __("Not available on a personal calendar.")
	return props.settings.form.is_published
		? __("Let other teams submit their events to be listed on your page. You approve each one.")
		: __("Make the team public on the Display tab to accept submissions from other teams.")
})
</script>

<template>
	<section class="space-y-4">
		<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Community") }}</h2>
		<Tooltip
			:text="
				isPersonal
					? __(
							'Personal calendars can\'t take submissions. Create a community to list other teams\' events.',
						)
					: undefined
			"
		>
			<div class="rounded-6 border border-outline-gray-2 p-1">
				<Switch
					v-model="settings.form.accept_community_submissions"
					padded
					:label="__('Community submissions')"
					:description="description"
					:disabled="isPersonal || !settings.canEditPage || !settings.form.is_published"
				/>
			</div>
		</Tooltip>
	</section>
</template>
