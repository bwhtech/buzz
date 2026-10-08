<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import {
	Avatar,
	Button,
	Divider,
	Dropdown,
	LoadingText,
	SettingsRow,
	Textarea,
	TextInput,
} from "frappe-ui"
import { computed, ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import PrefixedInput from "@/components/common/PrefixedInput.vue"
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

type Availability = { available: boolean; message: string }
const availability = ref<Availability | null>(null)
const checking = ref(false)

const needsCheck = (slug: string) => {
	const team = props.settings.overview.data
	return Boolean(team && slug.trim() && slug !== team.slug)
}

watch(
	() => form.value.slug,
	(slug) => {
		availability.value = null
		checking.value = needsCheck(slug)
	},
)

watchDebounced(
	() => form.value.slug,
	async (slug) => {
		const team = props.settings.overview.data
		if (!team || !needsCheck(slug)) return
		// A failed check says nothing rather than spinning forever; the save still checks.
		const answer = await checkTeamSlug.submit({ team: team.name, slug }).catch(() => null)
		// A later keystroke may have overtaken this request while it was in flight.
		if (form.value.slug !== slug) return
		checking.value = false
		availability.value = answer
	},
	{ debounce: 400 },
)

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
					<PrefixedInput
						v-model="form.slug"
						:prefix="urlPrefix"
						:label="__('Public URL')"
						:placeholder="__('your-team')"
						:disabled="!settings.canEditPage"
					/>
					<Transition
						enter-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
						enter-from-class="opacity-0 -translate-y-0.5"
						leave-active-class="transition duration-100 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
						leave-to-class="opacity-0"
						mode="out-in"
					>
						<LoadingText
							v-if="checking"
							key="checking"
							class="pt-1.5 !text-sm"
							:text="__('Checking availability')"
						/>
						<p
							v-else-if="availability"
							key="answer"
							class="flex items-center gap-1 pt-1.5 text-sm"
							:class="availability.available ? 'text-ink-green-6' : 'text-ink-amber-7'"
						>
							<span
								class="size-3.5 shrink-0"
								:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
								aria-hidden="true"
							/>
							{{ availability.message }}
						</p>
					</Transition>
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
