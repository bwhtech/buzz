<script setup lang="ts">
import { Avatar, Button, Divider, SettingsRow, Textarea } from "frappe-ui"
import { computed } from "vue"

import type { TeamSettings } from "@/composables/useTeamSettings"
import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { profileUrl } from "@/utils/teamUrl"

const props = defineProps<{ settings: TeamSettings }>()
const form = computed(() => props.settings.form)
const pageUrl = computed(() => {
	const username = userResource.data?.username
	return username ? profileUrl(username) : null
})
</script>

<template>
	<div class="flex flex-col gap-6">
		<Avatar size="3xl" :image="session.userImage ?? undefined" :label="session.fullName" />
		<div class="space-y-1">
			<h1 class="text-4xl font-semibold text-ink-gray-9 max-md:text-6xl">
				{{ session.fullName }}
			</h1>
			<p class="text-p-sm text-ink-gray-5">
				{{ __("Your name and photo come from your account.") }}
			</p>
			<Textarea
				v-model="form.short_description"
				variant="ghost"
				:rows="2"
				:aria-label="__('Short description')"
				:placeholder="__('Add a line about yourself')"
				class="resize-none !border-0 bg-transparent !px-0 text-ink-gray-6"
			/>
		</div>
	</div>

	<Divider />

	<section class="space-y-4">
		<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Profile page") }}</h2>
		<div class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 px-4">
			<SettingsRow
				:title="__('Public URL')"
				:description="__('Lists your published events. It goes live once you publish one.')"
			>
				<Button
					v-if="pageUrl"
					variant="ghost"
					:label="pageUrl.replace(/^https?:\/\//, '')"
					icon-right="lucide-arrow-up-right"
					:href="pageUrl"
				/>
			</SettingsRow>
			<SettingsRow
				:title="__('Team page and visibility')"
				:description="
					__(
						'A personal calendar has no team page of its own. Create a community for a public page at its own URL.',
					)
				"
			>
				<Button :label="__('Create a community')" href="/community?create" />
			</SettingsRow>
		</div>
	</section>
</template>
