<script setup lang="ts">
import { Switch } from "frappe-ui"

import type { TeamSettings } from "@/composables/useTeamSettings"

defineProps<{ settings: TeamSettings }>()
</script>

<template>
	<section class="space-y-4">
		<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Community") }}</h2>
		<div class="rounded-6 border border-outline-gray-2 p-1">
			<Switch
				v-model="settings.form.accept_community_submissions"
				padded
				:label="__('Community submissions')"
				:description="
					settings.form.is_published
						? __(
								'Let other teams submit their events to be listed on your page. You approve each one.',
							)
						: __('Make the team public on the Display tab to accept submissions from other teams.')
				"
				:disabled="!settings.canEditPage || !settings.form.is_published"
			/>
		</div>
	</section>
</template>
