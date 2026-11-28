<script setup lang="ts">
import { ErrorMessage, FormLabel, TextInput, Textarea } from "frappe-ui"
import { ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"
import { slugify } from "@/utils/slug"
import { SHORT_DESCRIPTION_MAX_LENGTH } from "@/utils/textLimits"

import { checkCommunitySlug, communityError, flow, saveCommunity } from "./useOnboarding"

const community = flow.community
const availability = ref<Availability | null>(null)

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
	Boolean(community.slug.trim()) &&
	(community.slug === community.savedSlug || Boolean(availability.value?.available))

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
			icon="lucide-upload"
			:title="__('Community logo')"
			:description="__('Optional. A square image works best.')"
		/>
		<TextInput
			v-model="community.team_name"
			:label="__('Community name')"
			:placeholder="__('Weekend Builders Club')"
			required
			autofocus
		/>
		<div class="flex flex-col gap-1.5">
			<FormLabel :label="__('Community page link')" required />
			<SlugInput
				v-model="community.slug"
				v-model:availability="availability"
				prefix="community/"
				:label="__('Community page link')"
				placeholder="weekend-builders-club"
				:saved-slug="community.savedSlug"
				:check="checkCommunitySlug"
			/>
			<p class="text-sm text-ink-gray-5">
				{{ __("Your public page, where people find your events.") }}
			</p>
		</div>
		<Textarea
			v-model="community.short_description"
			:label="__('Short description')"
			:placeholder="__('What you host, and who it is for')"
			:rows="2"
			:maxlength="SHORT_DESCRIPTION_MAX_LENGTH"
		/>
		<ErrorMessage :message="communityError" />
	</div>
</template>
