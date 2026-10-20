<script setup lang="ts">
import { Avatar, Button, Divider, Dropdown, SettingsRow, Textarea, TextInput } from "frappe-ui"
import { computed, ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"
import EventLinks from "@/components/dashboard/events/EventLinks.vue"
import type { TeamSettings } from "@/composables/useTeamSettings"
import { checkTeamSlug } from "@/data/teams"

const props = defineProps<{ settings: TeamSettings }>()
const form = computed(() => props.settings.form)

// Short enough that the menu fits a phone: frappe-ui sizes it to the longest line.
const VISIBILITY = [
	{
		published: true,
		label: "Public",
		icon: "lucide-globe",
		description: "Anyone with the link can see it.",
	},
	{
		published: false,
		label: "Private",
		icon: "lucide-lock",
		description: "Only team members can see it.",
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

const urlPrefix = `${window.location.hostname}/community/`

const availability = ref<Availability | null>(null)
const checkSlug = (slug: string) =>
	checkTeamSlug.submit({ team: props.settings.overview.data!.name, slug })

watch(availability, (answer) => (props.settings.slugTaken = Boolean(answer) && !answer?.available))
</script>

<template>
	<div class="space-y-8">
		<!-- gap, not space-y: the uploader leads with a hidden file input, which space-y
		     counts as the first item and pushes the logo down. -->
		<div class="flex flex-col gap-6">
			<AvatarUploader
				v-if="settings.canManage"
				v-model="form.logo"
				shape="square"
				size="lg"
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
				<TextInput
					v-model="form.team_name"
					variant="ghost"
					:maxlength="140"
					:disabled="!settings.canManage"
					:aria-label="__('Team name')"
					:placeholder="__('Name your team')"
					class="[&_input]:!h-auto [&_input]:!px-0 [&_input]:!text-4xl max-md:[&_input]:!text-6xl max-md:[&_input]:!font-semibold [&_input]:!font-semibold [&_input]:!text-ink-gray-9"
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
				<div class="pb-4.5">
					<SettingsRow
						:title="__('Public URL')"
						:description="__('Where the team page lives. Changing it moves the page.')"
					/>
					<SlugInput
						v-model="form.slug"
						v-model:availability="availability"
						:prefix="urlPrefix"
						:label="__('Public URL')"
						:placeholder="__('your-team')"
						:disabled="!settings.canEditPage"
						:saved-slug="settings.overview.data?.slug"
						:check="checkSlug"
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
