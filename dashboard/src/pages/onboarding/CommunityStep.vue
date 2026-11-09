<script setup lang="ts">
import { ErrorMessage, TextInput, Textarea } from "frappe-ui"
import { ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"

import { checkCommunitySlug, communityError, flow, saveCommunity } from "./useOnboarding"

const community = flow.community
const availability = ref<Availability | null>(null)

const slugify = (text: string) =>
	text
		.toLowerCase()
		.trim()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-|-$/g, "")

watch(
	() => community.team_name,
	(name) => {
		if (!community.slugEdited) community.slug = slugify(name)
	},
)
watch(
	() => community.slug,
	(slug) => {
		if (slug !== slugify(community.team_name)) community.slugEdited = true
	},
)

const slugReady = () =>
	community.slug === community.savedSlug || Boolean(availability.value?.available)

defineExpose({
	canContinue: () => Boolean(community.team_name.trim()) && slugReady(),
	save: saveCommunity,
})
</script>

<template>
	<div class="flex flex-col gap-5">
		<AvatarUploader
			v-model="community.logo"
			shape="square"
			:label="community.team_name || '?'"
			:title="__('Community logo')"
			:description="__('Optional. Your initials show until you add one.')"
		/>
		<TextInput
			v-model="community.team_name"
			:label="__('Community name')"
			:placeholder="__('Bangalore JS Meetup')"
			required
			autofocus
		/>
		<div class="flex flex-col gap-1.5">
			<p class="text-xs text-ink-gray-5">{{ __("Page address") }}</p>
			<SlugInput
				v-model="community.slug"
				v-model:availability="availability"
				prefix="community/"
				:label="__('Page address')"
				:saved-slug="community.savedSlug"
				:check="checkCommunitySlug"
			/>
		</div>
		<Textarea
			v-model="community.short_description"
			:label="__('Short description')"
			:placeholder="__('Monthly talks and hack nights for JavaScript folks in Bangalore.')"
			:rows="2"
		/>
		<p class="flex items-center gap-2 text-sm text-ink-gray-5">
			<span class="size-1.5 rounded-full bg-surface-green-3" />
			{{ __("Your community page goes live when you continue.") }}
		</p>
		<ErrorMessage :message="communityError" />
	</div>
</template>
