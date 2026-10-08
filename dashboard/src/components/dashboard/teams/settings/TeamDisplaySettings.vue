<script setup lang="ts">
import { Avatar, Button, Divider, Dropdown, SettingsRow, Textarea, TextInput } from "frappe-ui"
import { computed } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import PrefixedInput from "@/components/common/PrefixedInput.vue"
import EventLinks from "@/components/dashboard/events/EventLinks.vue"
import type { TeamSettings } from "@/composables/useTeamSettings"

const props = defineProps<{ settings: TeamSettings }>()
const form = computed(() => props.settings.form)

const VISIBILITY = [
	{
		published: true,
		label: "Public",
		icon: "lucide-globe",
		description: "Anyone with the link can see the team page and its published events.",
	},
	{
		published: false,
		label: "Private",
		icon: "lucide-lock",
		description: "Only members can see the team. Its page link shows not found.",
	},
]
const visibility = computed(() =>
	VISIBILITY.find((option) => option.published === form.value.is_published)!,
)
const visibilityOptions = computed(() =>
	VISIBILITY.map((option) => ({
		label: __(option.label),
		icon: option.icon,
		description: __(option.description),
		selected: option.published === form.value.is_published,
		onClick: () => (form.value.is_published = option.published),
	})),
)

// The host the dashboard is served from, so the field reads as the address it will be.
const urlPrefix = `${window.location.hostname}/community/`
</script>

<template>
	<div class="space-y-8">
		<div class="space-y-6">
			<AvatarUploader
				v-if="settings.canManage"
				v-model="form.logo"
				shape="square"
				:label="form.team_name"
				:title="__('Team logo')"
				:description="__('Shown wherever the team appears')"
			/>
			<Avatar
				v-else
				shape="square"
				size="3xl"
				:image="form.logo ?? undefined"
				:label="form.team_name"
			/>

			<div class="space-y-1">
				<!-- Ghost variants: no border, so the pair reads as the team's headline and subtitle. -->
				<TextInput
					v-model="form.team_name"
					variant="ghost"
					:maxlength="140"
					:disabled="!settings.canManage"
					:aria-label="__('Team name')"
					:placeholder="__('Name your team')"
					class="[&_input]:!h-auto [&_input]:!px-0 [&_input]:!text-4xl [&_input]:!font-semibold [&_input]:!text-ink-gray-9"
				/>
				<Textarea
					v-model="form.short_description"
					variant="ghost"
					:rows="2"
					:disabled="!settings.canEditPage"
					:aria-label="__('Short description')"
					:placeholder="__('Add a short description')"
					class="resize-none !border-0 bg-transparent !px-0 text-ink-gray-6"
				/>
			</div>
		</div>

		<Divider />

		<section class="space-y-4">
			<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Access") }}</h2>
			<div class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 px-4">
				<SettingsRow :title="__('Visibility')" :description="__('Who can see the team page.')">
					<Dropdown :options="visibilityOptions" align="end" :disabled="!settings.canEditPage">
						<Button
							:label="__(visibility.label)"
							:icon-left="visibility.icon"
							icon-right="lucide-chevron-down"
							:disabled="!settings.canEditPage"
						/>
					</Dropdown>
				</SettingsRow>
				<div class="pb-3.5">
					<SettingsRow
						:title="__('Public URL')"
						:description="__('Where the team page lives. Changing it moves the page.')"
					/>
					<PrefixedInput
						v-model="form.slug"
						:prefix="urlPrefix"
						:label="__('Public URL')"
						:placeholder="__('your-team')"
						:disabled="!settings.canEditPage"
					/>
				</div>
			</div>
		</section>

		<EventLinks
			v-if="settings.canEditPage"
			heading-class="text-xl font-semibold text-ink-gray-8"
			v-model="form.links"
			:hint="__('Website, forum, repository — wherever people can find the team.')"
		/>
	</div>
</template>
