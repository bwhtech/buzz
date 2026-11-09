<script setup lang="ts">
import { ErrorMessage, TextInput, useCall } from "frappe-ui"
import { computed, ref } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"
import { userResource } from "@/data/user"

import { attempt, fullName, profile } from "./useOnboarding"

const availability = ref<Availability | null>(null)
const savedUsername = userResource.data?.username

const checkUsername = useCall<Availability, { username: string }>({
	url: "/api/v2/method/buzz.api.onboarding.check_username",
	immediate: false,
})
const saveProfile = useCall<null, typeof profile>({
	url: "/api/v2/method/buzz.api.onboarding.save_profile",
	method: "POST",
	immediate: false,
})

const usernameReady = computed(
	() => profile.username === savedUsername || Boolean(availability.value?.available),
)

defineExpose({
	canContinue: () => Boolean(profile.first_name.trim()) && usernameReady.value,
	// Resolves false on failure; the error renders below the form.
	save: async () => {
		if (!(await attempt(saveProfile.submit({ ...profile })))) return false
		await userResource.reload()
		return true
	},
})
</script>

<template>
	<div class="flex flex-col gap-5">
		<AvatarUploader
			v-model="profile.user_image"
			:label="fullName || '?'"
			:title="__('Profile photo')"
			:description="__('Optional. Your initials show until you add one.')"
		/>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<TextInput v-model="profile.first_name" :label="__('First name')" required autofocus />
			<TextInput v-model="profile.last_name" :label="__('Last name')" />
		</div>

		<div class="flex flex-col gap-1.5">
			<p class="text-xs text-ink-gray-5">{{ __("Username") }}</p>
			<SlugInput
				v-model="profile.username"
				v-model:availability="availability"
				prefix="@"
				:label="__('Username')"
				:saved-slug="savedUsername"
				:check="(username) => checkUsername.submit({ username })"
			/>
		</div>

		<ErrorMessage :message="saveProfile.error?.message" />
	</div>
</template>
