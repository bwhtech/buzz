<script setup lang="ts">
import { ErrorMessage, TextInput, useCall } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"
import { userResource } from "@/data/user"

type Profile = { first_name: string; last_name: string; username: string; user_image: string }

const form = reactive<Profile>(savedProfile())
const availability = ref<Availability | null>(null)
const savedUsername = userResource.data?.username

// Email signup stores the whole name as the first name, so it is split at the first space.
function savedProfile(): Profile {
	const user = userResource.data
	const [first = "", ...rest] = (user?.first_name ?? "").split(" ")
	const splitName = !user?.last_name && rest.length
	return {
		first_name: splitName ? first : (user?.first_name ?? ""),
		last_name: splitName ? rest.join(" ") : (user?.last_name ?? ""),
		username: user?.username ?? "",
		user_image: user?.user_image ?? "",
	}
}

const checkUsername = useCall<Availability, { username: string }>({
	url: "/api/v2/method/buzz.api.onboarding.check_username",
	immediate: false,
})
const saveProfile = useCall<null, Profile>({
	url: "/api/v2/method/buzz.api.onboarding.save_profile",
	method: "POST",
	immediate: false,
})

const fullName = computed(() => [form.first_name, form.last_name].filter(Boolean).join(" "))
const usernameReady = computed(
	() => form.username === savedUsername || Boolean(availability.value?.available),
)

defineExpose({
	canContinue: () => Boolean(form.first_name.trim()) && usernameReady.value,
	// Resolves false on failure; the error renders below the form.
	save: async () => {
		await saveProfile.submit({ ...form })
		if (saveProfile.error) return false
		await userResource.reload()
		return true
	},
})
</script>

<template>
	<div class="flex flex-col gap-5">
		<AvatarUploader
			v-model="form.user_image"
			:label="fullName || '?'"
			:title="__('Profile photo')"
			:description="__('Optional. Your initials show until you add one.')"
		/>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<TextInput v-model="form.first_name" :label="__('First name')" required autofocus />
			<TextInput v-model="form.last_name" :label="__('Last name')" />
		</div>

		<div class="flex flex-col gap-1.5">
			<p class="text-xs text-ink-gray-5">{{ __("Username") }}</p>
			<SlugInput
				v-model="form.username"
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
