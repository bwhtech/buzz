<script setup lang="ts">
import { Button, ErrorMessage } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute } from "vue-router"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import LoginRequired from "@/components/LoginRequired.vue"
import { session } from "@/data/session"
import { loadUser, userResource } from "@/data/user"
import { resolveLoginRedirect } from "@/utils/loginRedirect"

import CommunityStep from "./CommunityStep.vue"
import DoneStep from "./DoneStep.vue"
import ForkStep from "./ForkStep.vue"
import InviteStep from "./InviteStep.vue"
import OnboardingSkeleton from "./OnboardingSkeleton.vue"
import PreviewPane from "./PreviewPane.vue"
import ProfileStep from "./ProfileStep.vue"
import ProgressDots from "./ProgressDots.vue"
import {
	back,
	currentStep,
	flow,
	invitedTeam,
	loadError,
	loadOnboarding,
	next,
	skip,
} from "./useOnboarding"

type StepHandle = { canContinue: () => boolean; save: () => Promise<boolean> }

const views = {
	profile: ProfileStep,
	fork: ForkStep,
	invite: InviteStep,
	community: CommunityStep,
	done: DoneStep,
}

const route = useRoute()
const ready = ref(false)
const saving = ref(false)
const step = ref<StepHandle>()
const user = computed(() => userResource.data)
const isDone = computed(() => currentStep.value === "done")
// Profile is required, and an invitee already has a place to land, so neither offers Skip.
const canSkip = computed(() => !["profile", "invite", "done"].includes(currentStep.value))

const headings = computed<Record<string, [string, string]>>(() => ({
	profile: [__("Set up your profile"), __("This is how hosts and guests see you on Buzz.")],
	fork: [__("How will you use Buzz?"), __("Pick what fits today. You can change it later.")],
	invite: [
		__("You're on the {0} team", [invitedTeam.value?.team_name ?? ""]),
		__("Continue to open the team in your dashboard."),
	],
	community: [__("Set up your community"), __("A home page for your events and members.")],
}))

// The route is full bleed, so the user is loaded here rather than by the router.
onMounted(async () => {
	const onboarding = session.isLoggedIn ? loadOnboarding() : null
	await loadUser()
	// Signup always passes through here, so with nothing to do it goes straight on.
	if (session.isLoggedIn && !user.value?.needs_onboarding)
		return window.location.replace(
			resolveLoginRedirect(route.query["redirect-to"], window.location.origin),
		)
	await onboarding
	ready.value = true
})

async function submit() {
	if (saving.value || !step.value?.canContinue()) return
	saving.value = true
	try {
		if (await step.value.save()) next()
	} finally {
		saving.value = false
	}
}

// Tracks the content height so the stage can ease between steps. Near-zero readings
// come from the gap between leave and enter, so they are ignored.
const stageInner = ref<HTMLElement>()
const stageHeight = ref<number>()
const observer = new ResizeObserver(([entry]) => {
	const height = (entry.target as HTMLElement).offsetHeight
	if (height > 24) stageHeight.value = height
})
onMounted(() => stageInner.value && observer.observe(stageInner.value))
onBeforeUnmount(() => observer.disconnect())
const stageStyle = computed(() => ({
	"--direction": flow.direction,
	height: stageHeight.value ? `${stageHeight.value}px` : undefined,
}))
</script>

<template>
	<LoginRequired v-if="!session.isLoggedIn" />
	<div v-else class="grid min-h-dvh bg-surface-white lg:grid-cols-2">
		<div class="flex min-w-0 flex-col">
			<header class="flex items-center justify-between px-4 py-5 sm:px-6">
				<!-- Waits for the user so a custom brand logo doesn't replace the Buzz one mid-load. -->
				<span v-if="!user" class="h-7" />
				<BuzzLogo
					v-else-if="!user.brand || user.brand.is_default"
					class="h-7 w-9 text-ink-gray-9"
				/>
				<img v-else class="h-6 w-auto" :src="user.brand.logo" alt="" />
				<span class="text-sm text-ink-gray-5">
					<span class="hidden sm:inline">{{ user?.email }} · </span>
					<button
						type="button"
						class="-my-2 rounded px-1 py-2 hover:text-ink-gray-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-8"
						@click="session.logout.submit()"
					>
						{{ __("Log out") }}
					</button>
				</span>
			</header>

			<main class="mx-auto w-full max-w-md px-4 sm:px-6 pb-32 pt-[6vh] sm:pt-[10vh]">
				<OnboardingSkeleton v-if="!ready" />
				<div v-else-if="loadError" class="flex flex-col items-start gap-3">
					<ErrorMessage :message="loadError" />
					<Button variant="subtle" :label="__('Try again')" @click="loadOnboarding()" />
				</div>
				<form v-else class="flex flex-col gap-6" @submit.prevent="submit">
					<ProgressDots v-if="!isDone" />
					<div class="step-stage -m-2" :style="stageStyle">
						<div ref="stageInner" class="p-2">
							<Transition name="step-slide" mode="out-in">
								<div :key="currentStep" class="flex flex-col gap-6">
									<header v-if="!isDone" class="flex flex-col gap-1">
										<h1 class="text-xl-semibold text-ink-gray-9">{{ headings[currentStep][0] }}</h1>
										<p class="text-base text-ink-gray-5">{{ headings[currentStep][1] }}</p>
									</header>
									<component :is="views[currentStep]" ref="step" />
								</div>
							</Transition>
						</div>
					</div>

					<div v-if="!isDone" class="flex items-center gap-2 border-t border-outline-gray-1 pt-4">
						<Button
							v-if="flow.stepIndex > 0"
							variant="ghost"
							icon-left="lucide-arrow-left"
							:label="__('Back')"
							:disabled="saving"
							@click="back"
						/>
						<div class="ml-auto flex items-center gap-2">
							<Button
								v-if="canSkip"
								variant="ghost"
								:label="__('Skip')"
								:disabled="saving"
								@click="skip"
							/>
							<Button
								type="submit"
								variant="solid"
								:label="__('Continue')"
								:loading="saving"
								:disabled="!step?.canContinue()"
							/>
						</div>
					</div>
				</form>
			</main>
		</div>
		<aside
			class="sticky top-0 hidden h-dvh overflow-hidden border-l border-outline-gray-1 bg-surface-gray-1 lg:block"
			:aria-label="__('Live preview')"
		>
			<PreviewPane v-if="ready" />
		</aside>
	</div>
</template>

<style scoped>
.step-stage {
	overflow: hidden;
	transition: height 280ms cubic-bezier(0.23, 1, 0.32, 1);
}
.step-slide-enter-active {
	transition:
		opacity 220ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.step-slide-leave-active {
	transition:
		opacity 120ms ease-out,
		transform 120ms ease-out;
}
.step-slide-enter-from {
	opacity: 0;
	transform: translateX(calc(var(--direction) * 16px));
}
.step-slide-leave-to {
	opacity: 0;
	transform: translateX(calc(var(--direction) * -8px));
}
@media (prefers-reduced-motion: reduce) {
	.step-stage {
		transition: none;
	}
	.step-slide-enter-from,
	.step-slide-leave-to {
		transform: none;
	}
}
</style>
