<script setup lang="ts">
import { SettingsRow, Switch } from "frappe-ui"

import type { TeamSettings } from "@/composables/useTeamSettings"

defineProps<{ settings: TeamSettings }>()
</script>

<template>
	<section class="space-y-4">
		<h2 class="text-base-semibold text-ink-gray-9">{{ __("Community") }}</h2>
		<div class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 px-4">
			<SettingsRow
				:title="__('Community submissions')"
				:description="
					settings.form.is_published
						? __(
								'Let other teams submit their events to be listed on your page. You approve each one.',
							)
						: __('Make the team public on the Display tab to accept submissions from other teams.')
				"
			>
				<Switch
					v-model="settings.form.is_a_community"
					:disabled="!settings.canEditPage || !settings.form.is_published"
					:aria-label="__('Community submissions')"
				/>
			</SettingsRow>
		</div>
	</section>
</template>
