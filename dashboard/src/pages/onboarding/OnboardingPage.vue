<script setup lang="ts">
import { Button, ErrorMessage, useCall } from "frappe-ui"
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import LoginRequired from "@/components/LoginRequired.vue"
import { session } from "@/data/session"
import { loadUser, userResource } from "@/data/user"
import { resolveLoginRedirect } from "@/utils/loginRedirect"

import ProfileStep from "./ProfileStep.vue"

const route = useRoute()
const router = useRouter()
const ready = ref(false)
const saving = ref(false)
const step = ref<InstanceType<typeof ProfileStep>>()
const user = computed(() => userResource.data)

const completeOnboarding = useCall<null>({
	url: "/api/v2/method/buzz.api.onboarding.complete_onboarding",
	method: "POST",
	immediate: false,
})

// The route is full bleed, so the user is loaded here rather than by the router.
onMounted(async () => {
	await loadUser()
	if (session.isLoggedIn && !user.value?.needs_onboarding) return router.replace("/")
	ready.value = true
})

async function submit() {
	if (!step.value?.canContinue() || saving.value) return
	saving.value = true
	try {
		if (!(await step.value.save())) return
		await completeOnboarding.submit()
		if (completeOnboarding.error) return
		window.location.replace(
			resolveLoginRedirect(route.query["redirect-to"], window.location.origin),
		)
	} finally {
		saving.value = false
	}
}
</script>

<template>
	<LoginRequired v-if="!session.isLoggedIn" />
	<div v-else-if="ready" class="min-h-dvh bg-surface-white">
		<div class="mx-auto flex max-w-md flex-col gap-10 px-4 pb-16 pt-6 sm:pt-[10vh]">
			<header class="flex items-center justify-between">
				<BuzzLogo v-if="!user?.brand || user.brand.is_default" class="h-7 w-9 text-ink-gray-9" />
				<img v-else class="h-6 w-auto" :src="user.brand.logo" alt="" />
				<span class="hidden text-sm text-ink-gray-5 sm:inline">
					{{ user?.email }} ·
					<button type="button" class="hover:text-ink-gray-8" @click="session.logout.submit()">
						{{ __("Log out") }}
					</button>
				</span>
			</header>

			<form class="flex flex-col gap-6" @submit.prevent="submit">
				<header class="flex flex-col gap-1">
					<h1 class="text-xl-semibold text-ink-gray-9">{{ __("Set up your profile") }}</h1>
					<p class="text-base text-ink-gray-5">
						{{ __("This is how hosts and guests see you on Buzz.") }}
					</p>
				</header>
				<ProfileStep ref="step" />
				<ErrorMessage :message="completeOnboarding.error?.message" />
				<div class="flex items-center justify-end border-t border-outline-gray-1 pt-4">
					<Button
						type="submit"
						variant="solid"
						:label="__('Continue')"
						:loading="saving"
						:disabled="!step?.canContinue()"
					/>
				</div>
			</form>
		</div>
	</div>
</template>
